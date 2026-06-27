# S3. Mimir Delivery & Reporting — 설계문서

> **스펙 ID**: S3
> **작성일**: 2026-05-31
> **상태**: 구현 완료 · S4/B1 확장 반영. 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
> **선행**: [S2 Analysis](2026-05-31-analysis-design.md) · [로드맵](../../architecture/roadmap.md)

---

## 1. 개요

S3는 S2가 만든 `insights`(와 S1 원천 데이터)를 읽어 두 가지 산출물을 만든다:
1. **풍부한 일일 HTML 리포트** — `reports/YYYY/MM/DD.html`로 저장(아카이브), `reports/index.html`에서 열람.
2. **텔레그램 다이제스트** — cadence별(매시간/매일/매주/매월) 요약 발송.

네트워크 출력은 텔레그램뿐이며, 입력은 저장된 JSONL이다(S2의 `DataReader` 재사용).

## 2. 범위

### 포함
- `build_report_html(insights, as_of)` — 종목 카드(⭐·방향·근거)·면책 포함 자립형 HTML
- `save_report(html, as_of, root)` + `rebuild_index(root)` — 날짜 아카이브 + index.html
- `build_digest(insights, cadence)` — 텔레그램용 짧은 텍스트(상위 ⭐ 종목)
- `deliver` CLI (`python -m mimir.deliver --date D --cadence daily`) — 리포트 저장 + 다이제스트 발송
- cadence 워크플로 체이닝: collect → analyze → history → evaluate → deliver → 커밋(data+reports)

### 제외(다음)
- 차트/그래프 시각화는 후속(텍스트·표 우선)

> 현재 상태: 이 문서는 최초 S3 설계에서 시작했지만, 현재 구현은 S4 과거 유사사례와
> B1 평가 성적표를 HTML 리포트에 함께 포함한다.

## 3. 설계 원칙
- **읽기 전용 입력**: `insights`/원천 데이터만 읽음. 분석은 S2가 끝냄.
- **자립형 HTML**: 인라인 CSS, 외부 의존 없음(어디서나 열림).
- **면책 항상**: 리포트·다이제스트에 "not financial advice".
- **graceful**: 인사이트가 없으면 "특이사항 없음" 리포트/다이제스트.
- **S1 저장소 재사용**: HTML은 `reports/`에 커밋되어 git에 아카이브됨.

## 4. 아키텍처
```
report/                         (기존 패키지 확장)
  daily_report.py   build_report_html · save_report · rebuild_index
  digest.py         build_digest(insights, cadence) -> str
  telegram.py       send_ping (기존) 재사용
deliver.py          CLI: insights/historical/evaluation 읽기 → HTML 저장 → 다이제스트 발송
```
흐름: `deliver --date D --cadence C` → `DataReader(JsonlStore).read(INSIGHTS/HISTORICAL/EVALUATION, D)` → HTML 저장 + index 갱신 → digest 생성 → `send_ping(settings, digest)`.

## 5. 산출물
- **HTML**: 헤더(날짜·cadence), 종목별 카드(⭐ 1~5, 강세/약세 배지, confidence, 근거 목록), 데이터 커버리지 요약, 면책. 인라인 CSS.
- **아카이브**: `reports/YYYY/MM/DD.html`; `reports/index.html`은 최신순 날짜 링크 목록.
- **다이제스트**: `🧭 Mimir <cadence> — <date>` 헤더 + 상위 N개 `⭐⭐⭐⭐ AAPL bullish — 근거`. 면책 한 줄.

## 6. 워크플로 체이닝
각 cadence 워크플로:
```
python -m mimir.collect  --cadence <c>
python -m mimir.analyze
python -m mimir.history
python -m mimir.evaluate
python -m mimir.deliver  --cadence <c>
git add data reports && commit || true && pull --rebase && push
```

## 7. 테스트(TDD, 80%+)
- `build_report_html`: 인사이트 → HTML에 심볼·⭐·방향·면책 포함; 빈 입력 → "특이사항 없음".
- `save_report`/`rebuild_index`: 파일 생성 + index가 날짜 링크 포함.
- `build_digest`: 상위 종목·⭐·면책 포함; cadence 헤더.
- `run_deliver`: 시드된 insights → HTML 파일 생성 + telegram 호출(mock).

## 8. 완료 기준
1. `python -m mimir.deliver --date D --cadence daily`가 `reports/YYYY/MM/DD.html` + `index.html` 생성.
2. 봇 토큰이 있으면 다이제스트 발송, 없으면 graceful no-op(기록).
3. 인사이트 0건도 깔끔한 리포트/다이제스트.
4. 워크플로가 collect→analyze→history→evaluate→deliver를 체이닝하고 reports를 커밋.
5. 커버리지 80%+, ruff·mypy --strict clean.
