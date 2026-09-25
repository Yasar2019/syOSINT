from datetime import datetime
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import unicodedata


TRACKING_KEYS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "gclid",
        "fbclid",
    }
)


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    hostname = (parts.hostname or "").lower()
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"

    userinfo = ""
    if parts.username is not None:
        userinfo = parts.username
        if parts.password is not None:
            userinfo += f":{parts.password}"
        userinfo += "@"

    port = parts.port
    if (parts.scheme.lower(), port) in {("http", 80), ("https", 443)}:
        port = None
    netloc = f"{userinfo}{hostname}{f':{port}' if port is not None else ''}"
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key.casefold() not in TRACKING_KEYS
        ],
        doseq=True,
    )
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", query, ""))


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def matches_topic(headline: str, required_terms: tuple[str, ...]) -> bool:
    normalized_headline = normalize_text(headline)
    return any(normalize_text(term) in normalized_headline for term in required_terms)


def fingerprint_item(
    source_id: str,
    native_id: str | None,
    url: str,
    headline: str,
    published_at: datetime | None,
) -> str:
    if native_id and native_id.strip():
        identity = f"native\0{native_id.strip()}"
    elif url and url.strip():
        identity = f"url\0{canonicalize_url(url)}"
    else:
        timestamp = published_at.isoformat() if published_at is not None else ""
        identity = f"content\0{normalize_text(headline).strip()}\0{timestamp}"
    return sha256(f"{source_id}\0{identity}".encode()).hexdigest()
