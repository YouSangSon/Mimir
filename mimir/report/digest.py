from __future__ import annotations

from datetime import date

from mimir.analysis.schema import DISCLAIMER, Insight

TOP_N = 5


def _stars(n: int) -> str:
    return "★" * n


def build_digest(insights: list[Insight], cadence: str, as_of: date, top: int = TOP_N) -> str:
    header = f"🧭 Mimir {cadence} — {as_of.isoformat()}"
    if not insights:
        return f"{header}\n특이사항 없음.\n\n{DISCLAIMER}"
    ordered = sorted(insights, key=lambda i: (-i.stars, i.symbol))[:top]
    lines = []
    for ins in ordered:
        reason = ins.reasons[0] if ins.reasons else ""
        lines.append(f"{_stars(ins.stars)} {ins.symbol} {ins.direction.value} — {reason}")
    return f"{header}\n" + "\n".join(lines) + f"\n\n{DISCLAIMER}"
