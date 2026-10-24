from __future__ import annotations

import html

from mimir.doctor.report import Severity

"""Shared HTML-rendering primitives for the report layer.

Consolidates helpers that were duplicated across daily_report / dashboard /
doctor_html so a single source of truth (esp. the severity color map) cannot
drift between renderers. The plain-text digest keeps its own star glyphs.
"""


def esc(value: object) -> str:
    return html.escape(str(value))


def stars(n: int) -> str:
    return "★" * n + "☆" * (5 - n)


SEVERITY_COLOR: dict[Severity, str] = {
    Severity.OK: "#15803d",
    Severity.WARN: "#b45309",
    Severity.CRITICAL: "#b91c1c",
}

VIEWPORT_META = '<meta name="viewport" content="width=device-width, initial-scale=1">'

REPORT_CSS = """
 :root{color-scheme:dark light;--bg:#0b0f17;--fg:#e5e7eb;--muted:#9ca3af;
   --surface:#111827;--border:#475569;--link:#c4b5fd;--stars:#fbbf24;--event:#a5b4fc}
 @media(prefers-color-scheme:light){
   :root{--bg:#ffffff;--fg:#111827;--muted:#4b5563;--surface:#f3f4f6;
     --border:#9ca3af;--link:#5b21b6;--stars:#92400e;--event:#3730a3}}
 *{box-sizing:border-box}
 body{font-family:system-ui,-apple-system,sans-serif;margin:0 auto;max-width:72rem;
   padding:clamp(1rem,3vw,2rem);background:var(--bg);color:var(--fg);line-height:1.6;
   overflow-wrap:anywhere}
 h1{font-size:1.4rem} h2{font-size:1.1rem;margin-top:2rem}
 a{color:var(--link);text-underline-offset:.2em}
 :focus-visible{outline:3px solid var(--link);outline-offset:3px}
 .meta,.empty,.examples{color:var(--muted)} .meta{margin:.3rem 0 1rem}
 .card{background:var(--surface);border:1px solid var(--border);border-radius:10px;
   padding:1rem;margin:.6rem 0}
 .card-head{display:flex;flex-wrap:wrap;align-items:center;gap:.6rem}
 .sym{font-weight:700;min-width:0} .card .sym{font-size:1.1rem}
 .badge,.sev,.hb{color:#fff;border-radius:6px;padding:.1rem .5rem;font-size:.85rem;
   white-space:nowrap}
 .badges{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:1rem}
 .hb{padding:.2rem .6rem} .attn{margin-left:auto;color:var(--muted);font-size:.85rem}
 .stars{color:var(--stars);white-space:nowrap} .card .stars{font-size:1.1rem}
 .reasons{margin:.5rem 0 0;padding-left:1.3rem;font-size:.95rem}
 .examples{font-size:.85rem} .evt{color:var(--event);font-size:.95rem}
 .table-scroll{max-width:100%;overflow-x:auto;margin:.5rem 0}
 table{border-collapse:collapse;width:100%;min-width:32rem;font-size:.9rem}
 td,th{border:1px solid var(--border);padding:.5rem .7rem;text-align:left;vertical-align:top}
 th{color:var(--muted);font-weight:600;background:var(--surface);white-space:nowrap}
 td:first-child{overflow-wrap:normal}
 td:last-child{min-width:16rem}
 .dis{color:var(--muted);font-size:.85rem;margin-top:2rem;
   border-top:1px solid var(--border);padding-top:1rem}
 li{margin:.3rem 0}
"""


def render_table(headers: str, rows: str, label: str) -> str:
    """Wrap already-escaped cells in a named, keyboard-scrollable table region."""
    return (
        f'<div class="table-scroll" role="region" tabindex="0" aria-label="{esc(label)}">'
        f"<table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table></div>"
    )
