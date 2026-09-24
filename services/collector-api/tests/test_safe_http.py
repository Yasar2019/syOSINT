from collections import defaultdict

import pytest

from syosint import safe_http
from syosint.safe_http import (
    FeedFetchError,
    ResponseTooLarge,
    SafeFeedClient,
    UnsafeFeedUrl,
)


class FakeResponse:
    def __init__(self, status_code=200, headers=None, chunks=()):
        self.status_code = status_code
        self.headers = headers or {"content-type": "application/rss+xml"}
        self._chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def iter_bytes(self):
        yield from self._chunks


class FakeTransport:
    def __init__(self):
        self.addresses = defaultdict(lambda: ["93.184.216.34"])
        self.responses = {}
        self.resolve_calls = defaultdict(int)
        self.opened = []

    def resolve(self, hostname, deadline):
        del deadline
        index = self.resolve_calls[hostname]
        self.resolve_calls[hostname] += 1
        values = self.addresses[hostname]
        return (values[min(index, len(values) - 1)],)

    def open(self, url, headers, addresses, deadline):
        self.opened.append((url, headers, addresses))
        return self.responses[url]


def test_pins_validated_dns_address_for_connection():
    transport = FakeTransport()
    transport.addresses["feed.example"] = ["93.184.216.34"]
    transport.responses["https://feed.example/rss"] = FakeResponse()

    SafeFeedClient(transport=transport).fetch("https://feed.example/rss")

    assert transport.opened[0][2] == ("93.184.216.34",)


def test_pinned_tls_connection_uses_validated_address_and_hostname(monkeypatch):
    connected = {}

    class Sock:
        def settimeout(self, timeout):
            connected["timeout_set"] = timeout

        def close(self):
            pass

    def create_connection(address, timeout, source_address):
        connected["address"] = address
        return Sock()

    class Context:
        def wrap_socket(self, sock, *, server_hostname):
            connected["server_hostname"] = server_hostname
            return sock

    monkeypatch.setattr(safe_http.socket, "create_connection", create_connection)
    connection = safe_http._PinnedHttpsConnection(
        "feed.example", "93.184.216.34", safe_http.time.monotonic() + 10
    )
    connection._context = Context()

    connection.connect()

    assert connected["address"] == ("93.184.216.34", 443)
    assert connected["server_hostname"] == "feed.example"
    assert connected["timeout_set"] > 0


def test_rejects_encoded_response_before_reading_decompressed_content():
    transport = FakeTransport()
    transport.responses["https://feed.example/rss"] = FakeResponse(
        headers={
            "content-type": "application/rss+xml",
            "content-encoding": "gzip",
        },
        chunks=(b"compressed",),
    )

    with pytest.raises(FeedFetchError, match="unsupported-content-encoding"):
        SafeFeedClient(transport=transport).fetch("https://feed.example/rss")


def test_enforces_total_deadline_while_streaming(monkeypatch):
    transport = FakeTransport()
    transport.responses["https://feed.example/rss"] = FakeResponse(
        chunks=(b"first", b"second")
    )
    clock = iter((0.0, 0.5, 1.1))
    monkeypatch.setattr(safe_http.time, "monotonic", lambda: next(clock))

    with pytest.raises(FeedFetchError, match="timeout"):
        SafeFeedClient(transport=transport, timeout_seconds=1).fetch(
            "https://feed.example/rss"
        )


def test_dns_resolution_obeys_total_deadline(monkeypatch):
    release = safe_http.threading.Event()
    calls = []

    def blocked_lookup(*_args, **_kwargs):
        calls.append(1)
        release.wait()
        return []

    monkeypatch.setattr(safe_http.socket, "getaddrinfo", blocked_lookup)
    resolver = safe_http._BoundedResolver()
    monkeypatch.setattr(safe_http, "_RESOLVER", resolver)
    started = safe_http.time.monotonic()
    try:
        with pytest.raises(FeedFetchError, match="timeout"):
            SafeFeedClient(timeout_seconds=0.05).fetch(
                "https://blocked.example/rss"
            )
        with pytest.raises(FeedFetchError, match="dns-busy"):
            SafeFeedClient(timeout_seconds=0.05).fetch(
                "https://second.example/rss"
            )
        assert len(calls) == 1
    finally:
        release.set()
        resolver._busy.wait(0.1)

    assert safe_http.time.monotonic() - started < 0.25


def test_absolute_deadline_watchdog_closes_blocked_connection(monkeypatch):
    closed = safe_http.threading.Event()

    class BlockedConnection:
        sock = None

        def __init__(self, *_args):
            pass

        def request(self, *_args, **_kwargs):
            closed.wait()

        def getresponse(self):
            raise OSError("closed by deadline")

        def close(self):
            closed.set()

    monkeypatch.setattr(safe_http, "_PinnedHttpsConnection", BlockedConnection)
    transport = safe_http.PinnedHttpsTransport()
    deadline = safe_http.time.monotonic() + 0.05

    with pytest.raises(FeedFetchError, match="timeout"):
        with transport.open(
            "https://feed.example/rss",
            {"accept": "application/rss+xml"},
            ("93.184.216.34",),
            deadline,
        ):
            pass


def test_maps_malformed_http_to_safe_fetch_error():
    class BrokenResponse(FakeResponse):
        def iter_bytes(self):
            raise safe_http.http.client.IncompleteRead(b"partial", 10)
            yield

    transport = FakeTransport()
    transport.responses["https://feed.example/rss"] = BrokenResponse()

    with pytest.raises(FeedFetchError, match="malformed-http"):
        SafeFeedClient(transport=transport).fetch("https://feed.example/rss")


def test_rejects_private_dns_and_unsafe_redirect():
    transport = FakeTransport()
    transport.responses["https://feed.example/rss"] = FakeResponse(
        302, {"location": "https://127.0.0.1/private"}
    )

    with pytest.raises(UnsafeFeedUrl):
        SafeFeedClient(transport=transport).fetch("https://feed.example/rss")


def test_stops_after_decompressed_limit():
    transport = FakeTransport()
    transport.responses["https://feed.example/rss"] = FakeResponse(
        chunks=(b"x" * 700_000, b"y" * 700_000)
    )

    with pytest.raises(ResponseTooLarge):
        SafeFeedClient(transport=transport, max_bytes=1_000_000).fetch(
            "https://feed.example/rss"
        )


def test_rechecks_dns_for_every_redirect_connection():
    transport = FakeTransport()
    transport.addresses["feed.example"] = ["93.184.216.34", "127.0.0.1"]
    transport.responses["https://feed.example/rss"] = FakeResponse(
        302, {"location": "https://feed.example/next"}
    )

    with pytest.raises(UnsafeFeedUrl):
        SafeFeedClient(transport=transport).fetch("https://feed.example/rss")

    assert transport.resolve_calls["feed.example"] == 2


@pytest.mark.parametrize(
    "url",
    [
        "http://feed.example/rss",
        "https://user:pass@feed.example/rss",
        "https://feed.example:444/rss",
        "https://feed.example/rss#fragment",
        "https://8.8.8.8/rss",
    ],
)
def test_rejects_unsafe_url_shapes(url):
    with pytest.raises(UnsafeFeedUrl):
        SafeFeedClient(transport=FakeTransport()).fetch(url)


def test_sends_validators_and_accepts_not_modified():
    from syosint.safe_http import HttpValidators

    transport = FakeTransport()
    transport.responses["https://feed.example/rss"] = FakeResponse(
        304, {"etag": '"v2"'}
    )

    result = SafeFeedClient(transport=transport).fetch(
        "https://feed.example/rss",
        HttpValidators(etag='"v1"', last_modified="Wed, 23 Sep 2026 15:00:00 GMT"),
    )

    assert result.status_code == 304
    assert result.content == b""
    assert transport.opened[0][1] == {
        "accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
        "accept-encoding": "identity",
        "if-none-match": '"v1"',
        "if-modified-since": "Wed, 23 Sep 2026 15:00:00 GMT",
    }
