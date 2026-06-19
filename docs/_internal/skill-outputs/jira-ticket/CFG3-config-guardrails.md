# CFG3: 설정 가드레일 (watchlist schema + LLM headline cap)

## 요약

1. 로컬 운영자 설정이 잘못됐을 때, 그 오류가 watchlist symbol을 손상시키거나 유료 LLM 호출량을 안전 범위 밖으로 늘리기 전에 설정 경계에서 막습니다.
2. `watchlist.yaml`은 schema 검증이 없어 `us: AAPL` 같은 스칼라가 `["A", "A", "P", "L"]`로 풀릴 수 있었습니다.
3. 이제 pydantic 모델이 비-매핑 최상위, 비-문자열 symbol, 공백 symbol을 거부하고, symbol 양끝 공백을 제거합니다.
4. `llm_sentiment_max_headlines`는 정수 타입만 검증해 `0`/음수/`51`도 받았습니다. 이제 `1`~`50`만 허용합니다.
5. CLI는 잘못된 watchlist를 raw traceback이 아니라 `[mimir] invalid watchlist.yaml:` 메시지에 파일 경로를 담아 보여줍니다.

---

## 1. Watchlist schema 검증

### 배경

`watchlist.yaml`은 Mimir가 다룰 종목을 시장별(`us`/`kr`)로 정합니다. 수집·분석·리포트 전 경로가 이 목록을 신뢰합니다.

| 용어 | 설명 |
| ---- | ---- |
| watchlist | 추적할 종목 symbol 목록입니다. |
| symbol | `AAPL`, `005930`처럼 종목을 식별하는 문자열입니다. |
| schema 검증 | 입력이 정해진 형태인지 경계에서 확인하는 것입니다. |

### 문제

검증이 없으면 다음이 모두 통과했습니다.

| 입력 | 기존 결과 | 운영 문제 |
| ---- | --------- | --------- |
| `us: AAPL` | `["A", "A", "P", "L"]` | 글자 단위로 풀린 엉뚱한 symbol 수집 |
| `us: [123]` | `[123]` | 숫자 symbol이 matcher 경계를 깨뜨림 |
| `us: [' AAPL ']` | `[" AAPL "]` | 공백이 붙어 dedup·matcher가 어긋남 |

git-as-DB 특성상 손상된 symbol로 커밋된 데이터는 되돌리기 어렵습니다.

### 해결

- `_WatchlistConfig`(`extra="forbid"`, `us`/`kr`는 `list[StrictStr]`)로 검증합니다.
- `_normalize_symbols` validator가 양끝 공백을 제거하고, 공백만 있는 symbol을 거부합니다.
- `load_watchlist()`는 `ValidationError`를 `WatchlistConfigError(f"{path}: {exc}")`로 감쌉니다.

---

## 2. LLM headline cap 경계

### 배경

`llm_sentiment_max_headlines`는 한 실행에서 LLM으로 분류할 headline 상한입니다. 설계가 정한 안전 상한은 `50`입니다.

### 문제

정수 타입만 검증해 `0`, 음수, `51` 이상도 받았습니다. `llm_sentiment_enabled: true`로 유료 경로를 켠 운영자가 큰 값을 실수로 적으면 호출량과 비용이 상한 의도를 벗어났습니다.

### 해결

- `SourcesConfig`와 `_TopLevelSourcesConfig` 두 모델 모두 `llm_sentiment_max_headlines: int = Field(default=50, ge=1, le=50)`.
- 두 모델에 모두 두는 이유는 raw YAML 검증 경로(`_TopLevelSourcesConfig`)와 직접 생성 경로(`SourcesConfig(...)`)를 모두 막기 위함입니다.
- 기본값 `50`과 `llm_sentiment_enabled: false`는 유지합니다.

---

## 3. CLI 오류 표면

`watchlist.yaml`을 읽는 CLI는 아래 패턴으로 schema 오류를 잡습니다.

```python
try:
    watchlist = load_watchlist(config_dir)
except WatchlistConfigError as exc:
    return report_invalid_watchlist(exc)
```

출력은 `[mimir] invalid watchlist.yaml: <path>: <상세>`, exit code 1입니다. 적용 대상은 `collect`, `analyze`, `run`, `backfill`, `dashboard`, `history`(`--symbol` 없을 때), `doctor`입니다.

---

## 인수 테스트

- [ ] `us: AAPL`(스칼라)는 `WatchlistConfigError`로 실패하고 메시지에 `watchlist.yaml`과 `us`를 포함한다.
- [ ] 비-매핑 최상위(`- AAPL`)는 실패한다.
- [ ] 비-문자열 symbol(`us: [123]`)은 실패한다.
- [ ] 공백 symbol(`us: ['   ']`)은 실패하고, `' AAPL '`는 `'AAPL'`로 정규화된다.
- [ ] `collect` CLI가 malformed watchlist에서 `[mimir] invalid watchlist.yaml:`와 파일 경로를 stderr에 내고 exit 1.
- [ ] `llm_sentiment_max_headlines`가 `0`/`-1`/`51`을 거부하고 `1`/`50`을 허용한다.
- [ ] `SourcesConfig(llm_sentiment_max_headlines=0)` 직접 생성도 실패한다.

## 배포 검증

```bash
uv run pytest tests/test_config.py tests/test_collect.py tests/sources/test_config.py -q
uv run ruff check mimir/config.py mimir/sources/config.py
uv run mypy mimir
```

순수 로컬 설정 검증이라 마이그레이션이 없습니다. 정상 설정은 동작이 그대로이고, 잘못된 설정만 실행 초입에서 friendly 오류로 실패합니다.
