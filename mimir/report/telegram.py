from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

# Telegram rejects messages over 4096 chars; keep a margin.
MAX_MESSAGE = 4000


def send_ping(
    *,
    bot_token: str | None,
    chat_id: str | None,
    text: str,
    session: requests.Session | None = None,
) -> bool:
    if not bot_token or not chat_id:
        return False
    if len(text) > MAX_MESSAGE:
        text = text[: MAX_MESSAGE - 1] + "…"
    session = session or requests.Session()
    try:
        resp = session.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=15,
        )
    except requests.RequestException:
        # Delivery is best-effort: never let a Telegram outage crash the run
        # (and never let the bot-token URL surface in a traceback).
        logger.warning("telegram send failed: network error")
        return False
    if resp.status_code != 200:
        logger.warning("telegram send failed: HTTP %s", resp.status_code)
        return False
    return True
