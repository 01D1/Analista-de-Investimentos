"""
Shared dark theme CSS for scanner_quant_profit_b3 pages.

DEPRECATED — Use src.ui.styles.PREMIUM_CSS directly.
This file is kept for backward compatibility only.

Canonical source: src.ui.styles.PREMIUM_CSS
Token source:    src.ui.design_tokens.css
"""

# Re-export for backward compat
try:
    from src.ui.styles import PREMIUM_CSS as DARK_CSS  # noqa: F401
except Exception:
    DARK_CSS: str = (
        "<!-- styles unavailable — use src.ui.styles.PREMIUM_CSS directly -->"
    )