# Increment 5. LLM 뉴스 감성 시그널 — off-by-default seam 설계

> **스펙 ID**: INC5 (카탈로그 B2)
> **작성일**: 2026-06-13
> **상태**: ✅ seam 구현 완료 (Increment 5 — off-by-default 스캐폴드). 기본 파이프라인은 LLM 호출 0건. 활성화: `[llm]` extra + `ANTHROPIC_API_KEY` + `llm_sentiment_enabled: true` (세 조건 AND). 실제 유료 classify 경로는 사용자 opt-in 시에만 실행(테스트는 fake classifier). 313 테스트 · ruff·mypy strict 클린.
> **선행**: [발전 카탈로그](../../architecture/improvement-catalog.md) · [S2 Analysis](2026-05-31-analysis-design.md)

---

## 1. 목적과 비-목적

이 문서는 **LLM 뉴스 감성 시그널을 지금 구현하지 않는다.** 대신 기존 `Signal` 프로토콜에 끼울 수 있는 *경계(seam)* 와 *off-by-default 스캐폴드*를 명시한다. Anthropic Claude API를 호출하는 유료 시그널이므로, 기본 파이프라인이 단 한 번도 유료 호출을 발생시키지 않도록 GRAY 소스와 동일한 **옵트인 토글 + 키 게이트** 철학으로 설계한다.

| | 이 스펙이 하는 것 | 이 스펙이 하지 않는 것 |
|---|---|---|
| 범위 | seam·게이트·캐시·계약·테스트 계획·비용 봉투를 확정 | 실제 `LlmSentimentSignal` 코드를 작성 |
| 결과물 | 엄밀한 spec(본 문서) | 키 발급·비용 승인·구현 PR |
| 트리거 | 사용자가 `ANTHROPIC_API_KEY` + 월 비용 한도를 승인 | (그 전까지는 설계로만 존재) |

**왜 설계만 하는가.** 로드맵은 "규칙 기반 → 하이브리드(LLM 후속)"를 명시하고, 백로그 R1은 `news_volume`이 실데이터에서 거의 무력함을 인정한다(공식 RSS 피드에 티커가 거의 없어 `_mentions`가 매칭되지 않음). LLM 감성은 가장 큰 분석 가치를 가지지만, **유료 호출을 기본값으로 켜면 프로젝트의 무료(free) 원칙과 정면충돌한다.** 따라서 분석/실행 분리와 동일한 정신으로, 켜는 결정과 비용 책임을 사용자에게 명시적으로 넘긴다.

---

## 2. 문제 정의 — `news_volume`의 한계

기존 `NewsVolumeSignal`(`mimir/analysis/signals/news_volume.py`)은 두 가지 구조적 한계를 가진다.

1. **방향성 없음.** 항상 `SignalDirection.NEUTRAL`을 반환한다 — "오늘 N건 언급, 평소 ~M건/일"이라는 *활동량*만 측정한다. `scorer.py`에서 NEUTRAL은 `attention`에만 기여하고 `stars`(방향 확신도)에는 기여하지 못한다.
2. **거의 무력.** `_mentions`는 단어 경계 매칭(`\b{symbol}\b`)으로 제목+요약을 훑지만, 공식 피드(SEC 보도자료 등)에는 티커가 거의 없다. 실데이터에서 대부분 `None`을 반환한다.

LLM 감성 시그널은 동일한 뉴스 레코드를 입력으로 받되, **헤드라인의 어조를 분류해 방향성(bullish/bearish/neutral) + 확신도**를 산출한다. 이것이 `news_volume`을 *보완*(하이브리드)하거나 장기적으로 *대체*한다.

---

## 3. 핵심 원칙 — seam은 source 게이트가 아니라 signal 게이트다

> ⚠️ **정확성 함정.** 프로젝트의 GRAY 게이트(`gray_enabled`)는 **수집(collection)** 시점에 `Registry.due()`가 `meta.legal_status`로 *소스*를 거르는 메커니즘이다(`mimir/core/registry.py`). LLM 감성은 **소스가 아니라 시그널**이며, *분석(analyze)* 시점에 `build_signals()`(`mimir/analysis/builder.py`)가 만든 리스트를 통해 등록된다. 그리고 오늘 `build_signals()`는 **인자를 받지 않으며 어떤 게이트도 통과하지 않는다.**

따라서 "GRAY 소스처럼 게이트한다"는 **철학**(설정 토글 + 키 존재 시에만 활성화)이지, 재사용 가능한 **메커니즘**이 아니다. 본 스펙은 시그널 경로에 **새 게이트**를 도입한다.

```
[수집 평면]  Registry.due() ──(gray_enabled, legal_status)──> 소스 필터        ← 기존
[분석 평면]  build_signals(settings, config) ──(opt-in + key)──> 시그널 필터   ← 본 스펙이 추가
```

- `build_signals()`의 시그니처와 `analyze.py`의 호출부가 **미래에** 바뀐다(아래 §4). A1의 계획된 `build_sources(settings, config)`(설정 기반 소스 척추)와 동일한 패턴이다.
- `engine.py`(`AnalysisEngine.run`), `scorer.py`(`score`), `SignalResult`/`SignalDirection`(`base.py`)은 **전혀 바뀌지 않는다.** 엔진은 시그널을 심볼당 한 번 `evaluate()`하고 `SignalResult | None`만 본다 — 새 시그널이 이 계약을 지키므로 다운스트림은 무지(無知)해도 된다.

---

## 4. off-by-default 게이트 — 두 조건의 AND

`LlmSentimentSignal`은 **다음 두 조건이 모두 참일 때만** 시그널 리스트에 추가된다. 하나라도 거짓이면 파이프라인은 **오늘과 정확히 동일하게** 동작한다(유료 호출 0건, 출력 동일).

| 조건 | 출처 | 부재 시 동작 |
|---|---|---|
| (a) 옵트인 플래그 `llm_sentiment_enabled: true` | `config/sources.yaml` | 시그널 미등록(기본 `false`) |
| (b) `ANTHROPIC_API_KEY` 존재 | `Settings.anthropic_api_key` (env) | 경고 로그 + 시그널 미등록 |
| (c) `anthropic` 패키지 설치됨 | `importlib.util.find_spec("anthropic")` | 경고 로그 + 시그널 미등록 |

> ⚠️ **선택적 의존성 + 지연 import (이것을 빠뜨리면 무료 원칙이 깨진다).** §4의 게이트는 *인스턴스화*는 막지만 *import*는 막지 못한다. 만약 `builder.py`가 모듈 최상단에서 `LlmSentimentSignal`을 import하고 그 모듈이 `import anthropic`을 하면, **빌더를 로드하는 것만으로** `anthropic`이 끌려온다 — SDK 없이 설치된 기본 환경이 import 시점에 깨지고, "오늘과 동일 동작" 불변식이 무너진다. CI는 `anthropic`(또는 fake)이 설치된 채 돌아 import가 항상 성공하므로, AC1/AC7로는 이 결함을 잡지 못한다(테스트 조건 ≠ 실제 배포 조건). 이미 코드베이스에 선례가 있다: pykrx는 선택적 `[kr]` extra이고 `build_sources`가 `importlib.util.find_spec("pykrx")`로 게이트하며 *지역(local)* import를 쓴다. 동일하게: `anthropic`은 선택적 extra(예: `[llm]`)로 두고, `find_spec("anthropic")` 가드 + `build_signals` 내부 지역 import로 지연시켜 **기본 경로가 절대 `anthropic`을 import하지 않게** 한다.

### 4.1 `Settings` 확장 (env-key 패턴 미러)

`mimir/settings.py`의 기존 패턴(`stooq_api_key` 등)을 그대로 따른다.

```python
# mimir/settings.py — 미래 추가(예시)
class Settings(BaseModel):
    # ... 기존 필드 ...
    anthropic_api_key: str | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        # ... 기존 로직 ...
        return cls(
            # ... 기존 필드 ...
            anthropic_api_key=env.get("ANTHROPIC_API_KEY"),
        )
```

### 4.2 설정 토글 (GRAY `gray_enabled` 미러)

`config/sources.yaml`은 이미 `gray_enabled`/`disabled_ids`/`lang`을 담는다. 동일한 파일에 분석 토글을 추가한다(읽기는 `load_sources_config`로 이미 가능).

```yaml
# config/sources.yaml — 미래 추가
gray_enabled: true
disabled_ids: []
lang: en
llm_sentiment_enabled: false      # 유료 LLM 감성 시그널. 기본 off. 켜려면 ANTHROPIC_API_KEY + anthropic 패키지 필요.
llm_sentiment_max_headlines: 50   # 1회 실행당 신규 분류 헤드라인 상한(비용 가드레일 — 실제 비용 동인)
```

### 4.3 게이트 배선 (`build_signals` 시그니처 변경)

```python
# mimir/analysis/builder.py — 미래(예시, 본 스펙이 정의하는 계약)
import importlib.util

def build_signals(
    settings: Settings,
    config: Mapping[str, Any] | None = None,
    *,
    classifier: HeadlineClassifier | None = None,  # 테스트 주입(§7)
) -> list[Signal]:
    signals: list[Signal] = [
        FilingEventSignal(),
        NewsVolumeSignal(),
        PriceMomentumSignal(),
        MacroRegimeSignal(),
    ]
    cfg = config or {}
    if _llm_sentiment_enabled(cfg, settings, classifier):
        # 지역 import — 기본 경로는 이 분기에 진입하지 않으므로 anthropic을 절대 import하지 않는다.
        from mimir.analysis.signals.llm_sentiment import (
            AnthropicHeadlineClassifier,
            LlmSentimentCache,
            LlmSentimentSignal,
        )
        signals.append(
            LlmSentimentSignal(
                classifier=classifier or AnthropicHeadlineClassifier(settings.anthropic_api_key),
                cache=LlmSentimentCache(...),       # §6
                max_headlines=int(cfg.get("llm_sentiment_max_headlines", 50)),
            )
        )
    else:
        logger.info("skipping signal 'llm_sentiment': disabled, no ANTHROPIC_API_KEY, or anthropic not installed")
    return signals


def _llm_sentiment_enabled(
    cfg: Mapping[str, Any], settings: Settings, classifier: HeadlineClassifier | None
) -> bool:
    if not cfg.get("llm_sentiment_enabled", False):
        return False
    if not settings.anthropic_api_key:
        logger.warning("llm_sentiment_enabled=true but ANTHROPIC_API_KEY is not set; signal disabled")
        return False
    # 테스트 fake 주입 시에는 SDK가 없어도 된다. 실 구현 경로에서만 패키지 존재를 요구.
    if classifier is None and importlib.util.find_spec("anthropic") is None:
        logger.warning("llm_sentiment_enabled=true but 'anthropic' is not installed (pip install -e '.[llm]'); signal disabled")
        return False
    return True
```

`analyze.py`의 `run_analyze`는 `build_signals(settings, load_sources_config(config_dir))`로 호출부를 바꾼다. 이것이 **이 스펙이 도입하는 주요 호출부 변경**이며, 엔진 계약은 불변이다. (정확히는 단순 한 줄이 아니다: 현재 `run_analyze`는 `Settings`도 config도 구성하지 않으며 `config_dir` 인자도 없다 — `main()`에만 있다. 따라서 `settings`+`config`를 `run_analyze`까지 배선하는 약간의 추가 작업이 따른다. 그러나 `engine.py`/`scorer.py`/`SignalResult` 계약은 그대로다.)

---

## 5. `LlmSentimentSignal` 설계 — 기존 `Signal` 계약 준수

### 5.1 프로토콜 적합성

`mimir/analysis/signals/base.py`의 `Signal` 프로토콜을 그대로 만족한다.

```python
class LlmSentimentSignal:  # Signal 프로토콜 충족
    id = "llm_sentiment"

    def __init__(
        self,
        *,
        classifier: HeadlineClassifier,
        cache: LlmSentimentCache,
        max_headlines: int,
        weight: float = 0.8,
    ) -> None: ...

    def evaluate(
        self, symbol: str, market: Market, as_of: date, reader: DataReader
    ) -> SignalResult | None: ...
```

반환 타입은 기존과 **동일한 `SignalResult`** — `signal`/`direction`/`strength`/`confidence`/`reason`/`weight`. 따라서 `scorer.score()`와 `engine.run()`은 수정이 필요 없다.

### 5.2 per-headline → one-SignalResult 집계 (핵심 설계 결정)

> ⚠️ **계약 갭.** 엔진은 심볼당 `evaluate()`를 **한 번** 호출하고 **하나의** `SignalResult`를 기대한다. 그러나 LLM 분류기의 출력은 *헤드라인별* `{direction, confidence, rationale}`이고, 무엇보다 `SignalResult`는 **`strength`를 필수로 요구**하는데 분류기 출력에는 `strength`가 없다. 따라서 N개 헤드라인 판정을 1개 `SignalResult`로 **집계**하는 규칙을 명시해야 한다.

**파이프라인:**

1. `news_volume`의 `_mentions`(단어 경계 매칭)를 재사용해 `as_of` 당일 뉴스 중 `symbol`을 언급한 레코드를 모은다. (헤드라인에 티커가 없으면 LLM 호출도 없다 — 무료 원칙과 비용 가드레일의 자연스러운 교집합.)
2. 각 레코드의 헤드라인+요약을 분류한다. **캐시 우선**(§6): `idempotency_key`로 캐시된 판정이 있으면 재사용, 없는 것만 LLM 호출. **신규 분류 헤드라인 수**는 `max_headlines`로 상한(실제 비용 동인). 배치는 호출 왕복만 줄일 뿐 헤드라인 상한을 바꾸지 않는다.
3. N개 판정을 다음 규칙으로 1개 `SignalResult`로 집계한다.

**집계 규칙(결정론적):**

| 산출 필드 | 계산 | 근거 |
|---|---|---|
| `signed[i]` | `DIRECTION_SIGN[d_i] * conf_i` (각 헤드라인) | `base.py`의 `DIRECTION_SIGN`(bullish +1 / bearish −1 / neutral 0) 재사용 |
| `mean_signed` | `mean(signed[i])` ∈ [−1, 1] | 확신도 가중 평균 방향 |
| `direction` | `mean_signed > +ε → BULLISH`, `< −ε → BEARISH`, else `NEUTRAL` | `scorer.py`의 `DIRECTION_EPS` 관례와 일치 |
| `strength` | `min(\|mean_signed\|, 1.0)` | 방향 일관성의 크기 — `SignalResult.strength`(필수)를 채운다 |
| `confidence` | `mean(conf_i) * volume_factor` | 볼륨이 적으면 확신도를 낮춘다(§5.3) |
| `reason` | `"N headlines: {b} bull / {x} bear / {n} neutral; mean={mean_signed:+.2f}"` | 사람이 읽는 근거 |
| `weight` | 생성자 `weight`(기본 0.8) | `news_volume`(0.5)보다 높게 — 방향성을 가진 정보이므로 |

집계 대상이 0건이면 `evaluate()`는 `None`을 반환한다(기존 시그널과 동일한 관례).

### 5.3 `volume_factor` — 소표본 다운웨이트

헤드라인 1건의 강한 판정이 과대평가되지 않도록, `confidence`에 볼륨 보정을 곱한다.

```
volume_factor = min(n_headlines / FULL_CONFIDENCE_VOLUME, 1.0)   # 예: FULL_CONFIDENCE_VOLUME = 3
```

1건이면 confidence가 1/3로 줄고, 3건 이상이면 보정 없음. 상수는 백테스트(B1)로 보정 대상.

---

## 6. 비용 가드레일 — git-as-DB 캐시 + 호출 상한 + 배치

> ⚠️ **캐시는 ad-hoc 파일이 아니라 git-as-DB 파생 데이터셋이어야 한다.** GitHub Actions 러너는 ephemeral이므로, 재실행 간 캐시가 살아남으려면 **append-only + idempotent**한 파생 데이터셋으로 영속화해야 한다. 이는 비용을 줄이는 동시에 프로젝트의 불변성·멱등성 원칙을 강화한다.

### 6.1 캐시 키 = 뉴스 레코드의 `idempotency_key`

RSS 레코드의 `idempotency_key`는 `f"rss:{link}"`(안정·고유)이다. 분류 결과를 이 키로 캐시한다.

```jsonc
// data/llm_sentiment/YYYY/MM/DD.jsonl — 파생 데이터셋(기존 envelope 재사용)
{ "source":"mimir_analysis", "dataset":"llm_sentiment", "market":"GLOBAL", "symbol":null,
  "ts":"...", "captured_at":"...",
  "idempotency_key":"llm_sentiment:rss:https://...",   // 원천 키를 prefix로 감싸 교차충돌 방지
  "payload": { "news_key":"rss:https://...", "model":"claude-haiku-4-5",
    "direction":"bullish", "confidence":0.72, "rationale":"..." } }
```

- **재실행 무료.** 매 실행 시 먼저 캐시 데이터셋을 읽고, 캐시된 `news_key`는 LLM 호출을 건너뛴다. 같은 헤드라인은 두 번 분류하지 않는다.
- **멱등.** `idempotency_key`로 dedup — 재실행이 같은 파티션에 같은 키를 다시 써도 중복이 생기지 않는다(기존 store 관례).
- **append-only.** 한 번 분류된 헤드라인의 판정은 불변. 모델 버전을 `payload.model`에 기록해, 모델이 바뀌면 재분류 가능하도록 추적성을 남긴다.

### 6.2 헤드라인 상한 (per-run cap)

`llm_sentiment_max_headlines`(기본 50)로 1회 실행당 **신규로 분류하는 헤드라인 수**를 상한한다 — 이것이 토큰·비용의 실제 동인이다. 캐시 히트는 카운트하지 않는다. (호출 수가 아니라 헤드라인 수를 캡하므로, 배치가 호출당 여러 헤드라인을 묶어도 비용 봉투가 무너지지 않는다.)

> ⚠️ **무음 실패 금지.** 상한에 도달해 분류되지 못한 헤드라인이 남으면 **로그로 명시**하고, 해당 심볼의 `SignalResult.reason`에 부분성을 표시한다(예: `"capped at 50 headlines; 12 unclassified"`). 조용히 누락하지 않는다. API 오류도 절대 swallow하지 않는다 — `anthropic.RateLimitError`/`APIStatusError`는 잡아서 로그·표면화하되, 한 실행을 통째로 죽이지는 않는다(소스 격리와 동일한 정신).

### 6.3 배치

헤드라인을 묶어 **호출 왕복(round-trip) 수**를 줄인다(비용 동인이 아니라 지연·오버헤드 최적화). 헤드라인 상한(§6.2)은 배치와 무관하게 신규 헤드라인 수를 캡한다. 두 가지 옵션:

- **동기(기본):** 다수 헤드라인을 한 메시지에 넣고 tool-use로 배열을 받는다(낮은 지연, 즉시 결과).
- **Batches API(선택):** 비latency-민감 cron에서 50% 비용 절감. 본 스펙은 동기를 기본으로 하고 Batches는 향후 최적화로 남긴다(러너 안에서 폴링 대기는 cron 모델과 맞지 않음).

### 6.4 비용 봉투 (대략)

권위 있는 가격(claude-api 스킬, 2026-06 캐시): **Haiku 4.5 = 입력 $1.00 / 출력 $5.00 (per 1M tokens)**.

| 항목 | 가정 | 값 |
|---|---|---|
| 헤드라인당 입력 토큰 | 제목+요약(≤500자) + 프롬프트 ≈ 250 tok | 250 |
| 헤드라인당 출력 토큰 | `{direction, confidence, rationale}` ≈ 50 tok | 50 |
| 헤드라인당 비용 | 250·$1/1M + 50·$5/1M = $0.00025 + $0.00025 | **≈ $0.0005** |
| 1회 실행 상한 | `max_headlines = 50` (신규만) | 50 헤드라인 |
| 1회 실행 비용 | 50 · $0.0005 | **≈ $0.025** |
| 월 실행 | 일 1회 cron × 30 | 30 |
| **월 비용 봉투** | 30 · $0.025 | **≈ $0.75 / 월** |

**상한이 헤드라인 단위라 봉투가 견고하다.** 비용 동인은 *헤드라인→토큰*이고 `max_headlines`가 바로 그 양을 캡한다. 배치(§6.3)가 호출당 10건을 묶어도 신규 헤드라인 총량은 여전히 50으로 제한되므로 위 계산이 그대로 성립한다(호출 수를 캡했다면 50호출×10헤드라인 = 10배로 봉투가 무너졌을 것이다 — 이를 피하려 헤드라인을 캡한다).

**캐시 효과:** 같은 헤드라인은 1회만 분류되므로, 정상 상태(steady-state)에서는 *새 헤드라인 수*만 비용에 기여한다. 위는 매 실행 50건이 전부 신규라는 **최악 가정**이다. 실제로는 신규 헤드라인 수가 상한보다 훨씬 적어 월 $0.75는 상한선에 가깝다. 헤드라인당 단가가 워낙 낮아(≈ $0.0005), 상한을 200으로 올려도 월 ~$3 수준이다.

**모델 선택 근거.** 3-class 헤드라인 분류는 Haiku 4.5로 충분하다 — 가장 저렴(입력 $1 / 출력 $5)하고 단순 분류에 적합. Sonnet 4.6($3/$15)·Opus 4.8($5/$25)는 비용 대비 이득이 없다. **B1(백테스트)이 Haiku의 적중률이 부족함을 보이면**, 동일 seam으로 Sonnet 승격이 가능하다 — *측정 기반*이지 가정이 아니다. (Haiku 4.5는 `effort`/`max`를 지원하지 않고 `temperature`는 지원하므로, 결정론을 위해 `temperature=0`을 사용한다 — §7.)

---

## 7. 결정론과 테스트 — 분류기 주입 (rss.py `parse_fn` 미러)

> ⚠️ **분석이 비결정적·네트워크 의존이 된다.** 오늘 `analyze`는 순수·오프라인이다. LLM은 둘 다 깬다. 완화책: (1) 캐시로 첫 분류 이후 재현 가능(같은 헤드라인 → 같은 판정); (2) 호출 시 `temperature=0`으로 변동 최소화; (3) 테스트는 **주입된 fake 분류기**로 네트워크 없이 돈다. 이 비결정성이 바로 시그널을 off-by-default로 두는 근거다.

### 7.1 분류기 포트 (Protocol)

`mimir/sources/rss.py`의 `parse_fn` 주입 패턴을 그대로 미러한다 — 생성자에 함수형 의존을 주입해 네트워크-free 테스트를 만든다.

```python
class HeadlineVerdict(BaseModel):       # tool-use 구조화 출력
    direction: SignalDirection          # bullish | bearish | neutral
    confidence: float                   # 0..1
    rationale: str

class HeadlineClassifier(Protocol):
    def classify(self, headlines: list[str]) -> list[HeadlineVerdict]: ...
```

### 7.2 실 구현 — Anthropic Messages API + 구조화 출력

```python
# 미래 구현(예시) — anthropic SDK, Haiku 4.5, tool-use/structured output
import anthropic

class AnthropicHeadlineClassifier:        # HeadlineClassifier 충족
    MODEL = "claude-haiku-4-5"
    def __init__(self, api_key: str | None) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)  # 없으면 env에서 해석

    def classify(self, headlines: list[str]) -> list[HeadlineVerdict]:
        # client.messages.parse(...) 로 타입드 출력(Pydantic) 검증.
        # temperature=0 (Haiku 4.5는 sampling param 지원), max_tokens 소량.
        # 배치: 다수 헤드라인을 한 호출에 넣고 verdict 배열을 받는다.
        ...
```

- **구조화/tool-use 출력**으로 `{direction, confidence, rationale}` 타입을 강제한다. `messages.parse()` + Pydantic 모델로 스키마 위반을 경계에서 잡는다.
- 키가 없으면 `__init__` 단계에서 막히지 않게 하되, 게이트(§4)가 키 부재 시 애초에 실 구현을 생성하지 않는다.

### 7.3 fake 분류기 (테스트)

```python
class FakeClassifier:                     # HeadlineClassifier 충족, 네트워크 없음
    def __init__(self, scripted: dict[str, HeadlineVerdict]) -> None:
        self._scripted = scripted
    def classify(self, headlines: list[str]) -> list[HeadlineVerdict]:
        return [self._scripted[h] for h in headlines]
```

`build_signals(settings, config, classifier=FakeClassifier(...))`로 주입한다. 단위 테스트는 결정론적 fake로 돌아 **네트워크 0건**.

---

## 8. 개인정보·ToS — 저장된 텍스트만 전송

> **저작권/ToS 경계.** LLM에 보내는 것은 **이미 저장된 헤드라인 + 요약 텍스트뿐**이다. 전체 기사 본문은 절대 보내지 않는다. `rss.py`는 `SUMMARY_MAX = 500`으로 요약을 잘라 저장하며, 코드 주석이 명시한다: *"store only a short summary; never full article text (copyright)"*. 본 시그널은 그 저장된 짧은 텍스트만 소비하므로, 동일한 저작권 경계 안에 머문다.

- 전송 데이터: `payload["title"]` + `payload["summary"]`(≤500자). 그 이상은 없음.
- PII·시크릿: 헤드라인에는 통상 없음. `ANTHROPIC_API_KEY`는 env/`.env`(gitignore)로만(기존 시크릿 관례), 코드·로그·커밋에 절대 노출 금지.

---

## 9. 면책 — 모든 인사이트에 계속 적용

LLM 감성이 켜져도 면책은 불변이다. `mimir/analysis/schema.py`의 `DISCLAIMER = "For information only. Not financial advice."`가 모든 `Insight`에 박혀 있고, `report/digest.py`는 i18n `t("disclaimer_report", lang)`로 면책을 모든 다이제스트에 붙인다. LLM 시그널은 이 경로를 바꾸지 않는다 — 단지 또 하나의 `SignalResult`를 더할 뿐이며, 분석/실행 분리(읽기 전용 시그널 발행)도 그대로다.

---

## 10. 수용 기준 (Acceptance Criteria)

| # | 기준 | 검증 |
|---|---|---|
| AC1 | 기본값(플래그 off OR 키 없음)에서 파이프라인이 오늘과 **바이트 동일** 동작 | 게이트 off일 때 `build_signals`가 4개 시그널만 반환 |
| AC2 | 세 조건(플래그 on + 키 set + `anthropic` 설치, 단 fake 주입 시 패키지 불요) 모두 참일 때만 `LlmSentimentSignal` 등록 | 셋 다 참 → 5개; 하나라도 거짓 → 4개 |
| AC2b | 기본(default) 경로가 `anthropic`을 **import하지 않음** | 게이트 off에서 `build_signals` 호출 시 `sys.modules`에 `anthropic` 부재 |
| AC3 | 반환 타입이 기존 `SignalResult`와 동일(엔진/스코어러 무수정) | `engine.py`/`scorer.py` diff 0 |
| AC4 | N개 헤드라인 판정을 결정론적으로 1개 `SignalResult`로 집계 | fake 분류기로 집계 규칙(§5.2) 단위 테스트 |
| AC5 | 캐시 히트 시 LLM 재호출 없음(재실행 무료) | 같은 `news_key` 두 번째 실행에서 호출 카운트 0 |
| AC6 | `max_headlines` 상한 도달 시 무음 누락 없이 로그+reason 표기 | 상한 < 헤드라인 수 시나리오 테스트 |
| AC7 | 모든 테스트가 네트워크 없이 통과(fake 주입) | CI에서 `anthropic` 실호출 0건 |
| AC8 | 전송 텍스트가 title+summary로 한정(본문 미전송) | 분류기 입력 어서션 |
| AC9 | mypy strict 통과 + 면책 불변 | `mypy` + digest 면책 테스트 |

---

## 11. 테스트 계획 (fake 분류기 주입)

| 테스트 | 유형 | 내용 |
|---|---|---|
| `test_gate_off_by_default` | unit | 플래그 미설정 시 4개 시그널만; 유료 경로 미생성 |
| `test_gate_requires_flag_key_and_package` | unit | (on, no-key)/(off, key)/(on, key, no-pkg & no-fake) 모두 미등록; (on, key, pkg-or-fake)만 등록 |
| `test_default_path_does_not_import_anthropic` | unit | 게이트 off에서 `build_signals` 후 `"anthropic" not in sys.modules` |
| `test_aggregate_mixed_verdicts` | unit | bull 2 / bear 1 → `mean_signed` 부호·`strength`·`direction` 검증 |
| `test_aggregate_single_headline_downweights_confidence` | unit | 1건 → `volume_factor`로 confidence 감소 |
| `test_returns_none_when_no_mentions` | unit | 심볼 미언급 → `evaluate()`가 `None` |
| `test_cache_hit_skips_llm_call` | unit | 캐시된 `news_key` → 분류기 호출 0 |
| `test_cap_logs_and_marks_partial` | unit | `max_headlines` 초과 → 로그 + reason에 부분성 |
| `test_signalresult_contract` | unit | 모든 필수 필드(특히 `strength`) 채워짐 |
| `test_only_title_and_summary_sent` | unit | 분류기에 전달된 텍스트가 저장 필드로 한정 |
| `test_engine_unchanged_with_llm_signal` | integration | fake로 5개 시그널 → `engine.run()` 정상, 면책 유지 |

모든 테스트는 `HeadlineClassifier` Protocol의 fake 구현을 주입 — **네트워크·키·비용 0**.

---

## 12. 승격 조건 (Promotion Conditions) — 코드가 되는 시점

이 문서는 다음이 모두 충족될 때에만 구현 사이클(brainstorming → plan → TDD → 구현 → finish)로 승격된다.

1. **사용자가 `ANTHROPIC_API_KEY`를 발급·승인**한다(GitHub Actions Secret / `.env`).
2. **사용자가 월 비용 한도를 승인**한다(§6.4 봉투 기준, 예: 월 $1 이내).
3. **B1(시그널 백테스트 하네스)가 선행**되어, Haiku 감성 시그널의 사후 적중률을 측정할 토대가 있다(모델 승격을 가정이 아닌 측정으로 결정하기 위함).

그 전까지 Mimir의 기본 파이프라인은 **무료 원칙을 100% 유지**하며, 본 시그널은 설계로만 존재한다.

---

## 13. 미해결·향후 (Open Questions)

| 항목 | 메모 |
|---|---|
| 하이브리드 vs 대체 | 초기에는 `news_volume`과 **병존**(하이브리드). 백테스트가 LLM 우위를 입증하면 `news_volume` weight 축소/제거 검토. |
| 모델 버전 캐시 무효화 | `payload.model`이 바뀌면 해당 헤드라인 재분류. 정책(전체 재분류 vs 신규만)은 비용과 함께 결정. |
| KR 시장 헤드라인 | 한국어 헤드라인 분류 품질·토큰 비용은 별도 검증 필요(샘플 측정). |
| Batches API 전환 | 비latency-민감 cron에서 50% 절감 가능하나 폴링 대기가 러너 모델과 충돌 — 향후 최적화. |
| 워치리스트 외 심볼 | `_mentions`는 워치리스트 심볼만 대상 — 피드 전체 분류는 비용 폭증, 범위 밖. |
