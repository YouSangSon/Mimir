from __future__ import annotations

import html
import re
from datetime import date
from pathlib import Path

from mimir.analysis.schema import DISCLAIMER, Insight
from mimir.analysis.signals.base import SignalDirection
from mimir.historical.schema import HistoricalInsight

DEFAULT_REPORTS_ROOT = Path("reports")
DATE_REPORT_RE = re.compile(r"\d{4}/\d{2}/\d{2}\.html$")

DIRECTION_BADGE: dict[SignalDirection, tuple[str, str]] = {
    SignalDirection.BULLISH: ("강세", "#16a34a"),
    SignalDirection.BEARISH: ("약세", "#dc2626"),
    SignalDirection.NEUTRAL: ("중립", "#6b7280"),
}


def _stars(n: int) -> str:
    return "★" * n + "☆" * (5 - n)


def _card(ins: Insight) -> str:
    label, color = DIRECTION_BADGE[ins.direction]
    reasons = "".join(f"<li>{html.escape(r)}</li>" for r in ins.reasons)
    return f"""<div class="card">
  <div class="card-head">
    <span class="sym">{html.escape(ins.symbol)}</span>
    <span class="badge" style="background:{color}">{label}</span>
    <span class="stars" title="confidence {ins.confidence}">{_stars(ins.stars)}</span>
  </div>
  <ul class="reasons">{reasons}</ul>
</div>"""


def _historical_card(h: HistoricalInsight) -> str:
    trig = (
        ' <span class="badge" style="background:#7c3aed">오늘 발생</span>'
        if h.triggered_today
        else ""
    )
    rows = "".join(
        f"<li>{s.horizon}d: median {s.median_return * 100:+.1f}%, "
        f"양봉 {s.pct_positive * 100:.0f}% (n={s.n})</li>"
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
) -> str:
    ordered = sorted(insights, key=lambda i: (-i.stars, i.symbol))
    if ordered:
        body = "\n".join(_card(i) for i in ordered)
    else:
        body = '<p class="empty">특이사항 없음 — 오늘 생성된 인사이트가 없습니다.</p>'
    meta = (
        f'{as_of.isoformat()} · {len(ordered)} insight(s) · '
        f'<a href="../../index.html">← 전체 리포트</a>'
    )
    hist = historical or []
    if hist:
        cards = "\n".join(_historical_card(h) for h in hist)
        historical_section = f'<h2>📈 과거 사례 (event-study)</h2>\n{cards}'
    else:
        historical_section = ""
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<title>Mimir {cadence} report {as_of.isoformat()}</title>
<style>
 body{{font-family:system-ui,-apple-system,sans-serif;margin:2rem;background:#0b0f17;color:#e5e7eb}}
 h1{{font-size:1.4rem}} a{{color:#7c3aed}}
 .meta{{color:#9ca3af;margin-bottom:1.5rem}}
 .card{{background:#111827;border:1px solid #1f2937;border-radius:10px;padding:1rem;margin:.6rem 0}}
 .card-head{{display:flex;align-items:center;gap:.6rem}}
 .sym{{font-weight:700;font-size:1.1rem}}
 .badge{{color:#fff;border-radius:6px;padding:.1rem .5rem;font-size:.8rem}}
 .stars{{color:#fbbf24;margin-left:auto;font-size:1.1rem}}
 .reasons{{margin:.5rem 0 0;color:#cbd5e1;font-size:.9rem}}
 .examples{{color:#94a3b8;font-size:.82rem}}
 .evt{{color:#a5b4fc;font-size:.9rem}}
 h2{{font-size:1.1rem;margin-top:2rem;color:#cbd5e1}}
 .empty{{color:#9ca3af}}
 .dis{{color:#6b7280;font-size:.8rem;margin-top:2rem;border-top:1px solid #1f2937;padding-top:1rem}}
</style></head>
<body>
<h1>🧭 Mimir — {cadence} report</h1>
<p class="meta">{meta}</p>
{body}
{historical_section}
<p class="dis">{DISCLAIMER}</p>
</body></html>"""


def save_report(html_doc: str, as_of: date, root: Path = DEFAULT_REPORTS_ROOT) -> Path:
    path = root / f"{as_of:%Y}" / f"{as_of:%m}" / f"{as_of:%d}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_doc, encoding="utf-8")
    return path


def rebuild_index(root: Path = DEFAULT_REPORTS_ROOT) -> Path:
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
    body = items or '<li class="empty">아직 리포트가 없습니다.</li>'
    doc = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>Mimir reports</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem;background:#0b0f17;color:#e5e7eb}}
a{{color:#7c3aed}} li{{margin:.3rem 0}}</style></head>
<body><h1>🧭 Mimir — reports</h1><ul>
{body}
</ul></body></html>"""
    index = root / "index.html"
    index.write_text(doc, encoding="utf-8")
    return index
