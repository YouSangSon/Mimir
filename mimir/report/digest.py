from __future__ import annotations

from datetime import date

from mimir.analysis.schema import Insight
from mimir.report.i18n import DEFAULT_LANG, t

TOP_N = 5


def _stars(n: int) -> str:
    return "★" * n


def build_digest(
    insights: list[Insight],
    cadence: str,
    as_of: date,
    lang: str = DEFAULT_LANG,
    top: int = TOP_N,
) -> str:
    header = t("digest_header", lang, cadence=cadence, date=as_of.isoformat())
    disclaimer = t("disclaimer_report", lang)
    if not insights:
        return f"{header}\n{t('digest_empty', lang)}\n\n{disclaimer}"
    ordered = sorted(insights, key=lambda i: (-i.stars, i.symbol))[:top]
    lines = []
    for ins in ordered:
        reason = ins.reasons[0] if ins.reasons else ""
        direction = t(f"direction_{ins.direction.value}", lang)
        lines.append(f"{_stars(ins.stars)} {ins.symbol} {direction} — {reason}")
    return f"{header}\n" + "\n".join(lines) + f"\n\n{disclaimer}"
