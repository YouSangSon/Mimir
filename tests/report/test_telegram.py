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


@responses.activate
def test_send_ping_returns_false_on_non_200():
    responses.add(
        responses.POST, "https://api.telegram.org/botTOK/sendMessage", json={}, status=403
    )
    assert send_ping(bot_token="TOK", chat_id="123", text="hi", session=requests.Session()) is False


@responses.activate
def test_send_ping_returns_false_on_network_error():
    # A Telegram outage must never crash the run (and never surface the token URL).
    responses.add(
        responses.POST,
        "https://api.telegram.org/botTOK/sendMessage",
        body=requests.exceptions.ConnectionError("boom"),
    )
    assert send_ping(bot_token="TOK", chat_id="123", text="hi", session=requests.Session()) is False
