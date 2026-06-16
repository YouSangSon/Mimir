# GitHub Actions Node24 Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GitHub Actions workflow에서 Node20 세대 action 사용을 제거하고 Node24 호환 major를 고정한다.

**Architecture:** workflow YAML은 직접 major tag만 바꾼다. 별도 Python 테스트가 `.github/workflows/*.yml`의 `actions/checkout`과 `actions/setup-python` 사용을 검사해 회귀를 막는다.

**Tech Stack:** GitHub Actions YAML, Python 3.14, pytest, ruff, mypy.

---

### Task 1: Workflow Version Guard

**Files:**
- Create: `tests/test_workflows.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/_pipeline.yml`

- [x] **Step 1: Write failing workflow version test**

Create `tests/test_workflows.py`:

```python
from __future__ import annotations

import re
from pathlib import Path


EXPECTED_WORKFLOW_ACTION_MAJORS = {
    Path(".github/workflows/ci.yml"): {
        "actions/checkout": "v6",
        "actions/setup-python": "v6",
    },
    Path(".github/workflows/_pipeline.yml"): {
        "actions/checkout": "v6",
        "actions/setup-python": "v6",
    },
}

ACTION_USES_RE = re.compile(r"uses:\s*(actions/(?:checkout|setup-python))@(v\d+)(?:\\b|$)")


def test_github_actions_use_node24_compatible_major_versions():
    mismatches: list[str] = []

    for path, expected_actions in EXPECTED_WORKFLOW_ACTION_MAJORS.items():
        seen: set[str] = set()
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = ACTION_USES_RE.search(line)
            if match is None:
                continue
            action, major = match.groups()
            seen.add(action)
            expected = expected_actions[action]
            if major != expected:
                mismatches.append(f"{path}:{line_no}: {action}@{major} should be {expected}")

        assert seen == set(expected_actions), f"{path} is missing expected actions"
    assert mismatches == []
```

- [x] **Step 2: Run test and verify RED**

Run:

```bash
.venv/bin/pytest tests/test_workflows.py::test_github_actions_use_node24_compatible_major_versions -q
```

Expected: FAIL with mismatches for `actions/checkout@v4` and `actions/setup-python@v5`.

- [x] **Step 3: Update workflow action versions**

Change `.github/workflows/ci.yml`:

```yaml
- uses: actions/checkout@v6
- uses: actions/setup-python@v6
```

Change `.github/workflows/_pipeline.yml`:

```yaml
- uses: actions/checkout@v6
- uses: actions/setup-python@v6
```

Do not change triggers, permissions, schedules, secrets, or commit commands.

- [x] **Step 4: Run workflow version test and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/test_workflows.py::test_github_actions_use_node24_compatible_major_versions -q
```

Expected: PASS.

### Task 2: Documentation and Verification

**Files:**
- Modify: `docs/IMPROVEMENTS.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/superpowers/specs/2026-06-16-github-actions-node24-design.md`
- Modify: `docs/superpowers/plans/2026-06-16-github-actions-node24.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

- [x] **Step 1: Update D2 docs**

Mark D2 implemented in `docs/IMPROVEMENTS.md` and `docs/architecture/improvement-catalog.md`.

Explain that the workflow now uses Node24-compatible major tags and that `tests/test_workflows.py` guards the contract.

- [x] **Step 2: Run verification**

Run:

```bash
.venv/bin/ruff check .
.venv/bin/mypy mimir
git diff --check
.venv/bin/coverage run -m pytest
.venv/bin/coverage report --fail-under=80
```

Expected: all pass. Update README test counts if the total changed.

- [x] **Step 3: Mark plan/spec complete**

After verification passes, update this plan's checkboxes to `[x]` and set the spec status to implemented with the verified test count.
