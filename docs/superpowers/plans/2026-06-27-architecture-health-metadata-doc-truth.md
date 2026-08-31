# Architecture Health Metadata Doc Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep README lint/type health metadata and architecture catalog current-health statements aligned with the actual mypy strict configuration and docs health guard contract.

**Architecture:** Add a focused docs health guard in `tests/test_readme_docs.py` that proves `pyproject.toml` owns strict mypy configuration, README lint/type rows describe that contract without pretending the CLI command uses `--strict`, and the architecture catalog no longer publishes fixed coverage or tool-clean snapshots as current verification. Then update only the affected docs rows to the canonical wording.

**Tech Stack:** Python stdlib `tomllib`, pytest, Markdown docs.

## Global Constraints

- Do not touch, stage, remove, or commit the unrelated untracked `uv.lock`.
- Do not stage or commit `CLAUDE.md`, `docs/superpowers/handoffs/`, or `.superpowers/` scratch files.
- Preserve the existing README EN/KO/ZH test count of `642`; this slice adds one test so the README count must become `643` only after collection confirms it.
- Keep legitimate domain references such as `mypy strict 내로잉`, `doctor --strict`, and historical plan examples outside this slice unchanged.
- `pyproject.toml` is the source of truth for strict mypy mode: `[tool.mypy] strict = true`.
- Current health metadata should name README test badges/docs health guards, not fixed command snapshots such as `mypy --strict clean` or `80%+ 커버리지`.

---

### Task 1: README And Architecture Health Metadata Guard

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Modify: `docs/architecture/improvement-catalog.md`

**Interfaces:**
- Consumes: `README_FILES`, `IMPROVEMENT_CATALOG`, and existing `_markdown_section()` from `tests/test_readme_docs.py`.
- Produces: `test_readme_and_architecture_health_metadata_use_current_contract()` as a docs health guard for README lint/type rows and architecture catalog current-health metadata.

- [ ] **Step 1: Add the failing docs health guard**

In `tests/test_readme_docs.py`, add `import tomllib` beside the stdlib imports:

```python
import re
import subprocess
import sys
import tomllib
from pathlib import Path
```

Add this test after `test_readme_test_badges_match_collected_pytest_count()`:

```python
def test_readme_and_architecture_health_metadata_use_current_contract() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["tool"]["mypy"]["strict"] is True

    canonical_lint_type = "ruff + mypy (`pyproject.toml` strict config) clean"
    stale_readme_lint_type = "ruff + mypy `--strict` clean"
    for path in README_FILES:
        text = path.read_text(encoding="utf-8")
        rows = [
            line
            for line in text.splitlines()
            if line.startswith("| **lint/type** |")
        ]
        assert rows == [f"| **lint/type** | {canonical_lint_type} |"]
        assert stale_readme_lint_type not in text

    catalog = IMPROVEMENT_CATALOG.read_text(encoding="utf-8")
    cov1_rows = [
        line
        for line in catalog.splitlines()
        if line.startswith("| **COV1-CONTRACT-COVERAGE** |")
    ]
    assert len(cov1_rows) == 1
    cov1_row = cov1_rows[0]
    assert "README/docs health guard가 추적하는 커버리지 게이트" in cov1_row
    assert "idempotency_key/partition 불변식 약속" in cov1_row
    assert "80%+ 커버리지" not in cov1_row

    anti_discovery = _markdown_section(catalog, "## 7. 안티-발견 (확인됨, 손대지 않음)")
    assert "pyproject.toml strict config" in anti_discovery
    assert "README 테스트 배지와 docs health guard가 추적" in anti_discovery
    assert "mypy strict 통과" not in anti_discovery
    assert "mypy --strict clean" not in anti_discovery
```

- [ ] **Step 2: Run the targeted test and verify RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_readme_and_architecture_health_metadata_use_current_contract -q
```

Expected: FAIL because README EN/KO/ZH still say `ruff + mypy `--strict` clean`, COV1 still says `80%+ 커버리지`, and the architecture catalog anti-discovery section still says `mypy strict 통과`.

- [ ] **Step 3: Update README lint/type rows**

In `README.md`, `README.ko.md`, and `README.zh.md`, replace the lint/type table row with:

```markdown
| **lint/type** | ruff + mypy (`pyproject.toml` strict config) clean |
```

Do not change the command block lines that show `.venv/bin/mypy mimir`; those lines are already the correct command and their comment can continue to say strict because `pyproject.toml` enables strict mode.

- [ ] **Step 4: Update architecture catalog current-health wording**

In `docs/architecture/improvement-catalog.md`, replace the COV1 traceability cell:

```markdown
80%+ 커버리지 + idempotency_key/partition 불변식 약속
```

with:

```markdown
README/docs health guard가 추적하는 커버리지 게이트 + idempotency_key/partition 불변식 약속
```

In the anti-discovery section, replace:

```markdown
- 레이어 그래프 순환 없음 · 파일 크기 건전(최대 ~150줄) · mypy strict 통과.
```

with:

```markdown
- 레이어 그래프 순환 없음 · 파일 크기 건전(최대 ~150줄) · 타입 검증은 pyproject.toml strict config와 README 테스트 배지와 docs health guard가 추적한다.
```

- [ ] **Step 5: Verify GREEN and update README test counts if needed**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_readme_and_architecture_health_metadata_use_current_contract -q
uv run pytest tests/test_readme_docs.py -q
uv run pytest --collect-only -q | tail -1
```

Expected after adding this test: the focused test passes, the docs test file passes, and collection reports `643 tests collected`.

If collection reports `643 tests collected`, update all README EN/KO/ZH test badge and table counts from `642` to `643` while preserving `98% cov`.

- [ ] **Step 6: Run final gates and commit**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: all pass.

Stage only:

```bash
git add tests/test_readme_docs.py README.md README.ko.md README.zh.md docs/architecture/improvement-catalog.md
git commit -m "test(docs): guard architecture health metadata truth"
```

Do not stage `uv.lock`, `CLAUDE.md`, `docs/superpowers/handoffs/`, or `.superpowers/`.
