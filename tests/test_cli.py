from __future__ import annotations

from pathlib import Path

import pytest

from mimir import cli


def test_cli_help_lists_subcommands(capsys) -> None:
    assert cli.main(["--help"]) == 0

    out = capsys.readouterr().out

    assert "Usage: mimir <command> [args...]" in out
    assert "collect" in out
    assert "dashboard" in out


def test_cli_dispatches_subcommand(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_collect(argv: list[str] | None = None) -> int:
        calls.append(list(argv or []))
        return 7

    monkeypatch.setitem(cli.COMMANDS, "collect", fake_collect)

    assert cli.main(["collect", "--cadence", "daily"]) == 7
    assert calls == [["--cadence", "daily"]]


def test_cli_unknown_subcommand_returns_usage_error(capsys) -> None:
    assert cli.main(["nope"]) == 2

    captured = capsys.readouterr()

    assert "unknown command: nope" in captured.err
    assert "Usage: mimir <command> [args...]" in captured.err


@pytest.mark.parametrize(
    ("command", "args", "filename"),
    [
        (command, args, filename)
        for command, args in [
            ("collect", ["--cadence", "daily"]),
            ("run", ["--cadence", "daily"]),
            ("backfill", ["--source", "ecos", "--since", "2026-01-01"]),
            ("analyze", []),
            ("dashboard", []),
            ("doctor", ["--html", "doctor.html"]),
        ]
        for filename in ("sources.yaml", "watchlist.yaml")
    ]
    + [("deliver", [], "sources.yaml"), ("history", [], "watchlist.yaml")],
)
def test_cli_rejects_malformed_yaml_before_side_effects(
    command: str, args: list[str], filename: str, tmp_path: Path, monkeypatch, capsys
) -> None:
    import requests

    from mimir.settings import Settings

    def forbidden(*args, **kwargs):
        pytest.fail("invalid config must stop before settings or network access")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Settings, "from_env", forbidden)
    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / filename).write_text("secret_fixture_value: [\n", encoding="utf-8")
    before = set(tmp_path.rglob("*"))

    assert cli.main([command, *args, "--config-dir", str(config_dir)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"[mimir] invalid {filename}:" in captured.err
    assert str(config_dir / filename) in captured.err
    assert "YAML" in captured.err
    assert "secret_fixture_value" not in captured.err
    assert "Traceback" not in captured.err
    assert set(tmp_path.rglob("*")) == before


@pytest.mark.parametrize("value", ["not-a-date", "2026-02-30"])
@pytest.mark.parametrize(
    ("command", "args", "option"),
    [
        ("analyze", [], "--date"),
        ("deliver", [], "--date"),
        ("history", [], "--date"),
        ("evaluate", [], "--date"),
        ("dashboard", [], "--date"),
        ("backfill", ["--source", "ecos"], "--since"),
    ],
)
def test_cli_rejects_invalid_dates_before_config_or_output(
    command: str, args: list[str], option: str, value: str,
    tmp_path: Path, monkeypatch, capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "config"
    config.mkdir()
    for filename in ("sources.yaml", "watchlist.yaml"):
        (config / filename).write_text("invalid: [", encoding="utf-8")
    before = set(tmp_path.rglob("*"))

    with pytest.raises(SystemExit) as exc:
        cli.main([command, *args, option, value])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage:" in captured.err
    assert option in captured.err
    assert value in captured.err
    assert "Traceback" not in captured.err
    assert "invalid sources.yaml" not in captured.err
    assert "invalid watchlist.yaml" not in captured.err
    assert set(tmp_path.rglob("*")) == before
