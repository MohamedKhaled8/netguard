"""Global stylesheet generation for NetGuard AI.

100% token-driven, dark warm-neutral graphite (#0E1012).
No glow, no neon, no gradients, flat surfaces separated by 1px hairlines.
"""

from __future__ import annotations
from app.ui import tokens

DARK_THEME_QSS = f"""
/* =========================================================================
   Base Window & Surfaces
   ========================================================================= */
QMainWindow, QDialog {{
    background-color: {tokens.BG};
    color: {tokens.TEXT};
    font-family: "{tokens.FONT_FAMILY_SANS}", "{tokens.FALLBACK_SANS}";
    font-size: 14px;
}}

QWidget {{
    color: {tokens.TEXT};
    font-family: "{tokens.FONT_FAMILY_SANS}", "{tokens.FALLBACK_SANS}";
}}

QWidget#CentralWidget {{
    background-color: {tokens.BG};
}}

/* =========================================================================
   Scroll Areas & ScrollBars (Clean Minimal Hairline)
   ========================================================================= */
QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {tokens.LINE};
    min-height: 24px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical:hover {{
    background: {tokens.LINE_STRONG};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: none;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: {tokens.LINE};
    min-width: 24px;
    border-radius: 3px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {tokens.LINE_STRONG};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: none;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* =========================================================================
   Text & Labels (Strictly No Borders on Text)
   ========================================================================= */
QLabel {{
    background: transparent;
    color: {tokens.TEXT};
    border: none;
    border-radius: 0px;
}}

/* =========================================================================
   Form Controls: Inputs & Combos
   ========================================================================= */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {tokens.BG};
    border: 1px solid {tokens.LINE};
    border-radius: {tokens.RADIUS_BUTTON}px;
    padding: 8px 12px;
    color: {tokens.TEXT};
    font-family: "{tokens.FONT_FAMILY_SANS}", "{tokens.FALLBACK_SANS}";
    font-size: 13px;
    selection-background-color: {tokens.SURFACE_HOVER};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {tokens.FOCUS_RING};
}}

QComboBox {{
    background-color: {tokens.BG};
    border: 1px solid {tokens.LINE};
    border-radius: {tokens.RADIUS_BUTTON}px;
    padding: 8px 12px;
    color: {tokens.TEXT};
    font-size: 13px;
    min-height: 22px;
}}

QComboBox:focus {{
    border: 1px solid {tokens.FOCUS_RING};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top left;
    width: 24px;
    border-left: none;
}}

QComboBox QAbstractItemView {{
    background-color: {tokens.SURFACE};
    border: 1px solid {tokens.LINE};
    border-radius: {tokens.RADIUS_BUTTON}px;
    color: {tokens.TEXT};
    selection-background-color: {tokens.SURFACE_HOVER};
    selection-color: {tokens.TEXT};
    padding: 4px;
}}

/* =========================================================================
   Tables
   ========================================================================= */
QTableWidget, QTableView {{
    background-color: transparent;
    border: none;
    gridline-color: {tokens.LINE};
    color: {tokens.TEXT};
    selection-background-color: {tokens.SURFACE_HOVER};
    selection-color: {tokens.TEXT};
}}

QHeaderView::section {{
    background-color: transparent;
    color: {tokens.TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {tokens.LINE};
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 500;
}}

/* =========================================================================
   Tooltips
   ========================================================================= */
QToolTip {{
    background-color: {tokens.SURFACE};
    border: 1px solid {tokens.LINE};
    border-radius: 6px;
    color: {tokens.TEXT};
    font-family: "{tokens.FONT_FAMILY_SANS}", "{tokens.FALLBACK_SANS}";
    font-size: 12px;
    padding: 6px 10px;
}}
"""
