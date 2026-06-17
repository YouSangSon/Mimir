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
            [make_record(Dataset.PRICES, day, symbol=f"S{i}", key=f"p-{day}-{i}")
             for i in range(40)],
        )
    write_partition(
        data_root, Dataset.PRICES, today,
        [make_record(Dataset.PRICES, today, symbol="S0", key="short")],
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


def test_cli_html_writes_file_and_preserves_text_stdout(
    tmp_path: Path, monkeypatch, capsys
):
    data_root = tmp_path / "data"
    write_fresh_tree(data_root, NOW)
    config_dir = _write_config(tmp_path, us=[])
    out = tmp_path / "reports" / "doctor.html"

    code = _run(
        [
            "--config-dir",
            str(config_dir),
            "--data-root",
            str(data_root),
            "--html",
            str(out),
        ],
        monkeypatch,
    )

    assert code == 0
    stdout = capsys.readouterr().out
    assert "mimir doctor" in stdout
    html = out.read_text()
    assert "Mimir" in html
    assert "All clear" in html


def test_cli_html_respects_lang(tmp_path: Path, monkeypatch, capsys):
    data_root = tmp_path / "data"
    write_fresh_tree(data_root, NOW)
    config_dir = _write_config(tmp_path, us=[])
    out = tmp_path / "reports" / "doctor.html"

    code = _run(
        [
            "--config-dir",
            str(config_dir),
            "--data-root",
            str(data_root),
            "--html",
            str(out),
            "--lang",
            "ko",
        ],
        monkeypatch,
    )

    assert code == 0
    html = out.read_text()
    assert 'lang="ko"' in html
    assert "데이터 닥터" in html


def test_cli_reports_invalid_sources_yaml_without_writing_html(
    tmp_path: Path, monkeypatch, capsys
):
    data_root = tmp_path / "data"
    write_fresh_tree(data_root, NOW)
    config_dir = _write_config(tmp_path, us=[])
    (config_dir / "sources.yaml").write_text(
        "- not-a-mapping\n",
        encoding="utf-8",
    )
    out = tmp_path / "reports" / "doctor.html"

    code = _run(
        [
            "--config-dir",
            str(config_dir),
            "--data-root",
            str(data_root),
            "--html",
            str(out),
        ],
        monkeypatch,
    )

    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("[mimir] invalid sources.yaml:")
    assert not out.exists()


def test_cli_json_html_preserves_json_stdout(tmp_path: Path, monkeypatch, capsys):
    data_root = tmp_path / "data"
    write_fresh_tree(data_root, NOW)
    config_dir = _write_config(tmp_path, us=[])
    out = tmp_path / "reports" / "doctor.html"

    code = _run(
        [
            "--config-dir",
            str(config_dir),
            "--data-root",
            str(data_root),
            "--format",
            "json",
            "--html",
            str(out),
        ],
        monkeypatch,
    )

    assert code == 0
    report = DoctorReport.model_validate_json(capsys.readouterr().out)
    assert report.worst is Severity.OK
    assert "All clear" in out.read_text()


def test_cli_html_preserves_critical_exit_code(tmp_path: Path, monkeypatch, capsys):
    data_root = tmp_path / "data"
    write_fresh_tree(data_root, NOW)
    import shutil

    shutil.rmtree(data_root / "macro")  # macro missing -> CRITICAL
    config_dir = _write_config(tmp_path, us=[])
    out = tmp_path / "reports" / "doctor.html"

    code = _run(
        [
            "--config-dir",
            str(config_dir),
            "--data-root",
            str(data_root),
            "--html",
            str(out),
        ],
        monkeypatch,
    )

    assert code == 1
    assert "critical" in capsys.readouterr().out.lower()
    assert "CRITICAL" in out.read_text()


def test_cli_html_preserves_strict_warn_exit_code(tmp_path: Path, monkeypatch, capsys):
    data_root = tmp_path / "data"
    write_fresh_tree(data_root, NOW)
    import shutil

    shutil.rmtree(data_root / "prices")
    today = NOW.date()
    for offset in (4, 3, 2, 1):
        day = date.fromordinal(today.toordinal() - offset)
        write_partition(
            data_root,
            Dataset.PRICES,
            day,
            [
                make_record(
                    Dataset.PRICES,
                    day,
                    symbol=f"S{i}",
                    key=f"p-{day}-{i}",
                )
                for i in range(40)
            ],
        )
    write_partition(
        data_root,
        Dataset.PRICES,
        today,
        [make_record(Dataset.PRICES, today, symbol="S0", key="short")],
    )
    config_dir = _write_config(tmp_path, us=[])
    out = tmp_path / "reports" / "doctor.html"

    code = _run(
        [
            "--config-dir",
            str(config_dir),
            "--data-root",
            str(data_root),
            "--strict",
            "--html",
            str(out),
        ],
        monkeypatch,
    )

    assert code == 1
    assert "warn" in capsys.readouterr().out.lower()
    assert "WARN" in out.read_text()
