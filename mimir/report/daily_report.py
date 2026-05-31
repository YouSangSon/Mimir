from __future__ import annotations

import html
import re
from datetime import date
from pathlib import Path

from mimir.analysis.schema import Insight
from mimir.analysis.signals.base import SignalDirection
from mimir.historical.schema import HistoricalInsight
from mimir.report.i18n import DEFAULT_LANG, t

DEFAULT_REPORTS_ROOT = Path("reports")
DATE_REPORT_RE = re.compile(r"\d{4}/\d{2}/\d{2}\.html$")

DIRECTION_COLOR: dict[SignalDirection, str] = {
    SignalDirection.BULLISH: "#16a34a",
    SignalDirection.BEARISH: "#dc2626",
    SignalDirection.NEUTRAL: "#6b7280",
}


def _stars(n: int) -> str:
    return "★" * n + "☆" * (5 - n)


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
{_stars(ins.stars)}</span>
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


def build_report_html(
    insights: list[Insight],
    as_of: date,
    cadence: str = "daily",
    historical: list[HistoricalInsight] | None = None,
    lang: str = DEFAULT_LANG,
) -> str:
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
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<title>{t("report_page_title", lang, cadence=cadence, date=as_of.isoformat())}</title>
<style>
 body{{font-family:system-ui,-apple-system,sans-serif;margin:2rem;background:#0b0f17;color:#e5e7eb}}
 h1{{font-size:1.4rem}} a{{color:#7c3aed}}
 .meta{{color:#9ca3af;margin-bottom:1.5rem}}
 .card{{background:#111827;border:1px solid #1f2937;border-radius:10px;padding:1rem;margin:.6rem 0}}
 .card-head{{display:flex;align-items:center;gap:.6rem}}
 .sym{{font-weight:700;font-size:1.1rem}}
 .badge{{color:#fff;border-radius:6px;padding:.1rem .5rem;font-size:.8rem}}
 .attn{{margin-left:auto;color:#94a3b8;font-size:.8rem}}
 .stars{{color:#fbbf24;font-size:1.1rem}}
 .reasons{{margin:.5rem 0 0;color:#cbd5e1;font-size:.9rem}}
 .examples{{color:#94a3b8;font-size:.82rem}}
 .evt{{color:#a5b4fc;font-size:.9rem}}
 h2{{font-size:1.1rem;margin-top:2rem;color:#cbd5e1}}
 .empty{{color:#9ca3af}}
 .dis{{color:#6b7280;font-size:.8rem;margin-top:2rem;border-top:1px solid #1f2937;padding-top:1rem}}
</style></head>
<body>
<h1>{t("report_heading", lang, cadence=cadence)}</h1>
<p class="meta">{meta}</p>
{body}
{historical_section}
<p class="dis">{t("disclaimer_report", lang)}</p>
</body></html>"""


def save_report(html_doc: str, as_of: date, root: Path = DEFAULT_REPORTS_ROOT) -> Path:
    path = root / f"{as_of:%Y}" / f"{as_of:%m}" / f"{as_of:%d}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_doc, encoding="utf-8")
    return path


def rebuild_index(root: Path = DEFAULT_REPORTS_ROOT, lang: str = DEFAULT_LANG) -> Path:
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
<html lang="{lang}"><head><meta charset="utf-8"><title>{t("index_page_title", lang)}</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem;background:#0b0f17;color:#e5e7eb}}
a{{color:#7c3aed}} li{{margin:.3rem 0}}</style></head>
<body><h1>{t("index_heading", lang)}</h1><ul>
{body}
</ul></body></html>"""
    index = root / "index.html"
    index.write_text(doc, encoding="utf-8")
    return index
