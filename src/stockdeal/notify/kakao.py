"""Kakao 나에게 보내기 (talk_message:send_to_self).

Flow:
- One-time consent: user issues authorization code via Kakao Developers,
  exchange code for access+refresh tokens (refresh stored in .env).
- At runtime: refresh access token automatically when 401.
- Endpoint: POST /v2/api/talk/memo/default/send

Template object example:
    {"object_type": "text", "text": "...",
     "link": {"web_url": "...", "mobile_web_url": "..."}}
"""
from __future__ import annotations

import httpx

from stockdeal.config import get_settings


TOKEN_URL = "https://kauth.kakao.com/oauth/token"
SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"


class KakaoNotifier:
    def __init__(self) -> None:
        s = get_settings()
        self._rest_key = s.kakao_rest_api_key.get_secret_value()
        self._refresh_token = s.kakao_refresh_token.get_secret_value()
        self._access_token: str | None = None

    async def _refresh_access(self) -> None:
        # TODO: POST TOKEN_URL with grant_type=refresh_token; persist new refresh if rotated.
        raise NotImplementedError

    async def send_text(self, text: str, link_url: str | None = None) -> None:
        # TODO: POST SEND_URL with template_object form-encoded JSON.
        raise NotImplementedError
