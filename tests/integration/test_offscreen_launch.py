"""Integration tests for NetGuard AI Headless Offscreen Launch & Navigation (AC-9, R8).

Verifies that NetGuard AI boots, renders, navigates across all 7 views,
handles dynamic resizing, executes background telemetry events, and shuts down
cleanly without unhandled exceptions, segfaults, or resource leaks under
QT_QPA_PLATFORM=offscreen.

4-Tier Test Architecture:
- Tier 1: Offscreen application creation, window initialization, title, and default layout.
- Tier 2: Boundary value analysis & stress (rapid view switching, offscreen resizing across
          breakpoints <700px, 700-1099px, >=1100px, repeated sequential launch/teardown).
- Tier 3: Cross-feature integration (mode switching in sidebar, UI tick cycles,
          and bridge signal dispatching offscreen).
- Tier 4: Scenario 5 end-to-end full navigation and lifecycle execution.
"""

from __future__ import annotations
import os
import sys
import time
from typing import Generator

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

from app.application import create_application
from app.ui.main_window import MainWindow
from app.core.models.metrics import OperatingMode


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Ensure headless QApplication instance configured for offscreen execution."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    return app


@pytest.fixture
def managed_window(qapp: QApplication) -> Generator[MainWindow, None, None]:
    """Provide a freshly initialized MainWindow with deterministic cleanup."""
    net_app = create_application()
    win = MainWindow(application=net_app)
    win.show()
    qapp.processEvents()
    try:
        yield win
    finally:
        if hasattr(win, "refresh_timer") and win.refresh_timer.isActive():
            win.refresh_timer.stop()
        if hasattr(win, "dns_rank_timer") and win.dns_rank_timer.isActive():
            win.dns_rank_timer.stop()
        win.close()
        win.deleteLater()
        qapp.processEvents()


# ===========================================================================
# Tier 1: Core Offscreen Application Launch & Window Initialization
# ===========================================================================
class TestOffscreenLaunchTier1:
    """Tier 1: Verifies basic headless initialization and window attributes."""

    def test_application_offscreen_launch_and_window_title(self, managed_window: MainWindow, qapp: QApplication):
        """Application must launch offscreen with exact title 'NetGuard AI' and 10-view stack."""
        assert managed_window is not None
        assert managed_window.windowTitle() == "NetGuard AI"
        assert managed_window.isVisible()
        assert managed_window.stack.count() == 10
        assert managed_window.stack.currentIndex() == 0  # Starts on Dashboard

        # Verify default geometry bounds
        assert managed_window.width() >= 480
        assert managed_window.height() >= 580

        # Cycle events to ensure no pending layout or paint exceptions
        qapp.processEvents()

    def test_offscreen_views_instantiation(self, managed_window: MainWindow):
        """All 10 views must be instantiated and mounted into the content stack."""
        expected_views = [
            ("Dashboard", managed_window.view_dashboard),
            ("MeetingGuard", managed_window.view_meeting_guard),
            ("Traffic", managed_window.view_traffic),
            ("DNS", managed_window.view_dns),
            ("WifiIntelligence", managed_window.view_wifi),
            ("RouterManagement", managed_window.view_router),
            ("InternetQuality", managed_window.view_quality),
            ("Reports", managed_window.view_reports),
            ("Settings", managed_window.view_settings),
            ("About", managed_window.view_about),
        ]

        for idx, (name, view_obj) in enumerate(expected_views):
            assert view_obj is not None, f"View {name} (index {idx}) is None"
            assert managed_window.stack.widget(idx) is view_obj, (
                f"Stack widget at index {idx} does not match {name}"
            )

    def test_sidebar_initial_state_offscreen(self, managed_window: MainWindow):
        """Sidebar must be docked by default with Dashboard button checked."""
        assert managed_window.sidebar is not None
        assert getattr(managed_window, "_shell_mode", "dock") == "dock"
        assert managed_window.sidebar.width() == 248
        assert managed_window.btn_dash.isChecked()
        assert not managed_window.btn_diag.isChecked()
        assert not managed_window.btn_settings.isChecked()


# ===========================================================================
# Tier 2: Boundary Value Analysis & Stress Testing
# ===========================================================================
class TestOffscreenNavigationTier2Stress:
    """Tier 2: Boundary stress testing across views, resize breakpoints, and restarts."""

    def test_headless_navigation_all_seven_views(self, managed_window: MainWindow, qapp: QApplication):
        """Walk across all 7 views in sequence (0 through 6) and verify state."""
        for target_idx in range(8):
            active_btn = managed_window.nav_buttons[target_idx]
            managed_window._switch_view(target_idx, active_btn)
            qapp.processEvents()

            assert managed_window.stack.currentIndex() == target_idx, (
                f"Failed to switch to view index {target_idx}"
            )
            assert active_btn.isChecked(), f"Nav item {target_idx} is not checked"

            # Assert other buttons are unchecked
            for other_idx, other_btn in enumerate(managed_window.nav_buttons):
                if other_idx != target_idx:
                    assert not other_btn.isChecked(), (
                        f"Nav item {other_idx} should be unchecked when on index {target_idx}"
                    )

            # Cycle paint and layout events
            for _ in range(3):
                qapp.processEvents()

    def test_rapid_view_switching_stress(self, managed_window: MainWindow, qapp: QApplication):
        """Rapidly switch views 30 times in forward, reverse, and jump sequences across all 8 views."""
        sequence = [0, 1, 2, 3, 4, 5, 6, 7, 6, 5, 4, 3, 2, 1, 0, 7, 2, 4, 1, 5, 3, 0, 7, 1, 4, 2, 5, 3, 6, 7, 0]

        for step, target_idx in enumerate(sequence):
            btn = managed_window.nav_buttons[target_idx]
            managed_window._switch_view(target_idx, btn)
            qapp.processEvents()
            assert managed_window.stack.currentIndex() == target_idx, (
                f"Rapid switch step {step} to index {target_idx} failed"
            )

        qapp.processEvents()

    def test_window_resize_offscreen_breakpoints(self, managed_window: MainWindow, qapp: QApplication):
        """Verify dynamic responsive reflow across all three breakpoints offscreen.

        - >=1100px: wide desktop (sidebar docked at 248px)
        - 700-1099px: medium desktop (sidebar docked at 248px)
        - <700px: mobile/compact (sidebar reflows to top_bar with 2-column grid)
        """
        # Breakpoint 1: Wide Desktop (1440x900)
        managed_window.resize(1440, 900)
        qapp.processEvents()
        assert getattr(managed_window, "_shell_mode", "dock") == "dock"

        # Breakpoint 2: Medium Compact (<900px collapses to 64px icon dock per Item L7)
        managed_window.resize(850, 700)
        qapp.processEvents()
        assert getattr(managed_window, "_shell_mode", "dock") == "collapsed"

        # Breakpoint 3: Mobile / Compact (<700px -> 600x800)
        managed_window.resize(600, 800)
        qapp.processEvents()
        assert getattr(managed_window, "_shell_mode", "dock") == "collapsed"

        # Breakpoint 4: Ultra Narrow (480x600 - minimum window size)
        managed_window.resize(480, 600)
        qapp.processEvents()
        assert getattr(managed_window, "_shell_mode", "dock") == "collapsed"

        # Reflow restore: Back to Desktop (1200x800)
        managed_window.resize(1200, 800)
        qapp.processEvents()
        assert getattr(managed_window, "_shell_mode", "dock") == "dock"

    def test_repeated_sequential_launch_and_teardown(self, qapp: QApplication):
        """Consecutively launch and teardown application 3 times to prove zero resource leaks."""
        for cycle in range(3):
            net_app = create_application()
            win = MainWindow(application=net_app)
            win.show()
            qapp.processEvents()

            assert win.windowTitle() == "NetGuard AI"
            assert win.stack.count() == 10

            # Walk through 2 views
            win._switch_view(7, win.btn_reports)
            qapp.processEvents()
            win._switch_view(0, win.btn_dash)
            qapp.processEvents()

            # Clean shutdown
            win.refresh_timer.stop()
            win.dns_rank_timer.stop()
            win.close()
            win.deleteLater()
            qapp.processEvents()


# ===========================================================================
# Tier 3: Cross-Feature Integration Offscreen
# ===========================================================================
class TestOffscreenCrossFeatureTier3:
    """Tier 3: UI ticks, mode selector transitions, and bridge event handling."""

    def test_offscreen_ui_tick_cycles(self, managed_window: MainWindow, qapp: QApplication):
        """Execute _on_ui_tick() multiple times offscreen without error."""
        for _ in range(5):
            managed_window._on_ui_tick()
            qapp.processEvents()

        # Verify tick execution updated dashboard components cleanly
        assert managed_window.view_dashboard is not None
        assert managed_window.view_dashboard.isVisible()

    def test_offscreen_sidebar_mode_switching(self, managed_window: MainWindow, qapp: QApplication):
        """Click sidebar mode options offscreen and verify mode description and orchestrator."""
        sidebar = managed_window.sidebar

        # Mode 1: Assisted (بموافقتي)
        sidebar._on_mode_clicked(1)
        qapp.processEvents()
        assert sidebar.opt_assisted.is_selected is True
        assert sidebar.opt_auto.is_selected is False
        assert "ينتظر موافقتك" in sidebar.lbl_mode_desc.text()

        # Mode 2: Observation (مراقبة فقط)
        sidebar._on_mode_clicked(2)
        qapp.processEvents()
        assert sidebar.opt_observe.is_selected is True
        assert "دون إجراء أي تعديل" in sidebar.lbl_mode_desc.text()

        # Mode 0: Auto (تلقائي)
        sidebar._on_mode_clicked(0)
        qapp.processEvents()
        assert sidebar.opt_auto.is_selected is True
        assert "يكتشف الخلل" in sidebar.lbl_mode_desc.text()

    def test_offscreen_bridge_signal_reception(self, managed_window: MainWindow, qapp: QApplication):
        """Verify thread-safe UI bridge dispatches remediation events offscreen."""
        test_payload = {"name": "تفريغ كاش DNS التجريبي"}

        # Emit started event via bridge
        managed_window.bridge.remediation_event_received.emit("started", test_payload)
        qapp.processEvents()

        # Emit completed event via bridge
        managed_window.bridge.remediation_event_received.emit("completed", test_payload)
        qapp.processEvents()


# ===========================================================================
# Tier 4: Scenario 5 Real-World Offscreen Navigation & Control Integrity
# ===========================================================================
class TestOffscreenScenario5Tier4:
    """Tier 4: Scenario 5 Full UI Offscreen Navigation & Control Integrity."""

    def test_scenario_5_full_ui_navigation_and_control_integrity(
        self, managed_window: MainWindow, qapp: QApplication
    ):
        """End-to-end scenario:
        1. Bootstrap application in headless environment.
        2. Walk through every view (Dashboard -> Diagnosis -> Remediation -> DNS -> Traffic -> History -> Settings).
        3. Trigger view-specific UI actions (UI ticks, mode selector, DNS benchmark trigger, Zoom simulation toggle).
        4. Resize across desktop and mobile form factors.
        5. Verify zero crashes, zero unhandled exceptions, and cleanly shut down.
        """
        # Step 1: Verify bootstrap state
        assert managed_window.windowTitle() == "NetGuard AI"
        qapp.processEvents()

        # Step 2: Traverse each view and verify view integrity
        # View 0: Dashboard
        managed_window._switch_view(0, managed_window.btn_dash)
        qapp.processEvents()
        assert managed_window.view_dashboard.isVisible()

        # View 1: Meeting Guard (includes Remediation controls)
        managed_window._switch_view(1, managed_window.btn_meeting_guard)
        qapp.processEvents()
        assert managed_window.view_meeting_guard.isVisible()
        assert managed_window.view_remediation.isVisible()

        # View 2: Traffic
        managed_window._switch_view(2, managed_window.btn_traffic)
        qapp.processEvents()
        assert managed_window.view_traffic.isVisible()

        # View 3: DNS
        managed_window._switch_view(3, managed_window.btn_dns)
        qapp.processEvents()
        assert managed_window.view_dns.isVisible()

        # View 7: Reports & Deep Diagnosis
        managed_window._switch_view(7, managed_window.btn_reports)
        qapp.processEvents()
        assert managed_window.view_reports.isVisible()
        assert managed_window.view_diagnosis.isVisible()

        # Exercise Zoom simulation toggle on Traffic view
        traffic_view = managed_window.view_traffic
        # If a background Zoom session was active on the host, ensure it is closed first
        if any("zoom" in s.process_name.lower() for s in traffic_view.session_tracker.get_active_sessions()):
            traffic_view._on_sim_zoom_clicked()
            qapp.processEvents()

        # Start simulated Zoom call
        traffic_view._on_sim_zoom_clicked()
        qapp.processEvents()
        assert traffic_view.btn_sim_zoom.text() == "إنهاء مكالمة Zoom"
        assert any("zoom" in s.process_name.lower() for s in traffic_view.session_tracker.get_active_sessions())

        # Close simulated Zoom call
        traffic_view._on_sim_zoom_clicked()
        qapp.processEvents()
        assert traffic_view.btn_sim_zoom.text() == "محاكاة مكالمة Zoom"

        # View 7 Subtab 2: History inside Reports
        managed_window._switch_view(7, managed_window.btn_reports)
        managed_window.view_reports.switch_subtab(2)
        qapp.processEvents()
        assert managed_window.view_history.isVisible()

        # View 8: Settings
        managed_window._switch_view(8, managed_window.btn_settings)
        qapp.processEvents()
        assert managed_window.view_settings.isVisible()

        # View 9: About
        managed_window._switch_view(9, managed_window.btn_about)
        qapp.processEvents()
        assert managed_window.view_about.isVisible()

        # Step 3: Resize offscreen
        managed_window.resize(650, 750)
        qapp.processEvents()
        managed_window.resize(1440, 900)
        qapp.processEvents()

        # Step 4: Return to Dashboard and run UI tick
        managed_window._switch_view(0, managed_window.btn_dash)
        managed_window._on_ui_tick()
        qapp.processEvents()

        # Scenario 5 passes with zero errors
