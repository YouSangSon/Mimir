# Increment 1. 설정 기반 소스 확장성 — 설계

> **스펙 ID**: INC1 (확장성 카탈로그 A1)
> **작성일**: 2026-06-13
> **상태**: ✅ 구현 완료 (feat/config-driven-extensibility). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다. 후속 A2/A3/A3b에서 macro series registry, 선언적 source registry, source entry points가 추가됐다.
> **선행**: [발전 카탈로그](../../architecture/improvement-catalog.md) · [S1 Collector](2026-05-31-collector-design.md) · [ADR-0001](../../architecture/adr/0001-incremental-extensibility-and-deferral.md)

---

## 1. 목적

사용자가 **파이썬 코드를 고치지 않고** `config/sources.yaml`만으로 거시 시리즈(FRED/ECOS)와 뉴스 피드(RSS)를 추가·제거할 수 있게 한다. 이는 새 기능이 아니라 *이미 어댑터 생성자에 존재하지만 배선되지 않은 seam*을 연결하는 일이다.

**비목표(이번 증분 아님).** 선언적 소스 레지스트리(§8), 시리즈 식별자 단일 진실원(§9), 타입드 페이로드, 백테스트, LLM 시그널. 모두 별도 증분/설계였고, A2/A3는 2026-06-16 후속 증분에서 구현 완료됐다.

---

## 2. 현재 상태 (증거)

세 어댑터 모두 설정 인자를 받지만 `build_sources`가 인자 없이 생성한다:

| 어댑터 | 생성자 seam | 하드코딩 기본값 (`mimir/sources/*.py`) |
|---|---|---|
| `FredSource(series: list[str])` | 미사용 | `DEFAULT_SERIES = ["DGS10","FEDFUNDS","CPIAUCSL"]` |
| `EcosSource(series: list[EcosSeries])` | 미사용 | `DEFAULT_SERIES = [EcosSeries("722Y001","M","0101000")]` |
| `RssSource(feeds: list[RssFeed])` | 미사용 | `DEFAULT_FEEDS = [RssFeed(SEC pressreleases)]` |

`build_sources(settings)`는 `core/builder.py`에 있고 `collect.py`(`run_collect`)와 `backfill.py`(`run_backfill`) 두 곳에서 호출된다. `run_collect`는 이미 `sources.yaml`을 로드(`gray_enabled`/`disabled_ids`/`lang`)하지만 `build_sources`로 넘기지 않는다.

---

## 3. 불변식 (테스트로 고정) — **가장 중요**

git-as-DB에서 키가 조용히 바뀌면 이미 커밋된 데이터가 고아/중복된다. 따라서:

1. **빈/부재 설정 = 오늘의 기본값.** `sources:` 블록이 없거나 특정 소스 블록이 없으면 그 소스는 정확히 현재 `DEFAULT_*`를 쓴다. (회귀 테스트로 고정)
2. **`idempotency_key` 포맷 불변.** `fred:{series_id}:{day}`, `ecos:{stat_code}:{item_code}:{time}`, `rss:{link}` — 설정 경로와 무관하게 동일.
3. **파티션 레이아웃 불변.** `data/<dataset>/YYYY/MM/DD.jsonl` 그대로.
4. **잘못된 설정 = 빠른 실패.** 스키마 위반(예: `fred.series`가 리스트 아님, `ecos.series` 항목에 `stat_code` 누락)은 명확한 메시지로 즉시 실패(무음 폴백 금지).

---

## 4. 설계

### 4.1 YAML 스키마 (`config/sources.yaml` 확장)

```yaml
gray_enabled: true
disabled_ids: []
lang: en

# (선택) 소스별 설정. 블록을 생략하면 그 소스는 코드 기본값을 쓴다.
sources:
  fred:
    series: ["DGS10", "FEDFUNDS", "CPIAUCSL", "T10Y2Y"]   # FRED series IDs
  ecos:
    series:
      - { stat_code: "722Y001", cycle: "M", item_code: "0101000" }   # BOK 기준금리
  rss:
    feeds:
      - { url: "https://www.sec.gov/news/pressreleases.rss", publisher: "SEC", market: "US" }
```

### 4.2 검증 모델 (`mimir/sources/config.py` — 신규)

`build_sources`(composition root, `core/builder.py`)는 이미 `mimir.sources.*`를 임포트하므로 레이어 역전이 없다. 기존 `EcosSeries`(`sources/ecos.py`)·`RssFeed`(`sources/rss.py`)를 **재사용**한다.

```python
class SourcesConfig(BaseModel):
    fred_series: list[str] | None = None
    ecos_series: list[EcosSeries] | None = None
    rss_feeds: list[RssFeed] | None = None

def parse_sources_config(raw: dict[str, Any]) -> SourcesConfig:
    """raw['sources'] 블록을 검증된 모델로. 누락=None(기본값 유지). 위반=ValidationError→명확한 메시지."""
```

- `None`(키 부재)은 "설정 안 됨 → 기본값 유지"를 의미. 어댑터 생성자가 `series or list(DEFAULT_*)`라서 빈 리스트 `[]`도 기본값으로 수렴한다(별도 구분 없음). **소스를 끄려면 `[]`가 아니라 `disabled_ids`를 쓴다** — 이것이 의도된 단일 비활성화 경로다.
- 최상위 `sources:`가 falsy 비-매핑(`0`/`false`/`[]`/`""`)이면 잘못된 설정으로 즉시 실패(무음 폴백 금지). 키 부재(YAML null)만 기본값으로 수렴.
- pydantic이 `EcosSeries`/`RssFeed` 항목 + 미지 키(`extra="forbid"`)를 자동 검증(필수 필드 누락·오타 시 실패).

### 4.3 빌더 시그니처 변경

```python
def build_sources(settings: Settings, config: SourcesConfig | None = None) -> list[Source]:
    cfg = config or SourcesConfig()
    ...
    sources.append(FredSource(api_key=settings.fred_api_key, series=cfg.fred_series))
    ...
    sources.append(EcosSource(api_key=settings.ecos_api_key, series=cfg.ecos_series))
    ...
    sources.append(RssSource(feeds=cfg.rss_feeds))
```

`series=None`/`feeds=None`이면 생성자가 이미 `or list(DEFAULT_*)`로 기본값을 쓴다 → **불변식 1 자동 충족.** `config=None` 기본값 → 기존 호출자(테스트 포함) 무변경.

### 4.4 호출부 배선

| 호출부 | 변경 |
|---|---|
| `collect.py:run_collect` | 이미 가진 `cfg`(dict)를 `parse_sources_config(cfg)` 해 `build_sources(settings, parsed)` |
| `run.py:run_pipeline` | `run_collect`에 위임 — 변경 없음(이미 `sources_config` 전달) |
| `backfill.py:run_backfill` | `load_sources_config(config_dir)` 추가 로드 → `parse_sources_config` → `build_sources(settings, parsed)`. (FRED 백필이 설정 시리즈를 쓰도록) |

`backfill.py:main`은 `--config-dir`을 이미 받으므로 거기서 로드한다.

---

## 5. 에러 처리

- **설정 위반**: `parse_sources_config`가 `pydantic.ValidationError`를 던지고, CLI(`main`)가 이를 잡아 `[mimir] invalid sources.yaml: <detail>`로 비-0 종료. (무음 폴백 금지 — 잘못된 설정은 빠르게, 크게 실패)
- **부분 설정**: `sources.fred`만 있고 `sources.ecos` 없음 → FRED만 설정 적용, 나머지 기본값.

---

## 6. 수용 기준 (Acceptance)

- [x] `config/sources.yaml`에 `sources.fred.series` 추가 시 FRED가 그 시리즈를 수집한다.
- [x] `sources:` 블록 부재 시 FRED/ECOS/RSS가 정확히 `DEFAULT_*`로 동작한다.
- [x] `idempotency_key`가 설정 경로와 무관하게 동일 포맷을 유지한다.
- [x] 잘못된 설정(`fred.series: "x"`, `ecos.series` 필드 누락)이 명확한 `invalid sources.yaml` 계열 에러로 실패한다.
- [x] `run_backfill`이 설정 시리즈를 사용한다.
- [x] `config/sources.yaml` 예시, README 3개 언어, `.env.example`, reference docs가 설정 기반 소스 확장을 설명한다.
- [x] 빈 리스트는 parse layer에서 `None`과 구분되지만 source 생성자는 기존 `DEFAULT_*` fallback을 유지한다. 소스 비활성화는 `disabled_ids`가 담당한다.
- [x] 최신 전체 검증은 README 테스트 배지와 docs health guard가 추적하며 ruff, mypy, pytest, coverage 80% gate가 통과한다.

---

## 7. 구현 작업 분해 (plan 입력)

1. **검증 모델**: `mimir/sources/config.py` (`SourcesConfig` + `parse_sources_config`) + 단위 테스트(파싱·검증·위반).
2. **빌더 배선**: `build_sources(settings, config=None)` + 회귀 테스트(불변식 1·2·4).
3. **호출부**: `run_collect`·`run_backfill` 배선 + 통합 테스트(설정 시리즈 수집).
4. **문서·설정**: `config/sources.yaml` 예시, README ×3, `.env.example`, `IMPROVEMENTS.md`/roadmap 갱신.

각 작업은 TDD(RED→GREEN→REFACTOR). 작업 간 의존: 1 → 2 → 3 → 4.

---

## 8. 부록 — 선언적 소스 등록 (A3, 구현 완료)

if-사다리(`build_sources`)를 데이터화하는 작업은 A3에서 구현 완료됐다. `mimir/core/builder.py`의 `BUILTIN_SOURCE_SPECS`가 내장 소스의 secret gate, optional package gate, 생성자 인자를 선언한다.

이번 A3 구현은 Python package entry-point까지 확장하지 않았다. 외부 플러그인 source는 이후 A3b에서 `mimir.sources` entry point로 구현됐다. 상세 설계는 [A3 declarative source registration 설계](2026-06-16-declarative-source-registration-design.md)와 [A3b source entry-point 설계](2026-06-16-source-entry-points-design.md)를 따른다.

## 9. 부록 — 시리즈 식별자 단일 진실원 (A2, 구현 완료)

`MacroRegimeSignal.RATE_SERIES`가 FRED/ECOS 시리즈 식별자를 재하드코딩하던 문제는 A2에서 별도 증분으로 처리했다. `mimir/core/macro_series.py`가 기본 수집 시리즈, macro-regime rate-series, doctor cadence를 제공하고, `analysis.macro_regime.rate_series`가 분석 해석 대상을 명시한다. 상세 설계는 [A2 macro series registry 설계](2026-06-16-macro-series-registry-design.md)를 따른다.
