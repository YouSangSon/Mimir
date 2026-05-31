import requests
import responses

from mimir.report.telegram import send_ping


def test_send_ping_noop_without_token():
    assert send_ping(bot_token=None, chat_id=None, text="hi") is False


@responses.activate
def test_send_ping_posts_when_configured():
    responses.add(
        responses.POST,
        "https://api.telegram.org/botTOK/sendMessage",
        json={"ok": True},
        status=200,
    )
    sent = send_ping(bot_token="TOK", chat_id="123", text="hi", session=requests.Session())
    assert sent is True
    assert responses.calls[0].request.url.endswith("/botTOK/sendMessage")
