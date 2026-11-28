"""Global stylesheet generation for NetGuard AI.

Token-driven deep navy/charcoal engineering workstation surfaces.
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
    font-size: 13px;
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
    border: 0px solid transparent;
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
    background: {tokens.LINE_STRONG};
    min-height: 28px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical:hover {{
    background: {tokens.LINE_THRESHOLD};
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
    background: {tokens.LINE_STRONG};
    min-width: 28px;
    border-radius: 3px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {tokens.LINE_THRESHOLD};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: none;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* =========================================================================
   Text & Labels
   ========================================================================= */
QLabel {{
    background: transparent;
    color: {tokens.TEXT};
    border: 0px solid transparent;
    border-radius: 0px;
    padding: 0px;
    outline: none;
}}

/* =========================================================================
   Form Controls: Inputs, SpinBoxes, CheckBoxes & Combos
   ========================================================================= */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {tokens.RANGE_TRACK};
    border: 1px solid {tokens.LINE_STRONG};
    border-radius: {tokens.RADIUS_BUTTON}px;
    padding: 7px 12px;
    min-height: 22px;
    color: {tokens.TEXT};
    font-family: "{tokens.FONT_FAMILY_SANS}", "{tokens.FALLBACK_SANS}";
    font-size: 13px;
    selection-background-color: {tokens.ACCENT};
    selection-color: {tokens.ON_ACCENT};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {tokens.FOCUS_RING};
}}

QComboBox {{
    background-color: {tokens.SURFACE_INSET};
    border: 1px solid {tokens.LINE};
    border-radius: {tokens.RADIUS_BUTTON}px;
    padding: 7px 12px;
    color: {tokens.TEXT};
    font-size: 13px;
    min-height: 22px;
}}

QComboBox:hover {{
    border-color: {tokens.LINE_STRONG};
}}

QComboBox:focus {{
    border: 1px solid {tokens.FOCUS_RING};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center left;
    width: 24px;
    border: 0px solid transparent;
}}

QComboBox QAbstractItemView {{
    background-color: {tokens.SURFACE_ELEVATED};
    border: 1px solid {tokens.LINE_STRONG};
    border-radius: {tokens.RADIUS_BUTTON}px;
    color: {tokens.TEXT};
    selection-background-color: {tokens.SURFACE_SELECTED};
    selection-color: {tokens.TEXT};
    padding: 4px;
}}

QCheckBox {{
    spacing: 8px;
    color: {tokens.TEXT_SECONDARY};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {tokens.LINE_STRONG};
    background-color: {tokens.SURFACE_INSET};
}}

QCheckBox::indicator:checked {{
    background-color: {tokens.ACCENT};
    border-color: {tokens.ACCENT};
}}

/* =========================================================================
   Tables
   ========================================================================= */
QTableWidget, QTableView {{
    font-size: 14px;
    background-color: {tokens.SURFACE_INSET};
    border: 1px solid {tokens.LINE};
    border-radius: {tokens.RADIUS_INNER}px;
    gridline-color: {tokens.LINE};
    color: {tokens.TEXT};
    selection-background-color: {tokens.SURFACE_SELECTED};
    selection-color: {tokens.TEXT};
}}

QHeaderView::section {{
    background-color: {tokens.SURFACE};
    color: {tokens.TEXT_MUTED};
    border: 0px solid transparent;
    border-bottom: 1px solid {tokens.LINE};
    padding: 10px 12px;
    min-height: 46px;
    font-size: 13px;
    font-weight: 600;
}}

QCheckBox {{
    font-size: 12px;
    min-height: 28px;
}}

/* =========================================================================
   Dialogs & MessageBoxes
   ========================================================================= */
QMessageBox {{
    background-color: {tokens.BG_ELEVATED};
    color: {tokens.TEXT};
}}

QMessageBox QLabel {{
    color: {tokens.TEXT};
    font-size: 13px;
    min-width: 260px;
}}

QMessageBox QPushButton, QDialog QDialogButtonBox QPushButton {{
    background-color: {tokens.ACCENT};
    color: {tokens.ON_ACCENT};
    border: 1px solid {tokens.ACCENT};
    border-radius: {tokens.RADIUS_BUTTON}px;
    padding: 6px 18px;
    min-height: 34px;
    min-width: 88px;
    font-size: 13px;
    font-weight: 600;
}}

QMessageBox QPushButton:hover, QDialog QDialogButtonBox QPushButton:hover {{
    background-color: {tokens.ACCENT_HOVER};
    border-color: {tokens.ACCENT_HOVER};
}}

QMessageBox QPushButton:pressed, QDialog QDialogButtonBox QPushButton:pressed {{
    background-color: {tokens.ACCENT_PRESSED};
}}

/* =========================================================================
   Tooltips
   ========================================================================= */
QToolTip {{
    background-color: {tokens.SURFACE_ELEVATED};
    border: 1px solid {tokens.LINE_STRONG};
    border-radius: 6px;
    color: {tokens.TEXT};
    font-family: "{tokens.FONT_FAMILY_SANS}", "{tokens.FALLBACK_SANS}";
    font-size: 12px;
    padding: 6px 10px;
}}
"""
