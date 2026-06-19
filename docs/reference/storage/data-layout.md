# 데이터 저장 레이아웃 레퍼런스 (git-as-DB)

> **상태**: 현재 구현 기준
> **최종 업데이트**: 2026-06-19
> **대상 독자**: repo에 커밋되는 데이터를 들여다보거나 백업·점검하는 운영자, 저장 동작을 이해하려는 개발자
> **관련**: 저장 *정책*의 배경은 [extensibility 가이드 §5](../../architecture/extensibility/README.md), 점검은 `mimir doctor`

Mimir는 상시 DB 없이 **수집 데이터를 repo에 JSONL로 커밋**한다(git-as-DB). 이 문서는 그 on-disk 구조와 규약을 한 곳에 모은다.

---

## 1. 파티션 레이아웃

```
data/<dataset>/<YYYY>/<MM>/<DD>.jsonl
```

`partition_path(dataset, dt, root="data")`가 만든다. 한 줄에 record 하나(JSON). 파티션 날짜는 record의 `ts.date()`(자정 UTC 기준 안정)다. NEWS도 `ts.date()`로 저장되지만, 뉴스 분석 시그널은 `captured_at.date()` 기준 윈도우로 읽는다([scoring.md](../analysis/scoring.md), extensibility §5).

운영 로그는 데이터셋이 아니라 별도다: `data/_manifest/<YYYY>/<MM>/<DD>.jsonl`에 수집·백필 실행 결과(source별 성공/실패·fetched/stored·실패 원인)를 남긴다.

---

## 2. 데이터셋

| dataset | 성격 | 저장 정책 |
|---|---|---|
| `prices` | 원천 가격 | append-only, first-write-wins |
| `filings` | 원천 공시 | append-only, first-write-wins |
| `news` | 원천 뉴스(제목·요약만) | append-only, first-write-wins |
| `macro` | 공식 거시 관측값(FRED/ECOS) | overwrite append, **last-write-wins**(공식 개정값 반영) |
| `insights` | 매 실행 재계산 | 당일 파티션 **전체 교체**(`replace_partition`) |
| `historical` | 매 실행 재계산(event-study) | 당일 파티션 전체 교체 |
| `evaluation` | 매 실행 재계산(시그널 성적표) | 당일 파티션 전체 교체 |

정책은 `append_overwrite_enabled(dataset)`(현재 `macro`만 overwrite)와 재생성 데이터셋의 `JsonlStore.replace_partition(dataset, day, records)`로 강제된다. 재생성 결과가 0건이면 파티션 파일을 삭제해 stale record가 다음 리포트에 남지 않게 한다.

- **first-write-wins**(가격/공시/뉴스): 같은 `idempotency_key`가 다시 와도 첫 record를 유지(원천 데이터는 불변).
- **last-write-wins**(macro): 같은 key가 다시 오면 최신 record로 교체(금리·통계 공식 개정 반영).
- **전체 교체**(insights/historical/evaluation): 당일 분을 통째로 다시 쓴다.

---

## 3. Idempotency key 규약

dedup 단위. source prefix로 교차충돌이 없다.

| source | 형식 |
|---|---|
| Stooq(가격) | `stooq:{symbol}:{day}` |
| pykrx(가격) | `pykrx:{code}:{day}` |
| SEC EDGAR(공시) | `sec_edgar:{cik10}:{accession}` |
| DART(공시) | `dart:{rcept_no}` |
| FRED(거시) | `fred:{series_id}:{day}` |
| ECOS(거시) | `ecos:{stat_code}:{item_code}:{time}` |
| RSS(뉴스) | `rss:{link}` 또는 symbol-tagged feed는 `rss:{symbol}:{link}` |

이 형식은 git-as-DB dedup의 안정 계약이다. 형식이 조용히 바뀌면 이미 커밋된 데이터가 고아가 되거나 중복되므로, 변경은 회귀 테스트로 고정한다(예: ECOS 비월간 cycle은 `TIME` token을 그대로 key에 쓴다 — [scoring.md] 관련 COV1 참고).

---

## 4. 운영 메모

- 데이터는 repo에 커밋되므로 git 히스토리가 곧 데이터 이력이다. 재생성 데이터셋(insights/historical/evaluation)은 매 실행 당일 파티션이 교체되어 churn이 있을 수 있다.
- 비밀값은 데이터·manifest·리포트에 추가로 노출하지 않는다(ECOS 키 URL 유출은 redaction 처리됨).
- 신선도·누락·schema 이상은 `mimir doctor`가 점검한다(read-only). doctor는 source fetch나 외부 다운로드를 하지 않는다.
- 리포트 산출물은 `reports/`에 있다: 일일 `reports/YYYY/MM/DD.html`, `reports/index.html`(아카이브), `reports/dashboard.html`(최신 운영 대시보드).
