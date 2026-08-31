# Increment 2. 타입드 페이로드 스키마 — 설계

> **스펙 ID**: INC2 (카탈로그 A4)
> **작성일**: 2026-06-13
> **상태**: ✅ 구현 완료 (Increment 2 typed payload rollout). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다. 이후 `Dataset.EVALUATION`/`BucketStat`도 같은 typed payload boundary에 포함됐다.
> **선행**: [발전 카탈로그](../../architecture/improvement-catalog.md) · [S1 Collector](2026-05-31-collector-design.md)

---

## 1. 목적

`RawRecord.payload`와 `Record.payload`는 `dict[str, Any]`다. 모든 다운스트림 시그널이 문자열 키로 페이로드를 더듬는다 — `payload.get("close")`(price_momentum), `payload.get("value")`(macro_regime), `payload.get("title")`/`payload.get("summary")`(news_volume), `payload.get("form_type")`(filing_event). 상류가 키 이름을 바꾸거나 형이 드리프트하면 `.get(...)`은 `None`을 돌려주고 시그널은 **조용히** 신호를 내지 않는다(무음 실패).

데이터셋별 pydantic 페이로드 모델은 이 드리프트를 **경계에서**(수집 normalize 시점 / 저장 read 시점) 잡는다. 핵심 제약은: **온디스크 JSONL이 바이트 단위로 동일하게 유지되어야 한다.** 즉 타입드 모델의 직렬화 결과가 현재 dict의 직렬화 결과와 같은 JSON 객체여야 하고, 따라서 데이터 마이그레이션이 필요 없고 `idempotency_key`가 절대 바뀌지 않는다.

**비목표(이번 증분 아님).** 시리즈 식별자 단일 진실원(A2), 백테스트, LLM 시그널, 스키마 버전 마이그레이션 엔진. `RawRecord.payload`는 수집 어댑터가 자유롭게 dict를 만들 수 있어야 하므로 **이번 증분에서 형을 바꾸지 않는다**(§4.6 참조).

---

## 2. 현재 상태 (증거)

### 2.1 봉투(envelope)와 저장 경로

`Record`(`mimir/storage/schema.py`)는 `payload: dict[str, Any]` 한 필드로 모든 데이터셋을 담는다. 직렬화/역직렬화는 `JsonlStore`(`mimir/storage/jsonl_store.py`)가 단독으로 수행한다:

| 경로 | 호출 | 의미 |
|---|---|---|
| 쓰기(append-only) | `rec.model_dump_json()` (`_append_only`) | prices/news/filings — **한 번 쓰고 다시 안 씀** |
| 쓰기(overwrite append) | `rec.model_dump_json()` (`_append_overwrite`) | macro — **같은 관측 key의 공식 개정값은 마지막 레코드로 교체** |
| 쓰기(partition replace) | `rec.model_dump_json()` (`replace_partition`) | insights/historical/evaluation — **매 실행 파티션 전체를 새 결과로 교체** |
| 읽기 | `Record.model_validate_json(line)` (`_read_file`) | 모든 데이터셋 |

`idempotency_key`는 **각 어댑터가 페이로드와 독립적으로 만드는 별도 필드**다(`fred:{series_id}:{day}` 등). 페이로드 직렬화에서 파생되지 않으므로, 페이로드 모델을 바꿔도 키는 영향받지 않는다. → "**키는 절대 바뀌지 않는다**"가 자동 성립.

> **사실(증거):** `find data -name '*.jsonl'`는 빈 결과다. 아직 커밋된 `data/**.jsonl`이 없다. 따라서 "기존 커밋 데이터가 파싱돼야 한다"는 요구는 *미래지향적 계약*이며, 검증은 실제 파일이 아니라 **각 어댑터의 정확한 페이로드 리터럴로 만든 골든-라인 픽스처**로 수행한다(§8).

### 2.2 데이터셋별 실제 페이로드 키 (소스 코드에서 열거)

| 데이터셋 | 어댑터 | 페이로드 키 (삽입 순서대로) |
|---|---|---|
| **PRICES** | `stooq.py` | `open, high, low, close, volume, currency, interval` |
| **PRICES** | `pykrx_source.py` | `open, high, low, close, volume, currency, interval` |
| **MACRO** | `fred.py` | `series_id, value, period` |
| **MACRO** | `ecos.py` | `stat_code, item_code, item_name, value, unit, time` |
| **NEWS** | `rss.py` | `title, url, publisher, market, published_at, summary` |
| **FILINGS** | `sec_edgar.py` | `form_type, title, accession, url, filed_at` |
| **FILINGS** | `dart.py` | `form_type, title, corp_name, url, filed_at, flr_nm` |
| **INSIGHTS** | `analysis/schema.py` | `Insight.model_dump(mode="json")` |
| **HISTORICAL** | `historical/schema.py` | `HistoricalInsight.model_dump(mode="json")` |

> **결정적 관찰 — 한 데이터셋이 두 모양을 가진다.**
> - **PRICES / NEWS**: 단일 모양(어댑터가 둘이어도 키 집합·순서 동일). 깔끔.
> - **MACRO**: `fred`(`series_id,value,period`)와 `ecos`(`stat_code,item_code,item_name,value,unit,time`)는 **공통 키가 `value`뿐**. 합집합 1개 모델은 함정이다(§3.3).
> - **FILINGS**: `sec_edgar`(`...accession...`)와 `dart`(`...corp_name...flr_nm`)는 공통 `form_type/title/url/filed_at`에 더해 각자 고유 키를 가진다.

### 2.3 시그널이 읽는 키 (소비 측)

| 시그널 | 읽는 키 | 형 가정 |
|---|---|---|
| `price_momentum` | `close`, `volume` | `float \| None` |
| `macro_regime` | `value` (필터 `.get("value")`, 본문 `["value"]`) | `float` |
| `news_volume` | `title`, `summary` | `str \| None` |
| `filing_event` | `form_type` | `str \| None` |

`historical/series.py:bars_from_records`도 prices의 `close`/`volume`를 읽는다. `deliver.py`는 insights/historical 레코드를 `Insight`/`HistoricalInsight`로 `model_validate(r.payload)`한다 — **즉 insights/historical 페이로드는 이미 사실상 타입드다**(§4.4).

---

## 3. 불변식 (테스트로 고정) — **가장 중요**

git-as-DB에서 직렬화가 한 바이트라도 달라지면 overwrite 계열 데이터셋이 매 실행 git diff를 만들고(노이즈), append-only 데이터셋은 역직렬화가 깨질 수 있다. 따라서:

### 3.1 핵심 대칭성 논증 (코드 실행 없이 성립)

이 설계는 design-only다. 바이트 동일성은 **실행 검증이 아니라 분석적 대칭성**으로 보장한다:

> 구버전 커밋 라인과 신버전 타입드 dump는 **동일한 `Record.model_dump_json()`**(같은 pydantic v2 인코더 — compact separators, 동일 float 포맷)을 통과한다. 봉투(`Record`)의 모든 비-payload 필드는 불변이다. 그러므로 바이트 동일성은 **payload 객체의 직렬화 동일성**으로 환원되고, 그것은 정확히 두 조건으로 환원된다:
>
> 1. **필드 집합 = 소스 dict의 키 집합** (추가 없음, 누락 없음).
> 2. **필드 정의 순서 = 소스 dict의 키 삽입 순서.**

### 3.2 모델링 규칙 — "전부 필수 + nullable 형"

조건 1·2를 플래그 의존 없이 견고하게 만드는 규칙:

- **모든 필드는 필수(required)로 선언하고, 값이 없을 수 있으면 형을 `X | None`으로 한다.** `item_name: str | None`처럼. **`= None` 디폴트를 주지 않는다.**
- 근거: 어떤 어댑터도 키를 *조건부로 누락*하지 않는다. `ecos`는 `item_name`이 `None`이어도 **키 자체는 항상 넣는다**(`row.get("ITEM_NAME1")`이 `None`을 반환해도 payload에 `"item_name": None`으로 존재). 따라서 모든 필드가 항상 존재 → dump가 저장된 키를 정확히 그대로 방출 → **`exclude_unset`/`exclude_none` 불필요**.
- `exclude_none`을 쓰면 안 되는 이유: `ecos`의 정당한 `null`(`item_name`/`unit`)을 잘못 떨어뜨려 키 집합이 달라진다 → 조건 1 위반.

### 3.3 문자열형 그대로 — date/datetime로 "개선" 금지

`period`("2026-01-15"), `time`("202601"), `filed_at`("2026-01-15"), `published_at`(RSS 원문 문자열), `accession` 등은 **날짜처럼 보이는 문자열**이다. 이를 `date`/`datetime`으로 바꾸면 dump 시 재포맷되어 바이트가 달라진다(조건 위반). **형은 저장된 JSON 스칼라를 정확히 미러링한다**: 문자열은 `str`, 숫자는 `float`/`int`, 불리언은 `bool`.

### 3.4 합집합 모델 금지 — 소스별 모델 + 유니온 별칭

MACRO/FILINGS를 단일 평면 모델("모든 키를 optional로")로 만들면:
- 부재 키가 dump에서 `null`로 방출됨 → 바이트 깨짐.
- `exclude_none`으로 막으려 하면 §3.2 위반.

따라서 **소스별 모델**을 정의하고 카탈로그가 요구한 이름은 **유니온 별칭**으로 노출한다:

```python
MacroPayload  = FredMacroPayload | EcosMacroPayload
FilingPayload = SecFilingPayload | DartFilingPayload
```

### 3.5 그 외 불변식

3. **`idempotency_key` 포맷 불변.** 페이로드 직렬화와 무관(§2.1) — 자동 충족.
4. **파티션 레이아웃 불변.** `data/<dataset>/YYYY/MM/DD.jsonl` 그대로.
5. **`extra="forbid"`로 드리프트 즉시 실패.** 상류가 키를 추가/이름변경하면 경계에서 **크게** 실패(무음 폴백 금지). 이것이 본 증분의 목적이다(§5).

---

## 4. 설계

### 4.1 페이로드 모델 (`mimir/core/payloads.py`)

신규 6개 모델은 `frozen=True`(불변), `extra="forbid"`(드리프트 차단). 필드 순서는 §2.2의 삽입 순서와 **정확히** 일치시킨다.

> **재사용 모델의 config 보정(§4.4 연계).** `Insight`/`HistoricalInsight`는 현재 `class X(BaseModel)`로 pydantic 기본값(`extra="ignore"`)이다. 이대로 `PAYLOAD_BY_DATASET`에 넣으면 insights/historical에서 드리프트한 키가 **조용히 버려진다** — A4가 없애려는 바로 그 무음 실패. 따라서 두 모델에 `model_config = ConfigDict(extra="forbid")`를 **추가**한다(필드는 그대로 — "재정의"가 아니라 "재사용 + config 보정"). 안전성: `deliver.py`의 `model_validate(r.payload)`는 오늘 추가 키를 보지 않으므로 현재 깨지지 않고, 미래 드리프트는 의도대로 크게 실패한다.

```python
from pydantic import BaseModel, ConfigDict

class _Payload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

# --- PRICES (stooq + pykrx, 단일 모양) ---
class PricePayload(_Payload):
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None
    currency: str        # "USD" | "KRW"
    interval: str        # "1d"

# --- MACRO (소스별) ---
class FredMacroPayload(_Payload):
    series_id: str
    value: float
    period: str          # "YYYY-MM-DD" 문자열 그대로

class EcosMacroPayload(_Payload):
    stat_code: str
    item_code: str
    item_name: str | None
    value: float
    unit: str | None
    time: str            # "YYYYMM" 등 ECOS 원문 그대로

MacroPayload = FredMacroPayload | EcosMacroPayload

# --- NEWS (rss, 단일 모양) ---
class NewsPayload(_Payload):
    title: str | None
    url: str
    publisher: str
    market: str          # "US" | "KR" | "GLOBAL" (봉투 market과 별개)
    published_at: str | None
    summary: str         # "" 가능, 절대 None 아님 (rss.py: `(... or "")[:SUMMARY_MAX]`)

# --- FILINGS (소스별) ---
class SecFilingPayload(_Payload):
    form_type: str | None
    title: str | None
    accession: str
    url: str
    filed_at: str        # "YYYY-MM-DD"

class DartFilingPayload(_Payload):
    form_type: str | None
    title: str | None
    corp_name: str | None
    url: str
    filed_at: str | None # dart.py: item.get("rcept_dt") — None 가능
    flr_nm: str | None

FilingPayload = SecFilingPayload | DartFilingPayload
```

> **형 정밀도 주의(증거 기반).**
> - `stooq._f` / `pykrx`의 OHLCV: stooq는 `None` 가능(`_f`가 `"N/D"`→`None`), pykrx는 항상 `float`. 합집합 단일 모양을 위해 OHLCV 5개는 `float | None`으로 통일 — pykrx의 항상-`float` 값도 `float | None`에 합치하며 dump는 동일.
> - `news.summary`는 `str`(비-nullable): rss.py가 `(entry.get("summary") or "")[:SUMMARY_MAX]`로 항상 문자열을 넣음.
> - `news.title`은 `str | None`: `entry.get("title")`이 `None` 가능.

### 4.2 데이터셋 → 모델 디스패치 (외부 판별자)

네이티브 pydantic `Field(discriminator=...)`는 **쓰지 않는다**: 판별자 태그를 payload 안에 넣어야 하므로 새 JSON 키가 생겨 바이트가 깨진다. 판별자(`dataset`)는 이미 `Record`에 있다. 따라서 **외부 디스패치**:

```python
# mimir/core/payloads.py
Payload = (
    PricePayload | MacroPayload | NewsPayload | FilingPayload
    | Insight | HistoricalInsight
)

PAYLOAD_BY_DATASET: dict[Dataset, type[BaseModel] | tuple[type[BaseModel], ...]] = {
    Dataset.PRICES:     PricePayload,
    Dataset.MACRO:      (FredMacroPayload, EcosMacroPayload),
    Dataset.NEWS:       NewsPayload,
    Dataset.FILINGS:    (SecFilingPayload, DartFilingPayload),
    Dataset.INSIGHTS:   Insight,
    Dataset.HISTORICAL: HistoricalInsight,
}

def parse_payload(dataset: Dataset, data: dict[str, Any]) -> Payload:
    """dataset으로 모델을 고르고, 소스별 분기는 extra='forbid' 구조로 해소.
    어느 모델에도 맞지 않으면 PayloadSchemaError(무음 실패 금지)."""
```

MACRO/FILINGS의 소스별 분기는 **구조적으로** 해소된다: `extra="forbid"` + 서로소(disjoint) 필수 키 집합이므로 `fred` dict는 `EcosMacroPayload`에 `extra` 위반으로 실패하고 `FredMacroPayload`에만 맞는다(반대도 동일). 이것이 본 스펙이 말하는 "**데이터셋별 판별 유니온**"이다 — 판별 정보는 봉투의 `dataset` + 페이로드 구조에 있고, 디스크 포맷에는 추가 키가 없다.

### 4.3 `Record` 통합 — 단계적 (§6 참조)

최종 상태에서 `Record.payload`는 `Payload` 유니온이 된다. 단, **저장 직렬화 경로(`JsonlStore`)는 한 줄도 바뀌지 않는다**: `model_dump_json()`/`model_validate_json()`은 그대로다.

**역직렬화는 봉투의 `dataset`로 판별한다(네이티브 smart-union 금지).** pydantic의 구조적 유니온 해소는 8개 멤버가 모두 서로소일 때만 동작하는데 그 가정에 의존하면 취약하다(§4.1의 config 보정 전에는 보장조차 안 됨). 대신 `Record`에 `model_validator(mode="before")`를 두어 §4.2의 디스패치를 그대로 쓴다:

```python
# mimir/storage/schema.py (개념, 단계 4)
class Record(BaseModel):
    payload: Payload
    @model_validator(mode="before")
    @classmethod
    def _typed_payload(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("payload"), dict):
            ds = Dataset(data["dataset"])
            return {**data, "payload": parse_payload(ds, data["payload"])}
        return data
```

이로써 역직렬화가 §4.2의 `dataset` 판별자로 **결정적**이 된다(smart-union 휴리스틱 의존 제거) — 본 스펙 제목 "**판별 유니온 BY DATASET**"이 직렬화 경로에서도 일관되게 성립한다. 직렬화(`model_dump_json`)는 §3 규칙으로 동일 바이트.

`Record.payload` 유니온화는 단계 4에서 완료된다.

### 4.4 insights / historical — 기존 모델 재사용 (재정의 금지)

`Insight`(`analysis/schema.py`)와 `HistoricalInsight`(`historical/schema.py`)가 이미 페이로드 모델이다. `to_record`가 `model_dump(mode="json")`로 payload를 만들고, `deliver.py`가 `model_validate(r.payload)`로 되읽는다. **새 모델을 만들지 않고 이 둘을 `PAYLOAD_BY_DATASET`에 그대로 등록**한다 — 두 번째 진실원이 생겨 드리프트하는 것을 막는다.

> 주의: insights/historical은 `_append_overwrite` 경로(매 실행 read→rewrite)다. 여기서 **재-dump 바이트 동일성이 실제로 git churn을 막는다**. 두 모델은 이미 `mode="json"` dump를 쓰므로 round-trip이 동일함을 골든 테스트로 고정(§8).

`Dataset.EVALUATION`은 후속 구현에서 `BucketStat` typed payload로 같은 boundary에 합류했다.

### 4.5 시그널 측 타입드 접근 (mypy strict 내로잉)

유니온 payload를 가진 단형(monomorphic) `Record`는 mypy strict에서 자동 내로잉되지 않는다. **내로잉 헬퍼**를 제공한다(외과적 선택):

```python
# mimir/core/payloads.py
def price_payload(rec: Record) -> PricePayload:
    if not isinstance(rec.payload, PricePayload):
        raise PayloadSchemaError(f"expected PricePayload, got {type(rec.payload).__name__}")
    return rec.payload
# macro_payload / news_payload / filing_payload 동형 — mismatch는 raise(무음 실패 금지)
```

시그널은 `rec.payload.get("close")` → `price_payload(rec).close`로 바뀐다. `macro_regime`은 `FredMacroPayload | EcosMacroPayload` 양쪽 모두 `.value`를 가지므로 `macro_payload(rec).value`로 일관 접근된다. `filing_event`도 양쪽 `.form_type`.

> **대안(채택 안 함):** 제네릭 `Record[P]`. 시그널 시그니처가 깔끔해지지만 `JsonlStore`/`reader`/`normalize` 전체에 형 매개변수가 번지는 침습적 변경이라 이번 증분 범위를 넘는다. 내로잉 헬퍼가 surgical하다.

### 4.6 `RawRecord.payload`는 dict 유지

수집 어댑터(`fetch`)는 외부 API의 가변 응답에서 dict를 조립한다. `RawRecord.payload`를 유니온으로 강제하면 어댑터마다 모델 생성 코드를 넣어야 하고 수집 경로가 무거워진다. **검증의 단일 지점은 `normalize()`**(경계)다 — 거기서 한 번 `parse_payload`로 드리프트를 잡는다(§4.7). `RawRecord.payload: dict[str, Any]`는 유지.

`RawRecord.payload`는 `dict[str, Any]` 유지.

### 4.7 `normalize()` — 쓰기 시점 드리프트 차단

```python
# mimir/core/normalize.py (개념)
def normalize(raw, meta, *, captured_at) -> Record:
    parse_payload(meta.dataset, raw.payload)   # 드리프트면 PayloadSchemaError → NormalizationError
    return Record(... payload=raw.payload ...)  # 저장은 여전히 dict (단계 2)
```

단계 4에서 `Record.payload`가 유니온이 되면 `Record(...)` 생성 자체가 검증을 수행하므로 별도 호출은 제거된다.

---

## 5. 에러 처리

- **스키마 드리프트(상류 키 추가/이름변경/형 변경)**: `extra="forbid"` 또는 형 불일치로 `parse_payload`가 `PayloadSchemaError`를 던진다. `normalize()`가 이를 `NormalizationError`로 감싸 수집을 **크게** 실패시킨다(무음 폴백 금지 — 카탈로그 A4의 목적).
- **유지보수 계약:** `forbid`는 의무를 만든다 — 상류가 정당한 새 키를 추가하면 경계에서 실패하고, 그때 해당 모델에 필드를 추가해야 한다. 이는 *의도된* 동작이다(드리프트를 눈에 보이게).
- **`PayloadSchemaError`**: `mimir/core/errors.py`에 신규 추가, `MimirError` 계열.

---

## 6. 단계적 롤아웃 (각 단계 테스트 그린 유지)

| 단계 | 변경 | 그린 유지 근거 |
|---|---|---|
| **1. 모델 추가** | `mimir/core/payloads.py` 모델·유니온·`parse_payload` + 골든 round-trip 테스트(§8). **아무것도 배선 안 함.** | 순수 추가. 기존 코드 무변경. |
| **2. 쓰기 검증** | `normalize()`가 `parse_payload`로 1회 검증(저장은 여전히 dict). | 직렬화 경로 무변경 → 바이트 동일성 자명. 기존 데이터/테스트 영향 없음. |
| **3. 시그널 마이그레이션** | `price_momentum`→`macro_regime`→`news_volume`→`filing_event` 순으로 `.get("...")` → 내로잉 헬퍼. `historical/series.py`도. **한 시그널씩.** | 각 시그널은 동일 값을 타입드로 읽음 — 출력 불변. 단계마다 그린. |
| **4. `Record.payload` 유니온화** | `Record.payload: Payload`로 변경. `normalize`의 별도 검증 제거(생성이 검증). | 골든 round-trip 테스트가 게이트. `dict[str,Any]` 제거 완료(A4 달성). |

단계 1→2→3→4 순서 의존. 각 단계 TDD(RED→GREEN→REFACTOR).

---

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
- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.

---

## 8. 테스트 계획

### 8.1 골든 round-trip (바이트 동일성 — make-or-break)

make-or-break 불변식은 **구(dict) 경로 바이트 == 신(typed) 경로 바이트**이지, typed 경로의 자기-멱등이 아니다. 따라서 골든 baseline을 손으로 쓰지 않는다(손으로 쓰면 pydantic float 포맷 가정이 baseline에 새겨져 버린다). **현재 dict 경로로 baseline을 생성**하고 typed 경로가 그것과 바이트 동일함을 단언한다. 각 어댑터의 **정확한 페이로드 dict 리터럴**(실제 `data/**.jsonl`이 없으므로 — §2.1)을 입력으로:

```python
# 어댑터별 실제 dict 리터럴 (예: fred)
PAYLOAD = {"series_id": "DGS10", "value": 4.5, "period": "2026-01-15"}

# 구 경로(현재 dict[str,Any]) baseline — 관찰된 바이트, 가정 아님
baseline = Record(dataset=Dataset.MACRO, ..., payload=PAYLOAD).model_dump_json()

# 신 경로(typed) — 동일 입력
typed = Record(dataset=Dataset.MACRO, ..., payload=parse_payload(Dataset.MACRO, PAYLOAD)).model_dump_json()

assert typed == baseline          # ← 마이그레이션 안전성 직접 검증
assert isinstance(parse_payload(Dataset.MACRO, PAYLOAD), FredMacroPayload)
```

7개 어댑터(prices, fred, ecos, news, sec, dart, + insights/historical) 전부에 대해 반복.

> 키 **순서** 동일이 §3.1 조건 2를, `null` 필드(ecos `item_name`/`unit`, news `published_at`) 보존이 §3.2(전부 필수+nullable, exclude_none 금지)를 검증한다. baseline을 dict 경로에서 뽑으므로 float/구분자 포맷은 *관찰*되며 가정되지 않는다.

### 8.2 드리프트 차단

- 추가 키: `{...,"extra":1}` → `PayloadSchemaError`.
- 키 누락: `value` 빠진 fred dict → `PayloadSchemaError`.
- 형 불일치: `"value":"x"`(문자열) → `PayloadSchemaError`.
- 날짜 문자열이 `str`로 유지되는지: `period`가 `date`로 강제 변환되지 않음(`isinstance(p.period, str)`).

### 8.3 소스별 유니온 해소

- `parse_payload(MACRO, fred_dict)`가 `FredMacroPayload` 인스턴스, `ecos_dict`가 `EcosMacroPayload`.
- 교차(ecos dict를 fred 모델로 직접) 시 실패.

### 8.4 시그널 동치 (회귀)

- 단계 3에서 시그널별로: 동일 입력 레코드에 대해 마이그레이션 전/후 `SignalResult`가 동일(direction/strength/confidence/reason).
- `historical/series.bars_from_records`가 동일 `Bar` 리스트 생성.

### 8.5 봉투 round-trip (overwrite 데이터셋 churn 방지)

- insights/historical: `to_record` → `model_dump_json` → `model_validate_json` → 재-`model_dump_json` 바이트 동일(매 실행 rewrite가 diff를 만들지 않음을 보장).
- 단계 4 후 `Record` 전체 round-trip을 모든 데이터셋 골든 라인에 대해 반복.

---

## 9. 구현 작업 분해 (plan 입력)

1. **모델**: `mimir/core/payloads.py`(6 모델 + 2 유니온 별칭 + `Payload` + `PAYLOAD_BY_DATASET` + `parse_payload`) + `PayloadSchemaError`(`core/errors.py`). 골든 round-trip·드리프트·유니온 해소 테스트(§8.1–8.3). → 단계 1.
2. **쓰기 검증**: `normalize()`에 `parse_payload` 1회 호출 + 테스트(드리프트가 `NormalizationError`로 전파). → 단계 2.
3. **시그널 배선**: 내로잉 헬퍼 + 4 시그널 + `historical/series` 마이그레이션 + 동치 회귀(§8.4). 한 시그널씩 커밋. → 단계 3.
4. **봉투 통합**: `Record.payload: Payload` + `normalize` 별도 검증 제거 + 봉투 round-trip(§8.5) + 문서/카탈로그 갱신. → 단계 4.

각 작업 TDD. 의존: 1 → 2 → 3 → 4. 단계 1·2는 기존 코드 무변경(순수 추가), 단계 3·4가 소비 측을 바꾼다.

---

## 10. 부록 — 시리즈 식별자 단일 진실원 (A2, 구현 완료)

`MacroRegimeSignal.RATE_SERIES`가 시리즈 식별자를 하드코딩하던 문제는 A2에서 별도 증분으로 처리했다. 타입드 페이로드는 *값*의 형을 고정했고, A2 macro series registry는 *어떤 시리즈를 보는지*를 `mimir/core/macro_series.py`와 `analysis.macro_regime.rate_series`로 분리했다. 본 증분은 시그널 디스패치를 건드리지 않았고, A2에서 그 경계를 별도로 배선했다.
