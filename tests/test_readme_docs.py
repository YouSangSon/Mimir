from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

README_FILES = (Path("README.md"), Path("README.ko.md"), Path("README.zh.md"))
IMPROVEMENT_CATALOG = Path("docs/architecture/improvement-catalog.md")
ROADMAP = Path("docs/architecture/roadmap.md")
INCREMENTAL_EXTENSIBILITY_ADR = Path(
    "docs/architecture/adr/0001-incremental-extensibility-and-deferral.md"
)
CLI_REFERENCE = Path("docs/reference/cli.md")
ROOT_STATE_DOCS = {
    Path("PLAN.md"): (
        "docs/superpowers/plans/",
        "BACKLOG.md",
        "WORKLOG.md",
        "DECISIONS.md",
    ),
    Path("BACKLOG.md"): (
        "docs/IMPROVEMENTS.md",
        "docs/architecture/improvement-catalog.md",
        "PROJECT-STATE-ENTRYPOINTS",
    ),
    Path("WORKLOG.md"): (
        "PROJECT-STATE-ENTRYPOINTS",
        "docs/superpowers/plans/2026-06-28-project-state-entrypoints.md",
        "uv run pytest",
    ),
    Path("DECISIONS.md"): (
        "PROJECT-STATE-ENTRYPOINTS",
        "docs/decisions/tech-spec/README.md",
        "https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency",
    ),
}
SEC_REFRESH_DESIGN_SPEC = Path(
    "docs/superpowers/specs/2026-06-19-sec-ticker-cik-map-cache-design.md"
)
LLM_SENTIMENT_SEAM_SPEC = Path(
    "docs/superpowers/specs/2026-06-13-llm-sentiment-seam-design.md"
)
ANALYSIS_DESIGN_SPEC = Path(
    "docs/superpowers/specs/2026-05-31-analysis-design.md"
)
NEWS_MENTION_ALIAS_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-news-mention-alias-design.md"
)
DEFAULT_NEWS_ALIASES_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-default-news-aliases-design.md"
)
CONFIG_DRIVEN_EXTENSIBILITY_SPEC = Path(
    "docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md"
)
TYPED_PAYLOAD_SPEC = Path(
    "docs/superpowers/specs/2026-06-13-typed-payload-design.md"
)
DATA_DOCTOR_SPEC = Path(
    "docs/superpowers/specs/2026-06-13-data-doctor-design.md"
)
MACRO_SERIES_REGISTRY_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-macro-series-registry-design.md"
)
DECLARATIVE_SOURCE_REGISTRATION_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-declarative-source-registration-design.md"
)
SOURCE_ENTRY_POINTS_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-source-entry-points-design.md"
)
MACRO_REVISION_POLICY_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-macro-revision-policy-design.md"
)
BACKFILL_MANIFEST_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-backfill-manifest-design.md"
)
BACKFILL_PREFLIGHT_MANIFEST_SPEC = Path(
    "docs/superpowers/specs/2026-06-18-backfill-preflight-manifest-design.md"
)
NEWS_CAPTURED_WINDOW_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-news-captured-window-design.md"
)
SYMBOL_TAGGED_RSS_FEEDS_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-symbol-tagged-rss-feeds-design.md"
)
RSS_FEED_CATALOG_SPEC = Path(
    "docs/superpowers/specs/2026-06-17-rss-feed-catalog-design.md"
)
CLI_ENTRYPOINTS_SPEC = Path(
    "docs/superpowers/specs/2026-06-18-cli-entrypoints-design.md"
)
DOTENV_CLI_AUTOLOAD_SPEC = Path(
    "docs/superpowers/specs/2026-06-18-dotenv-cli-autoload-design.md"
)
SOURCES_CONFIG_CLI_VALIDATION_SPEC = Path(
    "docs/superpowers/specs/2026-06-18-sources-config-cli-validation-design.md"
)
GITHUB_ACTIONS_NODE24_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-github-actions-node24-design.md"
)
PYKRX_RETRY_POLICY_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-pykrx-retry-policy-design.md"
)
PLUGIN_SETTINGS_NAMESPACE_SPEC = Path(
    "docs/superpowers/specs/2026-06-17-plugin-settings-namespace-design.md"
)
SEC_RSS_TICKER_INPUT_SPEC = Path(
    "docs/superpowers/specs/2026-06-18-sec-rss-ticker-input-design.md"
)
DOCTOR_HTML_REPORT_SPEC = Path(
    "docs/superpowers/specs/2026-06-18-doctor-html-report-design.md"
)
SEC_EDGAR_RSS_PROVIDER_SPEC = Path(
    "docs/superpowers/specs/2026-06-17-sec-edgar-rss-provider-design.md"
)
SEC_STRUCTURED_RSS_CATALOG_SPEC = Path(
    "docs/superpowers/specs/2026-06-18-sec-structured-rss-catalog-design.md"
)
SCHEDULED_DASHBOARD_PUBLICATION_SPEC = Path(
    "docs/superpowers/specs/2026-06-17-scheduled-dashboard-publication-design.md"
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
S2_ANALYSIS_DESIGN_STALE_PHRASES = (
    "Σ sign(dir)·strength·confidence·weight / Σ weight",
    "max(|net|, attention)",
    "LLM 시그널 → 하이브리드 후속",
    "LLM은 나중에 시그널 하나로 추가",
    "LLM은 같은 `Signal` 인터페이스를 구현하는 한 시그널로 후속 추가",
    "후속 추가한다",
)
COMPLETED_DESIGN_SPEC_STATUS_STALE_PHRASES = (
    "coverage gate",
    "coverage 80% gate",
    "커버리지 ≥ 80%",
    "diff-check",
    "diff check",
    "ruff · mypy",
    "ruff, mypy",
    "uv run pytest",
    "uv run ruff",
    "uv run mypy",
    "git diff --check",
)
COMPLETED_DESIGN_SPEC_STATUS_STALE_PATTERNS = (
    re.compile(r"\b\d{3,4}\s+tests?\b"),
    re.compile(r"\b\d{3,4}\s+passed\b"),
    re.compile(r"\b\d{3,4}\s+테스트\b"),
    re.compile(r"\b\d{2,3}%\s*(?:cov|coverage|커버리지)\b", re.IGNORECASE),
    re.compile(r"(?<![\w.-])(?:ruff|mypy|pytest)(?![\w.-])", re.IGNORECASE),
    re.compile(r"(?<![\w.-])(?:coverage|cov)(?![\w.-])|커버리지", re.IGNORECASE),
    re.compile(r"(?<![\w.-])diff[- ]check(?![\w.-])", re.IGNORECASE),
    re.compile(r"(?<![\w.-])uv\s+run(?:\s+[\w./:-]+)*", re.IGNORECASE),
    re.compile(r"(?<![\w.-])python\s+-m(?:\s+[\w.:-]+)*", re.IGNORECASE),
)
COMPLETED_DESIGN_SPEC_ACCEPTANCE_CURRENT_VERIFICATION = (
    "- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다."
)
COMPLETED_DESIGN_SPEC_COMPLETION_HEADING_KEYWORDS = (
    "완료 기준",
    "수용 기준",
    "Acceptance Criteria",
    "Acceptance",
)
COMPLETED_DESIGN_SPEC_NUMBERED_CURRENT_VERIFICATION = (
    "최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다."
)
COMPLETED_DESIGN_SPEC_TEST_HEADING_STALE_PATTERN = re.compile(
    r"^##\s+.*테스트.*(?:80%|coverage|커버리지)",
    re.IGNORECASE,
)
COMPLETED_DESIGN_SPEC_NUMBERED_ITEM_RE = re.compile(r"^\s*\d+\.\s+")
COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_TERMS = re.compile(
    r"(?<![\w.-])(?:ruff|mypy|pytest|coverage|cov)(?![\w.-])"
    r"|커버리지|diff[- ]check|uv\s+run|git\s+diff",
    re.IGNORECASE,
)
COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_COMMANDS = re.compile(
    r"(?<![\w.-])uv\s+run\s+(?:pytest|ruff|mypy|coverage)(?![\w.-])"
    r"|(?<![\w.-])git\s+diff\s+--check(?![\w.-])"
    r"|(?<![\w.-])diff[- ]check(?![\w.-])",
    re.IGNORECASE,
)
COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_TOOLS = re.compile(
    r"(?<![\w.-])(?:ruff|mypy|pytest)(?![\w.-])",
    re.IGNORECASE,
)
COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_OUTCOMES = re.compile(
    r"통과|passed|pass|gate|클린|clean|≥\s*80%",
    re.IGNORECASE,
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


def test_readme_and_architecture_health_metadata_use_current_contract() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["tool"]["mypy"]["strict"] is True

    canonical_lint_type = "ruff + mypy (`pyproject.toml` strict config) clean"
    stale_readme_lint_type = "ruff + mypy `--strict` clean"
    for path in README_FILES:
        text = path.read_text(encoding="utf-8")
        rows = [
            line
            for line in text.splitlines()
            if line.startswith("| **lint/type** |")
        ]
        assert rows == [f"| **lint/type** | {canonical_lint_type} |"]
        assert stale_readme_lint_type not in text

    catalog = IMPROVEMENT_CATALOG.read_text(encoding="utf-8")
    cov1_rows = [
        line
        for line in catalog.splitlines()
        if line.startswith("| **COV1-CONTRACT-COVERAGE** |")
    ]
    assert len(cov1_rows) == 1
    cov1_row = cov1_rows[0]
    assert "README/docs health guard가 추적하는 커버리지 게이트" in cov1_row
    assert "idempotency_key/partition 불변식 약속" in cov1_row
    assert "80%+ 커버리지" not in cov1_row

    anti_discovery = _markdown_section(catalog, "## 7. 안티-발견 (확인됨, 손대지 않음)")
    assert "pyproject.toml strict config" in anti_discovery
    assert "README 테스트 배지와 docs health guard가 추적" in anti_discovery
    assert "mypy strict 통과" not in anti_discovery
    assert "mypy --strict clean" not in anti_discovery


def test_architecture_roadmap_testing_metadata_uses_current_contract() -> None:
    text = ROADMAP.read_text(encoding="utf-8")
    cross_cutting = _markdown_section(text, "## 5. 횡단 관심사 (모든 스펙에 적용)")

    assert "TDD" in cross_cutting
    assert "README 테스트 배지와 docs health guard" in cross_cutting
    assert "coverage 80%+" not in cross_cutting
    assert "커버리지 80%+" not in cross_cutting


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


def test_root_project_state_entrypoints_link_canonical_sources() -> None:
    for path, required_fragments in ROOT_STATE_DOCS.items():
        assert path.exists(), f"{path} is missing"
        text = path.read_text(encoding="utf-8")
        for fragment in required_fragments:
            assert fragment in text, f"{path} missing {fragment}"


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


def test_s2_analysis_design_spec_matches_current_scoring_model() -> None:
    text = ANALYSIS_DESIGN_SPEC.read_text(encoding="utf-8")

    assert "directional_weight = Σ weight  (방향 시그널만; bullish/bearish)" in text
    assert "total_weight       = Σ weight  (모든 시그널)" in text
    assert "net       = Σ sign(dir)·strength·confidence·weight / directional_weight" in text
    assert "attention = Σ strength·confidence·weight / total_weight" in text
    assert "stars     = clamp(round(1 + 4·|net|), 1, 5)" in text
    assert "별점은 방향 확신" in text
    assert "방향 없는 활동" in text
    assert "attention" in text

    for phrase in S2_ANALYSIS_DESIGN_STALE_PHRASES:
        assert phrase not in text, f"{ANALYSIS_DESIGN_SPEC} still says: {phrase}"


def _readme_s2_roadmap_row(path: Path) -> str:
    rows = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("| **S2 Analysis & Scoring** |")
    ]
    assert len(rows) == 1, f"{path} should have exactly one S2 roadmap row"
    return rows[0]


def _markdown_section(text: str, heading: str) -> str:
    start = text.index(heading)
    rest = text[start + len(heading) :]
    next_heading = rest.find("\n## ")
    if next_heading == -1:
        return rest
    return rest[:next_heading]


def test_readme_s2_rows_match_current_llm_sentiment_state() -> None:
    expectations = {
        Path("README.md"): "Implemented (rules + off-by-default LLM seam:",
        Path("README.ko.md"): "구현 완료 (규칙 기반 + off-by-default LLM seam:",
        Path("README.zh.md"): "已实现（规则 + off-by-default LLM seam：",
    }
    stale_phrases = ("LLM to follow", "LLM 후속", "LLM 后续")
    activation_requirements = (
        "llm_sentiment_enabled",
        "ANTHROPIC_API_KEY",
        "[llm]",
    )

    for path, expected in expectations.items():
        text = path.read_text(encoding="utf-8")
        s2_row = _readme_s2_roadmap_row(path)
        assert expected in s2_row
        for requirement in activation_requirements:
            assert requirement in s2_row, f"{path} S2 row missing {requirement}"
        assert "off-by-default LLM seam" in s2_row, f"{path} S2 row missing LLM seam"
        assert "only when" in s2_row or "때만" in s2_row or "仅在" in s2_row, (
            f"{path} S2 row missing activation-condition wording"
        )
        assert "config flag" in s2_row or "설정 플래그" in s2_row or "配置开关" in s2_row, (
            f"{path} S2 row missing config-flag wording"
        )
        assert (
            "extra" in s2_row
            or "extras" in s2_row
            or "추가 설치" in s2_row
            or "额外安装" in s2_row
        ), (
            f"{path} S2 row missing extra-install wording"
        )
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"


def test_news_alias_specs_match_current_completion_state() -> None:
    r1 = NEWS_MENTION_ALIAS_SPEC.read_text(encoding="utf-8")
    r1c = DEFAULT_NEWS_ALIASES_SPEC.read_text(encoding="utf-8")

    for path, text, stale_count in (
        (NEWS_MENTION_ALIAS_SPEC, r1, "364 테스트"),
        (DEFAULT_NEWS_ALIASES_SPEC, r1c, "388 테스트"),
    ):
        assert stale_count not in text, f"{path} still carries stale test count"
        status_line = next(
            line for line in text.splitlines() if line.startswith("> **상태**:")
        )
        assert "구현 완료" in status_line
        assert "최신 검증은 README 테스트 배지와 docs health guard가 추적" in status_line
        assert "coverage gate" not in status_line

    acceptance = _markdown_section(r1, "## 9. 수용 기준")
    settings = _markdown_section(r1, "## 4. 설정 설계")
    builder = _markdown_section(r1, "## 6. 빌더 배선")

    assert "- [ ]" not in acceptance
    assert "기본 alias" in acceptance
    assert "R1c" in acceptance
    assert "빈 alias map" not in settings
    assert "설정을 생략하면 빈 alias map을 쓴다" not in settings
    assert "symbol-only" in settings
    assert "_news_aliases(cfg)" in builder or "merge_news_aliases" in builder
    assert "use_default_news_aliases=True" in r1
    assert "SourcesConfig()" in r1
    assert "설정이 없으면 기존 symbol-only 동작을 유지한다." not in r1
    assert "설정이 없으면 기존 동작과 시그널 수를 유지한다." not in r1
    assert "설정이 없음 | 기존 symbol-only 매칭 유지" not in r1
    assert "설정이 없을 때의 symbol-only 기본값" in r1
    assert "`NewsVolumeSignal()`과 `LlmSentimentSignal()`에만 해당한다." in r1
    assert "`build_signals(SourcesConfig())`" in r1
    assert "`_news_aliases(cfg)`" in r1
    assert "`DEFAULT_NEWS_ALIASES`를 병합" in r1
    assert "직접 `NewsVolumeSignal()`" in r1
    assert "`LlmSentimentSignal()`을 만들 때" in r1
    assert "build_signals(SourcesConfig())" in r1
    assert "analysis.news.use_default_aliases: false" in r1

    assert "NewsMentionMatcher" in r1
    assert "analysis.news.aliases" in r1
    assert "DEFAULT_NEWS_ALIASES" in r1
    assert "analysis.news.use_default_aliases" in r1
    assert "R1c" in r1
    assert "symbol-only 기본값" in r1
    assert "NewsVolumeSignal(aliases=cfg.news_aliases)" not in r1
    assert "_news_aliases(cfg)" in r1 or "merge_news_aliases" in r1
    assert "use_default_news_aliases=True" in r1 or "SourcesConfig()" in r1

    assert "DEFAULT_NEWS_ALIASES" in r1c
    assert "analysis.news.use_default_aliases" in r1c
    assert COMPLETED_DESIGN_SPEC_ACCEPTANCE_CURRENT_VERIFICATION in r1c


def _status_line(text: str) -> str:
    return next(line for line in text.splitlines() if line.startswith("> **상태**:"))


def _has_stale_acceptance_verification_metadata(line: str) -> bool:
    if COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_COMMANDS.search(line):
        return True

    tool_names = {
        match.group(0).lower()
        for match in COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_TOOLS.finditer(line)
    }
    if len(tool_names) >= 2:
        return True

    return bool(
        COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_TERMS.search(line)
        and COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_OUTCOMES.search(line)
    )


def test_completed_design_spec_status_lines_use_current_verification_metadata() -> None:
    current_status = (
        "> **상태**: ✅ 구현 완료. 최신 검증은 README 테스트 배지와 docs health guard가 추적한다."
    )
    assert not any(
        pattern.search(current_status)
        for pattern in COMPLETED_DESIGN_SPEC_STATUS_STALE_PATTERNS
    )

    stale_status_examples = (
        "> **상태**: ✅ 구현 완료. ruff + mypy clean.",
        "> **상태**: ✅ 구현 완료. pytest -q passed.",
        "> **상태**: ✅ 구현 완료. mypy strict clean.",
        "> **상태**: ✅ 구현 완료. coverage clean.",
        "> **상태**: ✅ 구현 완료. cov clean.",
        "> **상태**: ✅ 구현 완료. 커버리지 clean.",
        "> **상태**: ✅ 구현 완료. diff check clean.",
        "> **상태**: ✅ 구현 완료. uv run pytest -q passed.",
        "> **상태**: ✅ 구현 완료. python -m pytest passed.",
    )
    for status in stale_status_examples:
        assert any(
            pattern.search(status)
            for pattern in COMPLETED_DESIGN_SPEC_STATUS_STALE_PATTERNS
        )

    for path in sorted(Path("docs/superpowers/specs").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        try:
            status = _status_line(text)
        except StopIteration:
            continue

        if "구현 완료" not in status:
            continue

        assert "최신 검증은 README 테스트 배지와 docs health guard가 추적" in status, (
            f"{path} completed status must point at README/docs health verification"
        )
        for phrase in COMPLETED_DESIGN_SPEC_STATUS_STALE_PHRASES:
            assert phrase not in status, f"{path} completed status still says: {phrase}"
        for pattern in COMPLETED_DESIGN_SPEC_STATUS_STALE_PATTERNS:
            assert not pattern.search(status), (
                f"{path} completed status still carries stale fixed verification metadata"
            )


def test_completed_design_spec_acceptance_verification_lines_use_current_metadata() -> None:
    stale_examples = (
        "- [x] ruff, mypy, pytest, coverage 80% gate가 통과한다.",
        "- [x] `uv run pytest tests/test_cli.py -q`가 통과한다.",
        "- [x] `uv run pytest tests/test_cli.py -q`",
        "- [x] ruff + mypy + pytest",
        "- [x] 네트워크 호출 0 · ruff · mypy strict 클린 · 커버리지 ≥ 80%.",
    )
    current_examples = (
        COMPLETED_DESIGN_SPEC_ACCEPTANCE_CURRENT_VERIFICATION,
        (
            "- [x] **영업일 오탐 방지**: 금요일 종가가 최신, `now`=월요일 → "
            "DAILY 나이 = 1 영업일 → OK(오탐 없음)."
        ),
        "- [x] mypy strict 내로잉 헬퍼는 payload mismatch에서 예외를 낸다.",
        "- [x] doctor expected coverage는 A3 테이블에서 파생하지 않는다.",
    )

    for line in stale_examples:
        assert _has_stale_acceptance_verification_metadata(line)

    for line in current_examples:
        if line == COMPLETED_DESIGN_SPEC_ACCEPTANCE_CURRENT_VERIFICATION:
            continue
        assert not _has_stale_acceptance_verification_metadata(line)

    for path in sorted(Path("docs/superpowers/specs").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        try:
            status = _status_line(text)
        except StopIteration:
            continue
        if "구현 완료" not in status:
            continue

        for line in text.splitlines():
            if not line.startswith("- [x]"):
                continue
            if "README 테스트 배지와 docs health guard" in line:
                assert line == COMPLETED_DESIGN_SPEC_ACCEPTANCE_CURRENT_VERIFICATION, (
                    f"{path} uses non-canonical current verification acceptance: {line}"
                )
                continue
            assert not _has_stale_acceptance_verification_metadata(line), (
                f"{path} has stale acceptance verification metadata: {line}"
            )


def test_completed_design_spec_numbered_completion_criteria_use_current_metadata() -> None:
    stale_headings = (
        "## 9. 테스트 (TDD, 80%+)",
        "## 15. 테스트 전략 (TDD, 80%+)",
    )
    current_headings = (
        "## 9. 테스트 전략 (TDD)",
        "## 11. 테스트 계획 (TDD, 합성 데이터 · 네트워크 없음)",
    )
    stale_numbered_examples = (
        "5. 커버리지 80%+, ruff·mypy --strict clean.",
        "7. 커버리지 80%+ , `ruff`·`mypy` 통과.",
        "10. 커버리지 80%+, `ruff` clean, `mypy --strict` clean, 모든 파일 <800줄.",
    )
    current_numbered_examples = (
        "1. `python -m mimir.analyze --date D`가 저장된 데이터로 동작한다.",
        "2. 이벤트 2종 + analog 요약 + 엔진 단위/통합 테스트 통과.",
        f"5. {COMPLETED_DESIGN_SPEC_NUMBERED_CURRENT_VERIFICATION}",
    )

    for heading in stale_headings:
        assert COMPLETED_DESIGN_SPEC_TEST_HEADING_STALE_PATTERN.search(heading)
    for heading in current_headings:
        assert not COMPLETED_DESIGN_SPEC_TEST_HEADING_STALE_PATTERN.search(heading)
    for line in stale_numbered_examples:
        assert _has_stale_acceptance_verification_metadata(line)
    for line in current_numbered_examples:
        assert not _has_stale_acceptance_verification_metadata(line)

    for path in sorted(Path("docs/superpowers/specs").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        try:
            status = _status_line(text)
        except StopIteration:
            continue
        if "구현 완료" not in status:
            continue

        in_completion_section = False
        for line in text.splitlines():
            if line.startswith("## "):
                if "테스트" in line:
                    assert not COMPLETED_DESIGN_SPEC_TEST_HEADING_STALE_PATTERN.search(line), (
                        f"{path} test heading carries stale fixed verification metadata: {line}"
                    )
                in_completion_section = any(
                    keyword in line
                    for keyword in COMPLETED_DESIGN_SPEC_COMPLETION_HEADING_KEYWORDS
                )
                continue

            if not in_completion_section:
                continue
            if not COMPLETED_DESIGN_SPEC_NUMBERED_ITEM_RE.match(line):
                continue

            if "README 테스트 배지와 docs health guard" in line:
                item_text = COMPLETED_DESIGN_SPEC_NUMBERED_ITEM_RE.sub(
                    "", line.strip(), count=1
                )
                assert item_text.startswith(
                    COMPLETED_DESIGN_SPEC_NUMBERED_CURRENT_VERIFICATION
                ), f"{path} uses non-canonical numbered current verification: {line}"
                extra_text = item_text.removeprefix(
                    COMPLETED_DESIGN_SPEC_NUMBERED_CURRENT_VERIFICATION
                ).strip()
                assert not _has_stale_acceptance_verification_metadata(extra_text), (
                    f"{path} has stale numbered completion verification metadata: {line}"
                )
                continue

            assert not _has_stale_acceptance_verification_metadata(line), (
                f"{path} has stale numbered completion verification metadata: {line}"
            )


def test_architecture_adrs_do_not_publish_stale_current_verification_context() -> None:
    text = INCREMENTAL_EXTENSIBILITY_ADR.read_text(encoding="utf-8")
    header = text.split("\n## 결정", 1)[0]

    assert "122 테스트" not in header
    assert "95% 커버리지" not in header
    assert "mypy strict" not in header
    assert "발전 카탈로그" in header
    assert "README 테스트 배지와 docs health guard" in header

    for pattern in COMPLETED_DESIGN_SPEC_STATUS_STALE_PATTERNS:
        assert not pattern.search(header), (
            f"{INCREMENTAL_EXTENSIBILITY_ADR} header carries stale verification metadata"
        )


def test_foundation_design_specs_match_current_completion_state() -> None:
    specs = {
        CONFIG_DRIVEN_EXTENSIBILITY_SPEC: (
            "## 6. 수용 기준 (Acceptance)",
            ("144 테스트", "122개 기존 테스트"),
        ),
        TYPED_PAYLOAD_SPEC: (
            "## 7. 수용 기준 (Acceptance)",
            ("293 테스트", "97% 커버리지"),
        ),
        DATA_DOCTOR_SPEC: (
            "## 8. 수용 기준 (Acceptance)",
            (
                "179 테스트",
                "페이로드 스키마 이상 — 키 존재만 (얕게)",
                "EXPECTED_PAYLOAD_KEYS",
                "키 누락 → WARN(`schema`)",
                "prices 페이로드에 `close` 없음 | WARN",
            ),
        ),
    }

    texts = {path: path.read_text(encoding="utf-8") for path in specs}

    for path, (acceptance_heading, stale_phrases) in specs.items():
        text = texts[path]
        status = _status_line(text)
        acceptance = _markdown_section(text, acceptance_heading)

        assert "구현 완료" in status
        assert "최신 검증은 README 테스트 배지와 docs health guard가 추적" in status
        assert "- [ ]" not in acceptance, f"{path} still has unchecked acceptance"
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"

    inc1 = texts[CONFIG_DRIVEN_EXTENSIBILITY_SPEC]
    assert "A2" in inc1
    assert "A3" in inc1
    assert "disabled_ids" in inc1

    inc2 = texts[TYPED_PAYLOAD_SPEC]
    assert "`Record.payload` 유니온화" in inc2
    assert "`RawRecord.payload`는 `dict[str, Any]` 유지" in inc2
    assert "Dataset.EVALUATION" in inc2
    assert "BucketStat" in inc2

    inc3 = texts[DATA_DOCTOR_SPEC]
    assert "typed `Record.payload`" in inc3
    assert "storage boundary" in inc3
    assert "render_doctor_html" in inc3
    assert "dashboard" in inc3
    assert "doctor --strict" in inc3


def test_source_extensibility_design_specs_match_current_completion_state() -> None:
    specs = {
        MACRO_SERIES_REGISTRY_SPEC: (
            "## 8. 수용 기준",
            ("현재 364 테스트", "coverage gate 클린"),
        ),
        DECLARATIVE_SOURCE_REGISTRATION_SPEC: (
            "## 8. 수용 기준",
            ("현재 364 테스트", "coverage gate 클린"),
        ),
        SOURCE_ENTRY_POINTS_SPEC: (
            "## 6. 수용 기준",
            ("397 테스트", "coverage gate 클린"),
        ),
    }

    texts = {path: path.read_text(encoding="utf-8") for path in specs}

    for path, (acceptance_heading, stale_phrases) in specs.items():
        text = texts[path]
        status = _status_line(text)
        acceptance = _markdown_section(text, acceptance_heading)

        assert "구현 완료" in status
        assert "최신 검증은 README 테스트 배지와 docs health guard가 추적" in status
        assert "- [ ]" not in acceptance, f"{path} still has unchecked acceptance"
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"

    a2 = texts[MACRO_SERIES_REGISTRY_SPEC]
    assert "`mimir/core/macro_series.py`" in a2
    assert "`DEFAULT_MACRO_RATE_SERIES`" in a2
    assert "`default_fred_series()`" in a2
    assert "`default_ecos_series_specs()`" in a2
    assert "`macro_series_cadences()`" in a2
    assert "`analysis.macro_regime.rate_series`" in a2
    assert "A3" in a2
    assert "A3b" in a2

    a3 = texts[DECLARATIVE_SOURCE_REGISTRATION_SPEC]
    assert "`SourceSpec`" in a3
    assert "`BUILTIN_SOURCE_SPECS`" in a3
    assert "`required_secret_attr`" in a3
    assert "`required_module`" in a3
    assert "`meta`" in a3
    assert "`sources.plugins.<source_id>`" in a3
    assert "doctor expected coverage" in a3

    a3b = texts[SOURCE_ENTRY_POINTS_SPEC]
    assert "`SOURCE_ENTRY_POINT_GROUP = \"mimir.sources\"`" in a3b
    assert "`_load_entry_point_source_specs()`" in a3b
    assert "`load_source_specs()`" in a3b
    assert "`build_sources(..., specs=...)`" in a3b
    assert "`sources.plugins.<source_id>`" in a3b
    assert "sandbox" in a3b.lower()


def test_storage_backfill_design_specs_match_current_completion_state() -> None:
    specs = {
        MACRO_REVISION_POLICY_SPEC: (
            "## 7. 수용 기준",
            ("407 테스트", "coverage gate 클린"),
        ),
        BACKFILL_MANIFEST_SPEC: (
            "## 6. 수용 기준",
            (
                "368 테스트",
                "coverage gate 클린",
                "secret/package gate 때문에 사용할 수 없는 경우에는 현재처럼",
            ),
        ),
        BACKFILL_PREFLIGHT_MANIFEST_SPEC: (
            "## 6. 수용 기준",
            ("499 테스트", "coverage gate 클린"),
        ),
    }

    texts = {path: path.read_text(encoding="utf-8") for path in specs}

    for path, (acceptance_heading, stale_phrases) in specs.items():
        text = texts[path]
        status = _status_line(text)
        acceptance = _markdown_section(text, acceptance_heading)

        assert "구현 완료" in status
        assert "최신 검증은 README 테스트 배지와 docs health guard가 추적" in status
        assert "- [ ]" not in acceptance, f"{path} still has unchecked acceptance"
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"

    macro = texts[MACRO_REVISION_POLICY_SPEC]
    assert "`append_overwrite_enabled(dataset)`" in macro
    assert "`OVERWRITE_ON_APPEND_DATASETS`" in macro
    assert "`Dataset.MACRO`" in macro
    assert "`JsonlStore.append(overwrite=True)`" in macro
    assert "`_same_stored_record()`" in macro
    assert "`captured_at`" in macro
    assert "first-write-wins" in macro
    assert "last-write-wins" in macro

    manifest = texts[BACKFILL_MANIFEST_SPEC]
    assert "`Manifest(root=data_root)`" in manifest
    assert "`SourceResult`" in manifest
    assert "`_write_failure_manifest()`" in manifest
    assert "`append_overwrite_enabled(source.meta.dataset)`" in manifest
    assert "BF-PREFLIGHT" in manifest
    assert "registered-unavailable" in manifest
    assert "unknown source id" in manifest

    preflight = texts[BACKFILL_PREFLIGHT_MANIFEST_SPEC]
    assert "`SourceSpec(meta=...)`" in preflight
    assert "`load_source_specs()`" in preflight
    assert "`build_sources(settings, runtime.source_config, specs=specs)`" in preflight
    assert "`_preflight_unavailable_error()`" in preflight
    assert "`_write_failure_manifest()`" in preflight
    assert "`STOOQ_API_KEY is not set`" in preflight
    assert "`package not installed (pip install -e '.[kr]')`" in preflight
    assert "unknown source id" in preflight
    assert "manifest 없이 argument error" in preflight


def test_news_rss_design_specs_match_current_completion_state() -> None:
    specs = {
        NEWS_CAPTURED_WINDOW_SPEC: (
            "## 7. 수용 기준",
            ("377 테스트", "coverage gate 클린"),
        ),
        SYMBOL_TAGGED_RSS_FEEDS_SPEC: (
            "## 7. 수용 기준",
            ("415 테스트", "coverage gate 클린"),
        ),
        RSS_FEED_CATALOG_SPEC: (
            "## 13. 수용 기준",
            ("438 tests", "coverage gate 통과"),
        ),
    }

    texts = {path: path.read_text(encoding="utf-8") for path in specs}

    for path, (acceptance_heading, stale_phrases) in specs.items():
        text = texts[path]
        status = _status_line(text)
        acceptance = _markdown_section(text, acceptance_heading)

        assert "구현 완료" in status
        assert "최신 검증은 README 테스트 배지와 docs health guard가 추적" in status
        assert "- [ ]" not in acceptance, f"{path} still has unchecked acceptance"
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"

    captured = texts[NEWS_CAPTURED_WINDOW_SPEC]
    assert "`DataReader.read_captured_window()`" in captured
    assert "`captured_at.date()`" in captured
    assert "`_captured_date_index()`" in captured
    assert "`JsonlStore.read_all(dataset)`" in captured
    assert "`JsonlStore.revision`" in captured
    assert "captured-date index rebuilt" in captured
    assert "`NewsVolumeSignal`" in captured
    assert "`LlmSentimentSignal`" in captured
    assert "저장 파티션" in captured
    assert "on-disk index" in captured

    symbol_tagged = texts[SYMBOL_TAGGED_RSS_FEEDS_SPEC]
    assert "`sources.rss.feeds[].symbol`" in symbol_tagged
    assert "`RssFeed.symbol`" in symbol_tagged
    assert "`RawRecord.symbol`" in symbol_tagged
    assert "`rss:{link}`" in symbol_tagged
    assert "`rss:{symbol}:{link}`" in symbol_tagged
    assert "`NewsMentionMatcher`" in symbol_tagged
    assert "`record.symbol == symbol`" in symbol_tagged
    assert "`NewsVolumeSignal`" in symbol_tagged
    assert "`LlmSentimentSignal`" in symbol_tagged

    catalog = texts[RSS_FEED_CATALOG_SPEC]
    assert "`RssCatalogSelection`" in catalog
    assert "`RSS_CATALOG`" in catalog
    assert "`resolve_rss_catalogs()`" in catalog
    assert "`resolve_rss_feeds()`" in catalog
    assert "`sec_press_releases`" in catalog
    assert "`sec_structured_usgaap`" in catalog
    assert "`sec_structured_risk_return`" in catalog
    assert "`sec_structured_inline_xbrl`" in catalog
    assert "`sec_structured_all_xbrl`" in catalog
    assert "`sources.rss.sec.company_filings`" in catalog
    assert "`ticker_cik_map_refresh`" in catalog
    assert "`MIMIR_SEC_USER_AGENT`" in catalog
    assert "`catalogs`, `sec.company_filings`, `feeds`" in catalog
    assert "네트워크를 호출하지 않는다" in catalog
    assert "HTML scraping" in catalog
    assert "vendor URL" in catalog


def test_cli_config_design_specs_match_current_completion_state() -> None:
    specs = {
        CLI_ENTRYPOINTS_SPEC: (
            "## 8. 수용 기준",
            ("484 tests", "97% coverage", "coverage gate"),
            (
                "`mimir/cli.py`",
                "`COMMANDS`",
                "`_help_text()`",
                "`mimir <command>`",
                "`[project.scripts]`",
                '`mimir = "mimir.cli:main"`',
                '`mimir.doctor = "mimir.doctor.doctor_cli:main"`',
                "`mimir.collect`",
                "`python -m mimir.collect`",
                "`[mimir] unknown command:`",
            ),
        ),
        DOTENV_CLI_AUTOLOAD_SPEC: (
            "## 8. 수용 기준",
            ("492 tests", "98% coverage", "coverage gate"),
            (
                "`Settings.from_env(env=None)`",
                "`load_dotenv(find_dotenv(usecwd=True), override=False)`",
                "`env={...}`",
                "`override=False`",
                "`run_collect`",
                "`run_pipeline`",
                "`run_deliver`",
                "`run_backfill`",
                "`Settings.from_env(env)`",
            ),
        ),
        SOURCES_CONFIG_CLI_VALIDATION_SPEC: (
            "## 8. 수용 기준",
            ("495 tests", "98% coverage", "coverage gate"),
            (
                "`load_validated_sources_config()`",
                "`parse_runtime_sources_config()`",
                "`RuntimeSourcesConfig`",
                "`_resolve_sources_config_paths()`",
                "`report_invalid_sources()`",
                "`[mimir] invalid sources.yaml:`",
                "`SourcesConfigError`",
                "`collect`, `run`, `backfill`, `analyze`, `deliver`, `dashboard`, `doctor`",
                "`history`는 `sources.yaml`을 읽지 않는다",
                "`doctor_cli.main()`",
                "HTML 파일을 쓰기 전",
            ),
        ),
    }

    texts = {path: path.read_text(encoding="utf-8") for path in specs}

    for path, (acceptance_heading, stale_phrases, required_phrases) in specs.items():
        text = texts[path]
        status = _status_line(text)
        acceptance = _markdown_section(text, acceptance_heading)

        assert "구현 완료" in status
        assert "최신 검증은 README 테스트 배지와 docs health guard가 추적" in status
        assert "- [ ]" not in acceptance, f"{path} still has unchecked acceptance"
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"
        for phrase in required_phrases:
            assert phrase in text, f"{path} missing current truth: {phrase}"


def test_ops_config_design_specs_match_current_completion_state() -> None:
    specs = {
        GITHUB_ACTIONS_NODE24_SPEC: (
            "## 6. 수용 기준",
            (
                "365 테스트",
                "coverage gate 클린",
                "현재 workflow는 `actions/checkout@v4`와 "
                "`actions/setup-python@v5`를 쓴다",
            ),
            (
                "`actions/checkout@v6`",
                "`actions/setup-python@v6`",
                "`.github/workflows/ci.yml`",
                "`.github/workflows/_pipeline.yml`",
                "`tests/test_workflows.py`",
                "`EXPECTED_WORKFLOW_ACTION_MAJORS`",
                "`ACTION_USES_RE`",
            ),
        ),
        PYKRX_RETRY_POLICY_SPEC: (
            "## 6. 수용 기준",
            ("368 테스트", "coverage gate 클린"),
            (
                "`PykrxSource`",
                "`DEFAULT_MAX_RETRIES = 2`",
                "`DEFAULT_BACKOFF = 0.5`",
                "`max_retries`",
                "`backoff`",
                "`sleep`",
                "`_fetch_ohlcv()`",
                "`Throttle.wait()`",
                "`FetchError`",
                "`pykrx OHLCV failed after`",
                "manifest",
            ),
        ),
        PLUGIN_SETTINGS_NAMESPACE_SPEC: (
            "## 7. 수용 기준",
            ("424 테스트", "coverage gate 클린"),
            (
                "`sources.plugins.<source_id>`",
                "`SourcesConfig.plugin_settings`",
                "`plugin_config()`",
                "`parse_plugin_config()`",
                "`_SourcesBlock.plugins`",
                "`dict[str, dict[str, Any]]`",
                "`build_sources()`",
                "`source plugin config`",
                "`sources.plugins.rss`",
                "`sources.rss`",
                "`sources.plugins.sec_edgar`",
                "built-in sources do not read `sources.plugins`",
            ),
        ),
        SEC_RSS_TICKER_INPUT_SPEC: (
            "## 8. 수용 기준",
            (
                "478 tests",
                "diff check 통과",
                "uv run pytest tests/sources/test_rss_catalog.py "
                "tests/sources/test_config.py tests/core/test_builder.py -q",
                "uv run ruff check .",
                "uv run mypy mimir",
                "uv run pytest -q",
            ),
            (
                "`SecCompanyFilingFeed`",
                "`ticker`",
                "`cik`",
                "`_normalize_ticker()`",
                "`CIK=AAPL`",
                "`resolve_sec_company_filing_feeds()`",
                "`resolve_rss_feeds()`",
                "`duplicate RSS feed`",
                "네트워크를 호출하지 않는다",
                "`ticker_cik_map_refresh`",
            ),
        ),
    }

    texts = {path: path.read_text(encoding="utf-8") for path in specs}

    for path, (acceptance_heading, stale_phrases, required_phrases) in specs.items():
        text = texts[path]
        status = _status_line(text)
        acceptance = _markdown_section(text, acceptance_heading)

        assert "구현 완료" in status
        assert "최신 검증은 README 테스트 배지와 docs health guard가 추적" in status
        assert "- [ ]" not in acceptance, f"{path} still has unchecked acceptance"
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"
        for phrase in required_phrases:
            assert phrase in text, f"{path} missing current truth: {phrase}"


def test_ops_rss_visibility_design_specs_match_current_completion_state() -> None:
    specs = {
        DOCTOR_HTML_REPORT_SPEC: (
            "## 6. 수용 기준",
            ("coverage gate", "diff-check가 통과한다"),
            (
                "`mimir/report/doctor_html.py`",
                "`render_doctor_html()`",
                "`mimir doctor --html <path>`",
                "`--lang en|ko|zh`",
                "`Finding.scope`",
                "`Finding.message`",
                "`Finding.severity`",
                "`doctor_cli.main()`",
            ),
        ),
        SEC_EDGAR_RSS_PROVIDER_SPEC: (
            "## 10. 수용 기준",
            (
                "uv run pytest tests/sources/test_rss_catalog.py "
                "tests/sources/test_config.py tests/sources/test_rss.py "
                "tests/core/test_builder.py -q",
                "uv run ruff check .",
                "uv run mypy mimir",
                "uv run pytest -q",
            ),
            (
                "`SecCompanyFilingFeed`",
                "`sources.rss.sec.company_filings`",
                "`resolve_sec_company_filing_feeds()`",
                "`resolve_rss_feeds()`",
                "`RssSource(user_agent=settings.sec_user_agent)`",
                "`MIMIR_SEC_USER_AGENT`",
                "`User-Agent`",
                "`browse-edgar`",
                "`duplicate RSS feed`",
                "네트워크를 호출하지 않는다",
            ),
        ),
        SEC_STRUCTURED_RSS_CATALOG_SPEC: (
            "## 9. 수용 기준",
            (
                "uv run pytest tests/sources/test_rss_catalog.py "
                "tests/sources/test_config.py -q",
                "uv run ruff check .",
                "uv run mypy mimir",
                "uv run pytest -q",
                "git diff --check",
            ),
            (
                "`RSS_CATALOG`",
                "`RssCatalogSelection`",
                "`resolve_rss_catalogs()`",
                "`resolve_rss_feeds()`",
                "`sec_structured_usgaap`",
                "`sec_structured_risk_return`",
                "`sec_structured_inline_xbrl`",
                "`sec_structured_all_xbrl`",
                "broad SEC/XBRL feed",
                "symbol-specific feed가 아니다",
                "네트워크를 호출하지 않는다",
            ),
        ),
        SCHEDULED_DASHBOARD_PUBLICATION_SPEC: (
            "## 7. 수용 기준",
            (
                "uv run pytest tests/test_workflows.py -q",
                "uv run ruff check .",
                "uv run mypy mimir",
                "uv run pytest -q",
            ),
            (
                "`PIPELINE_WORKFLOW`",
                "`test_reusable_pipeline_publishes_dashboard_before_commit()`",
                "`test_reusable_pipeline_does_not_add_doctor_hard_gate()`",
                "`Run dashboard`",
                "`python -m mimir.dashboard --data-root data --reports-root reports`",
                "`Run pipeline`",
                "`Commit data + reports`",
                "`mimir.doctor`",
                "`--strict`",
                "publish-first",
            ),
        ),
    }

    texts = {path: path.read_text(encoding="utf-8") for path in specs}

    for path, (acceptance_heading, stale_phrases, required_phrases) in specs.items():
        text = texts[path]
        status = _status_line(text)
        acceptance = _markdown_section(text, acceptance_heading)

        assert "구현 완료" in status
        assert "최신 검증은 README 테스트 배지와 docs health guard가 추적" in status
        assert "- [ ]" not in acceptance, f"{path} still has unchecked acceptance"
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"
        for phrase in required_phrases:
            assert phrase in text, f"{path} missing current truth: {phrase}"


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
