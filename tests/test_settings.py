from mimir.settings import Settings


def test_settings_reads_env():
    env = {"DART_API_KEY": "abc", "MIMIR_SEC_USER_AGENT": "Me me@example.com"}
    s = Settings.from_env(env)
    assert s.dart_api_key == "abc"
    assert s.sec_user_agent == "Me me@example.com"
    assert s.telegram_bot_token is None


def test_settings_defaults_sec_user_agent():
    s = Settings.from_env({})
    assert "Mimir" in s.sec_user_agent
