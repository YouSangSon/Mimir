# `config/sources.yaml` 설정 레퍼런스

> **상태**: 현재 구현 기준
> **최종 업데이트**: 2026-06-23
> **대상 독자**: 로컬 실행자, GitHub Actions 운영자, 새 데이터 커버리지를 추가하는 개발자

---

## 1. 한눈에 보기

`sources.yaml`은 어떤 소스를 켤지, 어떤 언어로 리포트를 만들지, 어떤 외부 시리즈와 RSS 피드를 수집할지, 수집된 데이터를 분석 시그널이 어떻게 해석할지 정한다. 잘못된 최상위 키, `sources:` 블록, `analysis:` 블록은 조용히 무시하지 않는다. 파서가 실패시키고 CLI가 `invalid sources.yaml` 메시지를 낸다. 운영 점검 명령인 `mimir doctor`도 데이터 점검이나 HTML 파일 쓰기 전에 같은 schema 검증을 먼저 수행한다.

```yaml
gray_enabled: true
disabled_ids: []
lang: en
llm_sentiment_enabled: false
llm_sentiment_max_headlines: 50

# Optional. Omit to inherit the macro-series registry default.
analysis:
  news:
    use_default_aliases: true
    aliases:
      AAPL: ["Apple", "Apple Inc."]
      MSFT: ["Microsoft", "Microsoft Corp."]
  macro_regime:
    rate_series: ["DGS10", "FEDFUNDS", "722Y001.0101000"]

# Optional. Omit each source block to keep that source's code default.
sources:
  fred:
    series: ["DGS10", "FEDFUNDS", "CPIAUCSL"]
  ecos:
    series:
      - { stat_code: "722Y001", cycle: "M", item_code: "0101000" }
  rss:
    catalogs:
      - { id: "sec_press_releases" }
      - { id: "sec_structured_usgaap" }
      - { id: "sec_structured_risk_return" }
      - { id: "sec_structured_inline_xbrl" }
      - { id: "sec_structured_all_xbrl" }
    sec:
      ticker_cik_map_path: "cache/company_tickers.json"
      ticker_cik_map_refresh:
        enabled: true
        max_age_hours: 168
      company_filings:
        - ticker: "AAPL"
          symbol: "AAPL"
          forms: ["10-K", "10-Q", "8-K"]
          count: 40
          owner: "exclude"
    feeds:
      - { url: "https://www.sec.gov/news/pressreleases.rss", publisher: "SEC", market: "US" }
      - { url: "https://example.com/aapl.rss", publisher: "Example", market: "US", symbol: "AAPL" }
  plugins:
    acme_news:
      base_url: "https://internal.example.com/rss"
      symbols: ["AAPL", "MSFT"]
      timeout_seconds: 5
```

---

## 2. 최상위 키

| 키 | 타입 | 기본값 | 의미 |
|---|---|---|---|
| `gray_enabled` | boolean | `true` | GRAY 소스(예: pykrx)를 실행할지 정한다 |
| `disabled_ids` | string list | `[]` | 특정 소스 id를 끈다. 예: `["dart", "rss"]` |
| `lang` | string | `en` | 리포트 언어. 허용 값은 `en`, `ko`, `zh` |
| `llm_sentiment_enabled` | boolean | `false` | 유료 LLM 뉴스 감성 시그널을 분석 단계에 추가할지 정한다 |
| `llm_sentiment_max_headlines` | integer | `50` | 한 실행에서 LLM으로 분류할 최대 headline 수. 유효 범위는 `1`~`50`이며, `0`·음수·`51` 이상은 설정 오류다 |

위 표의 최상위 키와 `sources`, `analysis` 외의 키는 설정 오류로 처리한다. `analysis`를 `analysys`처럼 잘못 쓰면 기본값으로 조용히 돌아가지 않고 실패한다.

`lang`에 허용되지 않은 값이 들어오면 렌더러는 `en`으로 정규화한다. 이는 잘못된 설정이 `<html lang="...">` 속성에 직접 들어가는 일을 막기 위한 방어다.

---

## 3. `analysis:` 블록

`analysis:` 블록은 이미 수집한 데이터를 분석 시그널이 어떻게 해석할지 정한다. 수집 대상 자체를 늘리지는 않는다.

### 3.1 News aliases

```yaml
analysis:
  news:
    aliases:
      AAPL: ["Apple", "Apple Inc."]
      MSFT: ["Microsoft", "Microsoft Corp."]
      NVDA: ["NVIDIA", "Nvidia Corporation"]
      "005930": ["Samsung Electronics", "삼성전자"]
```

Mimir는 기본 watchlist의 핵심 symbol에 대해 보수적인 내장 alias를 기본으로 사용한다. 현재 기본값은 `AAPL`, `MSFT`, `NVDA`, `"005930"`의 대표 회사명이다. `aliases`는 여기에 사용자 회사명 표기를 추가하는 목록이다. RSS는 계속 공식 feed의 제목과 요약 metadata만 저장한다. 이 설정은 저장된 텍스트를 분석 단계에서 어떻게 해석할지만 바꾼다.

종목별 RSS feed를 이미 알고 있다면 `sources.rss.feeds[].symbol`을 쓰는 편이 더 직접적이다. 이 값은 수집된 record의 top-level symbol이 되며, 뉴스 matcher는 제목·요약 텍스트보다 이 symbol을 먼저 확인한다.

| 필드 | 의미 |
|---|---|
| `use_default_aliases` | 내장 alias를 쓸지 정한다. 기본값은 `true` |
| `AAPL`, `"005930"` 같은 key | watchlist symbol |
| list 안의 문자열 | 제목과 요약에서 추가로 찾을 회사명 또는 표기 |

`news_volume`은 record symbol, symbol 텍스트, alias를 모두 찾는다. 예를 들어 제목에 `AAPL`이 없어도 symbol-tagged feed에서 온 record이거나 기본 alias인 `Apple`이 있으면 `AAPL` 관련 뉴스로 셀 수 있다. 사용자 alias는 기본 alias 뒤에 추가되고, 같은 symbol 안의 중복은 대소문자 무시 기준으로 제거된다.

기본 alias를 끄고 직접 지정한 alias만 쓰려면 아래처럼 설정한다.

```yaml
analysis:
  news:
    use_default_aliases: false
    aliases:
      AAPL: ["Cupertino company"]
```

LLM 감성 시그널도 같은 alias matcher를 사용한다. 단, alias 설정만으로 LLM 호출이 켜지지는 않는다. LLM 감성 시그널은 여전히 `llm_sentiment_enabled`, `ANTHROPIC_API_KEY`, `[llm]` extra 세 조건이 모두 맞을 때만 등록된다.

Alias는 너무 넓게 잡으면 오탐을 만들 수 있다. `Apple`, `Meta`, `ON`처럼 일반 단어와 겹치는 이름은 feed 맥락을 보고 보수적으로 넣어야 한다. matcher는 단어 안쪽 매칭을 막지만, 사람이 보기에도 애매한 alias의 의미까지 판단하지는 않는다.

### 3.2 Macro regime rate series

```yaml
analysis:
  macro_regime:
    rate_series: ["DGS10", "FEDFUNDS", "722Y001.0101000"]
```

`rate_series`는 macro regime 시그널이 정책금리나 벤치마크 금리로 해석할 시리즈 id 목록이다. 이 목록에 있는 시리즈만 시장 전체의 risk-on/risk-off 방향 판단에 영향을 준다. `analysis:` 블록을 생략하면 `mimir/core/macro_series.py`의 registry 기본값을 사용한다.

이 설정은 `sources.fred.series`와 다르다. `sources.fred.series`는 무엇을 수집할지 정한다. `analysis.macro_regime.rate_series`는 수집된 macro 데이터 중 무엇을 금리 regime 신호로 사용할지 정한다.

예를 들어 `CPIAUCSL`은 수집할 수 있지만 기본 rate-series에는 없다. CPI는 물가지표이고, `MacroRegimeSignal`이 보는 정책금리 변화와 같은 의미로 해석하면 안 되기 때문이다.

### 3.3 Analysis signal plugin settings

외부 analysis signal plugin은 `mimir.analysis_signals` entry point로 등록한다. Signal plugin이 자체 설정을 필요로 하면 `analysis.plugins.<signal_id>` 아래에 둔다.

```yaml
analysis:
  plugins:
    acme_sentiment:
      model: "v1"
      lookback_days: 20
```

`analysis.plugins.<signal_id>`는 mapping이어야 한다. `signal_id`는 plugin이 등록한 entry point 이름과 같아야 하며, 기본 `build_signals()` 경로는 이 block이 비어 있으면 외부 plugin entry point를 읽지 않는다. 즉 installed package만으로 signal이 자동 실행되거나 import되지 않는다.

`analysis.plugins`는 외부 analysis signal plugin 전용 namespace다. Built-in signal은 이 namespace를 읽지 않는다. Built-in 설정은 각 signal의 문서화된 key를 사용한다: `news_volume`은 `analysis.news`, `macro_regime`은 `analysis.macro_regime`, LLM 감성 signal은 top-level `llm_sentiment_enabled`를 사용한다.

| 필드 | 의미 |
|---|---|
| `analysis.plugins` | 외부 analysis signal plugin 전용 namespace |
| `analysis.plugins.<signal_id>` | signal id별 설정 mapping |
| block 내부 key | plugin package가 소유한 설정 schema |

Mimir core는 plugin block이 mapping인지까지만 검증한다. 실제 필드 이름과 타입은 plugin factory가 `parse_analysis_plugin_config()`로 자기 pydantic 모델을 검증해야 한다. Core는 외부 plugin schema를 모른 채 namespace와 opt-in 계약만 고정한다.

민감한 값은 이 YAML에 넣지 않는다. API key, token, password는 환경변수나 GitHub Secrets에 둔다. Signal plugin은 Mimir 프로세스 안에서 실행되고 sandbox가 없으므로, 신뢰한 package만 설치해야 한다.

---

## 4. `sources:` 블록

`sources:` 블록은 FRED, ECOS, RSS의 커버리지를 파이썬 코드 수정 없이 늘리는 설정이다. 블록을 생략하면 코드 기본값을 쓴다.

### 4.1 FRED

```yaml
sources:
  fred:
    series: ["DGS10", "FEDFUNDS", "CPIAUCSL", "T10Y2Y", "UNRATE"]
```

`series`는 FRED series id 목록이다. FRED API key가 없으면 `fred` 소스 자체가 실행되지 않는다. key가 있고 `series`가 없으면 코드 기본값인 `DGS10`, `FEDFUNDS`, `CPIAUCSL`을 수집한다.

### 4.2 ECOS

```yaml
sources:
  ecos:
    series:
      - stat_code: "722Y001"
        cycle: "M"
        item_code: "0101000"
```

| 필드 | 의미 |
|---|---|
| `stat_code` | 한국은행 ECOS 통계 코드 |
| `cycle` | 주기. `D`, `M`, `Q`, `A` 형식을 사용한다 |
| `item_code` | 통계 항목 코드 |

ECOS API key가 없으면 `ecos` 소스 자체가 실행되지 않는다.

### 4.3 RSS

```yaml
sources:
  rss:
    catalogs:
      - id: "sec_press_releases"
      - id: "sec_structured_usgaap"
      - id: "sec_structured_risk_return"
      - id: "sec_structured_inline_xbrl"
      - id: "sec_structured_all_xbrl"
    sec:
      company_filings:
        - ticker: "AAPL"
          symbol: "AAPL"
          forms: ["10-K", "10-Q", "8-K"]
          count: 40
          owner: "exclude"
    feeds:
      - url: "https://www.sec.gov/news/pressreleases.rss"
        publisher: "SEC"
        market: "US"
      - url: "https://example.com/aapl.rss"
        publisher: "Example"
        market: "US"
        symbol: "AAPL"
```

RSS는 공식 feed의 제목과 요약 metadata만 저장한다. 기사 본문 전문을 가져오지 않는다. LLM 뉴스 감성 시그널도 저장된 제목과 요약만 사용한다.

`build_sources()`로 만든 RSS source는 `MIMIR_SEC_USER_AGENT` 값을 모든 RSS HTTP 요청의 `User-Agent` header로 보낸다. 이 header는 SEC feed뿐 아니라 manual RSS feed에도 같이 적용된다.

| 필드 | 필수 | 의미 |
|---|---|---|
| `catalogs` | 아니오 | Mimir가 코드에 담아 둔 검증된 RSS feed catalog 선택 목록 |
| `catalogs[].id` | 예 | catalog id. 아래 표의 내장 id 중 하나 |
| `sec.company_filings` | 아니오 | SEC EDGAR Company Search Atom feed를 CIK 또는 ticker token과 form 설정에서 조립하는 목록 |
| `sec.ticker_cik_map_path` | 아니오 | SEC `company_tickers.json` 로컬 파일 경로. 설정하면 ticker 입력을 10자리 CIK로 바꾼 뒤 URL을 만든다 |
| `sec.ticker_cik_map_refresh` | 아니오 | 로컬 SEC mapping file을 build 전에 best-effort로 갱신하는 opt-in 설정. 기본값은 disabled |
| `feeds` | 아니오 | 운영자가 직접 지정하는 RSS feed 목록 |
| `url` | 예 | RSS feed URL |
| `publisher` | 예 | payload에 저장할 발행자 이름 |
| `market` | 예 | payload에 저장할 feed market. record envelope market은 source 특성상 `GLOBAL`이다 |
| `symbol` | 아니오 | 이 feed가 특정 watchlist symbol 전용일 때 쓰는 값. 공백은 제거하고 빈 값은 오류로 처리한다 |

`sources.rss.catalogs`는 반복해서 쓰는 공식 feed URL을 id로 고르는 편의 기능이다. Resolver는 코드 안의 정적 catalog만 읽는다. Catalog를 해석하는 동안 네트워크를 호출하지 않으며, generic live discovery나 vendor URL 추측도 하지 않는다.

현재 내장 catalog id는 아래와 같다.

| id | Feed |
|---|---|
| `sec_press_releases` | SEC press releases |
| `sec_structured_usgaap` | US GAAP/IFRS tagged financial statement filings |
| `sec_structured_risk_return` | mutual fund risk/return tagged filings |
| `sec_structured_inline_xbrl` | Inline XBRL financial statement filings |
| `sec_structured_all_xbrl` | all XBRL filings submitted to the SEC |

`sec_structured_*` catalog는 SEC가 공식으로 공개한 broad SEC/XBRL feed다. 특정 watchlist symbol 전용 feed가 아니므로 `symbol`을 설정하지 않는다. 특정 종목의 SEC filing feed가 필요하면 사용자가 CIK 또는 ticker token을 명시하는 `sources.rss.sec.company_filings`를 쓴다. 운영자가 SEC `company_tickers.json` 파일을 로컬에 두고 `sec.ticker_cik_map_path`를 설정하면, Mimir는 ticker를 10자리 CIK로 바꾼 뒤 URL을 만든다. Generic live discovery는 여전히 보류지만, SEC mapping file refresh 자체는 `ticker_cik_map_refresh`로 opt-in 구현되어 있다.

`catalogs`, `sec.company_filings`, `feeds`를 함께 쓰면 catalog feed, SEC EDGAR feed, manual feed 순서로 붙는다. 같은 `(url, symbol)` 쌍이 두 번 나오면 실패한다. 중복을 조용히 제거하면 운영자가 같은 feed를 두 경로로 설정했다는 사실을 놓칠 수 있기 때문이다. 같은 URL이라도 symbol이 다르면 서로 다른 종목 관계를 뜻하므로 허용한다.

#### SEC EDGAR company filing feeds

`sources.rss.sec.company_filings`는 SEC EDGAR Company Search가 제공하는 Atom feed URL을 설정에서 조립한다. 이 기능은 SEC 페이지를 크롤링하지 않는다. 사용자는 `cik` 또는 `ticker` 중 정확히 하나를 명시하고, Mimir가 `browse-edgar?action=getcompany&output=atom` URL을 만든다.

`sources.rss.sec.ticker_cik_map_path`를 설정하면 `ticker` 입력의 의미가 달라진다. Mimir는 지정한 로컬 JSON 파일을 SEC `company_tickers.json` 형태로 읽고, ticker를 10자리 CIK로 정규화한다. 이 파일은 SEC가 제공하지만, SEC는 파일의 정확성과 범위를 보장하지 않는다고 설명한다. 파일이 없거나 읽을 수 없거나 유효한 JSON object가 아니면 경로가 포함된 설정 오류로 실패한다. 개별 entry가 object가 아니거나 `ticker`/`cik_str` 값이 잘못되면 파일 경로와 entry key가 포함된 설정 오류로 실패한다. 같은 ticker가 서로 다른 CIK로 두 번 나오면 모호한 매핑으로 보고 실패한다. 파일을 정상적으로 읽은 뒤에도 요청한 ticker가 mapping에 없으면 `SEC ticker CIK map has no entry for ticker <ticker> in <path>`처럼 실제 lookup에 사용한 파일 경로를 포함해 실패한다. `collect`, `run`, `backfill` CLI에서는 이런 source build 오류를 raw traceback이 아니라 `[mimir] invalid sources.yaml:` 메시지로 보여준다.

#### `ticker_cik_map_refresh`

```yaml
sources:
  rss:
    sec:
      ticker_cik_map_path: "cache/company_tickers.json"
      ticker_cik_map_refresh:
        enabled: true
        url: "https://www.sec.gov/files/company_tickers.json"
        max_age_hours: 168
```

| 필드 | 기본값 | 의미 |
|---|---|---|
| `enabled` | `false` | refresh를 켤지 정한다. 기본 경로는 `false`라서 SEC mapping download 요청을 0회 보낸다 |
| `url` | `https://www.sec.gov/files/company_tickers.json` | 가져올 SEC mapping file URL |
| `max_age_hours` | `168` | 로컬 cache file이 이 시간보다 오래됐을 때만 refresh를 시도한다 |

이 refresh는 RSS resolver 안이 아니라 **source build 직전 준비 단계**에서 실행된다. 그래서 resolver의 "로컬 파일만 읽고 네트워크는 하지 않는다" 계약은 그대로 유지된다.

구현 동작은 아래와 같다.

- `enabled: false`면 바로 반환한다. 표준 경로는 Tasks 1~2 이전과 같게 수동 파일 관리 + 네트워크 0회다.
- 로컬 file이 있고 mtime이 `max_age_hours` 이내면 TTL gate가 작동해 HTTP 요청을 보내지 않는다.
- stale file이면 저장된 `.etag` 값을 `If-None-Match`로 보내 조건부 GET을 시도한다.
- `304 Not Modified`에 로컬 file이 있으면 file mtime을 현재 시각으로 touch해 다음 build가 같은 TTL 창 안에서 재요청하지 않게 한다.
- `304 Not Modified`인데 `.etag`만 있고 실제 file이 없는 orphaned cache 상태면 warning만 남기고 계속 진행한다. collection 전체를 crash시키지 않는다.
- `200` download는 temp sibling file에 먼저 쓰고, resolver가 쓰는 canonical loader로 JSON object/entry/ticker ambiguity를 같은 규칙으로 검증한다.
- 검증을 통과한 temp file만 `os.replace()`로 atomically 채택한다.
- 네트워크 실패, invalid JSON, non-object JSON, entry validation 실패는 모두 기존 cache를 유지하고 warning만 남긴다.

| 필드 | 필수 | 기본값 | 의미 |
|---|---|---|---|
| `cik` | 조건부 | 없음 | `ticker`가 없을 때 필수. SEC CIK. 숫자 1~10자리 문자열 또는 YAML 숫자를 받으며 URL에는 10자리로 zero-pad된다 |
| `ticker` | 조건부 | 없음 | `cik`가 없을 때 필수. SEC Company Search가 받는 ticker token. 공백 제거 후 대문자로 정규화하며 letters/digits/dot/hyphen만 허용한다 |
| `symbol` | 아니오 | 없음 | 이 feed를 연결할 watchlist symbol |
| `forms` | 아니오 | 없음 | `10-K`, `10-Q`, `8-K`, `10-K/A` 같은 form type 목록 |
| `count` | 아니오 | `40` | SEC Atom feed의 count. 허용 범위는 10~100 |
| `owner` | 아니오 | `exclude` | SEC owner filter. `exclude`, `include`, `only` 중 하나 |

`ticker_cik_map_path`는 개별 `company_filings` 항목 안이 아니라 parent `sources.rss.sec` block에 둔다. 개별 항목에 넣으면 schema drift로 보고 실패한다.

`cik`와 `ticker`를 둘 다 쓰거나 둘 다 생략하면 설정 오류다. 운영자가 정확한 CIK를 알고 있거나 중복 feed 검출을 더 강하게 하고 싶으면 `cik`를 직접 쓰는 편이 낫다. `ticker_cik_map_path`가 없으면 `ticker`는 SEC Company Search RSS가 현재 받는 ticker token을 쓰는 편의 입력이다. `ticker_cik_map_path`가 있으면 Mimir가 로컬 파일에서 ticker를 찾아 CIK로 바꾼다. 파일에 해당 ticker가 없으면 설정을 조용히 무시하지 않고 실패한다.

SEC fair-access 정책은 자동화 도구가 자신을 식별하고 필요한 요청만 보내기를 요구한다. SEC feed를 쓰는 환경에서는 `MIMIR_SEC_USER_AGENT`를 `서비스명 이메일` 형식으로 설정한다.

`symbol`이 없으면 기존처럼 일반 뉴스 feed로 저장한다. idempotency key도 기존 형식인 `rss:{link}`를 유지한다.

`symbol`이 있으면 `RawRecord.symbol`에 그 값을 넣고, idempotency key는 `rss:{symbol}:{link}`가 된다. 같은 URL이 `AAPL` feed와 `MSFT` feed에 동시에 있어도 두 symbol 관계가 dedup으로 사라지지 않는다.

### 4.4 Source plugin settings

외부 source plugin은 `mimir.sources` entry point로 `SourceSpec`을 등록한다. Plugin이 자체 설정을 필요로 하면 `sources.plugins.<source_id>` 아래에 둔다.

```yaml
sources:
  plugins:
    acme_news:
      base_url: "https://internal.example.com/rss"
      symbols: ["AAPL", "MSFT"]
      timeout_seconds: 5
```

`acme_news`는 plugin이 등록한 `SourceSpec.id`와 같아야 한다. 한 package가 여러 source를 제공하면 각 source id 아래에 별도 설정을 둔다.

| 필드 | 의미 |
|---|---|
| `sources.plugins` | 외부 source plugin 전용 namespace |
| `sources.plugins.<source_id>` | plugin source id별 설정 mapping |
| block 내부 key | plugin package가 소유한 설정 schema |

Mimir core는 plugin block이 mapping인지까지만 검증한다. 실제 필드 이름과 타입은 plugin factory가 `SourcesConfig.parse_plugin_config()`로 자기 pydantic 모델을 검증해야 한다. 이 구조는 core가 외부 plugin schema를 알 필요 없이 typo를 plugin 경계에서 크게 실패시키기 위한 것이다.

Built-in source 설정은 이 namespace에 넣지 않는다. 예를 들어 RSS feed는 `sources.rss.feeds`를 써야 하고, `sources.plugins.rss`는 warning을 남긴다.

민감한 값은 이 파일에 쓰지 않는다. API key, token, password는 환경변수나 GitHub Secrets에 둔다. Plugin factory는 `Settings`도 받으므로 secret은 그 경로로 읽어야 한다.

---

## 5. 끄는 방법

소스를 끌 때는 빈 `series: []` 대신 `disabled_ids`를 쓴다.

```yaml
disabled_ids: ["rss", "dart"]
```

이 규칙은 설정의 뜻을 하나로 유지하기 위한 것이다. `sources.fred.series`는 "어떤 시리즈를 수집할지"를 말하고, `disabled_ids`는 "소스 자체를 실행하지 말지"를 말한다.

---

## 6. LLM 감성 시그널

LLM 감성 시그널은 세 조건이 모두 맞을 때만 켜진다.

1. `llm_sentiment_enabled: true`
2. `ANTHROPIC_API_KEY` 환경변수 존재
3. `[llm]` extra 설치로 `anthropic` package 사용 가능

기본값은 `false`다. 이 기본값은 프로젝트의 무료 실행 원칙을 지키기 위한 것이다. 설정만 켜고 key나 package가 없으면 경고를 남기고 시그널을 등록하지 않는다.

---

## 7. 잘못된 설정 예시

아래 설정은 실패해야 한다.

```yaml
sources:
  fred:
    serie: ["DGS10"]     # 오타. series가 맞다.
```

```yaml
sources:
  ecos:
    series:
      - { cycle: "M", item_code: "0101000" }  # stat_code 누락
```

```yaml
sources: "fred"          # sources는 mapping이어야 한다.
```

```yaml
analysis:
  news:
    use_defaults_aliases: false  # 오타. use_default_aliases가 맞다.
```

```yaml
analysis:
  news:
    aliasez: { AAPL: ["Apple"] }  # 오타. aliases가 맞다.
```

```yaml
analysis:
  news:
    aliases:
      AAPL: "Apple"  # aliases 값은 문자열 하나가 아니라 문자열 list여야 한다.
```

```yaml
sources:
  rss:
    catalogs:
      - { idd: "sec_press_releases" }
      # 오타. id가 맞다. RSS catalog 항목의 알 수 없는 필드는 오류다.
```

```yaml
sources:
  rss:
    catalogs:
      - { id: "unknown_feed" }
      # 알 수 없는 catalog id는 resolver가 실패시킨다.
```

```yaml
sources:
  rss:
    feeds:
      - { url: "https://x/feed.rss", publisher: "Example", market: "US", symbl: "AAPL" }
      # 오타. symbol이 맞다. RSS feed 항목의 알 수 없는 필드는 오류다.
```

```yaml
sources:
  rss:
    feeds:
      - { url: "https://x/feed.rss", publisher: "Example", market: "US", symbol: "   " }
      # symbol은 공백만 있으면 안 된다.
```

```yaml
sources:
  plugins:
    acme_news: "https://internal.example.com/rss"
    # plugin 설정은 문자열이 아니라 mapping이어야 한다.
```

```yaml
sources:
  plugins:
    rss:
      feeds: []
    # built-in RSS 설정은 sources.plugins.rss가 아니라 sources.rss.feeds를 써야 한다.
    # 이 설정은 파서는 통과하지만 builder가 warning을 남기며 built-in RSS에는 적용하지 않는다.
```

```yaml
analysis:
  macro_regime:
    rate_seriez: ["DGS10"]  # 오타. rate_series가 맞다.
```

```yaml
analysys:
  macro_regime:
    rate_series: ["DGS10"]  # 오타. analysis가 맞다.
```

```yaml
llm_sentiment_max_headlines: 0   # 0과 음수는 허용하지 않는다. 유효 범위는 1~50이다.
```

```yaml
llm_sentiment_max_headlines: 51  # 안전 상한 50을 넘는다. 유효 범위는 1~50이다.
```

실패를 빠르게 내는 이유는 명확하다. 설정 오타가 조용히 기본값으로 돌아가면 사용자는 새 시리즈가 수집되거나 분석에 반영된다고 믿지만 실제 동작은 바뀌지 않는다.
