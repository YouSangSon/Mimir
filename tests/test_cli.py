from __future__ import annotations

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
