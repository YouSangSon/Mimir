from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

README_FILES = (Path("README.md"), Path("README.ko.md"), Path("README.zh.md"))
IMPROVEMENT_CATALOG = Path("docs/architecture/improvement-catalog.md")
CLI_REFERENCE = Path("docs/reference/cli.md")
README_REQUIRED_LINKS = (
    "docs/architecture/improvement-catalog.md",
    "docs/decisions/tech-spec/README.md",
    "docs/reference/cli.md",
    "docs/reference/config/watchlist.md",
    "docs/reference/analysis/scoring.md",
    "docs/reference/storage/data-layout.md",
)
REFERENCE_DOCS = tuple(sorted(Path("docs/reference").rglob("*.md")))
SEC_REFRESH_DOCS = (
    Path("docs/reference/config/sources.md"),
    Path("docs/architecture/extensibility/README.md"),
)
BADGE_RE = re.compile(r"https://img\.shields\.io/badge/tests-(\d+)%20passing")
TABLE_RE = re.compile(r"\|\s*\*\*(?:Tests|테스트|测试)\*\*\s*\|\s*(\d+) passing")
COLLECTED_RE = re.compile(r"(?:(\d+) tests collected|collected (\d+) items)")
LATEST_COMPLETED_IDS = (
    "C2a-CAPTURED-NEWS-CACHE",
    "R1n-SEC-CIK-CLI-PATH-CONTRACT",
    "R1m-SEC-CIK-MISSING-PATH",
    "R1l-SEC-CIK-CLI-ERRORS",
    "DCHTML",
    "DOCHEALTH",
    "CFG2",
)


def _collected_test_count() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    matches = COLLECTED_RE.findall(result.stdout)
    assert matches, result.stdout
    last = matches[-1]
    return int(last[0] or last[1])


def test_readme_test_badges_match_collected_pytest_count() -> None:
    expected = _collected_test_count()

    for path in README_FILES:
        text = path.read_text(encoding="utf-8")
        badge = BADGE_RE.search(text)
        table = TABLE_RE.search(text)

        assert badge is not None, f"{path} has no tests badge"
        assert table is not None, f"{path} has no tests table row"
        assert int(badge.group(1)) == expected
        assert int(table.group(1)) == expected


def test_improvement_catalog_summary_mentions_latest_completed_ids() -> None:
    text = IMPROVEMENT_CATALOG.read_text(encoding="utf-8")
    status_line = next(
        line for line in text.splitlines() if line.startswith("> **상태**:")
    )
    conclusion = text[text.index("**결론.**") :]

    for item_id in LATEST_COMPLETED_IDS:
        assert item_id in status_line
        assert item_id in conclusion


def test_readmes_link_current_decision_and_config_docs() -> None:
    for path in README_FILES:
        text = path.read_text(encoding="utf-8")
        for link in README_REQUIRED_LINKS:
            assert link in text, f"{path} missing {link}"


def test_readme_links_all_reference_docs() -> None:
    required = tuple(str(path) for path in REFERENCE_DOCS)
    for path in README_FILES:
        text = path.read_text(encoding="utf-8")
        for link in required:
            assert link in text, f"{path} missing {link}"


def test_sec_ticker_cik_refresh_docs_match_implemented_state() -> None:
    for path in SEC_REFRESH_DOCS:
        text = path.read_text(encoding="utf-8")
        assert "ticker_cik_map_refresh" in text, f"{path} missing refresh config"
        assert "enabled" in text, f"{path} missing enabled field"
        assert "max_age_hours" in text, f"{path} missing TTL field"

    stale_phrases = (
        "SEC mapping file live download/cache와 generic discovery는 아직 보류",
        "파일을 자동으로 다운로드하거나 stale 여부를 판단하지 않는다",
        "파일 다운로드, freshness 검증, cache 갱신은 하지 않는다",
    )
    for path in SEC_REFRESH_DOCS:
        text = path.read_text(encoding="utf-8")
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"


def test_scoring_reference_documents_news_volume_confidence() -> None:
    text = Path("docs/reference/analysis/scoring.md").read_text(encoding="utf-8")

    assert "| `news_volume` | 항상 NEUTRAL | 0.5 | 0.5 |" in text


def test_cli_reference_documents_config_file_boundaries() -> None:
    text = CLI_REFERENCE.read_text(encoding="utf-8")

    assert (
        "| `mimir backfill` | 단일 source 과거 데이터 적재 | 예 | 예 | 일부 | 예 | 아니오 |"
        in text
    )
    assert (
        "| `mimir deliver` | 일일 HTML 리포트/인덱스/다이제스트 생성 | "
        "예 | 아니오 | 예 | 아니오 | 예 |"
        in text
    )
    assert (
        "| `mimir history` | 저장된 인사이트와 가격으로 과거 유사 사례 계산 | "
        "아니오 | 예 | 예 | 예 | 아니오 |"
        in text
    )
