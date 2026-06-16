# D2. GitHub Actions Node24 Runtime — 설계

> **스펙 ID**: D2
> **작성일**: 2026-06-16
> **상태**: ✅ 구현 완료 (`checkout@v6` + `setup-python@v6` + workflow guard). 365 테스트 · ruff · mypy · coverage gate 클린.
> **선행**: [개선 백로그](../../IMPROVEMENTS.md) · [발전 카탈로그](../../architecture/improvement-catalog.md)

---

## 1. 한눈에 보기

GitHub Actions는 2026-06-16부터 JavaScript action의 기본 런타임을 Node24로 옮기기 시작했다. 현재 workflow는 `actions/checkout@v4`와 `actions/setup-python@v5`를 쓴다. 두 버전은 Node20 세대라 deprecation 경고나 이후 제거 일정에 걸릴 수 있다.

D2는 workflow를 Node24 호환 major로 올린다. 동시에 테스트를 추가해 다음에 workflow가 다시 Node20 세대 action으로 내려가는 일을 막는다.

---

## 2. 근거

### 2.1 GitHub 전환 일정

GitHub 공식 changelog는 Node20의 EOL(수명 종료) 뒤 GitHub Actions runner가 Node24를 기본으로 쓰기 시작한다고 안내한다. 2026-06-16부터 runner가 Node24를 기본으로 사용하기 시작하고, 사용자는 Node24로 올라간 최신 action 버전을 쓰도록 요구된다.

### 2.2 현재 workflow 상태

현재 repository의 직접 JavaScript action 사용은 두 곳이다.

| 파일 | 현재 checkout | 현재 setup-python |
|---|---|---|
| `.github/workflows/ci.yml` | `actions/checkout@v4` | `actions/setup-python@v5` |
| `.github/workflows/_pipeline.yml` | `actions/checkout@v4` | `actions/setup-python@v5` |

`collect-hourly.yml`, `collect-daily.yml`, `collect-weekly.yml`, `collect-monthly.yml`는 reusable workflow만 호출한다. 따라서 직접 수정 대상은 `ci.yml`과 `_pipeline.yml`이다.

---

## 3. 목표와 비목표

### 목표

- `actions/checkout`을 Node24 호환 major로 올린다.
- `actions/setup-python`을 Node24 호환 major로 올린다.
- CI workflow와 reusable pipeline workflow를 모두 갱신한다.
- workflow 파일 검증 테스트를 추가해 `checkout@v4`/`setup-python@v5` 회귀를 잡는다.
- 개선 백로그와 발전 카탈로그에서 D2 상태를 구현 완료로 바꾼다.

### 비목표

- GitHub-hosted runner 대신 self-hosted runner를 지원하는 matrix를 추가하지 않는다.
- `checkout@v6`의 credential 저장 방식 변경에 맞춘 별도 migration을 만들지 않는다. 이 repo는 `ubuntu-latest` GitHub-hosted runner를 쓰고, checkout README는 일반 `git fetch`/`git push` workflow 변경이 필요 없다고 안내한다.
- workflow trigger, schedule, secrets, commit command를 바꾸지 않는다.
- dependency cache를 새로 추가하지 않는다. 이번 slice는 Node runtime deprecation 제거에 집중한다.

---

## 4. 설계

### 4.1 버전 선택

| action | 선택 | 이유 |
|---|---|---|
| `actions/checkout` | `@v6` | 현재 major가 Node24를 지원한다. GitHub-hosted runner는 요구 runner 버전을 충족한다. |
| `actions/setup-python` | `@v6` | v6가 Node24로 올라간 major다. 기존 `python-version: "3.14"` 입력은 유지한다. |

Major tag를 유지한다. 기존 workflow도 `@v4`, `@v5`처럼 major tag를 사용했기 때문이다.

### 4.2 검증 테스트

새 테스트 `tests/test_workflows.py`는 `.github/workflows/*.yml`에서 `uses: actions/checkout@...`와 `uses: actions/setup-python@...`를 찾는다.

테스트는 파일별 계약을 고정한다.

```python
EXPECTED_WORKFLOW_ACTION_MAJORS = {
    Path(".github/workflows/ci.yml"): {
        "actions/checkout": "v6",
        "actions/setup-python": "v6",
    },
    Path(".github/workflows/_pipeline.yml"): {
        "actions/checkout": "v6",
        "actions/setup-python": "v6",
    },
}
```

각 workflow에 대상 action이 모두 있어야 하고, major tag가 기대값과 같아야 한다. 이 테스트는 YAML parser에 의존하지 않는다. GitHub Actions의 `on:` 키가 일부 YAML parser에서 boolean으로 해석될 수 있기 때문이다.

---

## 5. 실패와 예외 처리

| 상황 | 처리 |
|---|---|
| workflow가 `actions/checkout@v4`로 돌아감 | `tests/test_workflows.py` 실패 |
| workflow가 `actions/setup-python@v5`로 돌아감 | `tests/test_workflows.py` 실패 |
| reusable caller workflow만 있음 | 직접 action `uses:`가 없으면 검사 대상 없음 |
| 외부 third-party action 추가 | 이번 테스트는 `actions/checkout`과 `actions/setup-python`만 검사 |

---

## 6. 수용 기준

- [x] `.github/workflows/ci.yml`이 `actions/checkout@v6`와 `actions/setup-python@v6`를 사용한다.
- [x] `.github/workflows/_pipeline.yml`이 `actions/checkout@v6`와 `actions/setup-python@v6`를 사용한다.
- [x] `tests/test_workflows.py`가 workflow action major를 검증한다.
- [x] D2 문서 상태가 구현 완료로 갱신된다.
- [x] ruff, mypy, pytest, coverage gate가 통과한다.
