# Project State Entrypoints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add root `PLAN.md`, `BACKLOG.md`, `WORKLOG.md`, and `DECISIONS.md` entrypoints so a future session can resume from repo documents and git history.

**Architecture:** Do not create a second project-management system. Add thin root documents that point to the existing canonical docs under `docs/`, record the current loop, and keep a docs health guard in `tests/test_readme_docs.py` so the entrypoints cannot disappear or drift away from the canonical sources.

**Tech Stack:** Python 3.14, pytest, Markdown docs.

## Global Constraints

- Do not touch, stage, remove, or commit the unrelated untracked `uv.lock`.
- Do not stage or commit `CLAUDE.md`, `docs/superpowers/handoffs/`, or `.superpowers/` scratch files.
- Keep this loop to one objective: root project-state entrypoints.
- Use root docs as pointers to canonical tracked sources, not duplicated long-form state.
- Record the external GitHub Actions concurrency research as a backlog/decision note only; do not change workflow YAML in this loop.

---

### Task 1: Root Project-State Entrypoints

**Files:**
- Modify: `tests/test_readme_docs.py`
- Create: `PLAN.md`
- Create: `BACKLOG.md`
- Create: `WORKLOG.md`
- Create: `DECISIONS.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

**Interfaces:**
- Consumes: existing `README_FILES` and `Path` usage in `tests/test_readme_docs.py`.
- Produces: `test_root_project_state_entrypoints_link_canonical_sources()`.

- [ ] **Step 1: Write the failing docs health guard**

Add this constant near the existing path constants in `tests/test_readme_docs.py`:

```python
ROOT_STATE_DOCS = {
    Path("PLAN.md"): (
        "docs/superpowers/plans/",
        "BACKLOG.md",
        "WORKLOG.md",
        "DECISIONS.md",
    ),
    Path("BACKLOG.md"): (
        "docs/IMPROVEMENTS.md",
        "docs/architecture/improvement-catalog.md",
        "PROJECT-STATE-ENTRYPOINTS",
    ),
    Path("WORKLOG.md"): (
        "PROJECT-STATE-ENTRYPOINTS",
        "docs/superpowers/plans/2026-06-28-project-state-entrypoints.md",
        "uv run pytest",
    ),
    Path("DECISIONS.md"): (
        "PROJECT-STATE-ENTRYPOINTS",
        "docs/decisions/tech-spec/README.md",
        "https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency",
    ),
}
```

Add this test near the other docs entrypoint guards:

```python
def test_root_project_state_entrypoints_link_canonical_sources() -> None:
    for path, required_fragments in ROOT_STATE_DOCS.items():
        assert path.exists(), f"{path} is missing"
        text = path.read_text(encoding="utf-8")
        for fragment in required_fragments:
            assert fragment in text, f"{path} missing {fragment}"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_root_project_state_entrypoints_link_canonical_sources -q
```

Expected: FAIL because `PLAN.md`, `BACKLOG.md`, `WORKLOG.md`, and `DECISIONS.md` do not exist yet.

- [ ] **Step 3: Create the root entrypoints**

Create:

- `PLAN.md`: active goal, canonical plan locations, current loop pointer.
- `BACKLOG.md`: priority policy, existing canonical backlog/catalog links, next candidate queue.
- `WORKLOG.md`: 2026-06-28 `PROJECT-STATE-ENTRYPOINTS` loop entry with planned and final verification commands.
- `DECISIONS.md`: `PROJECT-STATE-ENTRYPOINTS` decision, canonical decision index link, and GitHub Actions concurrency source note.

- [ ] **Step 4: Update README test counts**

Run:

```bash
uv run pytest --collect-only -q | tail -1
```

Update README EN/KO/ZH test badge and test table counts to the collected count.

- [ ] **Step 5: Verify**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_root_project_state_entrypoints_link_canonical_sources -q
uv run pytest tests/test_readme_docs.py -q
uv run pytest --collect-only -q | tail -1
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_readme_docs.py PLAN.md BACKLOG.md WORKLOG.md DECISIONS.md README.md README.ko.md README.zh.md
git commit -m "test(docs): guard project state entrypoints"
```
