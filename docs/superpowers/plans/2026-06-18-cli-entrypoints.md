# CLI Entrypoints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add installable CLI entry points so package metadata matches the README CLI surface while keeping existing `python -m mimir.X` commands unchanged.

**Architecture:** Add `mimir/cli.py` as a thin dispatcher over existing module-level `main(argv)` functions. Add `[project.scripts]` entries in `pyproject.toml` for `mimir` and the dotted command aliases already shown in README.

**Tech Stack:** Python 3.14, argparse, setuptools entry points, pytest, ruff, mypy, markdown docs.

## Global Constraints

- Do not add a new CLI dependency.
- Do not rewrite existing command option parsing.
- Do not change GitHub Actions workflow commands.
- Preserve all existing `python -m mimir.X` paths.
- Keep `uv.lock` untracked and unstaged.

---

## File Map

| File | Responsibility |
|---|---|
| `tests/test_cli.py` | Dispatcher behavior tests |
| `tests/test_pyproject_scripts.py` | Package metadata/script target tests |
| `mimir/cli.py` | Unified CLI dispatcher |
| `pyproject.toml` | Console script declarations |
| `README.md` | English CLI/docs/test-count sync |
| `README.ko.md` | Korean CLI/docs/test-count sync |
| `README.zh.md` | Chinese CLI/docs/test-count sync |
| `docs/architecture/improvement-catalog.md` | D1 tracking |
| `docs/IMPROVEMENTS.md` | Follow-up/backlog wording |
| `docs/superpowers/specs/2026-06-18-cli-entrypoints-design.md` | Acceptance checklist |

---

### Task 1: Add Failing CLI Contract Tests

- [x] Add `tests/test_cli.py` for help, dispatch, and unknown command behavior.
- [x] Add `tests/test_pyproject_scripts.py` for `[project.scripts]` declarations and importable targets.
- [x] Run focused tests and confirm RED:

```bash
uv run pytest tests/test_cli.py tests/test_pyproject_scripts.py -q
```

Expected: FAIL because `mimir.cli` and `[project.scripts]` do not exist yet.

### Task 2: Implement CLI Entrypoints

- [x] Create `mimir/cli.py`.
- [x] Add `[project.scripts]` to `pyproject.toml`.
- [x] Run focused tests and confirm GREEN.
- [x] Smoke test installed scripts with `uv run mimir --help` and at least one dotted alias help command.

### Task 3: Update Docs

- [x] Update README CLI section in EN/KO/ZH.
- [x] Update README feature/development lines if needed after coverage run.
- [x] Mark D1 complete in improvement catalog.
- [x] Update `docs/IMPROVEMENTS.md`.
- [x] Mark spec/plan checklists complete after verification.

### Task 4: Verify And Land

- [x] Run focused tests:

```bash
uv run pytest tests/test_cli.py tests/test_pyproject_scripts.py -q
```

- [x] Run full gates:

```bash
uv run ruff check .
uv run mypy mimir
uv run pytest -q
uv run coverage run -m pytest
uv run coverage report --fail-under=80
git diff --check
```

- [ ] Review diff.
- [ ] Final reviewer pass.
- [ ] Commit changes.
- [ ] Fast-forward merge to `main`.
- [ ] Push `main`.
