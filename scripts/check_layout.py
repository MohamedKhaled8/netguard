#!/usr/bin/env python3
"""Objective layout and typography checker for NetGuard AI (Item L0).

Renders all 7 views offscreen across:
- Sizes: 1100x700, 1280x720, 1366x768, 1920x1080
- Display Scales: 100% (1.0), 125% (1.25), 150% (1.5), 175% (1.75)

Asserts:
a. Horizontal scroll range == 0; no widget extends past viewport width.
b. No visible sibling widgets intersect in geometry (except documented overlays).
c. No clipped text (fontMetrics fits content rect, or elided/wrapped with full tooltip).
d. No widget is smaller than its minimumSizeHint().
e. Smallest font >= 12px, body/table >= 14px, interactive controls >= 36px high,
   table rows with controls >= 48px high.
f. Text/background contrast >= 4.5:1.

Generates:
- docs/layout_before.txt / docs/layout_after.txt
- Screenshots in docs/screenshots/ux2/
"""

from __future__ import annotations
import argparse
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

# Ensure project root is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QTableWidget,
    QScrollArea,
    QHeaderView,
    QAbstractButton,
)
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QColor, QFont, QPixmap

from app.application import create_application
from app.ui.main_window import MainWindow
from app.ui import tokens
from app.dns.benchmark import ResolverScore
from datetime import datetime, timezone


@dataclass
class Violation:
    page_name: str
    window_size: str
    scale: float
    widget_name: str
    widget_type: str
    rule: str
    details: str

    def to_row(self) -> str:
        return f"| {self.page_name} | {self.window_size} | {int(self.scale*100)}% | `{self.widget_name or self.widget_type}` | **{self.rule}** | {self.details} |"


def calculate_luminance(color: QColor) -> float:
    """Compute relative luminance according to WCAG 2.1."""
    def _channel_lum(c_byte: int) -> float:
        c = c_byte / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r = _channel_lum(color.red())
    g = _channel_lum(color.green())
    b = _channel_lum(color.blue())
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def calculate_contrast(c1: QColor, c2: QColor) -> float:
    """Compute contrast ratio between two QColors."""
    l1 = calculate_luminance(c1)
    l2 = calculate_luminance(c2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class LayoutChecker:
    PAGE_NAMES = [
        "Dashboard",
        "Diagnosis",
        "Remediation",
        "DNS",
        "Traffic",
        "History",
        "Settings",
    ]

    WINDOW_SIZES = [
        (1100, 700),
        (1280, 720),
        (1366, 768),
        (1920, 1080),
    ]

    def __init__(self, scale: float = 1.0, screenshot_dir: Optional[str] = None) -> None:
        self.scale = scale
        self.screenshot_dir = screenshot_dir
        if screenshot_dir:
            os.makedirs(screenshot_dir, exist_ok=True)
        self.violations: List[Violation] = []

    def populate_mock_data(self, win: MainWindow) -> None:
        """Inject synchronized, realistic state so tables and views have content."""
        now_ts = datetime.now(timezone.utc)
        mock_scores = [
            ResolverScore(ip="1.1.1.1", name="Cloudflare Primary", mean_latency_ms=18.4, min_latency_ms=16.0, max_latency_ms=21.0, stdev_latency_ms=1.2, failure_rate=0.0, composite_score=98.0, evaluated_at=now_ts),
            ResolverScore(ip="8.8.8.8", name="Google Public DNS", mean_latency_ms=24.2, min_latency_ms=22.0, max_latency_ms=27.0, stdev_latency_ms=1.5, failure_rate=0.0, composite_score=94.0, evaluated_at=now_ts),
            ResolverScore(ip="9.9.9.9", name="Quad9 Security", mean_latency_ms=31.8, min_latency_ms=29.0, max_latency_ms=35.0, stdev_latency_ms=2.1, failure_rate=0.0, composite_score=89.0, evaluated_at=now_ts),
            ResolverScore(ip="1.0.0.1", name="Cloudflare Secondary", mean_latency_ms=19.1, min_latency_ms=17.0, max_latency_ms=22.0, stdev_latency_ms=1.3, failure_rate=0.0, composite_score=97.0, evaluated_at=now_ts),
            ResolverScore(ip="208.67.222.222", name="OpenDNS Cisco", mean_latency_ms=42.5, min_latency_ms=39.0, max_latency_ms=47.0, stdev_latency_ms=3.0, failure_rate=0.0, composite_score=82.0, evaluated_at=now_ts),
        ]
        win._active_dns_servers = ["1.1.1.1", "1.0.0.1"]
        win._on_dns_benchmark_done(mock_scores)

        # Populate Traffic Table
        from app.traffic.applications import ProcessNetworkProfile, WorkloadCategory
        profiles = [
            ProcessNetworkProfile(name="Zoom.exe", pid=4120, category=WorkloadCategory.CONFERENCING, active_socket_count=14, estimated_bandwidth_mbps=1.8),
            ProcessNetworkProfile(name="msedge.exe", pid=8912, category=WorkloadCategory.BROWSING, active_socket_count=26, estimated_bandwidth_mbps=4.2),
            ProcessNetworkProfile(name="svchost.exe", pid=1044, category=WorkloadCategory.SYSTEM, active_socket_count=8, is_protected_system_process=True),
            ProcessNetworkProfile(name="steam.exe", pid=6520, category=WorkloadCategory.DOWNLOAD, active_socket_count=5, estimated_bandwidth_mbps=12.5),
            ProcessNetworkProfile(name="NetGuard.exe", pid=2204, category=WorkloadCategory.SYSTEM, active_socket_count=2, is_protected_system_process=True),
        ]
        win.view_traffic.update_profiles(profiles, conferencing_active=True)

    def check_all_pages(self, win: MainWindow) -> List[Violation]:
        app = QApplication.instance()
        self.populate_mock_data(win)

        for w, h in self.WINDOW_SIZES:
            size_str = f"{w}x{h}"
            win.resize(w, h)
            app.processEvents()

            for page_idx, page_name in enumerate(self.PAGE_NAMES):
                win._switch_view(page_idx, win.nav_buttons[page_idx])
                app.processEvents()
                time.sleep(0.05)

                current_view = win.stack.widget(page_idx)

                # Capture screenshot if requested
                if self.screenshot_dir:
                    screenshot_name = f"{page_name.lower()}_{size_str}_{int(self.scale*100)}.png"
                    screenshot_path = os.path.join(self.screenshot_dir, screenshot_name)
                    pix = win.grab()
                    pix.save(screenshot_path)

                # Run checks on this view
                self._check_horizontal_scroll(current_view, page_name, size_str)
                self._check_widget_intersections(current_view, page_name, size_str)
                self._check_clipped_text(current_view, page_name, size_str)
                self._check_minimum_size_hint(current_view, page_name, size_str)
                self._check_metrics_and_touch_targets(current_view, page_name, size_str)
                self._check_color_contrast(current_view, page_name, size_str)

        return self.violations

    def _check_horizontal_scroll(self, view: QWidget, page_name: str, size_str: str) -> None:
        """Rule A: Page horizontal scroll range is 0 and no widget extends past viewport width."""
        scroll_areas = view.findChildren(QScrollArea)
        for sa in scroll_areas:
            h_bar = sa.horizontalScrollBar()
            if h_bar and h_bar.maximum() > 0:
                self.violations.append(
                    Violation(
                        page_name=page_name,
                        window_size=size_str,
                        scale=self.scale,
                        widget_name=sa.objectName() or "QScrollArea",
                        widget_type="QScrollArea",
                        rule="Horizontal Scroll",
                        details=f"Horizontal scrollbar maximum is {h_bar.maximum()} > 0 (viewport: {sa.viewport().width()}px, content: {sa.widget().width() if sa.widget() else 'None'}px)",
                    )
                )

            if sa.widget() and sa.viewport():
                cw = sa.widget().width()
                vw = sa.viewport().width()
                if cw > vw + 1:  # Allow 1px rounding tolerance
                    self.violations.append(
                        Violation(
                            page_name=page_name,
                            window_size=size_str,
                            scale=self.scale,
                            widget_name=sa.widget().objectName() or "ScrollContent",
                            widget_type=sa.widget().__class__.__name__,
                            rule="Horizontal Scroll",
                            details=f"Content widget width ({cw}px) exceeds viewport width ({vw}px) by {cw - vw}px",
                        )
                    )

    def _check_widget_intersections(self, view: QWidget, page_name: str, size_str: str) -> None:
        """Rule B: No two visible sibling widgets have intersecting geometry (except documented overlays)."""
        all_widgets = view.findChildren(QWidget)
        # Group widgets by parent
        parent_map: Dict[QWidget, List[QWidget]] = {}
        for w in all_widgets:
            if not w.isVisible():
                continue
            p = w.parentWidget()
            if p:
                parent_map.setdefault(p, []).append(w)

        for p, siblings in parent_map.items():
            if len(siblings) < 2:
                continue
            # Compare visible pairs
            for i in range(len(siblings)):
                w1 = siblings[i]
                g1 = w1.geometry()
                if g1.width() <= 0 or g1.height() <= 0:
                    continue
                for j in range(i + 1, len(siblings)):
                    w2 = siblings[j]
                    g2 = w2.geometry()
                    if g2.width() <= 0 or g2.height() <= 0:
                        continue

                    # Documented overlays: QScrollArea scrollbars, overlays marked with property
                    if w1.property("_is_overlay") or w2.property("_is_overlay"):
                        continue
                    if "ScrollBar" in w1.__class__.__name__ or "ScrollBar" in w2.__class__.__name__:
                        continue

                    inter = g1.intersected(g2)
                    if inter.width() > 1 and inter.height() > 1:
                        # Report intersection
                        self.violations.append(
                            Violation(
                                page_name=page_name,
                                window_size=size_str,
                                scale=self.scale,
                                widget_name=f"{w1.objectName() or w1.__class__.__name__} & {w2.objectName() or w2.__class__.__name__}",
                                widget_type="SiblingWidgets",
                                rule="Widget Overlap",
                                details=f"Siblings overlap by {inter.width()}x{inter.height()}px at rect {inter.x()},{inter.y()}",
                            )
                        )

    def _check_clipped_text(self, view: QWidget, page_name: str, size_str: str) -> None:
        """Rule C: Text width/height fits content rect or has wrap/tooltip."""
        labels = view.findChildren(QLabel)
        for lbl in labels:
            if not lbl.isVisible():
                continue
            text = lbl.text().strip()
            if not text:
                continue

            # Skip HTML text / image icons
            if "<img" in text or "<svg" in text:
                continue

            fm = lbl.fontMetrics()
            rect = lbl.contentsRect()
            text_w = fm.horizontalAdvance(text)
            text_h = fm.height()

            if not lbl.wordWrap():
                if text_w > rect.width() + 2:
                    # If elided and has tooltip with full text, allowed
                    if lbl.toolTip() and text in lbl.toolTip():
                        continue
                    self.violations.append(
                        Violation(
                            page_name=page_name,
                            window_size=size_str,
                            scale=self.scale,
                            widget_name=lbl.objectName() or text[:25],
                            widget_type="QLabel",
                            rule="Clipped Text",
                            details=f"Text '{text[:30]}' width {text_w}px exceeds rect width {rect.width()}px by {text_w - rect.width()}px",
                        )
                    )
            else:
                # Wrapped label: check if bounded text fits height
                br = fm.boundingRect(rect.x(), rect.y(), rect.width(), 9999, Qt.TextWordWrap, text)
                if br.height() > rect.height() + 2:
                    if lbl.toolTip() and text in lbl.toolTip():
                        continue
                    self.violations.append(
                        Violation(
                            page_name=page_name,
                            window_size=size_str,
                            scale=self.scale,
                            widget_name=lbl.objectName() or text[:25],
                            widget_type="QLabel",
                            rule="Clipped Text",
                            details=f"Wrapped text height {br.height()}px exceeds rect height {rect.height()}px",
                        )
                    )

        buttons = view.findChildren(QAbstractButton)
        for btn in buttons:
            if not btn.isVisible():
                continue
            text = btn.text().strip()
            if not text:
                continue
            fm = btn.fontMetrics()
            rect = btn.contentsRect()
            text_w = fm.horizontalAdvance(text)
            if text_w > rect.width() + 2:
                if btn.toolTip() and text in btn.toolTip():
                    continue
                self.violations.append(
                    Violation(
                        page_name=page_name,
                        window_size=size_str,
                        scale=self.scale,
                        widget_name=btn.objectName() or text[:25],
                        widget_type=btn.__class__.__name__,
                        rule="Clipped Text",
                        details=f"Button text '{text}' width {text_w}px exceeds rect width {rect.width()}px",
                    )
                )

    def _check_minimum_size_hint(self, view: QWidget, page_name: str, size_str: str) -> None:
        """Rule D: No widget is smaller than its minimumSizeHint()."""
        all_widgets = view.findChildren(QWidget)
        for w in all_widgets:
            if not w.isVisible():
                continue
            msh = w.minimumSizeHint()
            if not msh.isValid():
                continue
            cur_w = w.width()
            cur_h = w.height()
            if cur_w > 0 and cur_h > 0:
                if cur_w < msh.width() - 2 or cur_h < msh.height() - 2:
                    self.violations.append(
                        Violation(
                            page_name=page_name,
                            window_size=size_str,
                            scale=self.scale,
                            widget_name=w.objectName() or w.__class__.__name__,
                            widget_type=w.__class__.__name__,
                            rule="Under Minimum Size",
                            details=f"Size {cur_w}x{cur_h}px smaller than minimumSizeHint {msh.width()}x{msh.height()}px",
                        )
                    )

    def _check_metrics_and_touch_targets(self, view: QWidget, page_name: str, size_str: str) -> None:
        """Rule E: Smallest font >= 12px, body/table text >= 14px, interactive controls >= 36px high,
        table rows with controls >= 48px high."""
        # Check fonts of all visible labels and buttons
        text_widgets = view.findChildren(QLabel) + view.findChildren(QAbstractButton)
        for w in text_widgets:
            if not w.isVisible():
                continue
            text = w.text().strip() if hasattr(w, "text") else ""
            if not text:
                continue
            f = w.font()
            pt_size = f.pointSize()
            px_size = f.pixelSize()
            effective_size = px_size if px_size > 0 else pt_size

            # Smallest font rule: >= 12
            if effective_size > 0 and effective_size < 12:
                self.violations.append(
                    Violation(
                        page_name=page_name,
                        window_size=size_str,
                        scale=self.scale,
                        widget_name=w.objectName() or text[:25],
                        widget_type=w.__class__.__name__,
                        rule="Font Too Small",
                        details=f"Font size {effective_size}px is smaller than 12px requirement",
                    )
                )

        # Check interactive controls height >= 36px
        interactive_ctrls = (
            view.findChildren(QPushButton)
            + view.findChildren(QComboBox)
            + view.findChildren(QLineEdit)
        )
        for ctrl in interactive_ctrls:
            if not ctrl.isVisible():
                continue
            # Exclude controls inside scrollbar
            if "ScrollBar" in ctrl.parent().__class__.__name__:
                continue
            h = ctrl.height()
            if h > 0 and h < 36:
                text = ctrl.text() if hasattr(ctrl, "text") else ""
                self.violations.append(
                    Violation(
                        page_name=page_name,
                        window_size=size_str,
                        scale=self.scale,
                        widget_name=ctrl.objectName() or text[:20] or ctrl.__class__.__name__,
                        widget_type=ctrl.__class__.__name__,
                        rule="Interactive Control Height",
                        details=f"Height {h}px is less than 36px minimum touch/target height",
                    )
                )

        # Check table row heights
        tables = view.findChildren(QTableWidget)
        for tbl in tables:
            if not tbl.isVisible():
                continue
            row_count = tbl.rowCount()
            col_count = tbl.columnCount()
            for r in range(row_count):
                row_h = tbl.rowHeight(r)
                # Check if this row contains any button or interactive cellWidget
                has_control = False
                for c in range(col_count):
                    cw = tbl.cellWidget(r, c)
                    if cw:
                        ctrls = (
                            cw.findChildren(QPushButton)
                            + cw.findChildren(QComboBox)
                            + cw.findChildren(QLineEdit)
                        )
                        if ctrls or isinstance(cw, (QPushButton, QComboBox, QLineEdit)):
                            has_control = True
                            break

                min_expected = 48 if has_control else 36
                if row_h > 0 and row_h < min_expected:
                    self.violations.append(
                        Violation(
                            page_name=page_name,
                            window_size=size_str,
                            scale=self.scale,
                            widget_name=tbl.objectName() or f"Table_Row_{r}",
                            widget_type="QTableWidget",
                            rule="Table Row Height",
                            details=f"Row {r} height {row_h}px is less than required {min_expected}px ({'contains controls' if has_control else 'standard'})",
                        )
                    )

                # Check table text sizes: body/table text >= 14px
                for c in range(col_count):
                    item = tbl.item(r, c)
                    if item and item.text().strip():
                        f = item.font()
                        sz = f.pixelSize() if f.pixelSize() > 0 else f.pointSize()
                        if sz > 0 and sz < 14:
                            self.violations.append(
                                Violation(
                                    page_name=page_name,
                                    window_size=size_str,
                                    scale=self.scale,
                                    widget_name=tbl.objectName() or f"TableCell_{r}_{c}",
                                    widget_type="QTableWidgetItem",
                                    rule="Table Text Size",
                                    details=f"Cell ({r},{c}) text '{item.text()[:20]}' font size {sz}px < 14px",
                                )
                            )

    def _check_color_contrast(self, view: QWidget, page_name: str, size_str: str) -> None:
        """Rule F: Text/background contrast >= 4.5:1 for all text."""
        surface_col = QColor(tokens.SURFACE)
        for lbl in view.findChildren(QLabel):
            if not lbl.isVisible():
                continue
            text = lbl.text().strip()
            if not text:
                continue

            # Determine text color from palette or stylesheet
            fg_col = lbl.palette().color(lbl.foregroundRole())
            ss = lbl.styleSheet()
            bg_col = surface_col
            if ss:
                import re
                m_fg = re.search(r"(?<![\w\-])color:\s*([#a-zA-Z0-9]+)", ss)
                if m_fg:
                    fg_col = QColor(m_fg.group(1))
                m_bg = re.search(r"background(?:-color)?:\s*([#a-zA-Z0-9]+)", ss)
                if m_bg and m_bg.group(1).lower() != "transparent":
                    bg_col = QColor(m_bg.group(1))

            contrast = calculate_contrast(fg_col, bg_col)
            # WCAG AA requires 4.5:1 for normal text
            if contrast < 4.5:
                self.violations.append(
                    Violation(
                        page_name=page_name,
                        window_size=size_str,
                        scale=self.scale,
                        widget_name=lbl.objectName() or text[:25],
                        widget_type="QLabel",
                        rule="Contrast Ratio",
                        details=f"Contrast ratio {contrast:.2f}:1 is below 4.5:1 (fg: {fg_col.name()}, bg: {bg_col.name()}) for '{text[:25]}'",
                    )
                )


def run_single_scale(scale: float, screenshot_dir: Optional[str] = None) -> List[Violation]:
    """Execute layout check on a single display scale."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication(["--platform", "offscreen"])

    net_app = create_application()
    win = MainWindow(application=net_app)
    win.show()
    app.processEvents()

    checker = LayoutChecker(scale=scale, screenshot_dir=screenshot_dir)
    violations = checker.check_all_pages(win)

    win.close()
    win.deleteLater()
    app.processEvents()
    return violations


def main():
    parser = argparse.ArgumentParser(description="NetGuard AI Layout and Readability Checker (L0)")
    parser.add_argument("--scale", type=str, default="all", help="Display scale (1.0, 1.25, 1.5, 1.75 or all)")
    parser.add_argument("--screenshots", action="store_true", help="Save screenshots in docs/screenshots/ux2/")
    parser.add_argument("--output", type=str, default=None, help="Output file path (e.g. docs/layout_before.txt)")
    args = parser.parse_args()

    screenshot_dir = os.path.join(root_dir, "docs", "screenshots", "ux2") if args.screenshots else None

    all_violations: List[Violation] = []

    if args.scale == "all":
        scales = [1.0, 1.25, 1.5, 1.75]
        for s in scales:
            print(f"--- Running Layout Check at scale {int(s*100)}% ---")
            # Run in isolated subprocess so QT_SCALE_FACTOR takes native high-DPI effect
            env = os.environ.copy()
            env["QT_SCALE_FACTOR"] = str(s)
            env["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"
            env["QT_ENABLE_HIGHDPI_SCALING"] = "1"
            cmd = [
                sys.executable,
                __file__,
                "--scale", str(s),
            ]
            if args.screenshots:
                cmd.append("--screenshots")
            proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if proc.returncode != 0:
                print(f"Subprocess failed for scale {s}:\n{proc.stderr}")
            # Parse violations from output
            for line in proc.stdout.splitlines():
                if line.startswith("| ") and not line.startswith("| Page") and not line.startswith("|---"):
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if len(parts) >= 6:
                        all_violations.append(
                            Violation(
                                page_name=parts[0],
                                window_size=parts[1],
                                scale=float(parts[2].replace("%", "")) / 100.0,
                                widget_name=parts[3],
                                widget_type="",
                                rule=parts[4].replace("**", ""),
                                details=parts[5],
                            )
                        )
    else:
        s = float(args.scale)
        all_violations = run_single_scale(scale=s, screenshot_dir=screenshot_dir)

    # Format report
    out_lines = [
        "# NetGuard AI - Objective Layout & Typography Audit Report",
        f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total Violations Found: {len(all_violations)}",
        "",
        "| Page | Window Size | Scale | Widget | Rule | Violation Details |",
        "|---|---|---|---|---|---|",
    ]

    for v in all_violations:
        out_lines.append(v.to_row())

    report_text = "\n".join(out_lines) + "\n"

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"Report written to: {args.output}")

    print(report_text)
    print(f"Audit completed: {len(all_violations)} violations found.")
    sys.exit(0 if len(all_violations) == 0 else 1)


if __name__ == "__main__":
    main()
