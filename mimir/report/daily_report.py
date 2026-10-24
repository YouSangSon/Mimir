from __future__ import annotations

import html
import re
from datetime import date
from pathlib import Path

from mimir.analysis.schema import Insight
from mimir.analysis.signals.base import SignalDirection
from mimir.evaluation.schema import BucketStat
from mimir.historical.schema import HistoricalInsight
from mimir.report.html import REPORT_CSS, VIEWPORT_META, render_table, stars
from mimir.report.i18n import DEFAULT_LANG, normalize_lang, t

DEFAULT_REPORTS_ROOT = Path("reports")
DATE_REPORT_RE = re.compile(r"\d{4}/\d{2}/\d{2}\.html$")

DIRECTION_COLOR: dict[SignalDirection, str] = {
    SignalDirection.BULLISH: "#15803d",
    SignalDirection.BEARISH: "#b91c1c",
    SignalDirection.NEUTRAL: "#4b5563",
}


def _card(ins: Insight, lang: str) -> str:
    color = DIRECTION_COLOR[ins.direction]
    label = t(f"direction_{ins.direction.value}", lang)
    reasons = "".join(f"<li>{html.escape(r)}</li>" for r in ins.reasons)
    activity = t("activity_label", lang, pct=f"{ins.attention:.0%}")
    return f"""<div class="card">
  <div class="card-head">
    <span class="sym">{html.escape(ins.symbol)}</span>
    <span class="badge" style="background:{color}">{label}</span>
    <span class="attn" title="{t("activity_tooltip", lang)}">{activity}</span>
    <span class="stars" title="{t("conviction_tooltip", lang, confidence=ins.confidence)}">\
{stars(ins.stars)}</span>
  </div>
  <ul class="reasons">{reasons}</ul>
</div>"""


def _historical_card(h: HistoricalInsight, lang: str) -> str:
    trig = (
        f' <span class="badge" style="background:#7c3aed">{t("triggered_today_badge", lang)}</span>'
        if h.triggered_today
        else ""
    )
    rows = "".join(
        "<li>"
        + t(
            "historical_horizon_row",
            lang,
            horizon=s.horizon,
            median=f"{s.median_return * 100:+.1f}",
            pct_positive=f"{s.pct_positive * 100:.0f}",
            n=s.n,
        )
        + "</li>"
        for s in h.horizons
    )
    examples = "".join(f"<li>{html.escape(e)}</li>" for e in h.examples)
    return f"""<div class="card">
  <div class="card-head">
    <span class="sym">{html.escape(h.symbol)}</span>
    <span class="evt">{html.escape(h.event_type)} ×{h.occurrences}</span>{trig}
  </div>
  <ul class="reasons">{rows}</ul>
  <ul class="reasons examples">{examples}</ul>
</div>"""


def _evaluation_section(buckets: list[BucketStat], lang: str) -> str:
    heading = f"<h2>{t('evaluation_section_heading', lang)}</h2>"
    head = (
        f"<th scope=\"col\">{t('evaluation_col_dimension', lang)}</th>"
        f"<th scope=\"col\">{t('evaluation_col_key', lang)}</th>"
        f"<th scope=\"col\">{t('evaluation_col_market', lang)}</th>"
        f"<th scope=\"col\">{t('evaluation_col_horizons', lang)}</th>"
    )
    rows = "\n".join(_evaluation_row(b, lang) for b in buckets)
    return heading + render_table(head, rows, t("evaluation_section_heading", lang))


def _evaluation_row(bucket: BucketStat, lang: str) -> str:
    horizons = " · ".join(
        t(
            "evaluation_horizon_cell",
            lang,
            horizon=h.horizon,
            hit=f"{h.hit_rate * 100:.0f}",
            edge=f"{h.mean_fwd_return * 100:+.1f}",
            n=h.n,
        )
        for h in bucket.horizons
    )
    return (
        f"<tr><td>{html.escape(bucket.dimension)}</td>"
        f"<td>{html.escape(bucket.key)}</td>"
        f"<td>{html.escape(bucket.market.value)}</td>"
        f"<td>{horizons}</td></tr>"
    )


def build_report_html(
    insights: list[Insight],
    as_of: date,
    cadence: str = "daily",
    historical: list[HistoricalInsight] | None = None,
    evaluation: list[BucketStat] | None = None,
    lang: str = DEFAULT_LANG,
) -> str:
    lang = normalize_lang(lang)
    cadence = html.escape(cadence)
    ordered = sorted(insights, key=lambda i: (-i.stars, i.symbol))
    if ordered:
        body = "\n".join(_card(i, lang) for i in ordered)
    else:
        body = f'<p class="empty">{t("report_empty", lang)}</p>'
    meta = (
        f"{as_of.isoformat()} · {t('report_meta_insight_count', lang, count=len(ordered))} · "
        f'<a href="../../index.html">{t("report_meta_all_reports_link", lang)}</a>'
    )
    hist = historical or []
    if hist:
        cards = "\n".join(_historical_card(h, lang) for h in hist)
        historical_section = f"<h2>{t('historical_section_heading', lang)}</h2>\n{cards}"
    else:
        historical_section = ""
    eval_buckets = evaluation or []
    evaluation_section = _evaluation_section(eval_buckets, lang) if eval_buckets else ""
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">{VIEWPORT_META}
<title>{t("report_page_title", lang, cadence=cadence, date=as_of.isoformat())}</title>
<style>{REPORT_CSS}</style></head>
<body><main>
<h1>{t("report_heading", lang, cadence=cadence)}</h1>
<p class="meta">{meta}</p>
{body}
{historical_section}
{evaluation_section}
<p class="dis">{t("disclaimer_report", lang)}</p>
</main></body></html>"""


def save_report(html_doc: str, as_of: date, root: Path = DEFAULT_REPORTS_ROOT) -> Path:
    path = root / f"{as_of:%Y}" / f"{as_of:%m}" / f"{as_of:%d}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_doc, encoding="utf-8")
    return path


def rebuild_index(root: Path = DEFAULT_REPORTS_ROOT, lang: str = DEFAULT_LANG) -> Path:
    lang = normalize_lang(lang)
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
    reports = sorted(
        (p for p in root.rglob("*.html") if DATE_REPORT_RE.search(p.as_posix())),
        key=lambda p: p.as_posix(),
        reverse=True,
    )
    items = "\n".join(
        f'<li><a href="{p.relative_to(root).as_posix()}">'
        f"{p.relative_to(root).as_posix().replace('.html', '').replace('/', '-')}</a></li>"
        for p in reports
    )
    body = items or f'<li class="empty">{t("index_empty", lang)}</li>'
    doc = f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">{VIEWPORT_META}
<title>{t("index_page_title", lang)}</title>
<style>{REPORT_CSS}</style></head>
<body><main><h1>{t("index_heading", lang)}</h1><ul>
{body}
</ul></main></body></html>"""
    index = root / "index.html"
    index.write_text(doc, encoding="utf-8")
    return index
