"""Terminal-only authentication. Never accept secrets in command arguments."""

import asyncio
import getpass
import os
from pathlib import Path
import stat
import sys
import warnings

from .telegram_client import TelegramAuthClient, TelethonAuthClient
from .telegram_session import TelegramSettings, session_path


class TerminalPrompts:
    def is_interactive(self) -> bool:
        return sys.stdin.isatty() and sys.stderr.isatty()

    def secret(self, label: str) -> str:
        # getpass must fail closed instead of falling back to echoed input.
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            return getpass.getpass(label)

    def confirm_logout(self) -> bool:
        print("Remove this local Telegram session? Type yes: ", end="", file=sys.stderr, flush=True)
        return input().strip().lower() == "yes"


def _session_files(settings: TelegramSettings) -> tuple[Path, ...]:
    """Validate the entire exact deletion/permission set before touching any file."""
    path = session_path(settings)
    root = settings.private_dir.resolve()
    if settings.private_dir.is_symlink() or path.parent.is_symlink():
        raise ValueError("unsafe-session")
    if not path.parent.resolve().is_relative_to(root):
        raise ValueError("unsafe-session")
    files = tuple(Path(str(path) + suffix) for suffix in ("", "-journal", "-wal", "-shm"))
    for candidate in files:
        if candidate.is_symlink() or not candidate.resolve().is_relative_to(path.parent.resolve()):
            raise ValueError("unsafe-session")
        if candidate.exists():
            info = candidate.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError("unsafe-session")
    return files


def _secure_files(settings: TelegramSettings) -> None:
    for path in _session_files(settings):
        if path.exists():
            path.chmod(0o600)


def _prepare_session(settings: TelegramSettings) -> None:
    files = _session_files(settings)
    settings.private_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    files[0].parent.mkdir(mode=0o700, exist_ok=True)
    files[0].parent.chmod(0o700)
    # Precreate before SQLite opens it, including under a permissive shell umask.
    fd = os.open(files[0], os.O_CREAT | os.O_APPEND | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    os.close(fd)
    _secure_files(settings)


async def _authenticate(command: str, settings: TelegramSettings, client: TelegramAuthClient | None, prompts) -> bool:
    active = client
    try:
        if active is None:
            active = TelethonAuthClient(settings)
        authorized = await active.is_authorized()
        if command == "login" and not authorized:
            phone = prompts.secret("Phone: ")
            if not phone or ":" in phone:
                raise ValueError("invalid-phone")
            await active.start(
                phone,
                lambda: prompts.secret("Code: "),
                lambda: prompts.secret("Two-factor password: "),
            )
            authorized = await active.is_authorized()
        return authorized
    finally:
        if active is not None:
            await active.disconnect()


def run_cli(argv=None, *, settings: TelegramSettings | None = None, client: TelegramAuthClient | None = None, prompts=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1 or args[0] not in {"login", "status", "logout"}:
        print("invalid-command")
        return 2
    command = args[0]
    prompts = prompts if prompts is not None else TerminalPrompts()
    try:
        settings = settings if settings is not None else TelegramSettings.load()
    except (ValueError, OSError):
        print("not-configured")
        return 1
    if command != "status" and not prompts.is_interactive():
        print("interactive-required")
        return 1
    if command != "logout" and not settings.configured:
        print("not-configured")
        return 1
    try:
        _session_files(settings)
        if command == "logout":
            if not prompts.confirm_logout():
                print("cancelled")
                return 1
            # Local logout only: no network login or server-side revocation.
            for path in _session_files(settings):
                path.unlink(missing_ok=True)
            print("logged-out")
            return 0
        _prepare_session(settings)
    except (OSError, ValueError):
        print("session-unavailable")
        return 1
    except (EOFError, KeyboardInterrupt):
        print("cancelled")
        return 1
    previous_umask = os.umask(0o077)
    try:
        try:
            authorized = asyncio.run(_authenticate(command, settings, client, prompts))
        finally:
            _secure_files(settings)
    except (Exception, KeyboardInterrupt):
        # Never print SDK exception details, tracebacks, session paths or inputs.
        authorized = False
    finally:
        os.umask(previous_umask)
    print("authenticated" if authorized else "reauthentication-required")
    return 0 if authorized else 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
