# D1. CLI Entrypoints Design

> **상태**: ✅ 구현 완료 (`mimir/cli.py` + `[project.scripts]` console scripts). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
> **작성일**: 2026-06-18
> **범위**: package install 후 `mimir` 통합 명령과 README에 문서화된 `mimir.collect` 계열 console script를 제공한다. 기존 `python -m mimir.X` 실행 경로는 유지한다.

---

## 1. 한눈에 보기

README는 `mimir.collect`, `mimir.analyze`, `mimir.doctor` 같은 실행 파일을 CLI 표면으로 보여준다. 하지만 `pyproject.toml`에는 `project.scripts`가 없어 editable install 후에도 해당 실행 파일이 생기지 않는다.

이번 증분은 문서와 패키지 계약을 맞춘다. 사용자는 기존처럼 `python -m mimir.collect`를 쓸 수 있고, 설치 후에는 `mimir collect ...` 또는 `mimir.collect ...`도 쓸 수 있다.

---

## 2. 목표

- `pyproject.toml`에 `mimir` 통합 console script를 추가한다.
- README가 이미 보여주는 dotted command도 alias로 제공한다.
- 통합 CLI는 첫 번째 인자를 subcommand로 해석하고 기존 module `main(argv)`에 나머지 인자를 그대로 넘긴다.
- 알 수 없는 subcommand는 종료 코드 `2`와 도움말을 반환한다.
- `--help`는 사용 가능한 subcommand 목록을 보여준다.
- 기존 module CLI와 GitHub Actions의 `python -m mimir.run`, `python -m mimir.dashboard` 경로는 바꾸지 않는다.

---

## 3. 비목표

| 제외 항목 | 이유 |
|---|---|
| Click/Typer 도입 | 현재 argparse 기반 CLI가 충분하고 새 dependency가 필요 없다. |
| 각 command option 재정의 | 기존 module `main(argv)`를 재사용하면 help, validation, exit code가 보존된다. |
| workflow 명령 변경 | CI/scheduled workflow 안정성을 위해 기존 `python -m` 명령은 유지한다. |
| S5 자동매매 command | 분석/실행 경계가 아직 미래 범위다. |

---

## 4. 사용자 계약

설치 후 지원되는 실행 방식:

```bash
mimir --help
mimir collect --cadence daily
mimir dashboard --reports-root reports

mimir.collect --cadence daily
mimir.dashboard --reports-root reports
```

기존 방식도 유지한다:

```bash
python -m mimir.collect --cadence daily
python -m mimir.dashboard --reports-root reports
```

---

## 5. 구현 설계

현재 구현은 `mimir/cli.py`에 있다. `COMMANDS`는 통합 CLI가 지원하는
subcommand와 기존 module-level `main(argv)` 함수를 연결하고, `_help_text()`는
`mimir <command>` 사용법과 사용 가능한 command 목록을 만든다.

```python
COMMANDS = {
    "collect": collect.main,
    "backfill": backfill.main,
    "analyze": analyze.main,
    "deliver": deliver.main,
    "history": history.main,
    "doctor": doctor_cli.main,
    "evaluate": evaluate.main,
    "dashboard": dashboard.main,
    "run": run.main,
}
```

`main(argv)`는 다음 순서로 동작한다.

1. `argv`가 없거나 `--help`/`-h`면 도움말을 출력하고 `0`을 반환한다.
2. 첫 번째 토큰을 subcommand로 읽는다.
3. subcommand가 없으면 `stderr`에 오류와 도움말을 출력하고 `2`를 반환한다.
4. 기존 module `main()`에 나머지 인자를 넘기고 그 반환값을 그대로 반환한다.

unknown command는 stderr에 `[mimir] unknown command:` prefix와 도움말을 쓰고 exit
code `2`를 반환한다.

`pyproject.toml`의 `[project.scripts]`에는 아래 script가 등록되어 있다.

```toml
[project.scripts]
mimir = "mimir.cli:main"
"mimir.collect" = "mimir.collect:main"
...
"mimir.doctor" = "mimir.doctor.doctor_cli:main"
```

따라서 설치 후에는 `mimir collect` 같은 `mimir <command>` 경로와 `mimir.collect`
같은 dotted aliases를 모두 쓸 수 있다. 기존 `python -m mimir.collect` module
fallback도 유지한다.

현재 script truth anchors는 `mimir = "mimir.cli:main"`과
`mimir.doctor = "mimir.doctor.doctor_cli:main"`이다.

---

## 6. 테스트 전략

- `tests/test_cli.py`
  - `mimir.cli.main(["--help"])`가 사용 가능한 subcommand를 출력한다.
  - `mimir.cli.main(["collect", ...])`가 등록된 command callable에 나머지 인자를 그대로 넘긴다.
  - unknown command는 종료 코드 `2`, stderr 메시지, 도움말을 낸다.
- `tests/test_pyproject_scripts.py`
  - `pyproject.toml`의 `[project.scripts]`가 통합 command와 dotted aliases를 모두 포함한다.
  - 모든 script target이 import 가능하고 callable이다.

---

## 7. 문서 영향

| 파일 | 변경 |
|---|---|
| `README.md` | CLI 섹션을 `mimir <subcommand>` + dotted alias + `python -m` fallback으로 정리하고 test badge/count를 갱신 |
| `README.ko.md` | 한국어 README 동기화 |
| `README.zh.md` | 중국어 README 동기화 |
| `docs/architecture/improvement-catalog.md` | D1을 구현 완료로 이동 |
| `docs/IMPROVEMENTS.md` | 문서-패키지 CLI 계약 정합성 개선을 기록 |

---

## 8. 수용 기준

- [x] `mimir --help`가 subcommand 목록을 보여준다.
- [x] `mimir collect --cadence daily` 형태가 기존 `mimir.collect.main()`으로 위임된다.
- [x] `mimir.collect` 등 README의 dotted command가 package script로 등록된다.
- [x] 기존 `python -m mimir.X` 실행 경로가 유지된다.
- [x] README 3개 언어의 CLI 설명은 현재 CLI 계약과 맞는다.
- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.
