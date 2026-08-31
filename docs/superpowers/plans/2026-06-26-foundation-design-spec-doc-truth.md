# Foundation Design Spec Docs Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the completed INC1/INC2/INC3 foundation design specs with current implementation truth and prevent stale completion metadata from returning.

**Architecture:** Add one focused docs health guard in `tests/test_readme_docs.py` for the three early completed design specs, then update only those specs and README test counts if the new docs guard changes the collected pytest count. The guard blocks stale fixed test-count claims and unchecked completed acceptance criteria while preserving design-history context.

**Tech Stack:** Python 3.14, pytest docs guards, Markdown design specs, README translations.

## Global Constraints

- Do not touch, stage, remove, or rewrite the pre-existing untracked `uv.lock`.
- Runtime code write scope is empty. Do not change `mimir/*`, config behavior, storage behavior, doctor behavior, typed payload behavior, source building, network, retry, LLM, or workflow behavior.
- Test write scope is `tests/test_readme_docs.py`.
- Documentation write scope is:
  - `docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md`
  - `docs/superpowers/specs/2026-06-13-typed-payload-design.md`
  - `docs/superpowers/specs/2026-06-13-data-doctor-design.md`
  - `README.md`, `README.ko.md`, `README.zh.md` only if the new docs test changes the collected pytest count.
- The INC1 spec must not carry stale fixed counts such as `144 테스트` or `122개 기존 테스트`.
- The INC2 spec must not carry stale fixed counts such as `293 테스트` or `97% 커버리지`.
- The INC3 spec must not carry stale fixed counts such as `179 테스트`.
- Completed acceptance sections for the selected specs must not contain unchecked `- [ ]` items. If a criterion was superseded by later work, mark it checked and state the later truth inline.
- INC3 must document that its original shallow schema check was superseded by INC2 typed `Record.payload` storage-boundary validation, not by a still-active doctor key-existence check.
- INC3 must document that HTML/i18n and dashboard integration now exist, while scheduled `mimir.doctor --strict` hard gating remains intentionally absent.
- If adding this guard changes `_collected_test_count()`, update README EN/KO/ZH badges and test table rows to the true collected count. Do not subtract from the collected count or special-case the guard.

---

### Task 1: Guard and Fix Foundation Design Spec Completion Truth

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md`
- Modify: `docs/superpowers/specs/2026-06-13-typed-payload-design.md`
- Modify: `docs/superpowers/specs/2026-06-13-data-doctor-design.md`
- Modify if collected test count changes: `README.md`, `README.ko.md`, `README.zh.md`

**Interfaces:**
- Consumes: existing docs guard helpers in `tests/test_readme_docs.py`, current implementation truth from `mimir/sources/config.py`, `mimir/core/builder.py`, `mimir/core/payloads.py`, `mimir/storage/schema.py`, `mimir/doctor/*`, `mimir/report/doctor_html.py`, `mimir/report/dashboard.py`, and the related tests.
- Produces: a docs health guard and updated completed design specs that no longer look half-finished or pinned to obsolete suite sizes.

- [ ] **Step 1: Add constants for the selected foundation specs**

Add these constants near the other design-spec paths in `tests/test_readme_docs.py`:

```python
CONFIG_DRIVEN_EXTENSIBILITY_SPEC = Path(
    "docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md"
)
TYPED_PAYLOAD_SPEC = Path(
    "docs/superpowers/specs/2026-06-13-typed-payload-design.md"
)
DATA_DOCTOR_SPEC = Path(
    "docs/superpowers/specs/2026-06-13-data-doctor-design.md"
)
```

- [ ] **Step 2: Write the failing foundation docs truth guard**

Add this test after `test_news_alias_specs_match_current_completion_state`:

```python
def _status_line(text: str) -> str:
    return next(line for line in text.splitlines() if line.startswith("> **상태**:"))


def test_foundation_design_specs_match_current_completion_state() -> None:
    specs = {
        CONFIG_DRIVEN_EXTENSIBILITY_SPEC: (
            "## 6. 수용 기준 (Acceptance)",
            ("144 테스트", "122개 기존 테스트"),
        ),
        TYPED_PAYLOAD_SPEC: (
            "## 7. 수용 기준 (Acceptance)",
            ("293 테스트", "97% 커버리지"),
        ),
        DATA_DOCTOR_SPEC: (
            "## 8. 수용 기준 (Acceptance)",
            ("179 테스트",),
        ),
    }

    texts = {path: path.read_text(encoding="utf-8") for path in specs}

    for path, (acceptance_heading, stale_phrases) in specs.items():
        text = texts[path]
        status = _status_line(text)
        acceptance = _markdown_section(text, acceptance_heading)

        assert "구현 완료" in status
        assert "최신 검증은 README 테스트 배지와 docs health guard가 추적" in status
        assert "- [ ]" not in acceptance, f"{path} still has unchecked acceptance"
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"

    inc1 = texts[CONFIG_DRIVEN_EXTENSIBILITY_SPEC]
    assert "A2" in inc1
    assert "A3" in inc1
    assert "disabled_ids" in inc1

    inc2 = texts[TYPED_PAYLOAD_SPEC]
    assert "`Record.payload` 유니온화" in inc2
    assert "`RawRecord.payload`는 `dict[str, Any]` 유지" in inc2
    assert "Dataset.EVALUATION" in inc2
    assert "BucketStat" in inc2

    inc3 = texts[DATA_DOCTOR_SPEC]
    assert "typed `Record.payload`" in inc3
    assert "storage boundary" in inc3
    assert "render_doctor_html" in inc3
    assert "dashboard" in inc3
    assert "doctor --strict" in inc3
```

- [ ] **Step 3: Verify RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_foundation_design_specs_match_current_completion_state -q
```

Expected: FAIL because the three selected specs still carry stale fixed counts and unchecked completed acceptance criteria.

- [ ] **Step 4: Update the INC1 status line and acceptance section**

In `docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (feat/config-driven-extensibility). 최신 검증은 README 테스트 배지와 docs health guard가 추적하며, ruff · mypy · coverage gate 클린 상태를 유지한다. 후속 A2/A3/A3b에서 macro series registry, 선언적 source registry, source entry points가 추가됐다.
```

Replace `## 6. 수용 기준 (Acceptance)` checklist with checked criteria:

```markdown
## 6. 수용 기준 (Acceptance)

- [x] `config/sources.yaml`에 `sources.fred.series` 추가 시 FRED가 그 시리즈를 수집한다.
- [x] `sources:` 블록 부재 시 FRED/ECOS/RSS가 정확히 `DEFAULT_*`로 동작한다.
- [x] `idempotency_key`가 설정 경로와 무관하게 동일 포맷을 유지한다.
- [x] 잘못된 설정(`fred.series: "x"`, `ecos.series` 필드 누락)이 명확한 `invalid sources.yaml` 계열 에러로 실패한다.
- [x] `run_backfill`이 설정 시리즈를 사용한다.
- [x] `config/sources.yaml` 예시, README 3개 언어, `.env.example`, reference docs가 설정 기반 소스 확장을 설명한다.
- [x] 빈 리스트는 parse layer에서 `None`과 구분되지만 source 생성자는 기존 `DEFAULT_*` fallback을 유지한다. 소스 비활성화는 `disabled_ids`가 담당한다.
- [x] 최신 전체 검증은 README 테스트 배지와 docs health guard가 추적하며 ruff, mypy, pytest, coverage 80% gate가 통과한다.
```

- [ ] **Step 5: Update the INC2 status line and acceptance section**

In `docs/superpowers/specs/2026-06-13-typed-payload-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (Increment 2 typed payload rollout). 최신 검증은 README 테스트 배지와 docs health guard가 추적하며, ruff · mypy · coverage gate 클린 상태를 유지한다. 이후 `Dataset.EVALUATION`/`BucketStat`도 같은 typed payload boundary에 포함됐다.
```

Replace `## 7. 수용 기준 (Acceptance)` checklist with checked criteria:

```markdown
## 7. 수용 기준 (Acceptance)

- [x] `mimir/core/payloads.py`에 6개 소스 페이로드 모델(`PricePayload`, `FredMacroPayload`, `EcosMacroPayload`, `NewsPayload`, `SecFilingPayload`, `DartFilingPayload`) + `MacroPayload`/`FilingPayload` 유니온 별칭 + `parse_payload`가 있다.
- [x] insights/historical은 기존 `Insight`/`HistoricalInsight`를 재사용한다.
- [x] evaluation은 후속 구현에서 `BucketStat` typed payload로 같은 boundary에 합류했다.
- [x] 골든 round-trip은 어댑터 페이로드 리터럴 → `parse_payload` → dump가 기존 dict 경로와 바이트 동일함을 고정한다.
- [x] 미지의 키(`extra`)·키 누락·형 불일치가 `PayloadSchemaError` 또는 storage-boundary validation failure로 실패한다.
- [x] `fred` dict는 `FredMacroPayload`, `ecos` dict는 `EcosMacroPayload`로 해소되며 반대 모델로는 실패한다. FILINGS도 SEC/DART 모델로 분기한다.
- [x] 4개 시그널, LLM sentiment, historical series가 타입드 접근 helper로 기존 출력 의미를 유지한다.
- [x] `Record.payload` 유니온화 후 `Record.model_validate_json`/`model_dump_json` round-trip이 주요 데이터셋에서 바이트 동일하다.
- [x] `RawRecord.payload`는 `dict[str, Any]`를 유지한다.
- [x] 최신 전체 검증은 README 테스트 배지와 docs health guard가 추적하며 ruff, mypy, pytest, coverage 80% gate가 통과한다.
```

- [ ] **Step 6: Update the INC3 status line and acceptance section**

In `docs/superpowers/specs/2026-06-13-data-doctor-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (Increment 3 doctor MVP + 후속 HTML/i18n/dashboard 통합). 최신 검증은 README 테스트 배지와 docs health guard가 추적하며, ruff · mypy · coverage gate 클린 상태를 유지한다. scheduled workflow의 `mimir.doctor --strict` hard gate는 의도적으로 추가하지 않았다.
```

Replace `## 8. 수용 기준 (Acceptance)` checklist with checked criteria:

```markdown
## 8. 수용 기준 (Acceptance)

- [x] **신선 데이터** 합성 트리(모든 기대 데이터셋 최신 파티션 존재) + 고정 `now` → 모든 `Finding`이 OK, `exit_code == 0`.
- [x] **정체 데이터**: `prices` 최신이 6 영업일 전 → CRITICAL(`stale`), `exit_code == 1`.
- [x] **누락**: 기대 데이터셋 `macro` 파티션 전무 → CRITICAL(`missing`).
- [x] **빈 파티션**: 최신 `prices` 파티션 존재하나 0건 → CRITICAL(`empty`).
- [x] **짧은 파티션**: 최신 레코드 수가 최근 중앙값의 30% 미만 → WARN(`short`); 파티션 < 3개면 점검 건너뛰고 INFO.
- [x] **워치리스트 커버리지**: 워치리스트에 `XYZ` 추가했으나 `prices`에 전무 → CRITICAL(`missing`, "수집된 적 없음").
- [x] **영업일 오탐 방지**: 금요일 종가가 최신, `now`=월요일 → DAILY 나이 = 1 영업일 → OK(오탐 없음).
- [x] **매크로 cadence 이질성**: `CPIAUCSL`(MONTHLY 등록) 최신이 20일 전 → OK. doctor는 `macro_series_cadences()`를 사용한다.
- [x] **미등록 매크로 시리즈**: 테이블에 없는 새 시리즈는 `DEFAULT_MACRO_CADENCE`(MONTHLY)로 평가 + 존재 사실 INFO.
- [x] **키 부재 ≠ 점검 소실**: 기대 집합이 `build_sources`가 아니라 명시 상수에서 옴을 단언한다. FRED 키 없이도 `macro` 부재가 CRITICAL로 잡힌다.
- [x] **스키마**: INC2 이후 typed `Record.payload` union이 storage boundary에서 payload schema drift를 실패시키므로 doctor의 얕은 key-existence check는 제거되었다.
- [x] **읽기 전용**: 닥터 실행 전후 `data/` 바이트 동일(쓰기 0)을 테스트로 단언한다.
- [x] **출력**: `--format json`이 유효 `DoctorReport` JSON을 출력하고, `--html`은 `render_doctor_html`로 3언어 라벨 섹션을 렌더한다.
- [x] **Dashboard 통합**: `mimir.dashboard`는 doctor report를 읽기 전용으로 생성해 health 섹션에 포함한다.
- [x] **CLI 종료코드**: CRITICAL → 1, WARN → 0, `--strict` 시 WARN → 1.
- [x] scheduled workflow에는 `python -m mimir.doctor --strict` hard gate를 추가하지 않았다. 기존 collect failure gate와 dashboard publication flow를 유지한다.
- [x] 네트워크 호출 0 · ruff · mypy strict 클린 · 커버리지 ≥ 80%.
```

- [ ] **Step 7: Verify GREEN for targeted guard**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_foundation_design_specs_match_current_completion_state -q
```

Expected: PASS.

- [ ] **Step 8: Run full docs guard file and update README counts if needed**

Run:

```bash
uv run pytest tests/test_readme_docs.py -q
```

Expected: if `test_readme_test_badges_match_collected_pytest_count` fails because the collected count increased by this new guard, update `README.md`, `README.ko.md`, and `README.zh.md` badges and test table rows to the actual collected count, then rerun the same command until it passes.

- [ ] **Step 9: Run full gates**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: full suite passes, ruff passes, mypy passes, and diff check has no output.

- [ ] **Step 10: Commit**

Stage only the intentional files:

```bash
git add tests/test_readme_docs.py \
  docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md \
  docs/superpowers/specs/2026-06-13-typed-payload-design.md \
  docs/superpowers/specs/2026-06-13-data-doctor-design.md \
  README.md README.ko.md README.zh.md
git commit -m "test(docs): guard foundation spec truth"
```
