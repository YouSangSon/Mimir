from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

README_FILES = (Path("README.md"), Path("README.ko.md"), Path("README.zh.md"))
IMPROVEMENT_CATALOG = Path("docs/architecture/improvement-catalog.md")
CLI_REFERENCE = Path("docs/reference/cli.md")
SEC_REFRESH_DESIGN_SPEC = Path(
    "docs/superpowers/specs/2026-06-19-sec-ticker-cik-map-cache-design.md"
)
LLM_SENTIMENT_SEAM_SPEC = Path(
    "docs/superpowers/specs/2026-06-13-llm-sentiment-seam-design.md"
)
R1I_SEC_CIK_TECH_SPEC = Path(
    "docs/decisions/tech-spec/sources/"
    "R1i-SEC-CIK_sec_ticker_cik_map_tech_spec_2026_06_18.md"
)
README_REQUIRED_LINKS = (
    "docs/architecture/improvement-catalog.md",
    "docs/decisions/tech-spec/README.md",
    "docs/decisions/tech-spec/analysis/AN1_signal_plugin_entrypoints_tech_spec_2026_06_23.md",
    "docs/reference/cli.md",
    "docs/reference/config/watchlist.md",
    "docs/reference/analysis/scoring.md",
    "docs/reference/storage/data-layout.md",
)
REFERENCE_DOCS = tuple(sorted(Path("docs/reference").rglob("*.md")))
SEC_REFRESH_DOCS = (
    Path("docs/reference/config/sources.md"),
    Path("docs/architecture/extensibility/README.md"),
    SEC_REFRESH_DESIGN_SPEC,
)
R1I_SEC_CIK_STALE_REFRESH_PHRASES = (
    "파일 다운로드와 cache 갱신은 하지 않으므로",
    "Mimir는 mapping file을 자동으로 가져오지 않습니다",
    "SEC mapping file live download",
    "mapping file freshness 검증",
    "mapping을 자동 download/cache로 만들면",
)
LLM_SENTIMENT_STALE_SPEC_PHRASES = (
    "LLM 뉴스 감성 시그널을 지금 구현하지 않는다",
    "실제 `LlmSentimentSignal` 코드를 작성",
    "설계로만 존재",
    "`build_signals()`는 **인자를 받지 않으며 어떤 게이트도 통과하지 않는다.**",
    "`build_signals()`의 시그니처와 `analyze.py`의 호출부가 **미래에** 바뀐다",
    "cache=LlmSentimentCache",
    "data/llm_sentiment",
    "test_cache_hit_skips_llm_call",
)
SEC_REFRESH_STALE_GUARD_DOCS = tuple(sorted(Path("docs").rglob("*.md")))
BADGE_RE = re.compile(r"https://img\.shields\.io/badge/tests-(\d+)%20passing")
TABLE_RE = re.compile(r"\|\s*\*\*(?:Tests|테스트|测试)\*\*\s*\|\s*(\d+) passing")
COLLECTED_RE = re.compile(r"(?:(\d+) tests collected|collected (\d+) items)")
LATEST_COMPLETED_IDS = (
    "AN6-ANALYSIS-SIGNAL-RESULT-BOUNDARY",
    "AN5-ANALYSIS-SIGNAL-SPECS-INJECTION",
    "AN4-ANALYSIS-ENGINE-SIGNAL-ISOLATION",
    "AN3-ANALYSIS-PLUGIN-BUILTIN-GUARD",
    "AN2-LLM-CLASSIFIER-CARDINALITY",
    "AN1-SIGNAL-PLUGIN-ENTRYPOINTS",
    "C2a-CAPTURED-NEWS-CACHE",
    "R1n-SEC-CIK-CLI-PATH-CONTRACT",
    "R1m-SEC-CIK-MISSING-PATH",
    "R1l-SEC-CIK-CLI-ERRORS",
    "DCHTML",
    "DOCHEALTH",
    "CFG2",
)
LATEST_COMPLETED_TECH_SPECS = {
    "AN5-ANALYSIS-SIGNAL-SPECS-INJECTION": Path(
        "docs/decisions/tech-spec/analysis/"
        "AN5_analysis_signal_specs_injection_tech_spec_2026_06_25.md"
    ),
    "AN6-ANALYSIS-SIGNAL-RESULT-BOUNDARY": Path(
        "docs/decisions/tech-spec/analysis/"
        "AN6_analysis_signal_result_boundary_tech_spec_2026_06_25.md"
    ),
    "AN4-ANALYSIS-ENGINE-SIGNAL-ISOLATION": Path(
        "docs/decisions/tech-spec/analysis/"
        "AN4_analysis_engine_signal_isolation_tech_spec_2026_06_25.md"
    ),
    "AN3-ANALYSIS-PLUGIN-BUILTIN-GUARD": Path(
        "docs/decisions/tech-spec/analysis/"
        "AN3_analysis_plugin_builtin_guard_tech_spec_2026_06_25.md"
    ),
    "AN2-LLM-CLASSIFIER-CARDINALITY": Path(
        "docs/decisions/tech-spec/analysis/"
        "AN2_LLM_classifier_cardinality_tech_spec_2026_06_23.md"
    ),
    "AN1-SIGNAL-PLUGIN-ENTRYPOINTS": Path(
        "docs/decisions/tech-spec/analysis/"
        "AN1_signal_plugin_entrypoints_tech_spec_2026_06_23.md"
    ),
}
TECH_SPEC_STATUS_RE = re.compile(r"\*\*상태\*\*:?\s*(.+)")


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


def test_latest_completed_tech_specs_are_not_left_as_draft() -> None:
    for item_id, path in LATEST_COMPLETED_TECH_SPECS.items():
        text = path.read_text(encoding="utf-8")
        status = TECH_SPEC_STATUS_RE.search(text)
        assert status is not None, f"{item_id} has no status metadata"
        assert status.group(1).strip() != "Draft", f"{item_id} is still Draft"


def test_readmes_link_current_decision_and_config_docs() -> None:
    for path in README_FILES:
        text = path.read_text(encoding="utf-8")
        for link in README_REQUIRED_LINKS:
            assert link in text, f"{path} missing {link}"


def test_signal_plugin_docs_match_extension_contract() -> None:
    docs = (
        Path("docs/architecture/extensibility/README.md"),
        Path("docs/reference/config/sources.md"),
        Path("docs/architecture/improvement-catalog.md"),
    )
    for path in docs:
        text = path.read_text(encoding="utf-8")
        assert "mimir.analysis_signals" in text, f"{path} missing signal entry point"
        assert "analysis.plugins" in text, f"{path} missing analysis plugin namespace"
        assert "sandbox" in text.lower(), f"{path} missing trust boundary"


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
        "SEC mapping file live download/cache",
        "SEC mapping file을 다운로드하거나 cache하지 않고",
        "SEC mapping file을 다운로드하지 않고, freshness를 판단하지 않고",
        "SEC mapping file live download/cache와 generic discovery는 아직 보류",
        "파일을 자동으로 다운로드하거나 stale 여부를 판단하지 않는다",
        "파일 다운로드, freshness 검증, cache 갱신은 하지 않는다",
        "If-Modified-Since",
    )
    for path in SEC_REFRESH_STALE_GUARD_DOCS:
        text = path.read_text(encoding="utf-8")
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"

    text = R1I_SEC_CIK_TECH_SPEC.read_text(encoding="utf-8")

    assert "ticker_cik_map_path" in text
    assert "ticker_cik_map_refresh.enabled" in text
    assert "ticker_cik_map_refresh.max_age_hours" in text
    assert "resolver" in text
    assert "SEC mapping download 요청을 0회" in text

    for phrase in R1I_SEC_CIK_STALE_REFRESH_PHRASES:
        assert phrase not in text, f"{R1I_SEC_CIK_TECH_SPEC} still says: {phrase}"


def test_llm_sentiment_seam_spec_matches_implemented_state() -> None:
    text = LLM_SENTIMENT_SEAM_SPEC.read_text(encoding="utf-8")

    assert "`LlmSentimentSignal`은 구현되어" in text
    assert "`build_signals(config, settings, *, classifier=...)`" in text
    assert "현재 구현은 `LlmSentimentCache`나 `Dataset.LLM_SENTIMENT`를 제공하지 않는다" in text
    assert "기본 경로의 LLM 호출은 0건이고, `anthropic`도 import하지 않는다" in text
    assert "`HeadlineClassifier` Protocol fake를 주입해 네트워크·key 없이 검증" in text

    for phrase in LLM_SENTIMENT_STALE_SPEC_PHRASES:
        assert phrase not in text, f"{LLM_SENTIMENT_SEAM_SPEC} still says: {phrase}"


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
