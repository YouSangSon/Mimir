from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

README_FILES = (Path("README.md"), Path("README.ko.md"), Path("README.zh.md"))
IMPROVEMENT_CATALOG = Path("docs/architecture/improvement-catalog.md")
BADGE_RE = re.compile(r"https://img\.shields\.io/badge/tests-(\d+)%20passing")
TABLE_RE = re.compile(r"\|\s*\*\*(?:Tests|테스트|测试)\*\*\s*\|\s*(\d+) passing")
COLLECTED_RE = re.compile(r"(?:(\d+) tests collected|collected (\d+) items)")
LATEST_COMPLETED_IDS = (
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
