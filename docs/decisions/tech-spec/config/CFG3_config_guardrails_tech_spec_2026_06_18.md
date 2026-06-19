# CFG3 Config Guardrails Tech Spec

## 한눈에 보기

이번 변경은 로컬 운영자 설정이 잘못됐을 때 그 오류가 watchlist symbol을 손상시키거나 유료 LLM headline 호출량을 안전 범위 밖으로 늘리기 전에 설정 경계에서 막습니다.

## 요약

두 가지 설정 입력이 무음 손상 또는 비용 위험을 안고 있었습니다.

1. `watchlist.yaml`은 schema 검증 없이 읽혔습니다. `us: AAPL`처럼 스칼라를 쓰면 list-of-char(`["A", "A", "P", "L"]`)로 풀려 엉뚱한 symbol이 수집·분석될 수 있었습니다.
2. `sources.yaml`의 `llm_sentiment_max_headlines`는 정수 타입만 검증했습니다. `0`, 음수, `51` 같은 값도 그대로 받아, off-by-default 토글을 켰을 때 유료 LLM 호출량 상한을 넘기거나 의미 없는 값으로 동작할 수 있었습니다.

| 결정 | 이유 | 결과 |
| ---- | ---- | ---- |
| `watchlist.yaml`을 pydantic `_WatchlistConfig`로 검증 | 스칼라/비-문자열/공백 symbol의 무음 손상 차단 | `WatchlistConfigError`로 fail-loud |
| symbol 공백 제거 + blank 거부 | `" AAPL "`는 정규화, `"   "`는 오류 | 일관된 symbol 정규화 |
| CLI가 `WatchlistConfigError`를 잡아 보고 | raw traceback 대신 운영자 메시지 | `[mimir] invalid watchlist.yaml:` + exit 1 |
| `llm_sentiment_max_headlines`에 `ge=1, le=50` | 유료 호출량을 안전 범위로 제한 | 1~50 외 값은 `ValidationError` |
| 두 모델 모두에 경계 적용 | top-level 검증과 직접 생성 경로 모두 차단 | 우회 경로 없음 |

## 목표

- 잘못된 `watchlist.yaml`을 파일 경로가 포함된 친절한 오류로 실패시킨다.
- watchlist symbol 양끝 공백을 제거하고, 공백만 있는 symbol을 거부한다.
- `llm_sentiment_max_headlines`를 정수 `1`~`50`으로만 허용한다.
- `llm_sentiment_enabled` 기본값 `false`와 `llm_sentiment_max_headlines` 기본값 `50`은 유지한다.
- 정상 설정의 기존 동작은 바꾸지 않는다.

## 목표가 아닌 것

| 항목 | 제외 이유 |
| ---- | --------- |
| 외부 네트워크 호출·provider discovery·SEC mapping download | 이번 변경은 로컬 설정 검증입니다. |
| 유료 LLM 호출 | cap 값만 검증하며, 실제 호출 조건(`enabled`+key+package)은 그대로입니다. |
| JSONL 저장 레이아웃·record 직렬화·`idempotency_key` 형식 | 설정 경계 검증은 저장 계약을 건드리지 않습니다. |
| watchlist symbol 존재성·시장 매칭 검증 | symbol이 실제 상장 종목인지까지는 판단하지 않습니다. |

## 위험 분석

### Watchlist 손상 위험

`load_watchlist()`는 `watchlist.yaml`을 읽어 `{"us": [...], "kr": [...]}`를 반환하고, 수집·분석·리포트 전 경로가 이 목록을 신뢰합니다. 검증이 없으면 다음이 모두 통과했습니다.

- `us: AAPL` → 글자 단위로 풀려 `["A", "A", "P", "L"]`.
- `us: [123]` → 숫자 symbol.
- `us: [' AAPL ']` → 공백이 붙은 symbol이 그대로 dedup·matcher 경계를 어긋나게 함.

git-as-DB 특성상 손상된 symbol로 수집된 데이터는 잘못된 파티션 키로 커밋되어 되돌리기 어렵습니다.

### LLM 비용 위험

`llm_sentiment_max_headlines`는 한 실행에서 LLM으로 분류할 headline 상한입니다. `llm_sentiment_enabled: true`로 유료 경로를 켠 운영자가 실수로 큰 값을 적으면 호출량과 비용이 상한 의도를 벗어납니다. `0`이나 음수는 의미가 없고, `51` 이상은 설계가 정한 안전 상한(50)을 넘습니다.

## 설계

### Watchlist schema

```python
class _WatchlistConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    us: list[StrictStr] = Field(default_factory=list)
    kr: list[StrictStr] = Field(default_factory=list)

    @field_validator("us", "kr")
    @classmethod
    def _normalize_symbols(cls, value: list[str]) -> list[str]:
        symbols = [symbol.strip() for symbol in value]
        if any(not symbol for symbol in symbols):
            raise ValueError("watchlist symbols must not be blank")
        return symbols
```

`StrictStr`는 숫자 symbol을 거부하고, `extra="forbid"`는 `us`/`kr` 외 키를 거부합니다. `load_watchlist()`는 `ValidationError`를 `WatchlistConfigError(f"{path}: {exc}")`로 감싸 파일 경로를 오류 표면에 포함합니다.

### LLM cap 경계

```python
llm_sentiment_max_headlines: int = Field(default=50, ge=1, le=50)
```

이 필드는 `SourcesConfig`와 `_TopLevelSourcesConfig` 두 모델에 모두 둡니다. `_TopLevelSourcesConfig`는 raw YAML을 먼저 검증하고, `parse_sources_config()`가 그 값을 `SourcesConfig`로 다시 넘깁니다. 두 모델 모두 경계를 가져야 직접 `SourcesConfig(...)`를 만드는 경로까지 막힙니다.

### CLI 오류 처리

`watchlist.yaml`을 읽는 각 CLI `main()`은 아래 패턴을 씁니다.

```python
try:
    watchlist = load_watchlist(config_dir)
except WatchlistConfigError as exc:
    return report_invalid_watchlist(exc)
```

`report_invalid_watchlist()`는 `[mimir] invalid watchlist.yaml: {exc}`를 stderr에 쓰고 `1`을 반환합니다. 적용 대상은 `collect`, `analyze`, `run`, `backfill`, `dashboard`, `history`(`--symbol` 없을 때), `doctor`입니다.

## 테스트

- `tests/test_config.py`: 스칼라 시장 값, 비-매핑 최상위, 비-문자열 symbol, 공백 symbol 거부와 공백 제거 정규화.
- `tests/test_collect.py`: malformed `watchlist.yaml`에서 `[mimir] invalid watchlist.yaml:`와 파일 경로가 stderr에 나오고 exit code 1.
- `tests/sources/test_config.py`: `llm_sentiment_max_headlines`가 `0`/`-1`/`51`을 거부하고 `1`/`50`을 허용. `SourcesConfig` 직접 생성도 경계를 강제.

## 롤아웃

순수 로컬 설정 검증이라 마이그레이션이 없습니다. 기존 정상 `watchlist.yaml`과 정상 `sources.yaml`은 동작이 그대로입니다. 잘못된 설정을 쓰던 환경만 이제 실행 초입에서 friendly 오류로 실패합니다.

## 보안·비용 영향

- 손상된 watchlist symbol로 잘못된 데이터가 git-as-DB에 커밋되는 경로를 차단합니다.
- 유료 LLM headline 호출량 상한을 1~50으로 강제해, off-by-default 토글을 켰을 때 비용 폭주를 막습니다.
- 새 네트워크 호출, 비밀값 노출, 저장 계약 변경은 없습니다.
