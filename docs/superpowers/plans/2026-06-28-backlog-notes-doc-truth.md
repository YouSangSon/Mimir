# Backlog Notes Doc Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop `BACKLOG.md` notes from describing completed work as if it still needs a pre-implementation guard.

**Architecture:** Add one docs health guard in `tests/test_readme_docs.py` for the root backlog notes section. Replace the stale item-specific note with a generic rule that completed items keep evidence in `WORKLOG.md` and `DECISIONS.md`.

**Tech Stack:** Python 3.14, pytest, Markdown docs.

## Global Constraints

- Do not touch, stage, remove, or commit the unrelated untracked `uv.lock`.
- Do not stage or commit `CLAUDE.md`, `docs/superpowers/handoffs/`, or `.superpowers/` scratch files.
- Keep this loop to one objective: `BACKLOG.md` notes truth.
- Do not rewrite historical tech-spec verification tables in `docs/decisions/tech-spec/`.

---

### Task 1: Backlog Notes Truth Guard

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `BACKLOG.md`
- Modify: `PLAN.md`
- Modify: `WORKLOG.md`
- Modify: `DECISIONS.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

**Interfaces:**
- Consumes: `_markdown_section()` in `tests/test_readme_docs.py`.
- Produces: `test_backlog_notes_do_not_treat_completed_workflow_queue_as_pending()`.

- [ ] **Step 1: Write the failing docs health guard**

Add `BACKLOG = Path("BACKLOG.md")` near existing path constants in `tests/test_readme_docs.py`.

Add this test near the root project-state docs guard:

```python
def test_backlog_notes_do_not_treat_completed_workflow_queue_as_pending() -> None:
    text = BACKLOG.read_text(encoding="utf-8")
    done = _markdown_section(text, "## Done")
    notes = _markdown_section(text, "## Notes")

    assert "WORKFLOW-CONCURRENCY-QUEUE" in done
    assert "needs its own RED workflow guard before changing YAML" not in notes
    assert "Completed items keep verification evidence in `WORKLOG.md`" in notes
    assert "decision rationale in `DECISIONS.md`" in notes
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_backlog_notes_do_not_treat_completed_workflow_queue_as_pending -q
```

Expected: FAIL because `BACKLOG.md` still says `WORKFLOW-CONCURRENCY-QUEUE` needs its own RED workflow guard before changing YAML.

- [ ] **Step 3: Update backlog and loop state**

- Replace the stale `WORKFLOW-CONCURRENCY-QUEUE` note in `BACKLOG.md` with a generic completed-item evidence rule.
- Set `PLAN.md` current loop to `BACKLOG-NOTES-DOC-TRUTH`.
- Add `BACKLOG-NOTES-DOC-TRUTH` entries to `WORKLOG.md` and `DECISIONS.md`.

- [ ] **Step 4: Update README test counts**

Run:

```bash
uv run pytest --collect-only -q | tail -1
```

Update README EN/KO/ZH test badge and test table counts to the collected count.

- [ ] **Step 5: Verify**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_backlog_notes_do_not_treat_completed_workflow_queue_as_pending -q
uv run pytest tests/test_readme_docs.py -q
uv run pytest --collect-only -q | tail -1
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_readme_docs.py BACKLOG.md PLAN.md WORKLOG.md DECISIONS.md README.md README.ko.md README.zh.md docs/superpowers/plans/2026-06-28-backlog-notes-doc-truth.md
git commit -m "test(docs): guard backlog notes state"
```
