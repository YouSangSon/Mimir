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
    Severity.OK: "#16a34a",
    Severity.WARN: "#d97706",
    Severity.CRITICAL: "#dc2626",
}
