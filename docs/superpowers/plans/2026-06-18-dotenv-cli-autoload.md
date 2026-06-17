# Runtime `.env` Autoload Implementation Plan

**Goal:** Make installed and module CLI paths honor the README promise that local `.env` files are auto-loaded at runtime, while keeping explicit test/library `env` injection deterministic.

**Architecture:** Runtime functions accept `env: Mapping[str, str] | None = None`. CLI entrypoints omit `env`, so `Settings.from_env()` uses the existing `find_dotenv(usecwd=True)` + `load_dotenv(..., override=False)` path. Tests can still pass `env={...}` to avoid reading local state.

## Global Constraints

- Do not log, render, or persist secret values.
- Do not change CI workflow secret handling.
- Do not change `.env` search semantics beyond the existing `Settings.from_env(None)` behavior.
- Keep untracked `uv.lock` unstaged.

---

## File Map

| File | Responsibility |
|---|---|
| `tests/test_collect.py` | CLI-level `.env` autoload contract tests |
| `mimir/collect.py` | Runtime/CLI env default for collect |
| `mimir/run.py` | Runtime/CLI env default for full pipeline |
| `mimir/deliver.py` | Runtime/CLI env default for report delivery |
| `mimir/backfill.py` | Runtime/CLI env default for backfill |
| `docs/architecture/improvement-catalog.md` | Tracking |
| `docs/IMPROVEMENTS.md` | Backlog/status |
| README files | User-facing CLI/env wording if needed |
| `docs/superpowers/specs/2026-06-18-dotenv-cli-autoload-design.md` | Acceptance checklist |

---

## Task 1: Add Failing CLI Env Tests

- [x] Add a collect CLI test that writes `.env` with `STOOQ_API_KEY`, disables keyless network sources, and verifies a Stooq price partition is written without exporting the key.
- [x] Add a collect CLI test showing exported `STOOQ_API_KEY` beats `.env`.
- [x] Run the focused test and confirm RED:

```bash
uv run pytest tests/test_collect.py -q
```

Expected: the new `.env` collect CLI test fails before implementation.

## Task 2: Implement Runtime Env Defaults

- [x] Change runtime function signatures to accept `env: Mapping[str, str] | None = None`.
- [x] Stop passing `os.environ` from CLI `main()` paths.
- [x] Preserve existing explicit-env tests.
- [x] Run focused tests and confirm GREEN.

## Task 3: Update Tracking Docs

- [x] Record the README `.env` autoload contract fix in `docs/IMPROVEMENTS.md`.
- [x] Add a small completed item to `docs/architecture/improvement-catalog.md`.
- [x] Mark spec/plan checklists complete after verification.

## Task 4: Verify

- [x] Run focused tests:

```bash
uv run pytest tests/test_settings.py tests/test_collect.py -q
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

- [ ] Final review.
- [ ] Commit branch.
