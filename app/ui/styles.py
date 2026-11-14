"""Executive Dark Minimalist Stylesheet for NetGuard AI Desktop.

Inspired by Dribbble top-tier desktop clients (WARP, Linear, Raycast, CleanMyMac):
- Deep OLED obsidian canvas (#07090e) with subtle slate containers (#0e1320).
- Pure hairline dividers (rgba(255, 255, 255, 0.08)) for depth through layering.
- Vibrant high-contrast status colors: Electric Emerald (#00e599), Cyan (#00d2ff), Amber (#e3b341), Coral (#f85149).
- Clean, accessible typography with native Arabic Segoe UI / Cairo support.
"""

DARK_THEME_QSS = """
QMainWindow, QWidget {
    background-color: #07090e;
    color: #e6edf3;
    font-family: "Segoe UI", "Tahoma", "Cairo", -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    font-size: 13px;
}

/* Header & Top Navigation Bar */
QFrame#TopHeader {
    background-color: #0d121e;
    border-bottom: 1px solid #161e30;
    min-height: 58px;
    max-height: 58px;
    padding: 0px 18px;
}

QLabel#BrandTitle {
    font-size: 16px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.5px;
}

QLabel#BrandBadge {
    font-size: 10px;
    font-weight: 700;
    color: #00e599;
    background-color: #0d221a;
    border: 1px solid #14402e;
    border-radius: 6px;
    padding: 2px 7px;
    margin-right: 6px;
}

/* Segmented Top Navigation Pills */
QPushButton.NavPill {
    background-color: transparent;
    color: #8b949e;
    padding: 7px 14px;
    border-radius: 8px;
    border: none;
    font-size: 12px;
    font-weight: 600;
    margin: 0px 2px;
}

QPushButton.NavPill:hover {
    background-color: #151d2e;
    color: #ffffff;
}

QPushButton.NavPill:checked {
    background-color: #1a253a;
    color: #00d2ff;
    font-weight: 700;
    border: 1px solid #283959;
}

/* Master Cards & Bento Containers */
QFrame.Card {
    background-color: #0c101a;
    border: 1px solid #161f30;
    border-radius: 12px;
    padding: 12px;
}

QFrame.Card:hover {
    border-color: #23314c;
    background-color: #0e1422;
}

QLabel.CardTitle {
    font-size: 12px;
    color: #8b949e;
    font-weight: 600;
}

QLabel.CardValue {
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
    margin: 2px 0px;
}

QLabel.CardUnit {
    font-size: 11px;
    color: #00d2ff;
    font-weight: 600;
}

QLabel.CardDesc {
    font-size: 11px;
    color: #6e7681;
    margin-top: 4px;
    line-height: 1.4;
}

/* Action Buttons */
QPushButton.PrimaryBtn {
    background-color: #1f6feb;
    color: #ffffff;
    font-weight: 700;
    padding: 9px 18px;
    border-radius: 8px;
    border: 1px solid #388bfd;
}

QPushButton.PrimaryBtn:hover {
    background-color: #388bfd;
}

QPushButton.SuccessBtn {
    background-color: #00e599;
    color: #07090e;
    font-weight: 800;
    padding: 9px 18px;
    border-radius: 8px;
    border: none;
}

QPushButton.SuccessBtn:hover {
    background-color: #1affb0;
}

/* Tables */
QTableWidget {
    background-color: #0c101a;
    border: 1px solid #161f30;
    border-radius: 10px;
    gridline-color: #141c2c;
    color: #e6edf3;
    selection-background-color: #19253b;
    font-size: 12px;
}

QHeaderView::section {
    background-color: #0f1524;
    color: #8b949e;
    padding: 9px;
    border: none;
    font-weight: 700;
    font-size: 11px;
}

/* Inputs & Form Controls */
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background-color: #111726;
    border: 1px solid #1f2b44;
    border-radius: 6px;
    padding: 7px 10px;
    color: #ffffff;
    font-size: 13px;
}

QComboBox QAbstractItemView {
    background-color: #111726;
    border: 1px solid #1f2b44;
    color: #ffffff;
    selection-background-color: #1f6feb;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #1c263c;
    min-height: 20px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #2a3a5c;
}
"""
