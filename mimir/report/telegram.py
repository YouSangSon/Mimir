from __future__ import annotations

import requests


def send_ping(
    *,
    bot_token: str | None,
    chat_id: str | None,
    text: str,
    session: requests.Session | None = None,
) -> bool:
    if not bot_token or not chat_id:
        return False
    session = session or requests.Session()
    resp = session.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data={"chat_id": chat_id, "text": text},
        timeout=15,
    )
    return resp.status_code == 200
