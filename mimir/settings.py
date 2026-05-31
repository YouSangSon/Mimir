from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import BaseModel

DEFAULT_SEC_UA = "Mimir/0.1 (set MIMIR_SEC_USER_AGENT to your contact email)"


class Settings(BaseModel):
    stooq_api_key: str | None = None
    dart_api_key: str | None = None
    fred_api_key: str | None = None
    ecos_api_key: str | None = None
    sec_user_agent: str = DEFAULT_SEC_UA
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = env if env is not None else os.environ
        return cls(
            stooq_api_key=env.get("STOOQ_API_KEY"),
            dart_api_key=env.get("DART_API_KEY"),
            fred_api_key=env.get("FRED_API_KEY"),
            ecos_api_key=env.get("ECOS_API_KEY"),
            sec_user_agent=env.get("MIMIR_SEC_USER_AGENT", DEFAULT_SEC_UA),
            telegram_bot_token=env.get("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=env.get("TELEGRAM_CHAT_ID"),
        )
