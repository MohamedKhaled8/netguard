"""Wheel event forwarder ensuring smooth vertical page scrolling over tables and charts (L2)."""

from __future__ import annotations
from typing import Optional
import shiboken6
from PySide6.QtCore import QObject, QEvent, Qt
from PySide6.QtWidgets import QWidget, QScrollArea, QSizePolicy, QTableWidget
from app.ui import tokens


def _is_valid(obj: Optional[QObject]) -> bool:
    """Check if QObject reference and underlying C++ instance are both valid."""
    try:
        return obj is not None and shiboken6.isValid(obj)
    except (RuntimeError, ReferenceError, Exception):
        return False


class WheelForwarder(QObject):
    """Event filter that delegates wheel events smoothly to the enclosing page vertical scrollbar."""

    def __init__(self, target_scroll: QScrollArea, parent: Optional[QObject] = None) -> None:
        super().__init__(parent or target_scroll)
        self.target_scroll = target_scroll

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        try:
            if not _is_valid(watched) or event is None:
                return False
            if event.type() == QEvent.Wheel:
                target = getattr(self, "target_scroll", None)
                if _is_valid(target):
                    target.wheelEvent(event)
                    return True
        except (RuntimeError, ReferenceError, Exception):
            pass
        return False


def make_scroll_transparent(widget: QWidget, target_scroll: QScrollArea) -> None:
    """Make a widget (and its viewport if an abstract item view) transparent to wheel scrolling."""
    forwarder = WheelForwarder(target_scroll, parent=widget)
    widget.installEventFilter(forwarder)
    if hasattr(widget, "viewport") and callable(widget.viewport):
        vp = widget.viewport()
        if vp:
            vp.installEventFilter(forwarder)


def fit_table_to_content(table: QTableWidget, max_rows_before_scroll: int = 15) -> None:
    """Give table its natural content height inside the page scroll area."""
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    base_font = tokens.get_sans_font(14, 400)
    if table.font().pixelSize() < 14:
        table.setFont(base_font)
    table.verticalHeader().setMinimumSectionSize(38)
    for r in range(table.rowCount()):
        for c in range(table.columnCount()):
            it = table.item(r, c)
            if it is not None:
                f = it.font()
                if f.pixelSize() < 14 and f.pointSize() <= 10:
                    it.setFont(base_font)
    header_h = table.horizontalHeader().height()
    if header_h <= 0:
        header_h = 46
    def_h = max(38, table.verticalHeader().defaultSectionSize())
    total_rows = table.rowCount()
    rows_h = sum(max(38, table.rowHeight(r)) if table.rowHeight(r) > 0 else def_h for r in range(total_rows))
    total_h = header_h + rows_h + 12
    table.setMinimumHeight(0)
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    table.setFixedHeight(max(total_h, 64))
    table.updateGeometry()
    p = table.parentWidget()
    for _ in range(5):
        if p is None:
            break
        p.updateGeometry()
        if p.layout() is not None:
            p.layout().activate()
        if isinstance(p, QScrollArea) and p.widget() is not None:
            p.widget().adjustSize()
            break
        p = p.parentWidget()
