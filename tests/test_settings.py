from pathlib import Path

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


def test_settings_auto_loads_dotenv(tmp_path: Path, monkeypatch):
    # With env=None, a local .env in the working dir is auto-loaded.
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DART_API_KEY=fromdotenv\n", encoding="utf-8")
    monkeypatch.delenv("DART_API_KEY", raising=False)
    assert Settings.from_env().dart_api_key == "fromdotenv"


def test_real_env_overrides_dotenv(tmp_path: Path, monkeypatch):
    # CI Secrets / exported vars must win over .env (override=False).
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DART_API_KEY=fromdotenv\n", encoding="utf-8")
    monkeypatch.setenv("DART_API_KEY", "fromrealenv")
    assert Settings.from_env().dart_api_key == "fromrealenv"
