# Runtime `.env` Autoload Design

> **상태**: ✅ 구현 완료 (`Settings.from_env(env=None)` runtime `.env` autoload). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
> **작성일**: 2026-06-18
> **범위**: CLI로 실행되는 수집·백필·파이프라인·전달 경로가 로컬 `.env`를 실제로 읽게 한다. 테스트와 라이브러리 호출에서 명시적으로 넘긴 `env` mapping은 그대로 우선한다.

---

## 1. 한눈에 보기

README는 `.env`가 실행 시 현재 디렉터리에서 자동 로드되고, CI의 실제 환경변수가 `.env`보다 우선한다고 설명한다. `Settings.from_env()`도 `env=None`일 때는 이 계약을 지킨다.

하지만 주요 CLI 경로는 `os.environ`을 명시적으로 넘긴다. 이 경우 `Settings.from_env(os.environ)`은 `.env`를 로드하지 않는다. 로컬 사용자가 Quick Start대로 `.env`에 키를 적어도, `mimir collect`나 `mimir run`이 그 키를 보지 못할 수 있다.

---

## 2. 목표

- CLI entrypoint에서 호출되는 runtime 함수가 기본적으로 `.env` 자동 로드를 사용한다.
- 테스트나 library caller가 `env={...}`를 명시하면 `.env`를 읽지 않고 해당 mapping만 사용한다.
- 실제 환경변수는 `.env` 값보다 우선한다.
- 기존 `python -m mimir.X`와 통합 `mimir <command>` 경로를 모두 보존한다.
- secret 값은 문서나 manifest에 노출하지 않는다.

---

## 3. 비목표

| 제외 항목 | 이유 |
|---|---|
| `.env` 파일 위치 설정 추가 | 현재 `find_dotenv(usecwd=True)` 계약이면 충분하다. |
| 설정 파일에 secret 저장 | 기존 secret 분리 정책과 충돌한다. |
| CI workflow 변경 | CI는 GitHub Actions Secrets를 환경변수로 주입하므로 `.env`가 없다. |
| plugin별 secret schema 추가 | plugin secret은 `Settings` 또는 직접 환경변수로 읽는 기존 정책을 유지한다. |

---

## 4. 사용자 계약

로컬 사용자는 repo root 또는 실행 cwd 상위의 `.env`에 다음처럼 키를 둔다.

```dotenv
STOOQ_API_KEY=...
TELEGRAM_BOT_TOKEN=...
```

그 뒤 아래 명령은 별도 `export` 없이 키를 읽는다.

```bash
mimir collect --cadence daily
mimir run --cadence daily
mimir backfill --source stooq --since 2018-01-01
mimir deliver --cadence daily
```

이미 shell이나 CI에 같은 이름의 환경변수가 있으면 실제 환경변수가 이긴다.

---

## 5. 구현 설계

현재 구현은 `Settings.from_env(env=None)`의 기본 경로를 runtime CLI 경계에서
사용한다. `env=None`이면 `load_dotenv(find_dotenv(usecwd=True), override=False)`가
실행되어 현재 작업 디렉터리 기준 `.env`를 찾고, `override=False` 때문에 이미
존재하는 실제 환경변수가 `.env` 값보다 우선한다.

`run_collect`, `run_pipeline`, `run_deliver`, `run_backfill`의 `env` 인자는 선택값이다.

- 기본값 `env=None`: `Settings.from_env()`가 `.env`를 로드하고 `os.environ`을 읽는다.
- 명시값 `env={...}`: `Settings.from_env(env)`가 테스트와 library caller가 제공한 mapping만 읽으므로 dotenv loading을 우회한다.

CLI `main()` 함수들은 `os.environ`을 직접 넘기지 않는다. 대신 runtime 함수의
기본 `env=None` 경로를 사용하고, runtime 함수 내부에서 `Settings.from_env(env)`를
호출한다.

---

## 6. 테스트 전략

- `mimir.collect` CLI가 `.env`의 `STOOQ_API_KEY`를 읽어 Stooq source를 활성화한다.
- 실제 환경변수와 `.env`가 충돌하면 실제 환경변수가 Stooq 요청 query에 들어간다.
- 기존 주입 테스트는 `env={...}`를 명시해 deterministic하게 유지한다.
- `Settings.from_env()`의 기존 dotenv 단위 테스트는 유지한다.

---

## 7. 문서 영향

| 파일 | 변경 |
|---|---|
| `docs/architecture/improvement-catalog.md` | runtime `.env` 계약 보정을 구현 완료 항목으로 기록 |
| `docs/IMPROVEMENTS.md` | README secret/autoload 계약 불일치 해결을 기록 |
| `README.md`, `README.ko.md`, `README.zh.md` | 필요 시 CLI synopsis의 실제 옵션 drift를 함께 보정 |

---

## 8. 수용 기준

- [x] CLI collect 경로가 `.env` key를 읽는다.
- [x] 실제 환경변수가 `.env`보다 우선한다.
- [x] 명시 `env` mapping을 넘기는 테스트와 library 사용은 `.env` 자동 로드에 영향받지 않는다.
- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.
