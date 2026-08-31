# Decisions Follow-up Doc Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop `DECISIONS.md` from keeping a stale `WORKFLOW-CONCURRENCY-QUEUE` follow-up after that loop is already complete.

**Architecture:** Add one docs health guard in `tests/test_readme_docs.py` for the `PROJECT-STATE-ENTRYPOINTS` decision section. Remove the stale follow-up from `DECISIONS.md` and record this cleanup in the root state docs.

**Tech Stack:** Python 3.14, pytest, Markdown docs.

---

## Global Constraints

- Do not touch, stage, remove, or commit the unrelated untracked `uv.lock`.
- Do not stage or commit `CLAUDE.md`, `docs/superpowers/handoffs/`, or `.superpowers/` scratch files.
- Keep this loop to one objective: stale `DECISIONS.md` follow-up cleanup.
- Do not rewrite historical verification tables in `docs/decisions/tech-spec/`.

### Task 1: Decisions Follow-up Truth Guard

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `DECISIONS.md`
- Modify: `PLAN.md`
- Modify: `BACKLOG.md`
- Modify: `WORKLOG.md`

**Interfaces:**
- Consumes: `_markdown_section()` in `tests/test_readme_docs.py`.
- Produces: `test_project_state_decision_does_not_keep_completed_workflow_followup()`.

- [ ] **Step 1: Write the failing docs health guard**

Add this test near the existing root project-state docs guards:

```python
def test_project_state_decision_does_not_keep_completed_workflow_followup() -> None:
    text = Path("DECISIONS.md").read_text(encoding="utf-8")
    project_state = _markdown_section(text, "## 2026-06-28 — PROJECT-STATE-ENTRYPOINTS")
    workflow_queue = _markdown_section(text, "## 2026-06-28 — WORKFLOW-CONCURRENCY-QUEUE")

    assert "concurrency.queue: max" in workflow_queue
    assert "WORKFLOW-CONCURRENCY-QUEUE" not in project_state
    assert "should be a separate loop with a workflow guard" not in project_state
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_project_state_decision_does_not_keep_completed_workflow_followup -q
```

Expected: FAIL because `DECISIONS.md` still says `WORKFLOW-CONCURRENCY-QUEUE` should be a separate loop.

- [ ] **Step 3: Remove stale follow-up and update loop state**

- Remove the `Follow-up:` block from the `PROJECT-STATE-ENTRYPOINTS` section in `DECISIONS.md`.
- Set `PLAN.md` current loop to `DECISIONS-FOLLOWUP-DOC-TRUTH`.
- Add `DECISIONS-FOLLOWUP-DOC-TRUTH` to `BACKLOG.md` Done.
- Add a `WORKLOG.md` entry with RED/GREEN/verifications and review state.

- [ ] **Step 4: Verify**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_project_state_decision_does_not_keep_completed_workflow_followup -q
uv run pytest tests/test_readme_docs.py -q
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_readme_docs.py DECISIONS.md PLAN.md BACKLOG.md WORKLOG.md docs/superpowers/plans/2026-06-28-decisions-followup-doc-truth.md
git commit -m "test(docs): guard decisions followup state"
```
