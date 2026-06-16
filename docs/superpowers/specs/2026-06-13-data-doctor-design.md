# Increment 3. 데이터 신선도·품질 닥터 (`mimir doctor`) — 설계

> **스펙 ID**: INC3 (카탈로그 C1)
> **작성일**: 2026-06-13
> **상태**: ✅ 구현 완료 (Increment 3, MVP §9.1–§9.5 · 179 테스트 · ruff·mypy strict 클린). §6.3 HTML/i18n + 워크플로 연결은 후속.
> **선행**: [발전 카탈로그](../../architecture/improvement-catalog.md) · [S1 Collector](2026-05-31-collector-design.md)

---

## 1. 목적

매니페스트(`_manifest`)는 **실행(run)이 일어났다**를 기록한다. 그러나 *데이터 평면*은 아무도 감시하지 않는다:

- "어제 `prices` 파티션이 비었다."
- "워치리스트 종목 `AAPL`이 10일째 가격 레코드가 없다."
- "FRED `CPIAUCSL`(소비자물가) 시리즈가 2달째 갱신 안 됐다."
- "`prices` 파티션은 존재하는데 레코드가 3건뿐이다(평소 30건)."

이들은 **무음으로 흘러간다.** 수집이 `ok=True`로 끝나도 — 한 소스가 부분 실패하거나, 워치리스트에 종목을 추가했는데 어댑터가 그것을 안 긁거나, API가 빈 응답을 주거나 — 매니페스트는 "실행됨"만 본다.

`mimir doctor`는 **읽기 전용 점검기**로, 저장된 데이터를 스캔해 신선도·커버리지·구조 이상을 등급(severity)과 함께 보고하고, **CRITICAL 정체 시 비-0 종료**한다. 이로써 프로젝트의 **"무음 실패 금지"** 약속을 *실행 평면*에서 *데이터 평면*으로 확장한다.

**비목표(이번 증분 아님).**

- 데이터 *수정*·재수집·자동 백필 트리거(닥터는 진단만 — 치료는 사람/별도 잡).
- 페이로드 **심층** 스키마 검증(타입·범위) → [타입드 페이로드 설계(A4)](2026-06-13-typed-payload-design.md)가 담당. 닥터는 **키 존재** 수준만 본다(§4.6).
- 파티션 인덱스(C2, 카탈로그에서 보류). 닥터는 `rglob` + 사전식 정렬로 충분(§3.2).
- 휴장 캘린더 정밀 구현(공휴일 DB 의존성). 영업일 근사 + slack으로 흡수(§5).

---

## 2. 설계 원칙 (프로젝트 약속과의 정합)

| 약속 | 닥터에서의 구현 |
|---|---|
| **무음 실패 금지** | CRITICAL 발견 시 비-0 종료 → CI/cron이 표면화. WARN은 0으로 종료하되 보고서에 남김. |
| **읽기 전용 / 분석·실행 분리** | `data/`에 **아무것도 쓰지 않는다.** 결과는 stdout(JSON) + 선택적 HTML 섹션. 보고서를 git-as-DB에 저장하지 **않는다**(그 자체가 또 감시 대상이 됨 — turtles all the way down). |
| **불변성** | `DataReader`/`JsonlStore`의 읽기 경로만 사용. 새 mutation 없음. |
| **무료·합법** | 네트워크 호출 0. 로컬 파일 스캔만. |
| **TDD + mypy strict** | 모든 점검 함수는 `now` 주입으로 결정론적. pydantic 모델로 보고서 타입 고정(§6). |

---

## 3. 데이터 모델 사실 확인 (정확성 근거)

설계는 아래 **실제 코드 사실**에 기반한다(추정 아님).

### 3.1 파티션·레코드 사실

| 사실 | 출처 | 닥터에서의 함의 |
|---|---|---|
| 파티션 경로 = `data/<dataset>/YYYY/MM/DD.jsonl` | `storage/paths.py:partition_path` | 사전식 정렬이 곧 시간순 정렬. |
| 파티션 날짜 = `rec.ts.date()` (`captured_at` 아님) | `jsonl_store.py:append` (`rec.ts.date()`로 키잉) | **신선도 = 오늘 vs 최신 파티션의 `ts` 날짜.** `captured_at`은 무시. |
| 레코드 식별자 = `Record.symbol` | `storage/schema.py` | 워치리스트·매크로 커버리지를 `symbol`로 조회 가능. |
| `prices` 종목 식별자 = `symbol` | `DataReader.read(symbol=...)` 필터 | 워치리스트 ↔ `prices.symbol` 직접 대조. |
| **macro 시리즈 식별자도 `symbol`** | FRED `symbol=series_id`; ECOS `symbol=f"{stat_code}.{item_code}"` | 매크로 **시리즈별** 신선도를 `symbol`로 점검 가능(§4.4). |

### 3.2 최신 파티션 탐색 (인덱스 없이)

```python
base = root / dataset.value
paths = sorted(base.rglob("*.jsonl"))   # YYYY/MM/DD → 사전식=시간순
latest = paths[-1] if paths else None   # 최신 파티션 경로
```

`read_window`이 이미 이 패턴을 쓴다(`base.rglob`). C2(파티션 인덱스)는 카탈로그에서 **보류**됐으므로 닥터도 인덱스를 **추가하지 않는다** — 데이터셋당 최신 1개만 찾으면 되고, 가장 비싼 경우라도 디렉터리 트리 1회 스캔이다.

### 3.3 Cadence는 데이터셋이 아니라 **소스**에 산다 — 핵심 함정

`Cadence`는 `SourceMeta`의 필드이지 `Dataset`의 속성이 **아니다**. 그리고 **한 데이터셋 안에서도 이질적**이다:

> **검증된 함정.** FRED `SourceMeta.cadence = DAILY`인데, 그 어댑터는 `DGS10`(일간)과 `CPIAUCSL`(**월간**)을 **함께** 발행한다. 즉 소스 메타의 cadence조차 *시리즈별로는 틀리다*. macro 파티션은 DGS10이 매일 쓰므로 **항상 신선해 보이지만**, "macro 시리즈는 3일 내 갱신" 같은 단일 규칙은 **CPI를 매일 오탐**한다.

따라서 닥터의 신선도 모델은 **데이터셋 단위가 아니라 (데이터셋, 시리즈/종목) 단위**로 cadence를 알아야 하며, 모르면 **가장 느슨한 cadence로 폴백**한다(§4.4, §7).

---

## 4. 점검 항목 (Checks)

각 점검은 0개 이상의 `Finding`을 낳는다(§6). 점검 단위는 **(dataset, scope)** — scope는 데이터셋 전체이거나 특정 종목/시리즈.

### 4.1 기대 커버리지 집합 — 설계의 심장

> **핵심 안티패턴 — 절대 `build_sources(settings)`에서 기대 집합을 유도하지 말 것.**
> `build_sources`의 if-사다리는 **API 키 유무로 소스를 조건부 추가**한다. 키가 빠지면 소스가 사라지고 — **닥터가 잡아야 할 바로 그 실패(데이터 부재)를 점검 자체가 조용히 건너뛴다.** "FRED 키 누락 → FRED 소스 없음 → FRED 신선도 점검 없음 → 데이터 없어도 OK"는 무음 실패다.

대신 **기대 커버리지를 명시적으로** 정의한다:

```python
# mimir/doctor/expectations.py — 코드 내 sane 기본값 (config로 override 가능)
EXPECTED_DATASETS: dict[Dataset, Cadence] = {
    Dataset.PRICES: Cadence.DAILY,
    Dataset.FILINGS: Cadence.DAILY,    # 영업일 기준 정기 공시 흐름
    Dataset.MACRO:  Cadence.DAILY,     # 데이터셋 바닥선; 시리즈별 override는 §4.4
    Dataset.NEWS:   Cadence.DAILY,
    Dataset.INSIGHTS: Cadence.DAILY,   # 파이프라인이 매 실행 생성
    # HISTORICAL: 신선도 점검 제외(백필성·비정기) — §4.7
}
```

그런 뒤 **명시적 기대 ↔ 실제 존재**를 대조한다. "데이터셋 X가 기대되는데 파티션이 전혀 없음/최신이 정체"는 **건너뛸 행이 아니라 발견(finding)**이다. 설정으로 데이터셋을 끌 수 있으나(예: 키 없는 운영자가 의도적으로 ECOS 비활성), 그건 **명시적 opt-out**이지 키 부재로 인한 암묵적 소실이 아니다.

### 4.2 데이터셋 신선도 — 최신 파티션 나이 vs cadence

각 기대 데이터셋에 대해:

1. 최신 파티션 날짜 `latest_ts_date` 탐색(§3.2). 없으면 → **CRITICAL(`missing`)**.
2. `now.date()` 기준 **영업일 나이**(§5) 계산.
3. `cadence → max_staleness` 테이블(§4.3)과 비교 → OK / WARN / CRITICAL.

### 4.3 cadence → 허용 정체 테이블 (영업일 인식)

4값 `Cadence` enum에서 바깥으로 모델을 세운다:

| Cadence | WARN 임계 | CRITICAL 임계 | 근거 |
|---|---|---|---|
| `HOURLY` | > 1 영업일 | > 2 영업일 | 시간 단위지만 **파티션은 일 단위**(자정 UTC). 사실상 일간으로 취급. |
| `DAILY` | > 2 영업일 | > 4 영업일 | 주말·공휴일 흡수. 월요일에 "일요일 데이터 없음" 오탐 금지(§5). |
| `WEEKLY` | > 9 일(캘린더) | > 16 일 | 한 주기 미스 = WARN, 두 주기 = CRITICAL. |
| `MONTHLY` | > 38 일 | > 70 일 | 발표 지연(예: CPI 익월 중순) 흡수. 한 발표 미스 = CRITICAL. |

값은 `mimir/doctor/policy.py`의 상수 테이블로 두어 조정·테스트 가능(매직넘버 금지). 임계는 **정책**이지 발견이 아니다 — 보수적으로 시작하고 오탐 데이터로 조인다.

### 4.4 매크로 시리즈별 신선도 — cadence 이질성 처리

§3.3의 함정을 정면 처리한다. macro는 **데이터셋 단위가 아니라 시리즈(`symbol`) 단위**로 본다:

1. 기대 매크로 시리즈 목록 + **시리즈별 cadence**를 명시적으로 안다:

```python
# mimir/doctor/expectations.py
MACRO_SERIES_CADENCE = macro_series_cadences()
DEFAULT_MACRO_CADENCE = Cadence.MONTHLY   # 미등록 시리즈 = 가장 느슨하게 폴백
```

2. 각 시리즈에 대해 `DataReader.read(Dataset.MACRO, symbol=series).` 윈도우로 최신 `ts` 날짜를 구하고, **그 시리즈의 cadence**로 §4.3 테이블 적용.
3. **미등록 시리즈는 `DEFAULT_MACRO_CADENCE`(MONTHLY)로 폴백** — 모르면 오탐보다 침묵 쪽으로(보수적). 단 "기대 목록에 없던 새 시리즈가 데이터에 존재" 자체는 INFO로 보고(설정 동기화 힌트).

> **불변식.** 닥터는 `SourceMeta.cadence`(소스 단위·시리즈엔 부정확)를 매크로 시리즈 신선도의 **단일 근거로 쓰지 않는다.** `mimir/core/macro_series.py`가 제공하는 시리즈별 cadence가 우선, 없으면 느슨한 폴백을 쓴다.

2026-06-16 A2 구현 뒤 `MACRO_SERIES_CADENCE`는 직접 dict literal을 갖지 않는다. macro registry가 cadence를 제공하므로 `MacroRegimeSignal`과 doctor가 같은 시리즈 메타데이터를 읽는다.

### 4.5 워치리스트 커버리지 — 종목별 최근 `prices`

1. `load_watchlist(config_dir)` → `{"us":[...], "kr":[...]}`.
2. 모든 심볼을 평탄화(시장 구분은 보고에만 사용).
3. 각 심볼에 대해 `DataReader.read(Dataset.PRICES, symbol=sym, since=now-N)` 최신 `ts` 날짜 확인.
4. PRICES는 DAILY → §4.3 DAILY 임계 적용.
   - 최근 윈도우 내 레코드 0건 → 영업일 나이로 WARN/CRITICAL.
   - **한 번도 없음**(전체 트리에 부재) → CRITICAL(`missing`) + "워치리스트엔 있으나 수집된 적 없음" 메시지(오타·미지원 심볼 힌트).

> **영업일 인식 필수.** 금요일 종가가 최신인 상태로 월요일 아침 닥터를 돌리면, 캘린더 나이는 3일이지만 **영업일 나이는 1일** → 오탐 금지(§5).

### 4.6 빈/짧은 파티션

1. 최신(및 선택적으로 최근 K개) 파티션의 **레코드 수**를 센다.
2. 0건 → **CRITICAL(`empty`)**: 파일은 있는데 데이터가 없음(부분 실패의 전형적 흔적 — 매니페스트는 `ok`로 보일 수 있음).
3. **비정상적으로 적음**(`short`) → WARN: 휴리스틱은 KISS로 — *동일 데이터셋 최근 N개 파티션 중앙값의 일정 비율 미만*(예: < 30%). 절대 임계 하드코딩 대신 **자기 기준선 대비 상대 비교**(데이터셋마다 규모가 다름). 표본이 부족하면(파티션 < 3개) `short` 점검은 **건너뛰고 그 사실을 INFO로** 남긴다(무음 금지).

### 4.7 페이로드 스키마 이상 — 키 존재만 (얕게)

데이터셋별 **필수 키 집합**이 페이로드에 있는지만 본다:

```python
EXPECTED_PAYLOAD_KEYS: dict[Dataset, frozenset[str]] = {
    Dataset.PRICES: frozenset({"close"}),
    Dataset.MACRO:  frozenset({"series_id", "value"}),
    # ...
}
```

- 최신 파티션에서 표본 레코드의 키 누락 → WARN(`schema`). 메시지에 누락 키 명시.
- **타입·범위·교차필드 검증은 하지 않는다** → [타입드 페이로드(A4)](2026-06-13-typed-payload-design.md)로 위임. 닥터는 "구조가 통째로 어긋남"의 조기 경보일 뿐, 그 스펙과 **중복 구현 금지**.
- `historical`은 백필성·비정기라 **신선도 점검에서 제외**하되, 존재 시 키 점검은 수행(선택).

---

## 5. 영업일 인식 정체 규칙 (실용적·근사)

시장은 주말·공휴일에 닫는다. 월요일에 "일요일 데이터 없음"으로 오탐하면 안 된다. **공휴일 DB 의존성 없이** 다음 근사를 쓴다(KISS):

```python
def business_days_between(start: date, end: date) -> int:
    """start(제외)~end(포함) 사이 월~금 일수. 공휴일은 §아래 slack이 흡수."""
    days = 0
    d = start
    while d < end:
        d += timedelta(days=1)
        if d.weekday() < 5:   # 0=월 ... 4=금
            days += 1
    return days
```

- **DAILY/HOURLY 신선도**는 `business_days_between(latest_ts_date, now.date())`로 나이를 잰다 → 주말 자동 흡수.
- **공휴일**(US `Independence Day`, KR `추석` 등)은 캘린더가 시장마다 다르므로 **명시 구현하지 않고**, §4.3 임계의 **slack(WARN>2, CRITICAL>4 영업일)이 1~2일 연휴를 흡수**하도록 둔다. 장기 연휴(설/추석 다일 휴장)는 드물게 WARN을 낼 수 있으나, CRITICAL(>4 영업일)까지 가긴 어렵다 — 의도적 트레이드오프(오탐 < 미탐).
- **WEEKLY/MONTHLY**는 캘린더일 기준(영업일 환산 불필요 — 임계가 충분히 넓음).
- **`now`는 주입**한다(`now: datetime | None = None`, 기본 `datetime.now(UTC)`) → 테스트 결정론. collect.py가 이미 같은 패턴.

> **나중에**: 영업일 정밀도가 필요해지면 시장별 휴장 캘린더를 `config/`로 받는 seam을 열 수 있으나(YAGNI), 지금은 slack 흡수로 충분.

---

## 6. 출력 — 구조화 보고서

### 6.1 pydantic 모델 (`mimir/doctor/report.py`)

```python
class Severity(StrEnum):
    OK = "ok"
    WARN = "warn"
    CRITICAL = "critical"

class FindingKind(StrEnum):
    STALE = "stale"          # 최신 파티션이 cadence 대비 오래됨
    MISSING = "missing"      # 기대 데이터셋/심볼이 전혀 없음
    EMPTY = "empty"          # 파티션 존재하나 0건
    SHORT = "short"          # 레코드 수가 기준선 대비 비정상적으로 적음
    SCHEMA = "schema"        # 필수 페이로드 키 누락
    INFO = "info"            # 점검 건너뜀·동기화 힌트 등(무음 금지)

class Finding(BaseModel):
    dataset: Dataset
    scope: str | None        # 심볼/시리즈, 데이터셋 전체면 None
    kind: FindingKind
    severity: Severity
    message: str             # 사람이 읽을 한 줄(언어 무관 진단 사실)
    latest_ts: date | None   # 최신 데이터 날짜(없으면 None)
    business_days_stale: int | None

class DoctorReport(BaseModel):
    checked_at: datetime
    data_root: str
    findings: list[Finding]

    @property
    def worst(self) -> Severity: ...   # CRITICAL > WARN > OK
    @property
    def exit_code(self) -> int:        # CRITICAL → 1, 그 외 → 0
        return 1 if self.worst is Severity.CRITICAL else 0
```

- 모든 점검 함수는 **부작용 없는 순수 함수**: `(store/reader, expectations, now) -> list[Finding]`. 테스트는 합성 트리 + 고정 `now`로 `Finding` 리스트를 직접 단언.
- `DoctorReport.model_dump_json()`이 stdout JSON 산출(머신리더블 — CI 파싱·다른 잡 연계).

### 6.2 CLI (`mimir/doctor.py`)

기존 진입점(`collect.py`/`run.py`/`backfill.py`) 컨벤션과 동일: `argparse` + `main(argv) -> int` + `sys.exit(main())`.

```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimir.doctor")
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--data-root", default=str(DEFAULT_ROOT))
    parser.add_argument("--format", choices=["json", "text"], default="text")
    parser.add_argument("--html", help="선택: 닥터 섹션 HTML 출력 경로")
    parser.add_argument("--strict", action="store_true",
                        help="WARN도 비-0으로 escalate(기본: CRITICAL만 비-0)")
    args = parser.parse_args(argv)

    watchlist = load_watchlist(Path(args.config_dir))
    store = JsonlStore(root=Path(args.data_root))
    report = run_doctor(store=store, watchlist=watchlist, now=datetime.now(UTC))

    _emit(report, fmt=args.format)             # text: 등급별 정렬 출력
    if args.html:
        render_doctor_html(report, Path(args.html), lang=...)   # §6.3

    code = report.exit_code
    if args.strict and report.worst is Severity.WARN:
        code = 1
    return code

if __name__ == "__main__":
    sys.exit(main())
```

- **기본**: CRITICAL → 1(비-0), WARN → 0. (태스크 요구: CRITICAL 정체 시 비-0.)
- `--strict`는 한 줄 옵션 — WARN까지 막고 싶은 엄격 cron용. 과설계 금지(빌드아웃 없음).
- `run_doctor`는 `now` 주입 가능한 오케스트레이터 — §4 점검들을 모아 `DoctorReport` 합성.

### 6.3 status.html 통합 (선택)

`render_status_html`(`report/status_html.py`)은 `RunRecord`를 받아 파일을 **통째로 덮어쓴다** — 닥터 보고서는 **다른 모양**이므로 그 함수에 끼워넣지 않는다. 대신:

- **별도 `render_doctor_html(report, out_path, lang)`** 를 두거나, 닥터 섹션 HTML 조각을 반환해 상태 페이지가 합성하게 한다.
- 신규 i18n 키를 **3개 언어(en/ko/zh) 모두** `report/i18n.py:STRINGS`에 추가(기존 패턴 준수):
  `doctor_heading`, `doctor_col_dataset`, `doctor_col_scope`, `doctor_col_severity`, `doctor_col_detail`, `doctor_sev_ok/warn/critical`, `doctor_all_clear`.
- `Finding.message`는 진단 사실(심볼·일수)을 담고, **등급·헤더 라벨만 i18n**한다(메시지 본문까지 3언어 번역은 과함 — 사실은 언어 무관).

---

## 7. 알려진 부채·후속 (명시)

| 항목 | 내용 |
|---|---|
| **시리즈 메타 이중화** | 2026-06-16 A2에서 `mimir/core/macro_series.py`로 해소. doctor는 `macro_series_cadences()`를 읽는다. |
| **기대 집합 수동** | `EXPECTED_DATASETS`/`EXPECTED_PAYLOAD_KEYS`는 코드 상수. A4(타입드 페이로드)가 데이터셋별 모델을 만들면 필수 키를 거기서 파생 가능. |
| **공휴일 근사** | slack 흡수. 장기 연휴 오탐 가능성 — 필요 시 시장별 휴장 캘린더 seam(YAGNI). |
| **`short` 휴리스틱** | 상대 기준선(중앙값 대비). 데이터 누적 후 임계 재보정 여지. |

---

## 8. 수용 기준 (Acceptance)

- [ ] **신선 데이터** 합성 트리(모든 기대 데이터셋 최신 파티션 존재) + 고정 `now` → 모든 `Finding`이 OK, `exit_code == 0`.
- [ ] **정체 데이터**: `prices` 최신이 6 영업일 전 → CRITICAL(`stale`), `exit_code == 1`.
- [ ] **누락**: 기대 데이터셋 `macro` 파티션 전무 → CRITICAL(`missing`).
- [ ] **빈 파티션**: 최신 `prices` 파티션 존재하나 0건 → CRITICAL(`empty`).
- [ ] **짧은 파티션**: 최신 레코드 수가 최근 중앙값의 30% 미만 → WARN(`short`); 파티션 < 3개면 점검 건너뛰고 INFO.
- [ ] **워치리스트 커버리지**: 워치리스트에 `XYZ` 추가했으나 `prices`에 전무 → CRITICAL(`missing`, "수집된 적 없음").
- [ ] **영업일 오탐 방지**: 금요일 종가가 최신, `now`=월요일 → DAILY 나이 = 1 영업일 → OK(오탐 없음).
- [ ] **매크로 cadence 이질성**: `CPIAUCSL`(MONTHLY 등록) 최신이 20일 전 → **OK**(DAILY 규칙이라면 CRITICAL일 상황) — 매일 오탐하지 않음을 회귀로 고정.
- [ ] **미등록 매크로 시리즈**: 테이블에 없는 새 시리즈는 `DEFAULT_MACRO_CADENCE`(MONTHLY)로 평가 + 존재 사실 INFO.
- [ ] **키 부재 ≠ 점검 소실**: 기대 집합이 `build_sources`가 아니라 명시 상수에서 옴을 단언 — FRED 키 없이도 `macro` 부재가 CRITICAL로 잡힘.
- [ ] **스키마**: `prices` 페이로드에 `close` 누락 → WARN(`schema`, 누락 키 명시).
- [ ] **읽기 전용**: 닥터 실행 전후 `data/` 바이트 동일(쓰기 0) — 테스트로 단언.
- [ ] **출력**: `--format json`이 유효 `DoctorReport` JSON; `--html`이 3언어 라벨로 섹션 렌더.
- [ ] **CLI 종료코드**: CRITICAL → 1, WARN → 0, `--strict` 시 WARN → 1.
- [ ] 네트워크 호출 0 · ruff · mypy strict 클린 · 커버리지 ≥ 80%.

### 8.1 테스트 계획 (합성 `data/` 트리, 무네트워크)

`tmp_path`에 데이터셋·파티션을 프로그램으로 만든다(헬퍼: `write_partition(root, dataset, day, records)`). 시나리오 매트릭스:

| 픽스처 | 구성 | 기대 |
|---|---|---|
| `fresh_tree` | 전 데이터셋 최신=`now` | OK / exit 0 |
| `stale_prices` | prices 최신=`now`-6영업일 | CRITICAL / exit 1 |
| `missing_macro` | macro 디렉터리 없음 | CRITICAL |
| `empty_latest` | prices 최신 파티션 0줄 | CRITICAL |
| `short_latest` | prices 최신 3건 vs 중앙값 40건 | WARN |
| `weekend_boundary` | prices 최신=금요일, now=월요일 | OK |
| `monthly_macro` | CPIAUCSL 최신=20일 전 | OK |
| `watchlist_gap` | 워치리스트 종목이 prices에 전무 | CRITICAL |
| `schema_drift` | prices 페이로드에 `close` 없음 | WARN |

`now`는 전 케이스 고정 주입. 어떤 테스트도 네트워크·실제 `data/`를 건드리지 않는다.

---

## 9. 구현 작업 분해 (plan 입력)

1. **보고서·정책 모델**: `mimir/doctor/report.py`(`Severity`/`FindingKind`/`Finding`/`DoctorReport`), `mimir/doctor/policy.py`(cadence→임계 테이블), `mimir/doctor/expectations.py`(기대 데이터셋·매크로 cadence·페이로드 키) + 단위 테스트.
2. **영업일·신선도 유틸**: `business_days_between` + cadence 적용 순수 함수 + 단위 테스트(경계·주말).
3. **점검 함수들**: 신선도·커버리지·빈/짧음·스키마 각각 `(reader, expectations, now) -> list[Finding]` + 테스트(§8.1 매트릭스).
4. **오케스트레이터**: `run_doctor(store, watchlist, now) -> DoctorReport`.
5. **CLI**: `mimir/doctor.py`(`main(argv)->int`, 종료코드·`--strict`·`--format`) + 통합 테스트.
6. **HTML·i18n(선택)**: `render_doctor_html` + 3언어 키 + 렌더 테스트.

각 작업 TDD(RED→GREEN→REFACTOR). 의존: 1 → 2 → 3 → 4 → 5 → 6. 1~5가 핵심(MVP), 6은 선택 통합.
