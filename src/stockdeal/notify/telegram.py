"""Telegram bot notifier + interactive command handler.

Outbound: simple sendMessage / sendPhoto via Bot HTTP API.
Inbound (bot commands handled by python-telegram-bot Application):
    /mode <off|sim|confirm|auto>
    /confirm <intent_id>
    /reject  <intent_id>
    /halt
    /status
"""
from __future__ import annotations

import httpx

from stockdeal.config import get_settings


class TelegramNotifier:
    def __init__(self) -> None:
        s = get_settings()
        self._token = s.telegram_bot_token.get_secret_value()
        self._chat_id = s.telegram_chat_id
        self._base = f"https://api.telegram.org/bot{self._token}"

    async def send(self, text: str, parse_mode: str = "Markdown") -> None:
        # TODO: POST /sendMessage with chat_id, text.
        async with httpx.AsyncClient(timeout=10.0) as http:
            await http.post(
                f"{self._base}/sendMessage",
                json={"chat_id": self._chat_id, "text": text, "parse_mode": parse_mode},
            )

    async def send_photo(self, photo_path: str, caption: str = "") -> None:
        # TODO: multipart/form-data upload.
        raise NotImplementedError


# Command handler skeleton — wire to python-telegram-bot Application in api.py.
async def run_bot_commands() -> None:
    # TODO: Application.builder().token(...).build() + add CommandHandlers.
    raise NotImplementedError
