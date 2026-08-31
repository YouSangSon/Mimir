# Analysis Design Doc Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the original S2 analysis design spec and README roadmap rows with the current implemented scoring model and off-by-default LLM sentiment seam.

**Architecture:** Add docs health tests that fail on the stale S2 scoring formula and stale "LLM later" README wording, then update only documentation to match the current runtime truth. The current scorer remains the source of truth: `net` normalizes by directional weight only, stars reflect `abs(net)` directional conviction, and directionless activity contributes to `attention` but not stars.

**Tech Stack:** Python 3.14, pytest docs guards in `tests/test_readme_docs.py`, Markdown docs under `docs/superpowers/specs/` and root README translations.

## Global Constraints

- Do not touch, stage, remove, or rewrite the pre-existing untracked `uv.lock`.
- Runtime code write scope is empty. Do not change `mimir/analysis/scorer.py`, `mimir/analysis/engine.py`, signal implementations, storage, config, plugin behavior, or LLM behavior.
- Test write scope is `tests/test_readme_docs.py`.
- Documentation write scope is `docs/superpowers/specs/2026-05-31-analysis-design.md`, `README.md`, `README.ko.md`, and `README.zh.md`.
- The S2 design spec must document the current scoring formula:
  - `directional_weight = Σ weight` for directional signals only.
  - `total_weight = Σ weight` for all signals.
  - `net = Σ sign(dir)·strength·confidence·weight / directional_weight`.
  - `attention = Σ strength·confidence·weight / total_weight`.
  - `stars = clamp(round(1 + 4·|net|), 1, 5)`.
- The S2 design spec must state that stars are directional conviction and directionless activity does not raise stars.
- The S2 design spec must not contain stale formula text `Σ sign(dir)·strength·confidence·weight / Σ weight` or `max(|net|, attention)`.
- The S2 design spec and README S2 rows must not describe LLM sentiment as merely future follow-up.
- The S2 design spec and README S2 rows must describe the current LLM sentiment state: implemented as an off-by-default seam that only activates when config, key, and optional extra are present.
- Preserve the existing README test count of `628` unless the test suite count changes for a reason outside this docs guard.
- Keep translations semantically aligned across English, Korean, and Chinese.

---

### Task 1: Guard and Fix S2 Analysis Design Truth

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/superpowers/specs/2026-05-31-analysis-design.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

**Interfaces:**
- Consumes: current implementation truth from `mimir/analysis/scorer.py` and `docs/reference/analysis/scoring.md`.
- Produces: docs guard tests and updated docs that preserve current scoring and LLM seam truth.

- [ ] **Step 1: Add constants for the S2 analysis design spec**

Add this constant near `LLM_SENTIMENT_SEAM_SPEC` in `tests/test_readme_docs.py`:

```python
ANALYSIS_DESIGN_SPEC = Path(
    "docs/superpowers/specs/2026-05-31-analysis-design.md"
)
```

Add this stale phrase tuple near `LLM_SENTIMENT_STALE_SPEC_PHRASES`:

```python
S2_ANALYSIS_DESIGN_STALE_PHRASES = (
    "Σ sign(dir)·strength·confidence·weight / Σ weight",
    "max(|net|, attention)",
    "LLM 시그널 → 하이브리드 후속",
    "LLM은 나중에 시그널 하나로 추가",
    "LLM은 같은 `Signal` 인터페이스를 구현하는 한 시그널로 후속 추가",
    "후속 추가한다",
)
```

- [ ] **Step 2: Write failing S2 scoring design guard**

Add this test after `test_llm_sentiment_seam_spec_matches_implemented_state`:

```python
def test_s2_analysis_design_spec_matches_current_scoring_model() -> None:
    text = ANALYSIS_DESIGN_SPEC.read_text(encoding="utf-8")

    assert "directional_weight = Σ weight  (방향 시그널만; bullish/bearish)" in text
    assert "total_weight       = Σ weight  (모든 시그널)" in text
    assert "net       = Σ sign(dir)·strength·confidence·weight / directional_weight" in text
    assert "attention = Σ strength·confidence·weight / total_weight" in text
    assert "stars     = clamp(round(1 + 4·|net|), 1, 5)" in text
    assert "별점은 방향 확신" in text
    assert "방향 없는 활동" in text
    assert "attention" in text

    for phrase in S2_ANALYSIS_DESIGN_STALE_PHRASES:
        assert phrase not in text, f"{ANALYSIS_DESIGN_SPEC} still says: {phrase}"
```

- [ ] **Step 3: Verify RED for S2 scoring design guard**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_s2_analysis_design_spec_matches_current_scoring_model -q
```

Expected: FAIL because `docs/superpowers/specs/2026-05-31-analysis-design.md` still contains the old total-weight net formula, `max(|net|, attention)`, and stale LLM future wording.

- [ ] **Step 4: Write failing README S2 LLM state guard**

Add this test after the S2 scoring design guard:

```python
def test_readme_s2_rows_match_current_llm_sentiment_state() -> None:
    expectations = {
        Path("README.md"): "Implemented (rules + off-by-default LLM seam)",
        Path("README.ko.md"): "구현 완료 (규칙 기반 + off-by-default LLM seam)",
        Path("README.zh.md"): "已实现（规则 + off-by-default LLM seam）",
    }
    stale_phrases = ("LLM to follow", "LLM 후속", "LLM 后续")

    for path, expected in expectations.items():
        text = path.read_text(encoding="utf-8")
        assert expected in text
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"
```

- [ ] **Step 5: Verify RED for README S2 LLM guard**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_readme_s2_rows_match_current_llm_sentiment_state -q
```

Expected: FAIL because the README S2 roadmap rows still say `LLM to follow`, `LLM 후속`, or `LLM 后续`.

- [ ] **Step 6: Update S2 analysis design scoring text**

In `docs/superpowers/specs/2026-05-31-analysis-design.md`, replace the scoring block with:

```markdown
directional_weight = Σ weight  (방향 시그널만; bullish/bearish)
total_weight       = Σ weight  (모든 시그널)
net       = Σ sign(dir)·strength·confidence·weight / directional_weight   # -1..1 방향 확신
attention = Σ strength·confidence·weight / total_weight                   # 0..1 전체 활동량
direction = BULLISH(net>ε) | BEARISH(net<-ε) | NEUTRAL
stars     = clamp(round(1 + 4·|net|), 1, 5)
confidence= Σ confidence·weight / total_weight
```

Immediately below the block, describe the current behavior:

```markdown
`sign`: BULLISH=+1, BEARISH=-1, NEUTRAL=0. 가격(weight 1.0)·거시(0.3)·LLM 감성(0.8, off-by-default)은 방향 기여, 공시(0.8)·뉴스(0.5)는 NEUTRAL로 attention만 기여한다. 별점은 방향 확신 `|net|`만 반영하므로, 방향 없는 활동(공시·뉴스량)이 많아도 stars는 올라가지 않는다.
```

Update the architecture `scorer.py` line to:

```markdown
  scorer.py        score(results) -> InsightScore(direction, stars, confidence, attention, reasons)
```

- [ ] **Step 7: Update S2 design LLM sections**

In `docs/superpowers/specs/2026-05-31-analysis-design.md`:

- Replace the included/excluded LLM bullet with current state:

```markdown
- `llm_sentiment` 시그널 seam — `llm_sentiment_enabled` + `ANTHROPIC_API_KEY` + `[llm]` extra가 모두 있을 때만 활성화되는 off-by-default 방향성 시그널
```

- Replace the design principle row:

```markdown
| **확장(하이브리드)** | LLM 감성은 같은 `Signal` 인터페이스의 `llm_sentiment`로 구현되어 있으며, 비용/키 조건을 만족할 때만 활성화 |
```

- Replace the future section with:

```markdown
## 11. 현재 LLM seam과 남은 미래 작업

`llm_sentiment`는 같은 `Signal` 인터페이스를 구현하는 off-by-default 방향성 시그널로 현재 코드에 존재한다. 기본 경로는 유료 LLM 호출 0건이며, `llm_sentiment_enabled`, `ANTHROPIC_API_KEY`, `[llm]` extra가 모두 있을 때만 build된다. 현재 구현은 persistent LLM sentiment cache dataset을 제공하지 않는다. 남은 미래 작업은 모델 품질 개선, 비용 관측, cache 설계처럼 별도 spec이 필요한 운영 고도화다.
```

- [ ] **Step 8: Update README S2 roadmap rows**

Change the S2 row in `README.md` to:

```markdown
| **S2 Analysis & Scoring** | Rule-based + off-by-default LLM ⭐ star-rated insights (direction + confidence) | ✅ Implemented (rules + off-by-default LLM seam) |
```

Change the S2 row in `README.ko.md` to:

```markdown
| **S2 Analysis & Scoring** | 규칙 기반 + off-by-default LLM ⭐별점(방향성+확신도) 인사이트 | ✅ 구현 완료 (규칙 기반 + off-by-default LLM seam) |
```

Change the S2 row in `README.zh.md` to:

```markdown
| **S2 Analysis & Scoring** | 规则 + off-by-default LLM ⭐星级（方向性+确信度）洞见 | ✅ 已实现（规则 + off-by-default LLM seam） |
```

- [ ] **Step 9: Verify GREEN for docs guard tests**

Run:

```bash
uv run pytest tests/test_readme_docs.py -q
```

Expected: all docs guard tests pass.

- [ ] **Step 10: Run full gates**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: full suite passes, ruff passes, mypy passes, diff check passes.

- [ ] **Step 11: Commit**

Stage only the intentional docs-truth files:

```bash
git add tests/test_readme_docs.py docs/superpowers/specs/2026-05-31-analysis-design.md README.md README.ko.md README.zh.md
git commit -m "test(docs): guard analysis design scoring truth"
```
