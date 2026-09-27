"""Fail-closed staging of individually approved, sanitized Telegram leads."""
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA = Path(__file__).resolve().parents[3] / "packages/schemas/src/public-telegram-wire.schema.json"
USERNAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")
PUBLIC_URL = re.compile(r"^https://t[.]me/([A-Za-z][A-Za-z0-9_]{4,31})/([1-9][0-9]*)$")


class PublicSchemaError(ValueError):
    pass


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _stamp(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")


def validate_public_telegram_wire(value: object) -> dict:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not Draft202012Validator(
        schema, format_checker=FormatChecker(),
    ).is_valid(value):
        raise PublicSchemaError("invalid public Telegram wire")
    seen = set()
    for entry in value["entries"]:
        if entry["id"] in seen:
            raise PublicSchemaError("duplicate public Telegram identifier")
        seen.add(entry["id"])
        match = PUBLIC_URL.fullmatch(entry["url"])
        if not match or urlsplit(entry["url"]).hostname != "t.me":
            raise PublicSchemaError("invalid public Telegram URL")
        if (entry["channel"]["username"].casefold() != match.group(1).casefold()
                or entry["id"].split(":")[-1] != match.group(2)):
            raise PublicSchemaError("channel identity does not match public link")
        if not all(str(text).strip() for text in (
            entry["channel"]["name"], *entry["headline"].values(),
        )):
            raise PublicSchemaError("empty public Telegram headline")
        revisions = entry["revisions"]
        if ((entry["status"] == "active" and revisions) or
                (entry["status"] != "active" and
                 (not revisions or revisions[-1]["action"] != entry["status"]))):
            raise PublicSchemaError("invalid public Telegram revision state")
        previous = datetime.fromisoformat(entry["approvedAt"].replace("Z", "+00:00"))
        for revision in revisions:
            at = datetime.fromisoformat(revision["revisedAt"].replace("Z", "+00:00"))
            if (at <= previous or not all(text.strip() for text in revision["reason"].values())
                    or (revision["action"] == "corrected" and
                        ("previousHeadline" not in revision or not all(
                            text.strip() for text in revision["previousHeadline"].values())))
                    or (revision["action"] == "withdrawn" and "previousHeadline" in revision)):
                raise PublicSchemaError("invalid public Telegram revision")
            previous = at
    return value


def _read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
        raise PublicSchemaError("public Telegram artifact unavailable")
    try:
        return validate_public_telegram_wire(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise PublicSchemaError("invalid public Telegram artifact") from exc


def _atomic_write(path: Path, value: dict, *, private: bool) -> Path:
    if path.is_symlink() or path.parent.is_symlink():
        raise PublicSchemaError("unsafe public Telegram artifact path")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700 if private else 0o755)
    if private:
        path.parent.chmod(0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".telegram-pending-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600 if private else 0o644)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        return path
    finally:
        Path(temporary).unlink(missing_ok=True)


def write_pending_telegram_export(directory: Path, records: list[dict],
                                  at: datetime | None = None) -> Path:
    stamp = _stamp(at or datetime.now(UTC))
    value = validate_public_telegram_wire({
        "schemaVersion": "1.0.0", "generatedAt": stamp,
        "lastEditorialUpdateAt": stamp, "entries": records,
    })
    return _atomic_write(directory / "telegram-pending.v1.json", value, private=True)


def _merge_record(current: dict, incoming: dict) -> dict:
    if current == incoming:
        return current
    if any(current[key] != incoming[key] for key in
           ("id", "channel", "url", "publishedAt", "approvedAt")):
        raise PublicSchemaError("public Telegram identity changed")
    old_revisions, new_revisions = current["revisions"], incoming["revisions"]
    if len(new_revisions) <= len(old_revisions) or new_revisions[:len(old_revisions)] != old_revisions:
        raise PublicSchemaError("public Telegram history cannot be rewritten")
    first = new_revisions[len(old_revisions)]
    if first["action"] == "corrected" and first["previousHeadline"] != current["headline"]:
        raise PublicSchemaError("public Telegram correction must retain previous headline")
    if current["status"] == "withdrawn":
        raise PublicSchemaError("withdrawn Telegram history cannot be resumed")
    return incoming


def stage_telegram_wire(pending: Path, current: Path, output: Path,
                        at: datetime | None = None) -> Path:
    if current.resolve() == output.resolve() and current.is_symlink():
        raise PublicSchemaError("unsafe public Telegram target")
    before = _read(current)
    proposed = _read(pending)
    result = {entry["id"]: entry for entry in before["entries"]}
    for entry in proposed["entries"]:
        result[entry["id"]] = (_merge_record(result[entry["id"]], entry)
                               if entry["id"] in result else entry)
    checked_at = _utc(at or datetime.now(UTC))
    cutoff = checked_at - timedelta(days=7)
    entries = [entry for entry in result.values() if _utc(datetime.fromisoformat(
        entry["publishedAt"].replace("Z", "+00:00"))) >= cutoff]
    entries.sort(key=lambda entry: (entry["publishedAt"], entry["id"]), reverse=True)
    value = validate_public_telegram_wire({
        "schemaVersion": "1.0.0", "generatedAt": _stamp(checked_at),
        "lastEditorialUpdateAt": max(
            before["lastEditorialUpdateAt"], proposed["lastEditorialUpdateAt"]),
        "entries": entries,
    })
    return _atomic_write(output, value, private=False)
