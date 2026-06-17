# 커밋 분석

**Date:** 2026-06-18 KST
**Branch:** `feat/sec-ticker-cik-map`

## Provenance

이 커밋 문서는 `8532995 docs(merge): add DOCHEALTH merge check` 이후의 R1i 변경만 설명합니다. 현재 브랜치에는 앞선 DOCHEALTH 커밋도 포함되어 있지만, 그 변경은 별도 commit artifact에 기록되어 있습니다.

## 변경 파일

| File | Changes |
| ---- | ------- |
| `mimir/sources/rss_catalog.py` | SEC `company_tickers.json` loader와 ticker→CIK resolver를 추가 |
| `mimir/sources/config.py` | `sources.rss.sec.ticker_cik_map_path` schema 추가 |
| `mimir/core/builder.py` | RSS source 생성 시 mapping file을 읽어 resolver에 전달 |
| `mimir/config.py` | CLI config loader가 relative mapping path를 config directory 기준으로 해석 |
| `tests/sources/test_rss_catalog.py` | mapping loader, CIK URL 변환, 누락 ticker, ambiguous duplicate를 검증 |
| `tests/sources/test_config.py`, `tests/test_config.py` | config schema와 relative path 해석 검증 |
| `tests/core/test_builder.py` | builder wiring 검증 |
| README 3종, docs, config example | 테스트 수치와 새 SEC mapping 설정 계약 갱신 |
| `docs/_internal/skill-outputs/jira-ticket/R1i-SEC-CIK-sec-ticker-cik-map.md` | ticket artifact 추가 |
| `docs/decisions/tech-spec/sources/R1i-SEC-CIK_sec_ticker_cik_map_tech_spec_2026_06_18.md` | tech spec 추가 |

## 커밋 메시지

feat(sources): add SEC ticker CIK map lookup

- Add `sources.rss.sec.ticker_cik_map_path` so ticker-based SEC company filing feeds can resolve through a local `company_tickers.json` file before URL assembly.
- Keep the existing ticker-token path when no mapping file is configured, while failing loudly for missing ticker mappings and ambiguous duplicate ticker entries.
- Resolve relative mapping paths from the CLI config directory so `--config-dir` users can keep the JSON file next to `sources.yaml`.
- Update RSS config docs, extensibility docs, improvement tracking, README health metadata, and R1i ticket/spec artifacts to describe the new opt-in boundary.

## 명령어

```bash
git commit -m "feat(sources): add SEC ticker CIK map lookup

- Add sources.rss.sec.ticker_cik_map_path so ticker-based SEC company filing feeds can resolve through a local company_tickers.json file before URL assembly.
- Keep the existing ticker-token path when no mapping file is configured, while failing loudly for missing ticker mappings and ambiguous duplicate ticker entries.
- Resolve relative mapping paths from the CLI config directory so --config-dir users can keep the JSON file next to sources.yaml.
- Update RSS config docs, extensibility docs, improvement tracking, README health metadata, and R1i ticket/spec artifacts to describe the new opt-in boundary."
```

## 분석

- **Type:** `feat` - 사용자가 설정으로 활성화할 수 있는 새 SEC RSS resolver 기능을 추가합니다.
- **Scope:** `sources` - 핵심 변경이 source config, RSS resolver, builder에 집중됩니다.
- **Verification:** targeted tests 132 passed, `ruff`, `mypy`, full pytest 520 passed, coverage TOTAL 98%, `git diff --check` 통과
