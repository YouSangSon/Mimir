# Increment 5. LLM 뉴스 감성 시그널 — off-by-default seam 설계

> **스펙 ID**: INC5 (카탈로그 B2)
> **작성일**: 2026-06-13
> **상태**: ✅ seam 구현 완료. 기본 파이프라인은 LLM 호출 0건. 활성화 조건은 `[llm]` extra + `ANTHROPIC_API_KEY` + `llm_sentiment_enabled: true`의 세 조건 AND다. 2026-06-16 R1a 이후 `analysis.news.aliases` 기반 shared matcher를 사용하며, 2026-06-23 AN2 이후 classifier verdict cardinality guard가 추가됐다.
> **선행**: [발전 카탈로그](../../architecture/improvement-catalog.md) · [S2 Analysis](2026-05-31-analysis-design.md)

---

## 1. 현재 구현 상태

이 문서는 INC5 LLM 뉴스 감성 seam의 현재 구현 계약을 기록한다. 초기 설계 목적은 유료 LLM 시그널을 기본 pipeline에 넣되, 사용자가 명시적으로 비용과 key를 승인하기 전에는 무료 경로가 절대 바뀌지 않게 하는 것이었다. 현재 repo는 그 seam을 구현했다.

`LlmSentimentSignal`은 구현되어 있으며, 기본 pipeline에서는 off-by-default gate 때문에 등록되지 않는다.

| 항목 | 현재 상태 |
|---|---|
| Signal 구현 | `mimir/analysis/signals/llm_sentiment.py`의 `LlmSentimentSignal` |
| Builder gate | `build_signals(config, settings, *, classifier=...)`가 세 조건을 확인한 뒤 append |
| 기본 동작 | `llm_sentiment_enabled=false`, key 없음, 또는 optional package 없음이면 signal 미등록 |
| 무료 원칙 | 기본 경로의 LLM 호출은 0건이고, `anthropic`도 import하지 않는다 |
| 테스트 seam | `HeadlineClassifier` Protocol fake를 주입해 네트워크·key 없이 검증 |
| 캐시 | 현재 구현은 `LlmSentimentCache`나 `Dataset.LLM_SENTIMENT`를 제공하지 않는다 |

`build_signals(config, settings, *, classifier=...)`는 config와 settings를 받는다. `classifier`는 테스트·임베디드 호출자가 실제 Anthropic client 대신 fake classifier를 넣는 seam이다. AN5 이후 같은 함수는 외부 signal plugin specs 주입을 위한 `specs=`도 받지만, INC5의 LLM enablement 계약은 `classifier`와 세 조건 gate에 의해 결정된다.

---

## 2. 문제 정의 — `news_volume`의 한계

`NewsVolumeSignal`은 저장된 뉴스가 특정 symbol을 언급하는지 보고 활동량을 측정한다. 구조적 한계는 두 가지다.

1. **방향성 없음.** 항상 `SignalDirection.NEUTRAL`을 반환한다. Attention에는 기여하지만 방향 확신도에는 기여하지 않는다.
2. **티커 언급 희소성.** 공식 RSS feed는 제목에 티커를 거의 싣지 않는다. R1a/R1d 이후 alias matcher와 symbol-tagged feed가 완화하지만, 뉴스 tone 자체는 여전히 규칙 기반으로 알 수 없다.

LLM 감성 signal은 같은 NEWS records의 `title`과 `summary`를 입력으로 받아 bullish/bearish/neutral 방향과 confidence를 산출한다. 이는 `news_volume`을 대체하기보다, 현재 구현에서는 방향성 있는 보조 signal로 병존한다.

---

## 3. 핵심 원칙 — source gate가 아니라 analysis signal gate

GRAY source gate는 collection 시점의 `Registry.due()`가 source metadata를 보고 수집 여부를 결정하는 장치다. LLM 감성은 source가 아니라 analysis signal이므로, 분석 시점의 signal builder에서 별도 gate를 갖는다.

```
[수집 평면]  Registry.due() ──(gray_enabled, legal_status)──> source filter
[분석 평면]  build_signals(config, settings) ──(flag + key + package)──> signal filter
```

엔진과 scorer 계약은 바뀌지 않는다. `AnalysisEngine.run()`은 모든 signal을 같은 `Signal.evaluate(symbol, market, as_of, reader)` protocol로 호출하고, `SignalResult | None`만 본다. `LlmSentimentSignal`도 이 protocol을 만족한다.

---

## 4. Off-by-default gate

`LlmSentimentSignal`은 다음 세 조건이 모두 참일 때만 signal list에 추가된다.

| 조건 | 출처 | 부재 시 동작 |
|---|---|---|
| `llm_sentiment_enabled: true` | `config/sources.yaml` / `SourcesConfig` | signal 미등록 |
| `ANTHROPIC_API_KEY` 존재 | `Settings.anthropic_api_key` | warning 후 signal 미등록 |
| `anthropic` package 설치 | optional `[llm]` extra | warning 후 signal 미등록 |

Fake classifier가 주입된 테스트 경로는 package check를 우회한다. 이는 network-free tests를 만들기 위한 예외이며, 실제 paid path는 optional package가 있어야 한다.

### 4.1 Settings

`Settings`는 `ANTHROPIC_API_KEY`를 `anthropic_api_key`로 읽는다. CLI runtime path는 기존 `.env` autoload 정책을 따르므로, repository에 secret을 저장하지 않는다.

### 4.2 SourcesConfig

`SourcesConfig`는 다음 field를 갖는다.

```yaml
llm_sentiment_enabled: false
llm_sentiment_max_headlines: 50
```

`llm_sentiment_max_headlines`는 `1`에서 `50` 사이여야 한다. 이 상한은 새로 분류할 headline 수를 제한해 paid path의 비용 폭주를 막는다. 기본값과 flag off 상태에서는 유료 호출이 없다.

### 4.3 Builder wiring

Current builder contract:

```python
def build_signals(
    config: SourcesConfig | None = None,
    settings: Settings | None = None,
    *,
    classifier: HeadlineClassifier | None = None,
    specs: Sequence[SignalSpec] | None = None,
) -> list[Signal]:
    ...
```

LLM branch는 `_llm_sentiment_enabled(cfg, settings, classifier)`가 참일 때만 local import를 실행한다.

```python
if _llm_sentiment_enabled(cfg, settings, classifier):
    from mimir.analysis.signals.llm_sentiment import (
        AnthropicHeadlineClassifier,
        LlmSentimentSignal,
    )
    signals.append(
        LlmSentimentSignal(
            classifier=classifier or AnthropicHeadlineClassifier(settings.anthropic_api_key),
            max_headlines=cfg.llm_sentiment_max_headlines,
            aliases=_news_aliases(cfg),
        )
    )
```

이 local import가 기본 경로의 optional dependency invariant를 지킨다. `build_signals()`를 import하거나 flag-off path를 호출해도 `anthropic`은 import되지 않는다.

---

## 5. `LlmSentimentSignal` contract

### 5.1 Protocol fit

```python
class LlmSentimentSignal:
    id = "llm_sentiment"

    def __init__(
        self,
        *,
        classifier: HeadlineClassifier,
        max_headlines: int,
        aliases: Mapping[str, Sequence[str]] | None = None,
        weight: float = 0.8,
    ) -> None: ...

    def evaluate(
        self, symbol: str, market: Market, as_of: date, reader: DataReader
    ) -> SignalResult | None: ...
```

The signal returns the existing `SignalResult` shape: `signal`, `direction`, `strength`, `confidence`, `reason`, and `weight`. Engine, scorer, persisted `Insight`, and report rendering do not need a special LLM branch.

### 5.2 Input selection

`LlmSentimentSignal` reads `Dataset.NEWS` using `DataReader.read_captured_window(..., since=as_of, until=as_of)`. It uses `NewsMentionMatcher`, the same matcher as `NewsVolumeSignal`.

Matcher behavior:

- symbol-tagged RSS records match before text inspection
- aliases from `analysis.news.aliases` are honored
- default aliases are included unless `analysis.news.use_default_aliases=false`
- alias configuration alone never enables LLM calls

Only stored `title` and `summary` are sent to the classifier. Full article text is not fetched or transmitted.

### 5.3 Aggregation

Classifier output is per headline:

```python
class HeadlineVerdict(BaseModel):
    direction: SignalDirection
    confidence: float
    rationale: str
```

The signal aggregates N headline verdicts into one `SignalResult`.

| Output field | Current calculation |
|---|---|
| `signed[i]` | `DIRECTION_SIGN[direction] * confidence` |
| `mean_signed` | average of `signed` |
| `direction` | positive above epsilon -> BULLISH, negative below epsilon -> BEARISH, otherwise NEUTRAL |
| `strength` | `abs(mean_signed)` capped at `1.0` |
| `confidence` | mean verdict confidence multiplied by volume factor |
| `reason` | headline count, bull/bear/neutral counts, mean signed value, cap note if partial |
| `weight` | constructor value, default `0.8` |

Volume factor is `min(len(verdicts) / 3, 1.0)`, so one headline is downweighted and three or more headlines receive full volume confidence.

### 5.4 Failure behavior

`LlmSentimentSignal.evaluate()` returns `None` for a symbol when:

- no matching news records exist
- classifier raises an exception
- classifier returns a verdict count different from the input headline count

Classifier exceptions are logged with traceback. Cardinality mismatch logs a warning with actual count, expected count, and symbol, then skips the symbol rather than partially averaging malformed output.

AN4 later added engine-level signal isolation as well. If an unexpected signal implementation error escapes `evaluate()`, `AnalysisEngine` skips only that signal result for that symbol and continues.

---

## 6. 비용과 cache boundary

Current implementation has headline cap and batching, but no persistent sentiment cache.

| Boundary | Current state |
|---|---|
| Per-run headline cap | implemented through `llm_sentiment_max_headlines` |
| Batch round-trip reduction | implemented by sending multiple headlines to classifier in one call |
| Persistent verdict reuse across runs | not implemented |
| New dataset for verdicts | not implemented |

This is deliberate documentation truth: any future persistent verdict cache must be a separate design/implementation slice. It should define storage layout, invalidation by model version, idempotency keys, stale behavior, and docs/tests before it is described as current behavior.

The rough cost envelope remains low because the cap is per headline, not per API call. With 50 new headlines/day and a small classification model, the paid path is bounded; however the default path remains free because the LLM signal is not registered unless the user opts in and provides credentials.

---

## 7. Determinism and tests

Tests use `HeadlineClassifier` fake implementations. They do not call Anthropic, require an API key, or import the optional package on the default path.

Current test coverage includes:

| Test area | Contract |
|---|---|
| Builder off-by-default | no config/settings returns the four base signals |
| Builder key/flag/package gate | all required conditions must be met |
| Default import invariant | `anthropic` is not imported on default path |
| Fake classifier path | fake classifier enables deterministic unit tests |
| Alias matcher | `news_volume` and opt-in `llm_sentiment` share alias/default alias behavior |
| Captured window | news captured today is eligible even if published earlier |
| Aggregation | mixed verdicts become one deterministic `SignalResult` |
| Volume factor | small headline counts downweight confidence |
| Cap behavior | cap logs partial classification and marks reason |
| Cardinality guard | mismatched verdict counts skip the symbol |
| Exception guard | classifier exception logs and returns `None` |
| Missing package error | constructing real classifier without optional package fails loudly |

---

## 8. Privacy, copyright, and ToS boundary

Mimir sends only stored headline/title and summary metadata to the classifier. RSS summaries are already capped by the source parser. The signal does not fetch full article text, bypass paywalls, scrape pages, or send stored secrets in prompts.

The output is still an analysis signal, not trading advice. Existing report disclaimers and the analysis/execution separation remain unchanged.

---

## 9. Acceptance Criteria

| # | Criterion | Evidence |
|---|---|---|
| AC1 | Default pipeline returns only base signals and makes no LLM call | builder tests |
| AC2 | LLM signal registers only with flag + key + package, except fake classifier tests | builder tests |
| AC3 | Default builder path does not import `anthropic` | import invariant test |
| AC4 | Signal returns normal `SignalResult` and engine/scorer need no special branch | signal and engine tests |
| AC5 | Headline verdicts aggregate deterministically into one result | signal tests |
| AC6 | `max_headlines` cap logs and marks partial results | signal tests |
| AC7 | Classifier cardinality mismatch skips malformed batches | AN2 tests |
| AC8 | Tests run with no network and no real key | fake classifier tests |
| AC9 | No persistent LLM sentiment cache is documented as implemented | docs guard in `tests/test_readme_docs.py` |

---

## 10. Future Work

| Item | Notes |
|---|---|
| Persistent verdict cache | Separate design required. Must define dataset/storage contract, model-version invalidation, and replay semantics before implementation. |
| Model comparison | B1 backtesting should decide whether a more expensive model improves signal quality enough to justify cost. |
| KR headline quality | Korean headline classification quality and token cost need sample measurement. |
| Batch API | Could reduce cost for cron workloads, but polling/wait behavior must fit GitHub Actions runtime. |
| Signal weight config | Currently deferred. Weight is a code constant like other signals; YAML exposure should be designed across all signals if needed. |
