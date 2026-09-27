"""Local Telegram settings and conservative, offline session state."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class TelegramSettings:
    api_id: int | None
    api_hash: str | None
    private_dir: Path

    @property
    def configured(self) -> bool:
        return self.api_id is not None and bool(self.api_hash)

    @classmethod
    def load(cls, private_dir: Path | None = None) -> "TelegramSettings":
        raw_id = os.environ.get("SYOSINT_TELEGRAM_API_ID", "").strip()
        if raw_id:
            try:
                api_id = int(raw_id)
            except ValueError:
                raise ValueError("SYOSINT_TELEGRAM_API_ID must be a positive integer") from None
            if api_id <= 0:
                raise ValueError("SYOSINT_TELEGRAM_API_ID must be a positive integer")
        else:
            api_id = None

        api_hash = os.environ.get("SYOSINT_TELEGRAM_API_HASH", "").strip() or None
        default_dir = Path(__file__).resolve().parents[3] / "private-data"
        local_dir = private_dir or Path(
            os.environ.get("SYOSINT_PRIVATE_DIR") or default_dir
        )
        return cls(api_id=api_id, api_hash=api_hash, private_dir=local_dir)


def session_path(settings: TelegramSettings) -> Path:
    """Return the local session path, rejecting symlink escapes."""
    path = settings.private_dir / "telegram" / "syosint.session"
    if not path.resolve().is_relative_to(settings.private_dir.resolve()):
        raise ValueError("Telegram session path outside private directory")
    return path


def safe_auth_state(
    settings: TelegramSettings,
) -> Literal["not-configured", "reauthentication-required"]:
    """Never assert authentication without a live Telegram authorization check."""
    return "reauthentication-required" if settings.configured else "not-configured"
