"""Quiet Telegram authentication adapter; no message collection or publication."""

import logging
from collections.abc import Callable
from typing import Protocol

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from .telegram_session import TelegramSettings, session_path


class TelegramAuthClient(Protocol):
    async def is_authorized(self) -> bool: ...

    async def start(
        self,
        phone: str,
        code_callback: Callable[[], str],
        password_callback: Callable[[], str],
    ) -> None: ...

    async def disconnect(self) -> None: ...


class _PrivateLogger(logging.Logger):
    def getChild(self, suffix):
        # SDK descendants must not rejoin Python's global logger hierarchy.
        return self


class TelethonAuthClient:
    """Owned by the terminal CLI; construct after it secures the session path."""

    def __init__(self, settings: TelegramSettings, *, transport=None):
        # A dedicated logger prevents SDK exceptions or identifiers reaching logs.
        logger = _PrivateLogger("syosint.telegram.private", level=logging.CRITICAL + 1)
        logger.disabled = True
        logger.addHandler(logging.NullHandler())
        logger.propagate = False
        self._client = transport if transport is not None else TelegramClient(
            str(session_path(settings)), settings.api_id, settings.api_hash,
            base_logger=logger, receive_updates=False,
        )

    async def is_authorized(self) -> bool:
        await self._client.connect()
        return await self._client.is_user_authorized()

    async def start(
        self,
        phone: str,
        code_callback: Callable[[], str],
        password_callback: Callable[[], str],
    ) -> None:
        await self._client.connect()
        if await self._client.is_user_authorized():
            return
        # Do not use Telethon.start(): it prints the authenticated display name.
        await self._client.send_code_request(phone)
        code = code_callback()
        if not code:
            raise ValueError("empty-code")
        try:
            await self._client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            await self._client.sign_in(password=password_callback())

    async def disconnect(self) -> None:
        await self._client.disconnect()
