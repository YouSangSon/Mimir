# CLI 레퍼런스

> **상태**: 현재 구현 기준
> **최종 업데이트**: 2026-06-23
> **대상 독자**: 로컬 실행자, GitHub Actions 운영자, 실행 계약을 확인하려는 개발자

---

## 1. 한눈에 보기

Mimir는 통합 진입점 `mimir <command>`를 기본으로 제공한다. `collect`, `run`, `backfill`, `analyze`, `deliver`, `history`, `doctor`, `evaluate`, `dashboard`를 같은 바이너리 아래에서 호출할 수 있다.

기존 문서와 스크립트 호환을 위해 module 실행(`python -m mimir.collect`)과 dotted alias(`mimir.collect`)도 계속 지원한다. 운영 문서에서는 새 표기인 `mimir <command>`를 우선으로 본다.

---

## 2. 명령 매트릭스

| 명령 | 주 역할 | `sources.yaml` | `watchlist.yaml` | `data/` 읽기 | `data/` 쓰기 | `reports/` 쓰기 |
|---|---|---:|---:|---:|---:|---:|
| `mimir run` | scheduled pipeline (`collect → analyze → history → evaluate → deliver`) | 예 | 예 | 예 | 예 | 예 |
| `mimir collect` | cadence에 맞는 소스 수집 + manifest/status 기록 | 예 | 예 | 일부 | 예 | `reports/status.html` |
| `mimir backfill` | 단일 source 과거 데이터 적재 | 예 | 아니오 | 일부 | 예 | 아니오 |
| `mimir analyze` | 저장된 원천 데이터에서 인사이트 생성 | 예 | 예 | 예 | 예 | 아니오 |
| `mimir deliver` | 일일 HTML 리포트/인덱스/다이제스트 생성 | 예 | 예 | 예 | 아니오 | 예 |
| `mimir history` | 저장된 인사이트와 가격으로 과거 유사 사례 계산 | 예 | 예 | 예 | 예 | 아니오 |
| `mimir doctor` | 설정 검증 + 데이터 상태 진단 | 예 | 예 | 예 | 아니오 | 선택(`--html`) |
| `mimir evaluate` | 저장된 인사이트와 가격으로 시그널 성적표 계산 | 아니오 | 아니오 | 예 | 예 | 아니오 |
| `mimir dashboard` | 최신 운영 대시보드 HTML 생성 | 예 | 예 | 예 | 아니오 | `reports/dashboard.html` |

`mimir evaluate`는 의도적으로 `--config-dir`를 받지 않는다. 저장된 `insights`와 `prices`만 읽어 평가를 계산하므로 현재 설정 파일을 다시 열 필요가 없다.

---

## 3. 주요 인자 계약

| 명령 | 핵심 인자 | 메모 |
|---|---|---|
| `run` | `--cadence`, `--config-dir`, `--data-root`, `--reports-root` | pipeline 전체를 한 번에 실행 |
| `collect` | `--cadence`, `--config-dir` | 상태 HTML은 항상 `reports/status.html`에 쓴다 |
| `backfill` | `--source`, `--since`, `--config-dir` | 등록된 단일 source만 처리 |
| `analyze` | `--date`, `--config-dir`, `--data-root` | watchlist 전체 또는 설정된 종목군 분석 |
| `deliver` | `--cadence`, `--date`, `--config-dir`, `--data-root`, `--reports-root` | 일일 리포트와 인덱스 생성 |
| `history` | `--symbol`, `--date`, `--config-dir`, `--data-root` | `--symbol`이 없으면 전체 watchlist |
| `doctor` | `--config-dir`, `--data-root`, `--format`, `--html`, `--lang`, `--strict` | 진단 보고서 출력 |
| `evaluate` | `--date`, `--data-root` | `--config-dir` 없음 |
| `dashboard` | `--config-dir`, `--data-root`, `--reports-root`, `--date`, `--lang` | latest-available 기준 대시보드 생성 가능 |

---

## 4. 설정 검증과 friendly error prefix

CLI 경계는 설정 파일 오류를 raw traceback 대신 고정된 prefix로 보여준다.

- `[mimir] invalid sources.yaml:`
- `[mimir] invalid watchlist.yaml:`

`collect`, `run`, `backfill`, `analyze`, `deliver`, `history`, `dashboard`, `doctor`는 필요할 때 설정 파일을 읽고 이 prefix 계약을 유지한다. 오타나 schema drift를 조용히 기본값으로 넘기지 않는 이유는 운영자가 "설정이 반영됐다"라고 믿는 상황을 막기 위해서다.

---

## 5. 운영자 관점 메모

- `doctor --strict`는 **운영자 선택 옵션**이다. WARN까지 비제로 종료로 올리고 싶을 때만 쓴다.
- scheduled pipeline의 기본 hard gate는 아니다. 기본 동작은 CRITICAL만 비제로 종료다.
- `run`은 `evaluate`를 pipeline 안에서 호출하지만, 평가 단계 자체는 여전히 저장된 데이터만 읽는 읽기-기반 계산이다.
- `dashboard`는 read-mostly 명령이다. 최종 산출물로 `reports/dashboard.html` 한 파일만 갱신한다.

---

## 6. 예시

```bash
mimir run --cadence daily
mimir collect --cadence hourly
mimir backfill --source stooq --since 2018-01-01
mimir analyze --date 2026-06-23
mimir history --symbol AAPL --date 2026-06-23
mimir evaluate --date 2026-06-23 --data-root data
mimir doctor --data-root data --html reports/doctor.html
mimir dashboard --reports-root reports --lang ko
```

Module form과 dotted alias도 계속 유효하다.

```bash
python -m mimir.collect --cadence daily
mimir.collect --cadence daily
```
