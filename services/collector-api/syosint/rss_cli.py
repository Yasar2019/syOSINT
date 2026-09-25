import argparse
from datetime import UTC, datetime
import ipaddress
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Mapping
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from .rss_collect import collect_sources
from .rss_parse import parse_feed
from .rss_public import build_public_wire, public_wire_from_dict
from .rss_types import FeedSource
from .safe_http import FeedFetchError, SafeFeedClient


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
NEWS_WIRE_SCHEMA = REPOSITORY_ROOT / "packages/schemas/src/public-news-wire.schema.json"
LEGACY_NEWS_WIRE_SCHEMA = (
    REPOSITORY_ROOT / "packages/schemas/src/public-news-wire-legacy.schema.json"
)
SAFE_LOG_CATEGORIES = frozenset(
    {
        "cancelled",
        "dns-busy",
        "dns-failure",
        "http-status",
        "malformed-http",
        "network-error",
        "other",
        "redirect-without-location",
        "responsetoolarge",
        "timeout",
        "too-many-redirects",
        "unsupported-content-encoding",
        "unsupported-content-type",
        "unsafefeedurl",
        "valueerror",
    }
)
SAFE_SOURCE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MAX_LOG_SOURCE_ID_LENGTH = 80


def _validated_terms(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(
        not isinstance(term, str) or not term.strip() for term in value
    ):
        raise ValueError(f"invalid {field}")
    return tuple(value)


def _validated_public_url(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("-")
        or any(character.isspace() for character in value)
    ):
        raise ValueError(f"invalid {field}")
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as error:
        raise ValueError(f"invalid {field}") from error
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or port not in (None, 443)
        or parts.fragment
    ):
        raise ValueError(f"invalid {field}")
    labels = parts.hostname.split(".")
    if any(
        not label
        or label.startswith("-")
        or label.endswith("-")
        or any(not (character.isalnum() or character == "-") for character in label)
        for label in labels
    ):
        raise ValueError(f"invalid {field}")
    try:
        ipaddress.ip_address(parts.hostname)
    except ValueError:
        return value
    raise ValueError(f"invalid {field}")


def _source_from_dict(value: Mapping) -> FeedSource:
    required = {
        "id",
        "label",
        "feedUrl",
        "homepageUrl",
        "language",
        "enabled",
        "requiredTerms",
    }
    unknown = set(value) - (
        required | {"attribution", "attributionUrl", "topicMode", "excludedTerms"}
    )
    missing = required - set(value)
    if unknown or missing:
        raise ValueError("invalid source configuration fields")
    if value["language"] not in {"en", "ar"}:
        raise ValueError("invalid source language")
    topic_mode = value.get("topicMode", "keyword-filtered")
    if topic_mode not in ("syria-only", "keyword-filtered"):
        raise ValueError("invalid topicMode")
    required_terms = _validated_terms(value["requiredTerms"], "requiredTerms")
    excluded_terms = _validated_terms(value.get("excludedTerms", []), "excludedTerms")
    if topic_mode == "keyword-filtered" and not required_terms:
        raise ValueError("keyword-filtered sources require requiredTerms")
    feed_url = _validated_public_url(value["feedUrl"], "feedUrl")
    homepage_url = _validated_public_url(value["homepageUrl"], "homepageUrl")
    attribution = value.get("attribution")
    attribution_url = value.get("attributionUrl")
    if value["enabled"]:
        if not isinstance(attribution, str) or not attribution.strip():
            raise ValueError("enabled sources require attribution")
        if attribution_url is None:
            raise ValueError("enabled sources require attributionUrl")
    if attribution is not None and (
        not isinstance(attribution, str) or not attribution.strip()
    ):
        raise ValueError("invalid attribution")
    if attribution_url is not None:
        attribution_url = _validated_public_url(attribution_url, "attributionUrl")
    return FeedSource(
        id=value["id"],
        label=value["label"],
        feed_url=feed_url,
        homepage_url=homepage_url,
        language=value["language"],
        enabled=value["enabled"],
        required_terms=required_terms,
        topic_mode=topic_mode,
        excluded_terms=excluded_terms,
        attribution=attribution,
        attribution_url=attribution_url,
    )


def _load_sources(path: Path) -> tuple[FeedSource, ...]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if set(value) != {"schemaVersion", "sources"} or value["schemaVersion"] != "1.0.0":
        raise ValueError("invalid source configuration")
    sources = tuple(_source_from_dict(source) for source in value["sources"])
    if len({source.id for source in sources}) != len(sources):
        raise ValueError("source ids must be unique")
    return sources


def _validate_wire(value: Mapping, schema_path: Path = NEWS_WIRE_SCHEMA) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    ids = [entry["id"] for entry in value["entries"]]
    if len(ids) != len(set(ids)):
        raise ValueError("news-wire entry ids must be unique")
    if schema_path == NEWS_WIRE_SCHEMA:
        source_ids = [state["id"] for state in value["sourceStates"]]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("news-wire source-state ids must be unique")
        if any(entry["sourceId"] not in source_ids for entry in value["entries"]):
            raise ValueError(
                "news-wire entries must reference an attributed source state"
            )


def _load_previous(url: str | None):
    if not url:
        return None
    try:
        result = SafeFeedClient(
            allowed_content_types=frozenset({"application/json"}), max_bytes=2_000_000
        ).fetch(url)
        value = json.loads(result.content)
        if not isinstance(value, dict):
            return None
        if value.get("schemaVersion") == "1.0.0":
            _validate_wire(value, LEGACY_NEWS_WIRE_SCHEMA)
        elif value.get("schemaVersion") == "1.1.0":
            _validate_wire(value)
        else:
            return None
        return public_wire_from_dict(value)
    except (FeedFetchError, json.JSONDecodeError, ValidationError, ValueError):
        return None


def _write_atomic(path: Path, value: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _report_collection(result) -> None:
    for outcome in result.outcomes:
        source_id = (
            outcome.source_id
            if len(outcome.source_id) <= MAX_LOG_SOURCE_ID_LENGTH
            and SAFE_SOURCE_ID.fullmatch(outcome.source_id)
            else "invalid-source"
        )
        status = (
            outcome.status
            if outcome.status in {"healthy", "not-modified", "delayed"}
            else "unknown"
        )
        category = outcome.error_category or "none"
        if category not in SAFE_LOG_CATEGORIES and category != "none":
            category = "other"
        print(
            f"source={source_id} status={status} "
            f"category={category} items={len(outcome.items)}"
        )

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        healthy = sum(
            outcome.status in {"healthy", "not-modified"}
            for outcome in result.outcomes
        )
        delayed = sum(
            outcome.status == "delayed" for outcome in result.outcomes
        )
        items = sum(len(outcome.items) for outcome in result.outcomes)
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write(
                "### RSS collection\n\n"
                f"- Configured: {len(result.sources)}\n"
                f"- Healthy: {healthy}\n"
                f"- Delayed: {delayed}\n"
                f"- Items: {items}\n"
            )


def collect_public(args: argparse.Namespace) -> int:
    now = datetime.now(UTC)
    sources = _load_sources(Path(args.config))
    previous = _load_previous(args.previous_url)
    result = collect_sources(sources, previous, now, SafeFeedClient())
    _report_collection(result)
    if not result.outcomes or all(
        outcome.status == "delayed" for outcome in result.outcomes
    ):
        raise RuntimeError("every enabled RSS source is delayed; refusing deployment")
    wire = build_public_wire(result, previous, now)
    _validate_wire(wire)
    _write_atomic(Path(args.output), wire)
    return 0


def check_source(args: argparse.Namespace) -> int:
    now = datetime.now(UTC)
    fetched = SafeFeedClient().fetch(args.url)
    source = FeedSource(
        "check",
        {"en": "Check", "ar": "فحص"},
        args.url,
        args.url,
        "en",
        True,
        ("",),
    )
    parsed = parse_feed(source, fetched.content, now)
    print(
        json.dumps(
            {
                "status": "ok",
                "bytes": len(fetched.content),
                "entries": len(parsed.items),
                "quarantined": len(parsed.quarantined),
            }
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m syosint.rss_cli")
    commands = parser.add_subparsers(required=True)
    collect = commands.add_parser("collect-public")
    collect.add_argument("--config", required=True)
    collect.add_argument("--output", required=True)
    collect.add_argument("--previous-url")
    collect.set_defaults(handler=collect_public)
    check = commands.add_parser("check-source")
    check.add_argument("url")
    check.set_defaults(handler=check_source)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
