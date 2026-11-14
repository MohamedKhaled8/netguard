"""Professional Dark Theme Stylesheet for NetGuard AI Desktop."""

DARK_THEME_QSS = """
QMainWindow, QWidget {
    background-color: #0b0f19;
    color: #e6edf3;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QFrame#Sidebar {
    background-color: #111625;
    border-right: 1px solid #1e2640;
    min-width: 210px;
    max-width: 210px;
}

QLabel#AppTitle {
    font-size: 16px;
    font-weight: bold;
    color: #58a6ff;
    padding: 16px 12px 4px 12px;
}

QLabel#AppSubtitle {
    font-size: 11px;
    color: #8b949e;
    padding: 0px 12px 16px 12px;
}

QPushButton.NavButton {
    background-color: transparent;
    color: #8b949e;
    text-align: left;
    padding: 10px 14px;
    border-radius: 6px;
    border: none;
    font-weight: 500;
    margin: 2px 8px;
}

QPushButton.NavButton:hover {
    background-color: #182238;
    color: #f0f6fc;
}

QPushButton.NavButton:checked {
    background-color: #1f2c4c;
    color: #58a6ff;
    font-weight: bold;
}

QFrame.Card {
    background-color: #111625;
    border: 1px solid #1e2640;
    border-radius: 8px;
    padding: 12px;
}

QLabel.CardTitle {
    font-size: 12px;
    color: #8b949e;
    font-weight: 500;
}

QLabel.CardValue {
    font-size: 24px;
    font-weight: bold;
    color: #ffffff;
}

QLabel.CardUnit {
    font-size: 12px;
    color: #8b949e;
}

QTableWidget {
    background-color: #111625;
    border: 1px solid #1e2640;
    border-radius: 6px;
    gridline-color: #1e2640;
    color: #e6edf3;
    selection-background-color: #1f2c4c;
}

QHeaderView::section {
    background-color: #161e33;
    color: #8b949e;
    padding: 6px;
    border: none;
    font-weight: bold;
}

QPushButton.PrimaryBtn {
    background-color: #238636;
    color: #ffffff;
    font-weight: bold;
    padding: 8px 16px;
    border-radius: 6px;
    border: none;
}

QPushButton.PrimaryBtn:hover {
    background-color: #2ea043;
}

QPushButton.DangerBtn {
    background-color: #da3633;
    color: #ffffff;
    font-weight: bold;
    padding: 8px 16px;
    border-radius: 6px;
    border: none;
}

QPushButton.DangerBtn:hover {
    background-color: #f85149;
}

QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background-color: #161e33;
    border: 1px solid #1e2640;
    border-radius: 6px;
    padding: 6px 10px;
    color: #ffffff;
}

QScrollBar:vertical {
    border: none;
    background: #0b0f19;
    width: 8px;
}

QScrollBar::handle:vertical {
    background: #212c47;
    min-height: 20px;
    border-radius: 4px;
}
"""
