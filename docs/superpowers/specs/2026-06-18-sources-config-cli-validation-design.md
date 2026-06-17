# Sources Config CLI Validation Design

> **상태**: 구현 완료. 495 tests · 98% coverage · ruff · mypy · diff-check 통과.
> **작성일**: 2026-06-18
> **범위**: `sources.yaml`을 읽는 CLI가 잘못된 설정을 같은 형식으로 보고하게 한다. 라이브러리 함수가 내부 pydantic 오류를 그대로 드러내는 기존 디버깅 경로는 유지한다.

---

## 1. 한눈에 보기

`docs/reference/config/sources.md`는 잘못된 `sources.yaml`을 조용히 무시하지 않고 CLI가 `invalid sources.yaml` 메시지로 실패한다고 설명한다.

현재 `collect`, `run`, `backfill`은 이 계약을 지킨다. 세 CLI는 `parse_sources_config()`를 좁은 `try/except ValidationError` 안에서 먼저 호출하고, 실패하면 `report_invalid_sources()`로 exit code 1을 반환한다.

하지만 `analyze`, `deliver`, `dashboard`는 같은 파일을 읽으면서도 검증 경로가 일관되지 않다.

- `analyze`는 `parse_sources_config(load_sources_config(...))`를 직접 호출한다. 설정 오류가 raw pydantic traceback으로 보일 수 있다.
- `deliver`와 `dashboard`는 `lang`만 raw dict에서 읽는다. `analysys:` 같은 잘못된 최상위 키가 있어도 리포트 생성이 계속될 수 있다.

이 증분은 CLI 경계에서만 설정 검증 정책을 통일한다. 잘못된 설정은 모든 관련 명령에서 같은 사용자 메시지로 실패한다.

---

## 2. 목표

- `mimir analyze`, `mimir deliver`, `mimir dashboard`가 malformed `sources.yaml`에 대해 `[mimir] invalid sources.yaml:` 메시지와 exit code 1을 반환한다.
- 기존 `collect`, `run`, `backfill`의 narrow catch 정책을 유지한다. 유효한 설정 뒤 downstream에서 난 `ValidationError`는 `sources.yaml` 오류로 오분류하지 않는다.
- raw `sources.yaml` dict와 parsed `SourcesConfig`가 필요한 경로를 명확히 나눈다.
- `lang` 조회가 raw dict fallback 때문에 config typo를 숨기지 않게 한다.
- 기존 `python -m mimir.X`, dotted alias, 통합 `mimir <command>` 경로를 모두 보존한다.

---

## 3. 비목표

| 제외 항목 | 이유 |
|---|---|
| `sources.yaml` schema 확장 | 이번 변경은 검증 표면을 통일하는 작업이다. |
| renderer의 `lang` 정규화 제거 | HTML attribute 방어는 별도 안전장치이므로 유지한다. |
| `watchlist.yaml` 검증 추가 | 현재 문제는 `sources.yaml` 계약 불일치다. |
| plugin 내부 schema 검증 방식 변경 | plugin-owned 설정은 각 plugin factory가 검증한다는 기존 설계를 유지한다. |
| 모든 CLI에 `--strict-config` 추가 | fail-fast가 이미 문서화된 기본 계약이다. |

---

## 4. 사용자 계약

운영자가 아래처럼 오타가 있는 설정을 저장했다고 가정한다.

```yaml
analysys:
  news:
    use_default_aliases: false
```

아래 CLI는 모두 같은 종류의 오류를 보여주고 종료해야 한다.

```bash
mimir analyze --config-dir config
mimir deliver --config-dir config
mimir dashboard --config-dir config
```

출력은 stderr에 `[mimir] invalid sources.yaml:`로 시작한다. 정상 실행 결과나 리포트 파일을 만들지 않는다.

---

## 5. 구현 설계

`mimir.config`에 CLI용 검증 helper를 둔다.

- `load_validated_sources_config(config_dir) -> tuple[dict[str, Any], SourcesConfig]`
- helper는 `load_sources_config(config_dir)`로 raw dict를 읽고, `parse_sources_config(raw)`로 검증한다.
- `ValidationError`는 helper에서 삼키지 않는다. CLI `main()`이 `except ValidationError`로 잡아 `report_invalid_sources()`를 반환한다.

CLI별 사용 방식은 다음과 같다.

| CLI | 필요한 값 | 변경 |
|---|---|---|
| `collect` | raw dict | helper로 검증 후 raw dict를 `run_collect()`에 전달 |
| `run` | raw dict | helper로 검증 후 raw dict를 `run_pipeline()`에 전달 |
| `backfill` | raw dict | helper로 검증 후 raw dict를 `run_backfill()`에 전달 |
| `analyze` | parsed `SourcesConfig` | helper의 parsed config를 `run_analyze()`에 전달 |
| `deliver` | raw dict의 `lang` | helper로 검증 후 raw dict에서 `lang`을 읽음 |
| `dashboard` | raw dict의 `lang` | helper로 검증 후 raw dict에서 `lang`을 읽음 |

이 방식은 downstream `ValidationError` 오분류를 막기 위해 `try` 범위를 계속 좁게 유지한다. `run_*` 호출은 `try` 바깥에 둔다.

---

## 6. 테스트 전략

- `analyze` CLI가 malformed `sources.yaml`을 friendly message로 보고한다.
- `deliver` CLI가 malformed `sources.yaml`을 friendly message로 보고하고 report를 만들지 않는다.
- `dashboard` CLI가 malformed `sources.yaml`을 friendly message로 보고하고 dashboard를 만들지 않는다.
- 기존 `collect`, `run`, `backfill`의 friendly message 테스트는 유지한다.
- `run`의 downstream `ValidationError` propagation 테스트를 유지해 catch 범위가 넓어지지 않았음을 고정한다.

---

## 7. 문서 영향

| 파일 | 변경 |
|---|---|
| `docs/architecture/improvement-catalog.md` | CLI config 검증 일관화 항목을 구현 완료로 기록 |
| `docs/IMPROVEMENTS.md` | `sources.yaml` validation drift 해결을 기록 |
| `docs/reference/config/sources.md` | 필요 시 CLI 계약 문구를 현재 구현에 맞춰 보강 |

---

## 8. 수용 기준

- [x] `mimir analyze`가 malformed `sources.yaml`에 대해 `[mimir] invalid sources.yaml:`를 stderr에 출력하고 1을 반환한다.
- [x] `mimir deliver`가 malformed `sources.yaml`에 대해 같은 메시지와 exit code를 반환한다.
- [x] `mimir dashboard`가 malformed `sources.yaml`에 대해 같은 메시지와 exit code를 반환한다.
- [x] downstream `ValidationError`가 `sources.yaml` 오류로 오분류되지 않는다.
- [x] `uv run pytest tests/test_analyze.py tests/test_deliver.py tests/test_dashboard_cli.py tests/test_run.py tests/test_backfill.py tests/test_collect.py -q`가 통과한다.
- [x] `uv run ruff check .`, `uv run mypy mimir`, `uv run pytest -q`, coverage gate, `git diff --check`가 통과한다.
