# Project Plan

This file is the root resume point for active work. It intentionally stays
small; detailed plans live under `docs/superpowers/plans/`.

## Active Goal

이전 Goal의 중단 예약 시각(2026-10-25 05:15 KST)은 지났고 타이머 handle도
완료됐다. 2026-10-25 새 Goal로 재개했으며 이번 요청에는 고정 실행 시간 제한이
없다. 명시적인 중단 요청과 실제 사용량·크레딧 조건은 계속 적용한다.
차단 상태의 연속 확인 횟수는 이번 재개부터 새로 센다.

Finish a usable, verified portfolio version of Mimir's existing S1–S4 pipeline.
The latest 2026-10-25 user request supersedes older execution limits and
continues the existing Goal scope. Commit/push/PR/main merge remain authorized.
Local checks must be lightweight, relevant and sequential; do not launch heavy
integration stacks. Required free remote CI stays mandatory. Use only existing
my-cloud for the requested minimal VM verification, after current resource,
shared-lock, billing-traffic and recovery checks. No paid execution, credential
changes, workflow reactivation, public demo or new cloud resources are authorized.
Preserve the existing GRAY-source policy and user-owned files.

Completion requires the finite `BACKLOG.md` queue, a runnable local demo with
real CLI/report success and failure flows, required local/review/CI gates,
main integration, verified branch/resource cleanup, and evidence under the
existing resume `자료수집` structure. S5 trading, paid LLM execution, generic
RSS discovery, and new cloud infrastructure remain outside this goal.

- Original loop contract: `GOAL.md`
- Current delivery evidence: `GATES.md`
- Decisions and work evidence: `DECISIONS.md`, `WORKLOG.md`

## Current Loop — VM AUTHENTICATION / RUNTIME VERIFICATION

구현과 포트폴리오 체크포인트는 main에 반영됐다. PR18·PR19의 필수 CI는
746개 테스트·프로덕션 커버리지 97%로 통과했다. 체크포인트 main1146307의 tree는
리뷰한 fd2e268과 같고 소스·테스트·실행 설정은 구현 main410c876과 같다.
유한 구현 대기열은 닫혔으며 새 기능을 추가할 필요가 없다. 활성 worktree와
branch 식별자는 현재 Git 상태를 따른다. VM 검증 단위는 아직 완료하지 못했다.

Actual installed CLI demo passed16 checks with synthetic data: insight8,
historical1, evaluation buckets3; invalid date/YAML/missing evidence and empty
store paths verified. Browser375/1280px, source preservation, keyboard table
scroll and report link verified. No paid LLM or external delivery was called.
Evidence is under resume `자료수집/2026-10-25/mimir-portfolio/`; root README
there maps problems, decisions, PRs, measured facts and limits. The source
contract remains `docs/reference/config/sources.md` §4.4.

남은 필수 gate는 my-cloud의 비공개 실행 환경 검증이다. 이전 제공사 화면은
9.9MB/3TB·예상 초과 요금 0원, 마지막 집계 2026-10-24 13:07:39(표시 timezone
미상)였다. 이번 재개의 현재 청구량 확인으로 재사용하지 않으며 자동 초과 과금
차단도 미확인이다.

2026-10-25 재확인: 인증정보를 보내지 않은 TCP22 연결은 5.03초 후 timeout됐다.
Orca의 실제 my-cloud alias도 요청한 호스트의 22번 포트를 사용하고
ProxyJump/ProxyCommand가 없다. 대상 VM으로 연결된 기존 SSH transport도 없다.
제공사 상세 탭은 다른 browser session이 사용 중이므로 제어하지 않았다.
과거 인증 창을 현재 접속 증거로 취급하지 않는다. 사용자 직접 로그인이나
정상 동작하는 승인된 SSH 경로가 필요하다. guest 자원·공통 잠금·현재 버전·복구·
runtime은 미검증이며, 이 조건과 잠금을 확인하기 전에는 배포하지 않는다.

이번 작업 소유의 로컬 HTTP/browser/SSH 자원은 종료했고 VM 잠금·workload는
만들지 않았다. 병합된 cadence/doc-health/provenance/portfolio branch는 검증 후
정리했다. 과거 main 복구 이력, 미병합 macro-policy branch와 활성 작업 branch는
보존한다. 처음부터 있던 사용자 소유 untracked 3개는 stage하지 않았다.

접속이 확보되면 현재 guest 서비스·메모리·디스크·OOM·공통 잠금부터 확인한다.
예산 안에서 비공개 합성 CLI smoke를 실행하고 source/artifact/runtime 대응을
검증한 뒤 소유 자원을 정리하고 전체 Goal 완료 조건을 다시 대조한다.
이번 새 Goal의 접속 차단 확인은 1회다. 이전 Goal의 3회 확인은 과거 기록이며
재사용하지 않는다. 구현·CI·데모 gate는 유지하되 VM gate와 최종 정리 증거가
없으므로 전체 Goal은 미완료다.

## Canonical Sources

- Implementation plans: `docs/superpowers/plans/`
- Improvement backlog: `docs/IMPROVEMENTS.md`
- Architecture catalog: `docs/architecture/improvement-catalog.md`
- Decision tech specs: `docs/decisions/tech-spec/README.md`
- History: `git log`

## Next Loop Candidates

Use `BACKLOG.md` first, then choose one coherent slice. Do not mix workflow,
docs-truth, and feature changes in the same loop unless one cannot be verified
without the other.
