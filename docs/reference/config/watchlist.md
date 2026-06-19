# `config/watchlist.yaml` 설정 레퍼런스

> **상태**: 현재 구현 기준
> **최종 업데이트**: 2026-06-18
> **대상 독자**: 로컬 실행자, GitHub Actions 운영자, watchlist 종목을 바꾸는 사람

---

## 1. 한눈에 보기

`watchlist.yaml`은 Mimir가 수집·분석·리포트에서 다룰 종목 목록을 시장별로 정한다. `us`는 미국 시장 symbol, `kr`은 한국 시장 symbol이다. 잘못된 형태(스칼라 값, 비-매핑 최상위, 문자열이 아닌 symbol, 공백 symbol)는 조용히 무시하지 않는다. 파서가 실패시키고 CLI가 `[mimir] invalid watchlist.yaml:` 메시지에 파일 경로를 담아 보여준다.

```yaml
us:
  - AAPL
  - MSFT
  - NVDA
kr:
  - "005930"   # 삼성전자
  - "000660"   # SK하이닉스
```

---

## 2. 스키마

| 키 | 타입 | 기본값 | 의미 |
|---|---|---|---|
| `us` | string list | `[]` | 미국 시장 watchlist symbol 목록 |
| `kr` | string list | `[]` | 한국 시장 watchlist symbol 목록 |

- `us`, `kr` 외의 최상위 키는 설정 오류로 처리한다(`extra="forbid"`).
- 각 시장 값은 반드시 문자열 list여야 한다. `us: AAPL`처럼 스칼라 하나를 쓰면 실패한다. 이전 구현은 스칼라를 글자 단위로 풀어 `["A", "A", "P", "L"]`로 만들 수 있었는데, 이 schema 검증이 그 무음 손상을 막는다.
- 각 symbol 양끝 공백은 제거한다. `" AAPL "`는 `"AAPL"`로 정규화된다.
- 공백만 있는 symbol(예: `"   "`)이나 빈 문자열은 설정 오류다.
- `005930`처럼 앞자리가 0인 한국 코드는 YAML이 숫자로 읽지 않도록 따옴표로 감싼다.

파일이 없으면 빈 watchlist(`{"us": [], "kr": []}`)로 동작한다. 이는 `load_yaml()`이 부재 파일을 빈 매핑으로 읽고, 기본값이 빈 list이기 때문이다.

---

## 3. 잘못된 설정 예시

아래 설정은 모두 실패해야 한다.

```yaml
us: AAPL          # 스칼라. us는 문자열 list여야 한다.
kr: []
```

```yaml
- AAPL            # 최상위가 매핑이 아니다. us/kr 키가 필요하다.
```

```yaml
us: [123]         # symbol은 문자열이어야 한다. 숫자는 오류다.
kr: []
```

```yaml
us:
  - "   "         # 공백만 있는 symbol은 허용하지 않는다.
kr: []
```

실패를 빠르게 내는 이유는 명확하다. watchlist가 조용히 손상되면 사용자는 특정 종목을 추적한다고 믿지만 실제로는 엉뚱한 symbol이 수집·분석된다.

---

## 4. CLI 오류 표면

`watchlist.yaml`을 읽는 CLI(`collect`, `analyze`, `run`, `backfill`, `dashboard`, `history`(`--symbol` 없을 때), `doctor`)는 schema 오류를 raw traceback 대신 친절한 메시지로 보여준다.

```
[mimir] invalid watchlist.yaml: <config_dir>/watchlist.yaml: <검증 상세>
```

오류 메시지에는 항상 읽으려던 `watchlist.yaml` 경로가 포함되므로, 여러 `--config-dir`을 쓸 때 어느 파일을 고쳐야 하는지 바로 알 수 있다. 이때 CLI exit code는 `1`이다.
