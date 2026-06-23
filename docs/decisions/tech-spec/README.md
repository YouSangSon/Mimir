# Tech Spec 색인

> **상태**: 현재 구현 기준
> **목적**: `docs/decisions/tech-spec/` 아래의 결정 tech spec을 도메인별로 한눈에 본다.

이 디렉터리는 비교적 최근의 결정 spec을 도메인별 하위 폴더로 모은다. S1–S4 단계의 설계문서는 여전히 `docs/superpowers/specs/`에 있고, 여기에는 그 위에 쌓인 증분 결정들이 들어온다.

## backfill

| Spec | 목적 |
|---|---|
| [BF-PREFLIGHT](backfill/BF-PREFLIGHT_backfill_preflight_manifest_tech_spec_2026_06_18.md) | 백필이 fetch 전에 실패해도 registered-but-unavailable source를 manifest에 기록 |

## analysis

| Spec | 목적 |
|---|---|
| [AN1-SIGNAL-PLUGIN-ENTRYPOINTS](analysis/AN1_signal_plugin_entrypoints_tech_spec_2026_06_23.md) | `mimir.analysis_signals` entry point와 `analysis.plugins.<signal_id>` opt-in 계약을 고정 |

## config

| Spec | 목적 |
|---|---|
| [CFG1](config/CFG1_sources_config_cli_validation_tech_spec_2026_06_18.md) | `sources.yaml` schema 오류를 CLI 경계에서 `[mimir] invalid sources.yaml:`로 검증 |
| [CFG2](config/CFG2_doctor_sources_config_validation_tech_spec_2026_06_18.md) | `mimir doctor`가 데이터 점검·HTML 쓰기 전에 `sources.yaml`을 검증 |
| [CFG3](config/CFG3_config_guardrails_tech_spec_2026_06_18.md) | `watchlist.yaml` schema 검증 + `llm_sentiment_max_headlines` cap 경계(1~50) |

## docs

| Spec | 목적 |
|---|---|
| [DOCHEALTH](docs/DOCHEALTH_readme_doc_health_tech_spec_2026_06_18.md) | README test badge·표와 실제 pytest 수집 개수의 drift를 회귀 테스트로 고정 |

## doctor

| Spec | 목적 |
|---|---|
| [DCHTML](doctor/DCHTML_doctor_html_report_tech_spec_2026_06_18.md) | `mimir doctor --html`이 같은 진단을 standalone HTML로 출력 |

## sources

| Spec | 목적 |
|---|---|
| [Design spec: SEC ticker CIK map cache](../../superpowers/specs/2026-06-19-sec-ticker-cik-map-cache-design.md) | `docs/decisions/tech-spec/` 이전 설계 문서. off-by-default SEC mapping cache refresh, TTL, ETag, fair-access 경계를 정의 |
| [R1i-SEC-CIK](sources/R1i-SEC-CIK_sec_ticker_cik_map_tech_spec_2026_06_18.md) | 로컬 SEC `company_tickers.json`으로 ticker→10자리 CIK 변환 |
| [R1j-SEC-CIK-ERRORS](sources/R1j-SEC-CIK-ERRORS_sec_ticker_cik_map_errors_tech_spec_2026_06_18.md) | mapping file 단위 오류를 path 포함 설정 오류로 정규화 |
| [R1k-SEC-CIK-ENTRY-ERRORS](sources/R1k-SEC-CIK-ENTRY-ERRORS_sec_ticker_cik_map_entry_errors_tech_spec_2026_06_18.md) | mapping entry 오류에 파일 경로와 entry key 포함 |
| [R1l-SEC-CIK-CLI-ERRORS](sources/R1l-SEC-CIK-CLI-ERRORS_sec_ticker_cik_map_cli_errors_tech_spec_2026_06_18.md) | source build `ValueError`를 CLI에서 friendly message로 출력 |
| [R1m-SEC-CIK-MISSING-PATH](sources/R1m-SEC-CIK-MISSING-PATH_sec_ticker_cik_missing_path_tech_spec_2026_06_18.md) | missing ticker lookup 오류에 사용한 mapping file 경로 포함 |
| [R1n-SEC-CIK-CLI-PATH-CONTRACT](sources/R1n-SEC-CIK-CLI-PATH-CONTRACT_sec_ticker_cik_cli_path_contract_tech_spec_2026_06_18.md) | `collect`/`run`/`backfill` CLI stderr 경로 계약을 테스트로 고정 |

## storage

| Spec | 목적 |
|---|---|
| [Design spec: captured-date persistent index](../../superpowers/specs/2026-06-19-captured-date-persistent-index-design.md) | `docs/decisions/tech-spec/` 이전 설계 문서. NEWS `captured_at` 창 반복 스캔 완화를 위한 persistent index 방향을 정리 |
| [C2a](storage/C2a_captured_news_window_cache_tech_spec_2026_06_18.md) | `DataReader`가 captured-date index를 메모리에 만들어 NEWS 반복 scan 완화 |
