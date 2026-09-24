import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import tempfile
from typing import Mapping

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from .rss_collect import collect_sources
from .rss_parse import parse_feed
from .rss_public import build_public_wire, public_wire_from_dict
from .rss_types import FeedSource
from .safe_http import FeedFetchError, SafeFeedClient


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
NEWS_WIRE_SCHEMA = REPOSITORY_ROOT / "packages/schemas/src/public-news-wire.schema.json"


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
    unknown = set(value) - (required | {"attribution"})
    missing = required - set(value)
    if unknown or missing:
        raise ValueError("invalid source configuration fields")
    if value["language"] not in {"en", "ar"}:
        raise ValueError("invalid source language")
    return FeedSource(
        id=value["id"],
        label=value["label"],
        feed_url=value["feedUrl"],
        homepage_url=value["homepageUrl"],
        language=value["language"],
        enabled=value["enabled"],
        required_terms=tuple(value["requiredTerms"]),
        attribution=value.get("attribution"),
    )


def _load_sources(path: Path) -> tuple[FeedSource, ...]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if set(value) != {"schemaVersion", "sources"} or value["schemaVersion"] != "1.0.0":
        raise ValueError("invalid source configuration")
    sources = tuple(_source_from_dict(source) for source in value["sources"])
    if len({source.id for source in sources}) != len(sources):
        raise ValueError("source ids must be unique")
    return sources


def _validate_wire(value: Mapping) -> None:
    schema = json.loads(NEWS_WIRE_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    ids = [entry["id"] for entry in value["entries"]]
    if len(ids) != len(set(ids)):
        raise ValueError("news-wire entry ids must be unique")


def _load_previous(url: str | None):
    if not url:
        return None
    try:
        result = SafeFeedClient(
            allowed_content_types=frozenset({"application/json"}), max_bytes=2_000_000
        ).fetch(url)
        value = json.loads(result.content)
        _validate_wire(value)
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


def collect_public(args: argparse.Namespace) -> int:
    now = datetime.now(UTC)
    sources = _load_sources(Path(args.config))
    previous = _load_previous(args.previous_url)
    result = collect_sources(sources, previous, now, SafeFeedClient())
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
