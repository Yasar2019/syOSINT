from collections.abc import Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import http.client
import ipaddress
import queue
import socket
import ssl
import threading
import time
from typing import ContextManager, Protocol
from urllib.parse import urljoin, urlsplit, urlunsplit

FEED_CONTENT_TYPES = frozenset(
    {
        "application/rss+xml",
        "application/atom+xml",
        "application/xml",
        "text/xml",
    }
)
FEED_ACCEPT = "application/rss+xml, application/atom+xml, application/xml, text/xml"
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


class UnsafeFeedUrl(ValueError):
    pass


class ResponseTooLarge(ValueError):
    pass


class FeedFetchError(RuntimeError):
    def __init__(
        self,
        category: str,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(category)
        self.category = category
        self.status_code = status_code
        self.retry_after = retry_after
        self.retryable = retryable


@dataclass(frozen=True)
class HttpValidators:
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True)
class FetchResult:
    status_code: int
    content: bytes
    validators: HttpValidators | None


class StreamingResponse(Protocol):
    status_code: int
    headers: Mapping[str, str]

    def iter_bytes(self) -> Iterable[bytes]: ...


class FeedTransport(Protocol):
    def resolve(self, hostname: str, deadline: float) -> tuple[str, ...]: ...

    def open(
        self,
        url: str,
        headers: Mapping[str, str],
        addresses: tuple[str, ...],
        deadline: float,
    ) -> ContextManager[StreamingResponse]: ...


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise FeedFetchError("timeout", retryable=True)
    return remaining


class _PinnedHttpsConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, address: str, deadline: float) -> None:
        super().__init__(
            hostname,
            port=443,
            timeout=_remaining(deadline),
            context=ssl.create_default_context(),
        )
        self._pinned_address = address
        self._deadline = deadline

    def connect(self) -> None:
        sock = socket.create_connection(
            (self._pinned_address, self.port),
            _remaining(self._deadline),
            self.source_address,
        )
        try:
            sock.settimeout(_remaining(self._deadline))
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


class _HttpResponse:
    def __init__(
        self,
        response: http.client.HTTPResponse,
        connection: _PinnedHttpsConnection,
        deadline: float,
    ) -> None:
        self.status_code = response.status
        self.headers = {key: value for key, value in response.getheaders()}
        self._response = response
        self._connection = connection
        self._deadline = deadline

    def iter_bytes(self) -> Iterable[bytes]:
        while True:
            if self._connection.sock is not None:
                self._connection.sock.settimeout(_remaining(self._deadline))
            chunk = self._response.read(64 * 1024)
            if not chunk:
                return
            yield chunk


class _BoundedResolver:
    def __init__(self) -> None:
        self._requests: queue.Queue = queue.Queue(maxsize=1)
        self._busy = threading.Event()
        self._submit_lock = threading.Lock()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        while True:
            hostname, results = self._requests.get()
            self._busy.set()
            try:
                try:
                    value = socket.getaddrinfo(
                        hostname, 443, type=socket.SOCK_STREAM
                    )
                except BaseException as error:
                    value = error
                results.put_nowait(value)
            finally:
                self._busy.clear()
                self._requests.task_done()

    def resolve(
        self,
        hostname: str,
        deadline: float,
        cancelled: threading.Event,
    ) -> tuple[str, ...]:
        results: queue.Queue = queue.Queue(maxsize=1)
        with self._submit_lock:
            if self._busy.is_set() or not self._requests.empty():
                raise FeedFetchError("dns-busy")
            self._requests.put_nowait((hostname, results))
        while True:
            if cancelled.is_set():
                raise FeedFetchError("cancelled")
            try:
                records = results.get(timeout=min(_remaining(deadline), 0.05))
                break
            except queue.Empty:
                continue
        if isinstance(records, BaseException):
            raise FeedFetchError("dns-failure", retryable=True) from records
        return tuple(dict.fromkeys(record[4][0] for record in records))


_RESOLVER = _BoundedResolver()


class PinnedHttpsTransport:
    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout_seconds = timeout_seconds
        self._active: set[_PinnedHttpsConnection] = set()
        self._lock = threading.Lock()
        self._closed = threading.Event()

    def resolve(self, hostname: str, deadline: float) -> tuple[str, ...]:
        return _RESOLVER.resolve(hostname, deadline, self._closed)

    @contextmanager
    def open(
        self,
        url: str,
        headers: Mapping[str, str],
        addresses: tuple[str, ...],
        deadline: float,
    ):
        parts = urlsplit(url)
        target = urlunsplit(("", "", parts.path or "/", parts.query, ""))
        connection = None
        connection_timer = None
        response = None
        last_error = None
        for address in addresses:
            if self._closed.is_set():
                raise FeedFetchError("cancelled")
            candidate = _PinnedHttpsConnection(
                parts.hostname or "", address, deadline
            )
            timer = threading.Timer(_remaining(deadline), candidate.close)
            timer.daemon = True
            timer.start()
            try:
                with self._lock:
                    self._active.add(candidate)
                if self._closed.is_set():
                    candidate.close()
                    raise FeedFetchError("cancelled")
                candidate.request(
                    "GET",
                    target,
                    headers={
                        "user-agent": "syOSINT-feed-collector/1.0",
                        **headers,
                    },
                )
                if candidate.sock is not None:
                    candidate.sock.settimeout(_remaining(deadline))
                response = candidate.getresponse()
                connection = candidate
                connection_timer = timer
                break
            except FeedFetchError:
                timer.cancel()
                candidate.close()
                with self._lock:
                    self._active.discard(candidate)
                raise
            except http.client.HTTPException as error:
                timer.cancel()
                candidate.close()
                with self._lock:
                    self._active.discard(candidate)
                category = (
                    "timeout" if time.monotonic() >= deadline else "malformed-http"
                )
                raise FeedFetchError(
                    category, retryable=category == "timeout"
                ) from error
            except OSError as error:
                timer.cancel()
                candidate.close()
                with self._lock:
                    self._active.discard(candidate)
                if time.monotonic() >= deadline:
                    raise FeedFetchError("timeout", retryable=True) from error
                last_error = error
        if response is None or connection is None:
            raise FeedFetchError("network-error", retryable=True) from last_error
        try:
            yield _HttpResponse(response, connection, deadline)
        finally:
            if connection_timer is not None:
                connection_timer.cancel()
            connection.close()
            with self._lock:
                self._active.discard(connection)

    def close(self) -> None:
        self._closed.set()
        with self._lock:
            active = tuple(self._active)
        for connection in active:
            connection.close()


def _header(headers: Mapping[str, str], name: str) -> str | None:
    wanted = name.casefold()
    return next(
        (value for key, value in headers.items() if key.casefold() == wanted), None
    )


def _retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return max(0.0, (parsed - datetime.now(UTC)).total_seconds())


class SafeFeedClient:
    def __init__(
        self,
        transport: FeedTransport | None = None,
        *,
        max_bytes: int = 1_000_000,
        max_redirects: int = 5,
        allowed_content_types: frozenset[str] = FEED_CONTENT_TYPES,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._transport = transport or PinnedHttpsTransport(timeout_seconds)
        self._max_bytes = max_bytes
        self._max_redirects = max_redirects
        self._allowed_content_types = allowed_content_types
        self._timeout_seconds = timeout_seconds
        self._closed = threading.Event()

    def close(self) -> None:
        self._closed.set()
        close = getattr(self._transport, "close", None)
        if close is not None:
            close()

    def _validate_connection(
        self, url: str, deadline: float
    ) -> tuple[str, ...]:
        parts = urlsplit(url)
        if parts.scheme != "https":
            raise UnsafeFeedUrl("feed URLs must use HTTPS")
        if not parts.hostname:
            raise UnsafeFeedUrl("feed URL must include a host")
        if parts.username is not None or parts.password is not None:
            raise UnsafeFeedUrl("feed URL credentials are not allowed")
        try:
            port = parts.port
        except ValueError as error:
            raise UnsafeFeedUrl("invalid feed URL port") from error
        if port not in (None, 443):
            raise UnsafeFeedUrl("feed URLs may only use port 443")
        if parts.fragment:
            raise UnsafeFeedUrl("feed URL fragments are not allowed")

        try:
            ipaddress.ip_address(parts.hostname)
        except ValueError:
            addresses = self._transport.resolve(parts.hostname, deadline)
        else:
            raise UnsafeFeedUrl("feed URL IP literals are not allowed")
        if not addresses:
            raise UnsafeFeedUrl("feed host did not resolve")
        for address in addresses:
            try:
                parsed = ipaddress.ip_address(address)
            except ValueError as error:
                raise UnsafeFeedUrl("feed host returned an invalid address") from error
            if not parsed.is_global:
                raise UnsafeFeedUrl("feed host resolves to a non-public address")
        return addresses

    def fetch(
        self, url: str, validators: HttpValidators | None = None
    ) -> FetchResult:
        headers = {
            "accept": FEED_ACCEPT
            if self._allowed_content_types == FEED_CONTENT_TYPES
            else ", ".join(sorted(self._allowed_content_types)),
            "accept-encoding": "identity",
        }
        if validators and validators.etag:
            headers["if-none-match"] = validators.etag
        if validators and validators.last_modified:
            headers["if-modified-since"] = validators.last_modified

        current_url = url
        deadline = time.monotonic() + self._timeout_seconds
        for redirect_count in range(self._max_redirects + 1):
            if self._closed.is_set():
                raise FeedFetchError("cancelled")
            _remaining(deadline)
            addresses = self._validate_connection(current_url, deadline)
            try:
                response_context = self._transport.open(
                    current_url, headers, addresses, deadline
                )
                with response_context as response:
                    if response.status_code in REDIRECT_STATUSES:
                        location = _header(response.headers, "location")
                        if not location:
                            raise FeedFetchError(
                                "redirect-without-location",
                                status_code=response.status_code,
                            )
                        if redirect_count >= self._max_redirects:
                            raise FeedFetchError("too-many-redirects")
                        current_url = urljoin(current_url, location)
                        continue

                    result_validators = HttpValidators(
                        etag=_header(response.headers, "etag"),
                        last_modified=_header(response.headers, "last-modified"),
                    )
                    if response.status_code == 304:
                        return FetchResult(304, b"", result_validators)
                    if response.status_code < 200 or response.status_code >= 300:
                        retryable = response.status_code in {408, 425, 429} or (
                            response.status_code >= 500
                        )
                        raise FeedFetchError(
                            "http-status",
                            status_code=response.status_code,
                            retry_after=_retry_after(
                                _header(response.headers, "retry-after")
                            ),
                            retryable=retryable,
                        )

                    content_type = (
                        _header(response.headers, "content-type") or ""
                    ).split(";", 1)[0].strip().casefold()
                    if content_type not in self._allowed_content_types:
                        raise FeedFetchError("unsupported-content-type")
                    content_encoding = (
                        _header(response.headers, "content-encoding") or "identity"
                    ).strip().casefold()
                    if content_encoding != "identity":
                        raise FeedFetchError("unsupported-content-encoding")
                    content_length = _header(response.headers, "content-length")
                    if content_length and int(content_length) > self._max_bytes:
                        raise ResponseTooLarge("response exceeds limit")

                    buffer = bytearray()
                    for chunk in response.iter_bytes():
                        _remaining(deadline)
                        if len(buffer) + len(chunk) > self._max_bytes:
                            raise ResponseTooLarge("decoded response exceeds limit")
                        buffer.extend(chunk)
                    return FetchResult(200, bytes(buffer), result_validators)
            except socket.timeout as error:
                if self._closed.is_set():
                    raise FeedFetchError("cancelled") from error
                raise FeedFetchError("timeout", retryable=True) from error
            except http.client.HTTPException as error:
                if self._closed.is_set():
                    raise FeedFetchError("cancelled") from error
                raise FeedFetchError("malformed-http") from error
            except OSError as error:
                if self._closed.is_set():
                    raise FeedFetchError("cancelled") from error
                raise FeedFetchError("network-error", retryable=True) from error

        raise FeedFetchError("too-many-redirects")
