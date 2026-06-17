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
PIPELINE_WORKFLOW = Path(".github/workflows/_pipeline.yml")


def test_github_actions_use_node24_compatible_major_versions() -> None:
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


def test_reusable_pipeline_publishes_dashboard_before_commit() -> None:
    text = PIPELINE_WORKFLOW.read_text(encoding="utf-8")

    run_pipeline = text.index("- name: Run pipeline")
    run_dashboard = text.index("- name: Run dashboard")
    dashboard_command = text.index("run: python -m mimir.dashboard --data-root data --reports-root reports")
    commit_data = text.index("- name: Commit data + reports")

    assert run_pipeline < run_dashboard < dashboard_command < commit_data


def test_reusable_pipeline_does_not_add_doctor_hard_gate() -> None:
    text = PIPELINE_WORKFLOW.read_text(encoding="utf-8")

    assert "python -m mimir.doctor" not in text
    assert "--strict" not in text
