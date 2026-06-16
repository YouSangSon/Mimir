from __future__ import annotations

import html
from pathlib import Path

from mimir.manifest.manifest import RunRecord
from mimir.report.i18n import DEFAULT_LANG, normalize_lang, t


def render_status_html(run: RunRecord, out_path: Path, lang: str = DEFAULT_LANG) -> None:
    lang = normalize_lang(lang)
    rows = []
    for r in run.results:
        status = t("status_ok", lang) if r.ok else t("status_fail", lang)
        detail = (
            html.escape(r.error or "")
            if not r.ok
            else t("status_detail_fetched_stored", lang, fetched=r.fetched, stored=r.stored)
        )
        rows.append(
            f"<tr><td>{html.escape(r.source)}</td><td>{status}</td><td>{detail}</td></tr>"
        )
    table = "\n".join(rows)
    headers = (
        f"<th>{t('status_table_header_source', lang)}</th>"
        f"<th>{t('status_table_header_status', lang)}</th>"
        f"<th>{t('status_table_header_detail', lang)}</th>"
    )
    doc = f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><title>{t("status_page_title", lang)}</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem}}
table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:.4rem .8rem}}
.dis{{color:#888;font-size:.85rem;margin-top:1rem}}</style></head>
<body>
<h1>{t("status_heading", lang)}</h1>
<p>{t("status_last_run", lang, time=run.ran_at.isoformat(), cadence=run.cadence.value)}</p>
<table><tr>{headers}</tr>
{table}
</table>
<p class="dis">{t("disclaimer_status", lang)}</p>
</body></html>"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, encoding="utf-8")
