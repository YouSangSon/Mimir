from datetime import UTC, date, datetime
from pathlib import Path

from mimir import deliver as deliver_module
from mimir.analysis.schema import Insight, to_record
from mimir.analysis.signals.base import SignalDirection
from mimir.core.source import Market
from mimir.deliver import run_deliver
from mimir.evaluation.schema import BucketStat, HorizonEval
from mimir.evaluation.schema import to_record as evaluation_to_record
from mimir.historical.analog import HorizonStat
from mimir.historical.schema import HistoricalInsight
from mimir.historical.schema import to_record as historical_to_record
from mimir.storage.jsonl_store import JsonlStore


def _historical() -> HistoricalInsight:
    return HistoricalInsight(
        symbol="AAPL",
        market=Market.US,
        as_of=date(2026, 5, 31),
        event_type="sharp_drop",
        occurrences=12,
        triggered_today=True,
        horizons=[HorizonStat(horizon=5, n=12, median_return=0.004, pct_positive=0.58)],
        examples=["2024-08-05: -6.1% then +3.2% (5d)"],
    )


def _insight() -> Insight:
    return Insight(
        symbol="AAPL",
        market=Market.US,
        as_of=date(2026, 5, 31),
        direction=SignalDirection.BULLISH,
        stars=4,
        confidence=0.8,
        signals=[],
        reasons=["[price_momentum] +6%"],
    )


def _bucket() -> BucketStat:
    return BucketStat(
        dimension="per_signal",
        key="price_momentum",
        market=Market.US,
        horizons=[
            HorizonEval(horizon=5, n=12, hit_rate=0.58, mean_fwd_return=0.004, neutral_n=2)
        ],
    )


def test_run_deliver_writes_report_and_noops_telegram(tmp_path: Path):
    data_root = tmp_path / "data"
    reports_root = tmp_path / "reports"
    JsonlStore(root=data_root).append([to_record(_insight(), datetime(2026, 5, 31, tzinfo=UTC))])

    result = run_deliver(
        cadence="daily",
        env={},  # no telegram token -> graceful no-op
        data_root=data_root,
        reports_root=reports_root,
        as_of=date(2026, 5, 31),
    )
    assert result["insights"] == 1
    assert result["sent"] is False
    assert (reports_root / "2026/05/31.html").exists()
    assert (reports_root / "index.html").exists()


def test_run_deliver_includes_historical_section(tmp_path: Path):
    data_root = tmp_path / "data"
    reports_root = tmp_path / "reports"
    store = JsonlStore(root=data_root)
    store.append([to_record(_insight(), datetime(2026, 5, 31, tzinfo=UTC))])
    store.append([historical_to_record(_historical(), datetime(2026, 5, 31, tzinfo=UTC))])

    result = run_deliver(
        cadence="daily",
        env={},
        data_root=data_root,
        reports_root=reports_root,
        as_of=date(2026, 5, 31),
    )
    assert result["historical"] == 1
    html = (reports_root / "2026/05/31.html").read_text()  # default lang = en
    assert "Historical cases" in html
    assert "sharp_drop" in html
    assert "Triggered today" in html  # triggered_today badge


def test_run_deliver_includes_evaluation_scorecard(tmp_path: Path):
    data_root = tmp_path / "data"
    reports_root = tmp_path / "reports"
    store = JsonlStore(root=data_root)
    captured_at = datetime(2026, 5, 31, tzinfo=UTC)
    store.append([to_record(_insight(), captured_at)])
    store.append([evaluation_to_record(_bucket(), date(2026, 5, 31), captured_at)])

    result = run_deliver(
        cadence="daily",
        env={},
        data_root=data_root,
        reports_root=reports_root,
        as_of=date(2026, 5, 31),
    )
    assert result["evaluation"] == 1
    html = (reports_root / "2026/05/31.html").read_text()
    assert "Signal scorecard" in html
    assert "price_momentum" in html


def test_run_deliver_empty_is_graceful(tmp_path: Path):
    result = run_deliver(
        cadence="daily",
        env={},
        data_root=tmp_path / "data",
        reports_root=tmp_path / "reports",
        as_of=date(2026, 5, 31),
    )
    assert result["insights"] == 0
    assert (tmp_path / "reports/2026/05/31.html").exists()


def test_run_deliver_default_env_loads_dotenv_for_telegram(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "TELEGRAM_BOT_TOKEN=token-from-dotenv\n"
        "TELEGRAM_CHAT_ID=chat-from-dotenv\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    captured: dict[str, str | None] = {}

    def _fake_send_ping(
        *, bot_token: str | None, chat_id: str | None, text: str
    ) -> bool:
        captured.update({"bot_token": bot_token, "chat_id": chat_id, "text": text})
        return True

    monkeypatch.setattr(deliver_module, "send_ping", _fake_send_ping)

    result = run_deliver(
        cadence="daily",
        data_root=tmp_path / "data",
        reports_root=tmp_path / "reports",
        as_of=date(2026, 5, 31),
    )

    assert result["sent"] is True
    assert captured["bot_token"] == "token-from-dotenv"
    assert captured["chat_id"] == "chat-from-dotenv"


def test_main_uses_default_env_path(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    captured: dict[str, object] = {}

    def _fake_run_deliver(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "insights": 0,
            "report": tmp_path / "reports/2026/05/31.html",
            "sent": False,
        }

    monkeypatch.setattr(deliver_module, "run_deliver", _fake_run_deliver)

    rc = deliver_module.main(
        [
            "--cadence",
            "daily",
            "--config-dir",
            str(config_dir),
            "--data-root",
            str(tmp_path / "data"),
            "--reports-root",
            str(tmp_path / "reports"),
        ]
    )

    assert rc == 0
    assert "env" not in captured
