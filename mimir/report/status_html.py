from __future__ import annotations

import html
from pathlib import Path

from mimir.manifest.manifest import RunRecord

DISCLAIMER = "For information only. This is not financial advice."


def render_status_html(run: RunRecord, out_path: Path) -> None:
    rows = []
    for r in run.results:
        status = "OK" if r.ok else "FAIL"
        detail = (
            html.escape(r.error or "") if not r.ok else f"fetched={r.fetched} stored={r.stored}"
        )
        rows.append(
            f"<tr><td>{html.escape(r.source)}</td><td>{status}</td><td>{detail}</td></tr>"
        )
    table = "\n".join(rows)
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Mimir status</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem}}
table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:.4rem .8rem}}
.dis{{color:#888;font-size:.85rem;margin-top:1rem}}</style></head>
<body>
<h1>Mimir — collection status</h1>
<p>Last run: {run.ran_at.isoformat()} ({run.cadence.value})</p>
<table><tr><th>source</th><th>status</th><th>detail</th></tr>
{table}
</table>
<p class="dis">{DISCLAIMER}</p>
</body></html>"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, encoding="utf-8")
