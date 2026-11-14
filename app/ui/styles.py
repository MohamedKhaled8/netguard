"""High-End Dark Theme Stylesheet for NetGuard AI Desktop.

Follows ui-ux-pro-max design guidelines:
- Dark mode palette with #0c101c root background and #111625 surface cards.
- High-contrast, crystal-clear typography with native Arabic support (Segoe UI, Cairo, Tahoma).
- Refined borders, subtle glows, and deliberate interactive hover states.
"""

DARK_THEME_QSS = """
QMainWindow, QWidget {
    background-color: #0c101c;
    color: #e6edf3;
    font-family: "Segoe UI", "Tahoma", "Cairo", -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    font-size: 13px;
}

/* Sidebar Navigation */
QFrame#Sidebar {
    background-color: #111625;
    border-right: 1px solid #1c2438;
    border-left: 1px solid #1c2438;
    min-width: 230px;
    max-width: 230px;
}

QLabel#AppTitle {
    font-size: 18px;
    font-weight: 800;
    color: #58a6ff;
    padding: 18px 14px 4px 14px;
    letter-spacing: 0.5px;
}

QLabel#AppSubtitle {
    font-size: 12px;
    color: #8b949e;
    padding: 0px 14px 16px 14px;
}

QPushButton.NavButton {
    background-color: transparent;
    color: #9aa7b8;
    text-align: left;
    padding: 12px 16px;
    border-radius: 8px;
    border: none;
    font-size: 13px;
    font-weight: 600;
    margin: 2px 8px;
}

QPushButton.NavButton:hover {
    background-color: #172136;
    color: #ffffff;
}

QPushButton.NavButton:checked {
    background-color: #1c2b4a;
    color: #58a6ff;
    font-weight: 700;
    border: 1px solid #29426f;
}

/* Master Cards */
QFrame.Card {
    background-color: #111625;
    border: 1px solid #1c253b;
    border-radius: 10px;
    padding: 14px;
}

QFrame.Card:hover {
    border-color: #2b3956;
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
    color: #58a6ff;
    font-weight: 600;
}

QLabel.CardDesc {
    font-size: 11px;
    color: #6e7681;
    margin-top: 4px;
}

/* Master Hero Status Banner */
QFrame#HeroBanner {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #101c2e, stop:1 #111625);
    border: 1px solid #233453;
    border-radius: 12px;
    padding: 16px;
}

/* Buttons */
QPushButton.HeroActionBtn {
    background-color: #1f6feb;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 22px;
    border-radius: 8px;
    border: 1px solid #388bfd;
}

QPushButton.HeroActionBtn:hover {
    background-color: #388bfd;
}

QPushButton.HeroActionBtn:pressed {
    background-color: #1a56b7;
}

QPushButton.SuccessBtn {
    background-color: #238636;
    color: #ffffff;
    font-weight: 700;
    padding: 9px 18px;
    border-radius: 7px;
    border: none;
}

QPushButton.SuccessBtn:hover {
    background-color: #2ea043;
}

QPushButton.SecondaryBtn {
    background-color: #1c253b;
    color: #c9d1d9;
    font-weight: 600;
    padding: 8px 16px;
    border-radius: 7px;
    border: 1px solid #2a3754;
}

QPushButton.SecondaryBtn:hover {
    background-color: #24324f;
    color: #ffffff;
}

/* Language Toggle Button */
QPushButton#LangToggleBtn {
    background-color: #1c263e;
    color: #58a6ff;
    font-weight: 700;
    font-size: 12px;
    padding: 6px 14px;
    border-radius: 16px;
    border: 1px solid #2c3c61;
}

QPushButton#LangToggleBtn:hover {
    background-color: #27375a;
    color: #ffffff;
}

/* Tables */
QTableWidget {
    background-color: #111625;
    border: 1px solid #1c253b;
    border-radius: 8px;
    gridline-color: #182033;
    color: #e6edf3;
    selection-background-color: #1c2b4a;
    font-size: 12px;
}

QHeaderView::section {
    background-color: #151d30;
    color: #8b949e;
    padding: 8px;
    border: none;
    font-weight: 700;
    font-size: 11px;
}

/* Inputs & Combos */
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background-color: #161e30;
    border: 1px solid #24324e;
    border-radius: 6px;
    padding: 6px 10px;
    color: #ffffff;
    font-size: 13px;
}

QComboBox::drop-down {
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #161e30;
    border: 1px solid #24324e;
    color: #ffffff;
    selection-background-color: #1f6feb;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #0c101c;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #232f48;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #34476e;
}
"""
