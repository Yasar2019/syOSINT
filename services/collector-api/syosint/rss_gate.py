import argparse
from collections.abc import Callable, Sequence
import json
from pathlib import Path
import re
import subprocess
import sys

from .rss_cli import SAFE_LOG_CATEGORIES, _load_sources
from .rss_types import FeedSource


Runner = Callable[..., subprocess.CompletedProcess]
SAFE_SOURCE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MAX_SOURCE_ID_LENGTH = 80


class GateFailure(RuntimeError):
    pass


def _safe_source_id(value: str) -> str:
    if len(value) <= MAX_SOURCE_ID_LENGTH and SAFE_SOURCE_ID.fullmatch(value):
        return value
    return "invalid-source"


def _report(source_id: str, category: str, *, items: int = 0) -> None:
    status = "ok" if category == "none" else "failed"
    print(
        f"source={_safe_source_id(source_id)} status={status} "
        f"category={category} items={items}"
    )


def _item_count(stdout: str | bytes | None) -> int | None:
    try:
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8")
        value = json.loads(stdout or "")
        items = value["entries"]
        if (
            value.get("status") != "ok"
            or not isinstance(items, int)
            or isinstance(items, bool)
            or not 0 <= items <= 1_000_000
        ):
            return None
        return items
    except (KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _failure_category(stdout: str | bytes | None) -> str:
    try:
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8")
        value = json.loads(stdout or "")
        if not isinstance(value, dict) or value.get("status") != "failed":
            return "check-failed"
        category = value.get("category")
        if category not in SAFE_LOG_CATEGORIES | {"parse-failed", "internal-failed"}:
            return "check-failed"
        status = value.get("httpStatus")
        if category == "http-status" and type(status) is int and 400 <= status <= 599:
            return f"http-status-{status}"
        if "httpStatus" in value:
            return "check-failed"
        return category
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return "check-failed"


def check_enabled_sources(
    sources: Sequence[FeedSource],
    *,
    runner: Runner = subprocess.run,
    python: str = sys.executable,
) -> None:
    enabled = tuple(source for source in sources if source.enabled)
    if not enabled:
        _report("config", "no-enabled")
        raise GateFailure("rss gate failed")
    failed = False
    for source in enabled:
        command = [
            python,
            "-m",
            "syosint.rss_cli",
            "check-source",
            "--",
            source.feed_url,
        ]
        try:
            completed = runner(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except subprocess.CalledProcessError:
            _report(source.id, "check-failed")
            failed = True
            continue
        except Exception:
            _report(source.id, "execution-failed")
            failed = True
            continue
        if completed.returncode != 0:
            _report(source.id, _failure_category(completed.stdout))
            failed = True
            continue
        items = _item_count(completed.stdout)
        if items is None:
            _report(source.id, "invalid-result")
            failed = True
            continue
        _report(source.id, "none", items=items)
    if failed:
        raise GateFailure("rss gate failed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m syosint.rss_gate")
    parser.add_argument("--config", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        sources = _load_sources(Path(args.config))
    except Exception:
        _report("config", "config-failed")
        return 1
    try:
        check_enabled_sources(sources)
    except GateFailure:
        return 1
    except Exception:
        _report("config", "internal-failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
