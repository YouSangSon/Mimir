"""CLI integration for `python -m mimir.doctor` (§6.2). No network, fixed trees."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from mimir.core.source import Dataset
from mimir.doctor import doctor_cli
from mimir.doctor.report import DoctorReport, Severity
from tests.doctor.conftest import make_record, write_fresh_tree, write_partition

NOW = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)


def _write_config(tmp_path: Path, us: list[str]) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "watchlist.yaml").write_text(
        "us: [" + ", ".join(us) + "]\nkr: []\n", encoding="utf-8"
    )
    return config_dir


def _run(argv: list[str], monkeypatch) -> int:
    # Pin `now` so the CLI boundary is deterministic in tests.
    monkeypatch.setattr(doctor_cli, "_now", lambda: NOW)
    return doctor_cli.main(argv)


def test_cli_fresh_tree_exit_zero(tmp_path: Path, monkeypatch, capsys):
    data_root = tmp_path / "data"
    write_fresh_tree(data_root, NOW)
    config_dir = _write_config(tmp_path, us=[])
    code = _run(
        ["--config-dir", str(config_dir), "--data-root", str(data_root), "--format", "json"],
        monkeypatch,
    )
    assert code == 0
    out = capsys.readouterr().out
    report = DoctorReport.model_validate_json(out)
    assert report.worst is Severity.OK


def test_cli_critical_exits_one(tmp_path: Path, monkeypatch, capsys):
    data_root = tmp_path / "data"
    write_fresh_tree(data_root, NOW)
    import shutil

    shutil.rmtree(data_root / "macro")  # macro missing -> CRITICAL
    config_dir = _write_config(tmp_path, us=[])
    code = _run(
        ["--config-dir", str(config_dir), "--data-root", str(data_root), "--format", "json"],
        monkeypatch,
    )
    assert code == 1


def test_cli_strict_escalates_warn_to_one(tmp_path: Path, monkeypatch, capsys):
    data_root = tmp_path / "data"
    write_fresh_tree(data_root, NOW)
    # Force a WARN (short) without any CRITICAL: rewrite prices with a short latest.
    import shutil

    shutil.rmtree(data_root / "prices")
    today = NOW.date()
    for offset in (4, 3, 2, 1):
        day = date.fromordinal(today.toordinal() - offset)
        write_partition(
            data_root, Dataset.PRICES, day,
            [make_record(Dataset.PRICES, day, symbol=f"S{i}", key=f"p-{day}-{i}",
                         payload={"close": 1.0}) for i in range(40)],
        )
    write_partition(
        data_root, Dataset.PRICES, today,
        [make_record(Dataset.PRICES, today, symbol="S0", key="short", payload={"close": 1.0})],
    )
    config_dir = _write_config(tmp_path, us=[])
    base = ["--config-dir", str(config_dir), "--data-root", str(data_root)]
    assert _run(base, monkeypatch) == 0  # WARN -> exit 0 by default
    assert _run([*base, "--strict"], monkeypatch) == 1  # --strict escalates


def test_cli_text_format_emits_summary(tmp_path: Path, monkeypatch, capsys):
    data_root = tmp_path / "data"
    write_fresh_tree(data_root, NOW)
    config_dir = _write_config(tmp_path, us=[])
    code = _run(
        ["--config-dir", str(config_dir), "--data-root", str(data_root), "--format", "text"],
        monkeypatch,
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "ok" in out.lower()
    with pytest.raises(json.JSONDecodeError):  # text is not JSON
        json.loads(out)
