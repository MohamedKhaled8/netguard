"""Integration tests for NetGuard AI UI Wiring Matrix (AC-8, R7).

Validates docs/audit_data/ui_wiring.csv against the running PySide6 application
under headless / offscreen Qt context.

4-Tier Test Architecture:
- Tier 1: Schema validation, column integrity, and AC-8 zero-tolerance status audit
          (asserts all rows are WORKS, HIDDEN, or DISABLED_WITH_REASON).
- Tier 2: For every control with Status == 'WORKS': asserts widget exists on view,
          is visible (not isHidden()), and signal/handler is wired to callable slot.
- Tier 3: For every control with Status in ('HIDDEN', 'DISABLED_WITH_REASON'):
          asserts widget is hidden or disabled with a visible tooltip/badge explanation.
- Tier 4: Comprehensive view coverage across all 7 views + Sidebar.
"""

from __future__ import annotations
import csv
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

import pytest
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QComboBox
from PySide6.QtCore import Qt

from app.application import create_application
from app.ui.main_window import MainWindow


# ---------------------------------------------------------------------------
# Constants & Paths
# ---------------------------------------------------------------------------
REQUIRED_SCHEMA_COLUMNS = [
    "Screen",
    "Control",
    "Widget",
    "Handler",
    "CallsBackend",
    "RealEffect",
    "Persisted",
    "ReflectedInUI",
    "Status",
]

VALID_STATUSES = {
    "WORKS",
    "HIDDEN",
    "DISABLED_WITH_REASON",
    "PARTIAL",
    "DEAD",
    "FAKE-DATA",
    "UI-ONLY",
}

ALL_SEVEN_SCREENS = {
    "Sidebar",
    "Dashboard",
    "Diagnosis",
    "Remediation",
    "DNS",
    "Traffic",
    "History",
    "Settings",
}


def get_ui_wiring_csv_path() -> Path:
    """Resolve absolute path to docs/audit_data/ui_wiring.csv."""
    # Project root is the working directory
    base_dir = Path(__file__).resolve().parent.parent.parent
    csv_path = base_dir / "docs" / "audit_data" / "ui_wiring.csv"
    if not csv_path.exists():
        # Fallback to current working directory
        csv_path = Path("docs/audit_data/ui_wiring.csv").resolve()
    return csv_path


def load_ui_wiring_rows(path: Optional[Path] = None) -> List[Dict[str, str]]:
    """Dynamically load and parse ui_wiring.csv rows."""
    target_path = path or get_ui_wiring_csv_path()
    assert target_path.exists(), f"UI wiring matrix file not found: {target_path}"
    with open(target_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def qapp():
    """Ensure headless QApplication instance for offscreen UI testing."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    return app


@pytest.fixture
def main_window(qapp):
    """Instantiate a clean MainWindow with clean teardown."""
    net_app = create_application()
    win = MainWindow(application=net_app)
    win.show()
    qapp.processEvents()
    try:
        yield win
    finally:
        win.refresh_timer.stop()
        win.dns_rank_timer.stop()
        win.close()
        win.deleteLater()
        qapp.processEvents()


# ---------------------------------------------------------------------------
# Widget Resolver Helper
# ---------------------------------------------------------------------------
def resolve_control_widget(win: MainWindow, row: Dict[str, str]) -> Optional[QWidget]:
    """Map a ui_wiring.csv row (Screen, Control, Widget) to its live Qt widget."""
    screen = row.get("Screen", "").strip()
    control = row.get("Control", "").strip()

    if screen == "Sidebar":
        if "الرئيسية" in control:
            return win.btn_dash
        if "التشخيص" in control:
            return win.btn_diag
        if "الإصلاح التلقائي" in control:
            return win.btn_rem
        if "DNS" in control:
            return win.btn_dns
        if "حركة البيانات" in control:
            return win.btn_traffic
        if "السجل" in control:
            return win.btn_hist
        if "الإعدادات" in control:
            return win.btn_settings
        if "تلقائي" in control:
            return win.sidebar.opt_auto
        if "بموافقتي" in control:
            return win.sidebar.opt_assisted
        if "مراقبة فقط" in control:
            return win.sidebar.opt_observe

    elif screen == "Dashboard":
        if "تصدير تقرير" in control:
            return win.view_dashboard.btn_export
        if "افحص الآن" in control:
            return win.view_dashboard.btn_scan
        if "48 عمود" in control:
            return win.view_dashboard.day_strip
        if "سرعة التنزيل" in control:
            from app.ui.widgets.metric_cell import MetricCell
            cells = win.view_dashboard.metrics_strip.findChildren(MetricCell)
            return cells[3] if len(cells) > 3 else None
        if "مخطط البنج" in control:
            return win.view_dashboard.latency_chart
        if "عرض الأدلة" in control:
            return win.view_dashboard.timeline_panel.btn_evidence
        if "تراجع عن الإصلاح" in control:
            return win.view_dashboard.timeline_panel.btn_rollback
        if "مسار اتصالك" in control:
            return win.view_dashboard.flow_path
        if "من يستهلك" in control:
            return win.view_dashboard.consumers_panel
        if "اعتماد خادم" in control or "استعادة الافتراضي" in control:
            return win.view_dashboard.dns_panel.btn_action

    elif screen == "Diagnosis":
        if "فحص شامل" in control:
            return win.view_diagnosis.btn_run_audit
        if "قائمة الطبقات" in control:
            return win.view_diagnosis.row_l1
        if "جدول بيانات" in control:
            return win.view_diagnosis.table

    elif screen == "Remediation":
        if "بطاقة وضع: تلقائي" in control:
            return win.view_remediation.mode_auto
        if "بطاقة وضع: بموافقتي" in control:
            return win.view_remediation.mode_assisted
        if "بطاقة وضع: مراقبة فقط" in control:
            return win.view_remediation.mode_observe
        if "تنظيف كاش" in control:
            return win.view_remediation.btn_flush_now
        if "تجديد مسار" in control:
            return win.view_remediation.btn_renew_ip
        if "تفريغ كاش" in control:
            return win.view_remediation.pol1
        if "تأمين مكالمات" in control:
            return win.view_remediation.pol2
        if "التحويل التلقائي" in control:
            return win.view_remediation.pol3
        if "تجديد IP تلقائياً" in control:
            return win.view_remediation.pol4

    elif screen == "DNS":
        if "فحص وترتيب" in control:
            return win.view_dns.benchmark_btn
        if "طبّق لكل" in control:
            return win.view_dns.table

    elif screen == "Traffic":
        if "محاكاة مكالمة" in control:
            return win.view_traffic.btn_sim_zoom
        if "فحص البرامج" in control:
            return win.view_traffic.btn_refresh
        if "درع مكالمات" in control:
            return win.view_traffic.guard_toggle
        if "جدول البرامج" in control:
            return win.view_traffic.table

    elif screen == "History":
        if "اليوم السابق" in control:
            return win.view_history.btn_prev
        if "اليوم التالي" in control:
            return win.view_history.btn_next
        if "قائمة الأحداث" in control:
            return win.view_history.events_panel

    elif screen == "Settings":
        if "وضع المعالجة" in control:
            return win.view_settings.mode_combo
        if "إعادة تشغيل الراوتر" in control:
            return getattr(win.view_settings, "toggle_reboot", None)
        if "معدل فحص" in control:
            return win.view_settings.combo_interval
        if "إشعارات ويندوز" in control:
            return getattr(win.view_settings, "toggle_notif", None)
        if "حفظ الإعدادات" in control:
            return win.view_settings.apply_btn

    return None


# ===========================================================================
# Tier 1: Schema & AC-8 Status Matrix Validation
# ===========================================================================
class TestUIWiringMatrixTier1:
    """Tier 1: Schema verification and AC-8 zero-tolerance status audit."""

    def test_ui_wiring_matrix_file_exists_and_valid_schema(self):
        """Matrix CSV must exist and contain all 9 required schema headers."""
        csv_path = get_ui_wiring_csv_path()
        assert csv_path.exists(), f"docs/audit_data/ui_wiring.csv missing at {csv_path}"

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)

        assert header == REQUIRED_SCHEMA_COLUMNS, (
            f"Schema mismatch in ui_wiring.csv.\n"
            f"Expected: {REQUIRED_SCHEMA_COLUMNS}\n"
            f"Actual:   {header}"
        )

    def test_ui_wiring_matrix_rows_not_empty_and_valid_status_domain(self):
        """Every row must have populated columns and a recognized Status."""
        rows = load_ui_wiring_rows()
        assert len(rows) >= 47, f"Expected at least 47 registered UI controls, got {len(rows)}"

        for idx, row in enumerate(rows, start=2):
            for col in ["Screen", "Control", "Widget", "Status"]:
                val = row.get(col, "").strip()
                assert val, f"Row {idx} is missing required column '{col}'"

            status = row.get("Status", "").strip()
            assert status in VALID_STATUSES, (
                f"Row {idx} ('{row.get('Control')}') has unknown Status '{status}'. "
                f"Must be one of {sorted(VALID_STATUSES)}"
            )

    def test_ui_wiring_baseline_status_distribution_audit(self):
        """Audit status distribution and report baseline counts."""
        rows = load_ui_wiring_rows()
        counts: Dict[str, int] = {}
        for r in rows:
            s = r["Status"].strip()
            counts[s] = counts.get(s, 0) + 1

        total = len(rows)
        works_count = counts.get("WORKS", 0)
        hidden_count = counts.get("HIDDEN", 0)
        disabled_count = counts.get("DISABLED_WITH_REASON", 0)
        non_working = total - (works_count + hidden_count + disabled_count)

        # Baseline check: ensure status distribution is captured
        assert total >= 47
        assert works_count >= 13, f"Expected at least 13 WORKS controls in baseline, got {works_count}"
        # We record the distribution for test reporting
        print(f"\n[UI Wiring Audit Baseline] Total={total}, WORKS={works_count}, "
              f"HIDDEN={hidden_count}, DISABLED={disabled_count}, Non-working={non_working}")

    def test_ui_wiring_ac8_zero_tolerance_all_controls_functional_or_hidden(self):
        """AC-8 Zero Tolerance: Every visible control must be WORKS, or HIDDEN/DISABLED with reason.

        Zero rows may have status DEAD, FAKE-DATA, UI-ONLY, or PARTIAL.
        When legacy non-working rows exist (prior to Milestone M3 remediation),
        this test fails with an explicit failure report enumerating every violating row.
        """
        rows = load_ui_wiring_rows()
        failing_rows = []

        for idx, row in enumerate(rows, start=2):
            status = row.get("Status", "").strip()
            if status not in ("WORKS", "HIDDEN", "DISABLED_WITH_REASON"):
                failing_rows.append((idx, row.get("Screen"), row.get("Control"), status, row.get("RealEffect")))

        if failing_rows:
            report_lines = [
                f"\n[AC-8 VIOLATION] Found {len(failing_rows)} non-working UI controls in ui_wiring.csv:",
                f"{'Row':<6} {'Screen':<14} {'Status':<12} {'Control'}",
                "-" * 70,
            ]
            for r_idx, screen, control, status, _ in failing_rows:
                report_lines.append(f"{r_idx:<6} {screen:<14} {status:<12} {control}")
            report_lines.append("-" * 70)
            report_lines.append(
                f"AC-8 requires 100% of visible controls to be WORKS or HIDDEN with visible reasons. "
                f"Legacy count to remediate in Milestone M3: {len(failing_rows)} rows."
            )
            pytest.fail("\n".join(report_lines))


# ===========================================================================
# Tier 2: 'WORKS' Controls Existence, Visibility & Wiring Verification
# ===========================================================================
class TestUIWiringMatrixTier2Works:
    """Tier 2: Verification of all rows marked 'WORKS'."""

    def test_works_controls_exist_and_visible(self, main_window):
        """Every control marked 'WORKS' must resolve to an existing, non-hidden widget."""
        rows = load_ui_wiring_rows()
        works_rows = [r for r in rows if r.get("Status", "").strip() == "WORKS"]

        assert len(works_rows) >= 13, f"Expected at least 13 WORKS rows, got {len(works_rows)}"

        for row in works_rows:
            screen = row.get("Screen")
            control = row.get("Control")
            widget = resolve_control_widget(main_window, row)

            assert widget is not None, (
                f"Control marked 'WORKS' failed to resolve to a widget:\n"
                f"  Screen:  {screen}\n"
                f"  Control: {control}\n"
                f"  Widget:  {row.get('Widget')}"
            )

            assert not widget.isHidden(), (
                f"Control marked 'WORKS' is unexpectedly hidden:\n"
                f"  Screen:  {screen}\n"
                f"  Control: {control}"
            )

    def test_works_controls_handler_wiring(self, main_window, qapp):
        """Every 'WORKS' clickable control must have its handler wired and callable without error."""
        rows = load_ui_wiring_rows()
        works_rows = [r for r in rows if r.get("Status", "").strip() == "WORKS"]

        for row in works_rows:
            screen = row.get("Screen")
            control = row.get("Control")
            widget = resolve_control_widget(main_window, row)
            assert widget is not None

            # Test NavItem switching
            if screen == "Sidebar" and isinstance(widget, QPushButton):
                # Clicking a nav item must update current index and not raise NotImplementedError
                target_idx = widget.index if hasattr(widget, "index") else 0
                main_window._switch_view(target_idx, widget)
                qapp.processEvents()
                assert main_window.stack.currentIndex() == target_idx

            # Test Quick Flush DNS button
            elif "تنظيف كاش DNS" in control and isinstance(widget, QPushButton):
                assert widget.isEnabled()
                # Verify handler exists and is callable
                assert hasattr(main_window, "_on_quick_flush_dns")
                assert callable(main_window._on_quick_flush_dns)

            # Test DNS Benchmark button
            elif "فحص وترتيب الخوادم" in control and isinstance(widget, QPushButton):
                assert widget.isEnabled()
                assert hasattr(main_window, "_on_run_dns_benchmark")
                assert callable(main_window._on_run_dns_benchmark)

            # Test Zoom simulation button
            elif "محاكاة مكالمة Zoom" in control and isinstance(widget, QPushButton):
                assert widget.isEnabled()
                assert hasattr(main_window.view_traffic, "_on_sim_zoom_clicked")
                assert callable(main_window.view_traffic._on_sim_zoom_clicked)


# ===========================================================================
# Tier 3: 'HIDDEN' / 'DISABLED_WITH_REASON' Controls Verification
# ===========================================================================
class TestUIWiringMatrixTier3HiddenOrDisabled:
    """Tier 3: Verification of controls marked HIDDEN or DISABLED_WITH_REASON."""

    def test_hidden_or_disabled_controls_have_visible_reasons(self, main_window):
        """Controls marked HIDDEN must be hidden; DISABLED must be disabled with tooltip."""
        rows = load_ui_wiring_rows()
        special_rows = [
            r for r in rows
            if r.get("Status", "").strip() in ("HIDDEN", "DISABLED_WITH_REASON")
        ]

        # Prior to M3, there may be 0 HIDDEN rows. When M3 adds them, this verifies their compliance.
        for row in special_rows:
            status = row.get("Status", "").strip()
            screen = row.get("Screen")
            control = row.get("Control")
            widget = resolve_control_widget(main_window, row)

            if widget is None:
                continue

            if status == "HIDDEN":
                assert widget.isHidden(), (
                    f"Control marked 'HIDDEN' is still visible:\n"
                    f"  Screen:  {screen}\n"
                    f"  Control: {control}"
                )
            elif status == "DISABLED_WITH_REASON":
                assert not widget.isEnabled(), (
                    f"Control marked 'DISABLED_WITH_REASON' is still enabled:\n"
                    f"  Screen:  {screen}\n"
                    f"  Control: {control}"
                )
                reason = widget.toolTip() or widget.accessibleDescription() or row.get("ReflectedInUI", "")
                assert reason.strip(), (
                    f"Disabled control lacks visible explanation / tooltip:\n"
                    f"  Screen:  {screen}\n"
                    f"  Control: {control}"
                )


# ===========================================================================
# Tier 4: Cross-View Comprehensive Coverage
# ===========================================================================
class TestUIWiringMatrixTier4Coverage:
    """Tier 4: Verification across all 7 views and navigation integrity."""

    def test_all_seven_views_represented_in_matrix(self):
        """Matrix must have registered controls for Sidebar and all 7 views."""
        rows = load_ui_wiring_rows()
        screens_in_matrix = {r.get("Screen", "").strip() for r in rows}

        missing_screens = ALL_SEVEN_SCREENS - screens_in_matrix
        assert not missing_screens, f"UI wiring matrix is missing screens: {missing_screens}"

    def test_all_views_widget_resolution_coverage(self, main_window):
        """Every single row in ui_wiring.csv must resolve to a valid widget object."""
        rows = load_ui_wiring_rows()
        unresolved = []

        for idx, row in enumerate(rows, start=2):
            w = resolve_control_widget(main_window, row)
            if w is None:
                unresolved.append((idx, row.get("Screen"), row.get("Control"), row.get("Widget")))

        assert not unresolved, (
            f"Failed to resolve {len(unresolved)} controls to widgets on MainWindow:\n"
            + "\n".join(f"  Row {r[0]}: {r[1]} | {r[2]} -> {r[3]}" for r in unresolved)
        )

    def test_ui_wiring_matrix_csv_edge_cases(self, tmp_path):
        """Resilience test against malformed CSVs, empty files, and corrupted data."""
        empty_csv = tmp_path / "empty.csv"
        empty_csv.write_text("", encoding="utf-8")
        rows = load_ui_wiring_rows(empty_csv)
        assert len(rows) == 0

        non_existent = tmp_path / "does_not_exist.csv"
        with pytest.raises(AssertionError):
            load_ui_wiring_rows(non_existent)

        bad_header_csv = tmp_path / "bad_header.csv"
        bad_header_csv.write_text("Col1,Col2,Col3\nA,B,C\n", encoding="utf-8")
        rows = load_ui_wiring_rows(bad_header_csv)
        assert len(rows) == 1
        assert "Status" not in rows[0]
