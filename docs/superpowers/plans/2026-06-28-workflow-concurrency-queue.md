# Workflow Concurrency Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Queue all pending scheduled collection runs in the shared `collect` concurrency group instead of letting GitHub Actions keep only one pending run.

**Architecture:** Add `queue: max` to the reusable collection pipeline's existing workflow-level concurrency block while keeping `cancel-in-progress: false`. Guard that contract in `tests/test_workflows.py`, update README health counts, and record the official GitHub Actions source in `WORKLOG.md`/`DECISIONS.md`.

**Tech Stack:** GitHub Actions YAML, Python 3.14, pytest, Markdown docs.

## External Source

- GitHub Docs, control workflow/job concurrency: `https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency`
- GitHub Docs, workflow syntax: `https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax`
- GitHub Docs, Actions limits: `https://docs.github.com/en/actions/reference/limits`

## Global Constraints

- Do not touch, stage, remove, or commit the unrelated untracked `uv.lock`.
- Do not stage or commit `CLAUDE.md`, `docs/superpowers/handoffs/`, or `.superpowers/` scratch files.
- Keep this loop to one objective: workflow concurrency queueing.
- Do not change workflow triggers, cadence files, commit-back behavior, secrets, permissions, or pipeline commands.
- `queue: max` must not be combined with `cancel-in-progress: true`.

---

### Task 1: Queue Scheduled Pipeline Runs

**Files:**
- Modify: `tests/test_workflows.py`
- Modify: `.github/workflows/_pipeline.yml`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Modify: `PLAN.md`
- Modify: `BACKLOG.md`
- Modify: `WORKLOG.md`
- Modify: `DECISIONS.md`

**Interfaces:**
- Consumes: `PIPELINE_WORKFLOW` in `tests/test_workflows.py`.
- Produces: `test_reusable_pipeline_queues_pending_collect_runs()`.

- [ ] **Step 1: Write the failing workflow guard**

Add this test near the other reusable pipeline tests in `tests/test_workflows.py`:

```python
def test_reusable_pipeline_queues_pending_collect_runs() -> None:
    text = PIPELINE_WORKFLOW.read_text(encoding="utf-8")

    assert re.search(
        r"(?m)^concurrency:\n  group: collect\n  cancel-in-progress: false\n  queue: max\n",
        text,
    )
    assert "cancel-in-progress: true" not in text
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
uv run pytest tests/test_workflows.py::test_reusable_pipeline_queues_pending_collect_runs -q
```

Expected: FAIL because `_pipeline.yml` has `group: collect` and `cancel-in-progress: false`, but no `queue: max`.

- [ ] **Step 3: Add `queue: max`**

Update `.github/workflows/_pipeline.yml`:

```yaml
concurrency:
  group: collect
  cancel-in-progress: false
  queue: max
```

- [ ] **Step 4: Update user-facing docs and loop state**

- In README EN/KO/ZH Schedule & Delivery, change the commit-back row from plain `concurrency` guard to queued concurrency guard.
- In `PLAN.md`, set the current loop to `WORKFLOW-CONCURRENCY-QUEUE`.
- In `BACKLOG.md`, move `WORKFLOW-CONCURRENCY-QUEUE` to Done and leave the docs-truth scan as next.
- In `WORKLOG.md`, add the loop entry with RED/GREEN and final verification.
- In `DECISIONS.md`, add the workflow queue decision with GitHub Docs sources.

- [ ] **Step 5: Update README test counts**

Run:

```bash
uv run pytest --collect-only -q | tail -1
```

Update README EN/KO/ZH test badge and test table counts to the collected count.

- [ ] **Step 6: Verify**

Run:

```bash
uv run pytest tests/test_workflows.py::test_reusable_pipeline_queues_pending_collect_runs -q
uv run pytest tests/test_workflows.py -q
uv run pytest tests/test_readme_docs.py -q
uv run pytest --collect-only -q | tail -1
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

- [ ] **Step 7: Commit**

```bash
git add tests/test_workflows.py .github/workflows/_pipeline.yml README.md README.ko.md README.zh.md PLAN.md BACKLOG.md WORKLOG.md DECISIONS.md
git commit -m "ci(docs): queue scheduled workflow runs"
```
