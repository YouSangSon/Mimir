# Project Plan

This file owns the delivery scope and resume boundary. Detailed plans stay in
`docs/superpowers/plans/`; implementation history stays in Git and `WORKLOG.md`.

## Delivery Scope — PORTFOLIO CLOSEOUT (2026-10-25)

Mimir의 기존 S1–S4 파이프라인을 사용할 수 있게 다듬는 유한 구현 대기열은
닫혔다. 사용자의 최신 요청 "우선 안되면 vm은 건너뛰어"에 따라 이번 목표에서
my-cloud 배포·runtime 검증을 제외한다. VM 접속을 더 재시도하거나 이를 대신할
새 서버·공개 데모를 만들지 않는다. 새로운 요청이 있을 때만 VM 검증을 재개한다.

구현·로컬 데모·필수 무료 CI·main 반영·소유 자원 정리·포트폴리오 근거는 이번
목표에 유지한다. commit/push/PR/main merge의 기존 승인은 유지하며 필수 CI를
생략하지 않는다. 유료 실행·credential 변경·외부 발송은 승인되지 않았다.
S5 거래, 유료 LLM, 범용 RSS discovery와 새 인프라는 범위 밖이다.

## Current Verification — POPULATED-CADENCE-PIPELINE

새 Goal의 첨부 지시는 이전과 byte가 같으며 VM 제외 요청을 유지한다. 완료 근거를
대조한 결과, 기존 run 검사는 빈 입력이고 실제 CLI 데모는 이미 저장된 자료에서
시작했다. `tests/test_run.py`에 HTTP mock 응답의 실제 수집·정규화·저장부터
분석·historical·evaluation·HTML까지 이어지는 작은 검사를 보완했다.

5개 과거 관측이 평가의 최소 표본 gate를 넘도록 이후 세션까지 진행하며, 응답에
미래 가격을 미리 넣지 않는다. 수집403 실패 때는 기존 가격 bytes를 보존하고
manifest·상태 화면에 오류를 남기면서 새 리포트를 생성하는지 확인했다. 앱 코드·
설정·의존성은 바꾸지 않는다. 실제 API·개인 VM·실서비스를 검증한 것으로 표현하지 않는다.
최종 검사·리뷰·CI/main·정리 근거는 resume 기존 폴더의 `populated-pipeline/`에 남긴다.

PR22의 필수 CI40152251520은747개 테스트·프로덕션3443 statements/85 missed로
통과해 main `adca1bf`에 반영됐다. 표시 단위로 반올림하면98%이며, 새 검사가 추가로
덮은 코드량은2줄이다. README 세 언어의 현재 커버리지 표시는 이 결과에 맞춘다.

## Completed Implementation and Verification

- `BACKLOG.md`의 구현 대기열은 비어 있다. 입력 오류 경계, macro 단일 읽기,
  리포트 접근성, 네 cadence 계약, 문서 건강도와 실제 입력의 출처 snapshot을
  PR12–18로 반영했다. 상세 계약은 `docs/reference/config/sources.md` §4.4가 소유한다.
- 구현 main `410c876`의 필수 원격 CI40113216793은 746개 테스트와 프로덕션
  `mimir/*` 커버리지97%로 통과했다. PR20 CI40146225888도 같은 결과로 통과했다.
  문서 체크포인트 main `ffbd336`의 소스·테스트·실행 설정은 구현 main과 같다.
- 실제 설치된 CLI의 합성·offline 데모16개 검사를 통과했다. insight8,
  historical1, evaluation3과 날짜/YAML/출처 증빙 실패·빈 저장소 경로를 확인했다.
  실제 생성 HTML의 모바일/desktop 링크·키보드 표 스크롤·출처 보존도 확인했다.
  합성 수치는 투자 성과나 실제 외부 API 운영 경험이 아니다.
- 원본 로그·스크립트·스크린샷·리뷰·CI/main 근거는 resume
  `자료수집/2026-10-25/mimir-portfolio/`에 보존한다. 별도 resume 저장소의
  push·merge는 하지 않는다. 최종 문서 반영과 정리는 그 폴더의 `completion/`이 기록한다.

## VM Verification — EXCLUDED, NOT VERIFIED

Orca의 실제 my-cloud 대상은 요청한 호스트·port22이며 proxy가 없다. 직접 SSH는
인증 전에 연결 timeout(8.03초, exit255)으로 실패했다. 같은 맥에서 GitHub22/443은
연결됐지만 VM22/443은 timeout됐다. guest 네트워크·방화벽·sshd 중 원인은 미확인이다.
제공사 화면의 실행중 표시와 청구량은 guest runtime 검증을 대신하지 않는다.

VM 배포·잠금·workload·credential 변경은 없었다. guest 자원·공통 잠금·기존 서비스·
백업/복구·Linux 설치·실행 버전은 미검증이다. 자동 초과 과금 차단도 미확인이다.
107KB 순수 Python wheel은 준비됐지만 VM에는 설치하지 않았다. 이 항목은 사용자가
이번 완료 조건에서 제외한 것이며 통과한 검사로 표현하지 않는다.

## Preservation and Future Resume

이번 작업 소유 HTTP/browser/SSH 프로세스는 종료했다. 병합 branch 정리는 대응
PR/head/main tree·고유 커밋·worktree·최신 remote ref를 확인한 대상만 수행한다.
과거 main 복구 이력, 미병합 macro-policy branch와 처음부터 있던 사용자 소유
`CLAUDE.md`, `docs/superpowers/handoffs/`, `uv.lock`은 보존한다.

향후 VM 요청은 현재 접속 경로·청구량·guest 자원·공통 잠금·복구 절차부터 다시
확인해야 한다. 로컬·CI 결과를 배포 완료나 실서비스 운영 근거로 승격하지 않는다.

## Canonical Sources

- Original loop contract: `GOAL.md` (the latest user scope above takes precedence)
- Current evidence: `GATES.md`
- Closed queue: `BACKLOG.md`
- Decisions and history: `DECISIONS.md`, `WORKLOG.md`
- Plans: `docs/superpowers/plans/`
- Architecture: `docs/architecture/improvement-catalog.md`
