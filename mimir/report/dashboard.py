from __future__ import annotations

import html
from datetime import datetime

from mimir.analysis.schema import Insight
from mimir.doctor.report import DoctorReport, Finding, Severity
from mimir.evaluation.schema import BucketStat
from mimir.historical.schema import HistoricalInsight
from mimir.manifest.manifest import RunRecord, SourceResult
from mimir.report.daily_report import DIRECTION_COLOR
from mimir.report.i18n import DEFAULT_LANG, normalize_lang, t

SEVERITY_COLOR: dict[Severity, str] = {
    Severity.OK: "#16a34a",
    Severity.WARN: "#d97706",
    Severity.CRITICAL: "#dc2626",
}

_STATUS_HTML_HREF = "status.html"


def _stars(n: int) -> str:
    return "★" * n + "☆" * (5 - n)


def _esc(value: object) -> str:
    return html.escape(str(value))


def _badge(text: str, color: str) -> str:
    return f'<span class="hb" style="background:{color}">{_esc(text)}</span>'


def _badges(
    report: DoctorReport,
    run: RunRecord | None,
    insight_count: int,
    sufficient: bool,
    lang: str,
) -> str:
    worst = report.worst
    health = t("dashboard_badge_health", lang, severity=worst.value.upper())
    parts = [_badge(health, SEVERITY_COLOR[worst])]
    if run is not None:
        ok = sum(1 for r in run.results if r.ok)
        total = len(run.results)
        color = SEVERITY_COLOR[Severity.OK] if ok == total else SEVERITY_COLOR[Severity.WARN]
        parts.append(_badge(t("dashboard_badge_sources", lang, ok=ok, total=total), color))
    parts.append(_badge(t("dashboard_badge_insights", lang, count=insight_count), "#374151"))
    if sufficient:
        eval_label = t("dashboard_badge_eval_sufficient", lang)
        parts.append(_badge(eval_label, SEVERITY_COLOR[Severity.OK]))
    else:
        parts.append(_badge(t("dashboard_badge_eval_insufficient", lang), "#374151"))
    return f'<div class="badges">{"".join(parts)}</div>'


def _health_section(report: DoctorReport, lang: str) -> str:
    heading = f"<h2>{t('dashboard_section_health', lang)}</h2>"
    if not report.findings:
        return f"{heading}\n<p class=\"empty\">{t('dashboard_health_all_clear', lang)}</p>"
    head = (
        f"<th>{t('dashboard_health_col_dataset', lang)}</th>"
        f"<th>{t('dashboard_health_col_scope', lang)}</th>"
        f"<th>{t('dashboard_health_col_severity', lang)}</th>"
        f"<th>{t('dashboard_health_col_detail', lang)}</th>"
    )
    rows = "\n".join(_health_row(f) for f in _ordered_findings(report.findings))
    return f"{heading}\n<table><tr>{head}</tr>\n{rows}\n</table>"


def _ordered_findings(findings: list[Finding]) -> list[Finding]:
    rank = {Severity.CRITICAL: 0, Severity.WARN: 1, Severity.OK: 2}
    return sorted(findings, key=lambda f: rank[f.severity])


def _health_row(f: Finding) -> str:
    color = SEVERITY_COLOR[f.severity]
    sev = f'<span class="sev" style="background:{color}">{_esc(f.severity.value)}</span>'
    scope = _esc(f.scope) if f.scope else "—"
    return (
        f"<tr><td>{_esc(f.dataset.value)}</td><td>{scope}</td>"
        f"<td>{sev}</td><td>{_esc(f.message)}</td></tr>"
    )


def _insights_section(insights: list[Insight], lang: str) -> str:
    heading = f"<h2>{t('dashboard_section_insights', lang)}</h2>"
    if not insights:
        return f"{heading}\n<p class=\"empty\">{t('dashboard_insights_empty', lang)}</p>"
    head = (
        f"<th>{t('dashboard_insights_col_symbol', lang)}</th>"
        f"<th>{t('dashboard_insights_col_market', lang)}</th>"
        f"<th>{t('dashboard_insights_col_direction', lang)}</th>"
        f"<th>{t('dashboard_insights_col_stars', lang)}</th>"
        f"<th>{t('dashboard_insights_col_confidence', lang)}</th>"
        f"<th>{t('dashboard_insights_col_reason', lang)}</th>"
    )
    ordered = sorted(insights, key=lambda i: (-i.stars, i.symbol))
    rows = "\n".join(_insight_row(i, lang) for i in ordered)
    return f"{heading}\n<table><tr>{head}</tr>\n{rows}\n</table>"


def _insight_row(ins: Insight, lang: str) -> str:
    color = DIRECTION_COLOR[ins.direction]
    direction = (
        f'<span class="badge" style="background:{color}">'
        f"{t(f'direction_{ins.direction.value}', lang)}</span>"
    )
    reason = _esc(ins.reasons[0]) if ins.reasons else "—"
    return (
        f"<tr><td class=\"sym\">{_esc(ins.symbol)}</td>"
        f"<td>{_esc(ins.market.value)}</td><td>{direction}</td>"
        f'<td class="stars">{_stars(ins.stars)}</td>'
        f"<td>{ins.confidence:.2f}</td><td>{reason}</td></tr>"
    )


def _scorecard_section(buckets: list[BucketStat], lang: str) -> str:
    heading = f"<h2>{t('dashboard_section_scorecard', lang)}</h2>"
    if not buckets:
        return f"{heading}\n<p class=\"empty\">{t('dashboard_scorecard_insufficient', lang)}</p>"
    head = (
        f"<th>{t('dashboard_scorecard_col_dimension', lang)}</th>"
        f"<th>{t('dashboard_scorecard_col_key', lang)}</th>"
        f"<th>{t('dashboard_scorecard_col_market', lang)}</th>"
        f"<th>{t('dashboard_scorecard_col_horizons', lang)}</th>"
    )
    rows = "\n".join(_bucket_row(b, lang) for b in buckets)
    return f"{heading}\n<table><tr>{head}</tr>\n{rows}\n</table>"


def _bucket_row(b: BucketStat, lang: str) -> str:
    cells = " · ".join(
        t(
            "dashboard_scorecard_horizon_cell",
            lang,
            horizon=h.horizon,
            hit=f"{h.hit_rate * 100:.0f}",
            edge=f"{h.mean_fwd_return * 100:+.1f}",
            n=h.n,
        )
        for h in b.horizons
    )
    return (
        f"<tr><td>{_esc(b.dimension)}</td><td>{_esc(b.key)}</td>"
        f"<td>{_esc(b.market.value)}</td><td>{cells}</td></tr>"
    )


def _historical_section(historical: list[HistoricalInsight], lang: str) -> str:
    heading = f"<h2>{t('dashboard_section_historical', lang)}</h2>"
    if not historical:
        return f"{heading}\n<p class=\"empty\">{t('dashboard_historical_empty', lang)}</p>"
    rows = "\n".join(_historical_row(h, lang) for h in historical)
    return f"{heading}\n<table>\n{rows}\n</table>"


def _historical_row(h: HistoricalInsight, lang: str) -> str:
    trig = (
        f' <span class="badge" style="background:#7c3aed">{t("triggered_today_badge", lang)}</span>'
        if h.triggered_today
        else ""
    )
    horizons = " · ".join(
        t(
            "historical_horizon_row",
            lang,
            horizon=s.horizon,
            median=f"{s.median_return * 100:+.1f}",
            pct_positive=f"{s.pct_positive * 100:.0f}",
            n=s.n,
        )
        for s in h.horizons
    )
    return (
        f"<tr><td class=\"sym\">{_esc(h.symbol)}</td>"
        f"<td>{_esc(h.event_type)} ×{_esc(h.occurrences)}{trig}</td>"
        f"<td>{horizons}</td></tr>"
    )


def _collection_section(run: RunRecord | None, lang: str) -> str:
    heading = f"<h2>{t('dashboard_section_collection', lang)}</h2>"
    if run is None:
        return f"{heading}\n<p class=\"empty\">{t('dashboard_collection_empty', lang)}</p>"
    head = (
        f"<th>{t('status_table_header_source', lang)}</th>"
        f"<th>{t('status_table_header_status', lang)}</th>"
        f"<th>{t('status_table_header_detail', lang)}</th>"
    )
    rows = "\n".join(_collection_row(r, lang) for r in run.results)
    link = f'<p><a href="{_STATUS_HTML_HREF}">{t("dashboard_collection_link", lang)}</a></p>'
    return f"{heading}\n<table><tr>{head}</tr>\n{rows}\n</table>\n{link}"


def _collection_row(r: SourceResult, lang: str) -> str:
    source = _esc(r.source)
    color = SEVERITY_COLOR[Severity.OK] if r.ok else SEVERITY_COLOR[Severity.CRITICAL]
    status = t("status_ok", lang) if r.ok else t("status_fail", lang)
    status_cell = f'<span class="sev" style="background:{color}">{status}</span>'
    if r.ok:
        detail = t("status_detail_fetched_stored", lang, fetched=r.fetched, stored=r.stored)
    else:
        detail = _esc(r.error or "")
    return f"<tr><td>{source}</td><td>{status_cell}</td><td>{detail}</td></tr>"


def build_dashboard_html(
    *,
    doctor_report: DoctorReport,
    insights: list[Insight],
    buckets: list[BucketStat],
    historical: list[HistoricalInsight],
    run: RunRecord | None,
    lang: str = DEFAULT_LANG,
    now: datetime,
) -> str:
    """Pure renderer: turn already-loaded data into a self-contained HTML page.

    No I/O — all data is injected so this is deterministic and unit-testable.
    Every user-derived string is escaped; every section degrades gracefully.
    """
    lang = normalize_lang(lang)
    sufficient = bool(buckets)
    generated = now.isoformat(timespec="seconds")
    badges = _badges(doctor_report, run, len(insights), sufficient, lang)
    sections = "\n".join(
        [
            _health_section(doctor_report, lang),
            _insights_section(insights, lang),
            _scorecard_section(buckets, lang),
            _historical_section(historical, lang),
            _collection_section(run, lang),
        ]
    )
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<title>{t("dashboard_page_title", lang)}</title>
<style>
 body{{font-family:system-ui,-apple-system,sans-serif;margin:2rem;background:#0b0f17;color:#e5e7eb}}
 h1{{font-size:1.4rem}} a{{color:#7c3aed}}
 h2{{font-size:1.1rem;margin-top:2rem;color:#cbd5e1}}
 .meta{{color:#9ca3af;margin-bottom:1rem}}
 .badges{{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:1rem}}
 .hb{{color:#fff;border-radius:6px;padding:.2rem .6rem;font-size:.8rem}}
 table{{border-collapse:collapse;width:100%;margin:.5rem 0;font-size:.9rem}}
 td,th{{border:1px solid #1f2937;padding:.4rem .7rem;text-align:left}}
 th{{color:#94a3b8;font-weight:600;background:#111827}}
 .sym{{font-weight:700}}
 .stars{{color:#fbbf24}}
 .badge,.sev{{color:#fff;border-radius:6px;padding:.1rem .5rem;font-size:.8rem}}
 .empty{{color:#9ca3af}}
 .dis{{color:#6b7280;font-size:.8rem;margin-top:2rem;border-top:1px solid #1f2937;padding-top:1rem}}
</style></head>
<body>
<h1>{t("dashboard_heading", lang)}</h1>
<p class="meta">{t("dashboard_generated_at", lang, time=generated)}</p>
{badges}
{sections}
<p class="dis">{t("disclaimer_report", lang)}</p>
</body></html>"""
