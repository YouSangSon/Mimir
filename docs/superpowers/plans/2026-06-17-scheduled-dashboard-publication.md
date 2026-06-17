# Scheduled Dashboard Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** scheduled workflow가 pipeline 성공 뒤 `reports/dashboard.html`을 생성하고 `data/`·`reports/` commit에 포함하게 만든다.

**Architecture:** `mimir.run` 내부에는 dashboard 생성을 넣지 않는다. Reusable GitHub Actions workflow(`.github/workflows/_pipeline.yml`)가 `python -m mimir.run` 성공 뒤 별도 `python -m mimir.dashboard --data-root data --reports-root reports` step을 실행한다. Doctor finding은 dashboard에 표시하지만 `mimir.doctor --strict` hard gate는 추가하지 않는다.

**Tech Stack:** GitHub Actions YAML, Python 3.14, pytest text-based workflow tests, Markdown docs.

---

## File Structure

| File | Responsibility |
|---|---|
| `.github/workflows/_pipeline.yml` | reusable scheduled pipeline wiring. It owns the order `run -> dashboard -> commit`. |
| `tests/test_workflows.py` | text-based workflow contract tests. It avoids YAML parsers so GitHub Actions `on:` is not misread as boolean. |
| `README.md` | English operator-facing scheduled output description. |
| `README.ko.md` | Korean operator-facing scheduled output description. |
| `README.zh.md` | Chinese operator-facing scheduled output description. |
| `docs/architecture/extensibility/README.md` | developer architecture guide for extension points and data/output flow. |
| `docs/architecture/improvement-catalog.md` | improvement tracking catalog. It records OPS1 as implemented and keeps hard gate policy deferred. |
| `docs/superpowers/specs/2026-06-17-scheduled-dashboard-publication-design.md` | source spec. It gets implementation status and acceptance criteria updates after code/docs are verified. |

No new Python production module is needed. `mimir.dashboard` already renders and writes the dashboard. No API, database, data model, frontend, or migration document is needed for this increment.

---

### Task 1: Workflow Contract Tests

**Files:**
- Modify: `tests/test_workflows.py`

- [ ] **Step 1: Add pipeline workflow constants and tests**

Append this code after `ACTION_USES_RE` in `tests/test_workflows.py`:

```python
PIPELINE_WORKFLOW = Path(".github/workflows/_pipeline.yml")
```

Append these tests after `test_github_actions_use_node24_compatible_major_versions()`:

```python
def test_reusable_pipeline_publishes_dashboard_before_commit() -> None:
    text = PIPELINE_WORKFLOW.read_text(encoding="utf-8")

    run_pipeline = text.index("- name: Run pipeline")
    run_dashboard = text.index("- name: Run dashboard")
    commit_data = text.index("- name: Commit data + reports")

    assert run_pipeline < run_dashboard < commit_data
    assert "run: python -m mimir.dashboard --data-root data --reports-root reports" in text


def test_reusable_pipeline_does_not_add_doctor_hard_gate() -> None:
    text = PIPELINE_WORKFLOW.read_text(encoding="utf-8")

    assert "python -m mimir.doctor" not in text
    assert "--strict" not in text
```

- [ ] **Step 2: Run workflow tests to verify RED**

```bash
uv run pytest tests/test_workflows.py -q
```

Expected: FAIL because `_pipeline.yml` does not contain `- name: Run dashboard` yet. The negative hard-gate test may already pass; the ordering test is the required red test.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_workflows.py
git commit -m "test: cover scheduled dashboard workflow contract"
```

---

### Task 2: Workflow Dashboard Step

**Files:**
- Modify: `.github/workflows/_pipeline.yml`

- [ ] **Step 1: Update reusable workflow comment**

Change the top comment in `.github/workflows/_pipeline.yml` from:

```yaml
# Reusable pipeline: collect -> analyze -> history -> deliver, then commit data + reports.
```

to:

```yaml
# Reusable pipeline: collect -> analyze -> history -> evaluate -> deliver -> dashboard,
# then commit data + reports.
```

Keep the existing caller comment below it.

- [ ] **Step 2: Add dashboard step between pipeline and commit**

Insert this block after the existing `Run pipeline` step and before `Commit data + reports`:

```yaml
      - name: Run dashboard
        run: python -m mimir.dashboard --data-root data --reports-root reports
```

Do not add `python -m mimir.doctor`, `--strict`, or `continue-on-error`. Do not change the existing `Run pipeline` step exit behavior.

- [ ] **Step 3: Run workflow tests to verify GREEN**

```bash
uv run pytest tests/test_workflows.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit workflow implementation**

```bash
git add .github/workflows/_pipeline.yml
git commit -m "ci: publish dashboard from scheduled pipeline"
```

---

### Task 3: User and Architecture Docs

**Files:**
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/architecture/improvement-catalog.md`

- [ ] **Step 1: Update English README scheduled workflow text**

In `README.md`, replace the scheduled workflow blockquote under the CLI examples with:

```markdown
> The scheduled workflows (hourly/daily/weekly/monthly) call the reusable pipeline, which chains `collect → analyze → history → evaluate → deliver → dashboard` and commits `data/` and `reports/` to the repo. The daily HTML report is kept permanently at `reports/YYYY/MM/DD.html`, `reports/index.html` browses the archive, and `reports/dashboard.html` is refreshed as the latest operations dashboard.
```

- [ ] **Step 2: Update Korean README scheduled workflow text**

In `README.ko.md`, replace the scheduled workflow blockquote under the CLI examples with:

```markdown
> 스케줄 워크플로(hourly/daily/weekly/monthly)는 reusable pipeline을 호출해 `collect → analyze → history → evaluate → deliver → dashboard`를 실행하고 `data/`·`reports/`를 repo에 커밋한다. 일일 HTML 리포트는 `reports/YYYY/MM/DD.html`로 영구 보관되고, `reports/index.html`은 리포트 archive를 보여주며, `reports/dashboard.html`은 최신 운영 대시보드로 갱신된다.
```

- [ ] **Step 3: Update Chinese README scheduled workflow text**

In `README.zh.md`, replace the scheduled workflow blockquote under the CLI examples with:

```markdown
> 调度工作流（hourly/daily/weekly/monthly）会调用 reusable pipeline，按 `collect → analyze → history → evaluate → deliver → dashboard` 执行，并把 `data/` 和 `reports/` 提交到 repo。每日 HTML 报告以 `reports/YYYY/MM/DD.html` 永久保存，`reports/index.html` 用于浏览报告归档，`reports/dashboard.html` 会刷新为最新运维仪表盘。
```

- [ ] **Step 4: Update extensibility guide output-surface row**

In `docs/architecture/extensibility/README.md`, replace the `출력 표면` table row with:

```markdown
| 출력 표면 | `daily_report`, `dashboard`, `digest` | `mimir/report/` | 일일 리포트와 대시보드가 인사이트·과거사례·평가를 표시한다. Scheduled workflow는 pipeline 성공 뒤 dashboard CLI를 실행해 `reports/dashboard.html`을 최신 운영 표면으로 publish한다 |
```

- [ ] **Step 5: Update extensibility guide data-flow paragraph**

In `docs/architecture/extensibility/README.md`, replace the paragraph immediately after the Mermaid diagram with:

```markdown
`mimir.run`은 scheduled pipeline에서 `collect -> analyze -> history -> evaluate -> deliver` 순서로 실행한다. `evaluate`는 주문이나 외부 API를 호출하지 않는다. 저장된 `insights`와 `prices`만 읽어 시그널 성적표를 만든다. Reusable scheduled workflow는 `mimir.run` 성공 뒤 `mimir.dashboard`를 실행해 같은 commit에 최신 `reports/dashboard.html`을 포함한다.
```

- [ ] **Step 6: Add OPS1 to improvement catalog summary**

In `docs/architecture/improvement-catalog.md`, add this row after the `C1` row in the "한눈에 보기" table:

```markdown
| **OPS1** | Scheduled dashboard publication (`reports/dashboard.html`) | 운영가시성 | README + 현행 spec | **✅ 구현 완료 (2026-06-17)** | workflow + 테스트 + docs · [spec](../superpowers/specs/2026-06-17-scheduled-dashboard-publication-design.md) |
```

- [ ] **Step 7: Add OPS1 implementation section**

In `docs/architecture/improvement-catalog.md`, add this section after the `### C1. 데이터 신선도·품질 닥터 — **구현 완료**` section and before `### BF-MANIFEST...`:

```markdown
### OPS1. Scheduled dashboard publication — **구현 완료 (2026-06-17)**

`mimir.dashboard`는 저장된 데이터, 최신 manifest, doctor finding을 읽어 `reports/dashboard.html`을 만들 수 있었다. 하지만 reusable scheduled workflow는 `python -m mimir.run` 뒤 바로 `git add data reports`를 실행했다. 그래서 scheduled run이 일일 리포트와 status page는 커밋해도 최신 dashboard를 생성하지 않았다.

구현 후 `_pipeline.yml`은 `Run pipeline` 뒤, `Commit data + reports` 앞에서 `python -m mimir.dashboard --data-root data --reports-root reports`를 실행한다. Hourly, daily, weekly, monthly caller는 모두 같은 reusable workflow를 호출하므로 cadence별 중복 없이 dashboard publish 계약을 공유한다.

Doctor WARN/CRITICAL은 dashboard health table에 표시한다. 그러나 scheduled workflow에 `python -m mimir.doctor`나 `--strict` hard gate는 넣지 않는다. Existing `mimir.run` collect failure gate는 그대로 유지하고, doctor finding을 배포 차단 정책으로 쓰는 문제는 별도 설계로 분리한다.
```

- [ ] **Step 8: Update improvement catalog sequencing list**

In `docs/architecture/improvement-catalog.md`, add this line after `BF-MANIFEST ─ backfill success/failure manifest`:

```text
OPS1 ─────── scheduled dashboard publication · reports/dashboard.html
```

- [ ] **Step 9: Update improvement catalog conclusion**

Replace the final conclusion sentence with:

```markdown
**결론.** 본 작업은 *확장성 천장 제거 + 성숙기 피드백 루프 + 운영 가시성 강화*를 만드는 흐름이다. A3, A3b, A3c, R1a, R1b, R1c, R1d, R1e, MR1, D2, C3, BF-MANIFEST, OPS1까지 구현되었고, 남은 신규 아키텍처 부채는 provider별 RSS live discovery다.
```

- [ ] **Step 10: Run documentation grep checks**

```bash
rg -n "collect → analyze → history → deliver|daily workflow chains|매일 워크플로는|每日工作流将" README.md README.ko.md README.zh.md docs/architecture/extensibility/README.md .github/workflows/_pipeline.yml
```

Expected: no matches.

- [ ] **Step 11: Commit docs**

```bash
git add README.md README.ko.md README.zh.md docs/architecture/extensibility/README.md docs/architecture/improvement-catalog.md
git commit -m "docs: document scheduled dashboard publication"
```

---

### Task 4: Spec Completion Update

**Files:**
- Modify: `docs/superpowers/specs/2026-06-17-scheduled-dashboard-publication-design.md`

- [ ] **Step 1: Update spec status**

Change the status line near the top from:

```markdown
> **상태**: 설계 승인됨. 구현 전.
```

to:

```markdown
> **상태**: 구현 완료.
```

- [ ] **Step 2: Mark acceptance criteria complete**

In section `## 7. 수용 기준`, change every unchecked box from `- [ ]` to `- [x]` after Tasks 1-3 pass. The completed block should be:

```markdown
- [x] `_pipeline.yml`이 `Run pipeline` 뒤, `Commit data + reports` 앞에서 `python -m mimir.dashboard --data-root data --reports-root reports`를 실행한다.
- [x] `_pipeline.yml` 주석이 실제 흐름을 `collect -> analyze -> history -> evaluate -> deliver -> dashboard`로 설명한다.
- [x] `tests/test_workflows.py`가 dashboard step의 존재, command, 순서를 검증한다.
- [x] `tests/test_workflows.py`가 `_pipeline.yml`에 `mimir.doctor`와 `--strict` hard gate가 없음을 검증한다.
- [x] README 3개 언어가 모든 scheduled cadence가 reusable workflow를 통해 `reports/dashboard.html`도 갱신한다고 설명한다.
- [x] Architecture/improvement docs가 OPS1 완료 상태와 doctor hard gate 보류 정책을 설명한다.
- [x] Doctor WARN/CRITICAL은 dashboard에 표시되지만 workflow 실패 조건으로 쓰지 않는다는 정책이 문서에 남는다.
- [x] 기존 `mimir.run` collect failure gate는 변경하지 않는다.
- [x] `uv run pytest tests/test_workflows.py -q`가 통과한다.
- [x] `uv run ruff check .`, `uv run mypy mimir`, `uv run pytest -q`가 통과한다.
```

- [ ] **Step 3: Run placeholder scan**

```bash
rg -n "TB[D]|TO[D]O|similar[ ]to|구현 전" docs/superpowers/specs/2026-06-17-scheduled-dashboard-publication-design.md
```

Expected: no matches.

- [ ] **Step 4: Commit spec completion**

```bash
git add docs/superpowers/specs/2026-06-17-scheduled-dashboard-publication-design.md
git commit -m "docs: mark scheduled dashboard publication complete"
```

---

### Task 5: Quality Gates and Final Review

**Files:**
- No planned source edits. This task verifies the complete branch.

- [ ] **Step 1: Run targeted workflow tests**

```bash
uv run pytest tests/test_workflows.py -q
```

Expected: PASS.

- [ ] **Step 2: Run lint**

```bash
uv run ruff check .
```

Expected: PASS.

- [ ] **Step 3: Run type check**

```bash
uv run mypy mimir
```

Expected: PASS.

- [ ] **Step 4: Run full test suite**

```bash
uv run pytest -q
```

Expected: PASS. Current baseline before this plan was `438 passed`; this branch adds workflow tests, so the exact count should be higher.

- [ ] **Step 5: Check whitespace**

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 6: Verify branch status**

```bash
git status --short --branch
git log --oneline --decorate --max-count=10
```

Expected: only the pre-existing untracked `uv.lock` is untracked. Do not stage `uv.lock`.

---

## Self-Review

### Spec Coverage

| Spec requirement | Plan coverage |
|---|---|
| Dashboard runs after pipeline and before commit | Task 1 test, Task 2 workflow implementation |
| `_pipeline.yml` comment includes evaluate and dashboard | Task 2 Step 1 |
| Workflow tests cover dashboard command and order | Task 1 |
| Workflow tests cover no doctor hard gate | Task 1 |
| README EN/KO/ZH describe scheduled cadence dashboard publish | Task 3 Steps 1-3 |
| Architecture/improvement docs track OPS1 and hard gate deferral | Task 3 Steps 4-9 |
| Doctor findings visible but not failure gate | Task 1 hard-gate negative test, Task 3 OPS1 section |
| Existing collect failure gate unchanged | Task 2 says not to change `Run pipeline`; Task 4 acceptance criterion |
| Targeted and full quality gates pass | Task 5 |

### Placeholder Scan

This plan intentionally contains no placeholder markers, no copy-by-reference phrases, and no undefined helper function references. Every code-changing step names exact files and exact snippets.

### Type and Command Consistency

The workflow tests use only `Path.read_text`, `str.index`, and substring assertions already compatible with the existing `tests/test_workflows.py` style. Commands consistently use `uv run ...`, matching the repo's current verification flow.
