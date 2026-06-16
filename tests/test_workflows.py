from __future__ import annotations

import re
from pathlib import Path

EXPECTED_WORKFLOW_ACTION_MAJORS = {
    Path(".github/workflows/ci.yml"): {
        "actions/checkout": "v6",
        "actions/setup-python": "v6",
    },
    Path(".github/workflows/_pipeline.yml"): {
        "actions/checkout": "v6",
        "actions/setup-python": "v6",
    },
}

ACTION_USES_RE = re.compile(r"uses:\s*(actions/(?:checkout|setup-python))@(v\d+)(?:\b|$)")


def test_github_actions_use_node24_compatible_major_versions():
    mismatches: list[str] = []

    for path, expected_actions in EXPECTED_WORKFLOW_ACTION_MAJORS.items():
        seen: set[str] = set()
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = ACTION_USES_RE.search(line)
            if match is None:
                continue
            action, major = match.groups()
            seen.add(action)
            expected = expected_actions[action]
            if major != expected:
                mismatches.append(f"{path}:{line_no}: {action}@{major} should be {expected}")

        assert seen == set(expected_actions), f"{path} is missing expected actions"
    assert mismatches == []
