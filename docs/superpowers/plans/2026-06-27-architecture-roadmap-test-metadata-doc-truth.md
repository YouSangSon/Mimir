# Architecture Roadmap Test Metadata Doc Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the architecture roadmap from publishing stale fixed coverage metadata as current testing truth.

**Architecture:** Add one docs health guard beside the existing README/architecture health tests. Update only the roadmap test-principle line and README EN/KO/ZH test counts created by the new guard.

**Tech Stack:** Python 3.14, pytest, Markdown docs.

---

### Task 1: Guard roadmap testing metadata

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/architecture/roadmap.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

- [ ] **Step 1: Write the failing test**

Add `ROADMAP = Path("docs/architecture/roadmap.md")` near the existing docs path constants.

Add this test near `test_readme_and_architecture_health_metadata_use_current_contract()`:

```python
def test_architecture_roadmap_testing_metadata_uses_current_contract() -> None:
    text = ROADMAP.read_text(encoding="utf-8")
    cross_cutting = _markdown_section(text, "## 5. 횡단 관심사 (모든 스펙에 적용)")

    assert "TDD" in cross_cutting
    assert "README 테스트 배지와 docs health guard" in cross_cutting
    assert "coverage 80%+" not in cross_cutting
    assert "커버리지 80%+" not in cross_cutting
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_architecture_roadmap_testing_metadata_uses_current_contract -q
```

Expected: fails because `docs/architecture/roadmap.md` still says `커버리지 80%+`.

- [ ] **Step 3: Update the roadmap line**

Replace the stale testing bullet in `docs/architecture/roadmap.md` with:

```markdown
- **테스트** — TDD를 기본으로 하고, 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.
```

- [ ] **Step 4: Update README test counts**

Run:

```bash
uv run pytest --collect-only -q | tail -1
```

Update the README EN/KO/ZH test badge and test table counts to the collected count.

- [ ] **Step 5: Verify**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_architecture_roadmap_testing_metadata_uses_current_contract -q
uv run pytest tests/test_readme_docs.py -q
uv run pytest --collect-only -q | tail -1
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_readme_docs.py docs/architecture/roadmap.md README.md README.ko.md README.zh.md
git commit -m "test(docs): guard architecture roadmap test metadata"
```
