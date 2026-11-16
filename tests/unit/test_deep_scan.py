"""Unit tests verifying DeepScanner runs genuine multi-step diagnostics without fake delays or static claims."""

import pytest
from app.diagnosis.deep_scan import DeepScanner, DeepScanReport
from app.platform.windows.adapter import WindowsPlatformAdapter


class MockFailingPlatform(WindowsPlatformAdapter):
    """Platform simulator where gateway ping fails."""
    def get_default_gateway(self):
        return "192.168.1.1"

    def ping(self, target, timeout_sec=1.5):
        if target == "192.168.1.1":
            return False, 0.0
        return True, 25.0


def test_deep_scan_real_execution():
    """Verify DeepScanner runs all 5 probe steps and computes real numbers."""
    scanner = DeepScanner()
    progress_steps = []

    def on_progress(step_idx, total_steps, message):
        progress_steps.append((step_idx, message))

    report = scanner.run_scan(progress_callback=on_progress)

    assert isinstance(report, DeepScanReport)
    assert len(report.steps) == 5
    assert len(progress_steps) == 5
    assert report.duration_sec >= 0.05
    # The summary text must never be the hardcoded fake string
    assert "مؤشرات الاستقرار 100%" not in report.explanation_arabic
    assert report.gateway_latency_ms is not None or not report.steps[0].passed


def test_deep_scan_step_failure_detected():
    """Verify that when a probe fails, the scan reports failure instead of claiming 100% stability."""
    failing_platform = MockFailingPlatform()
    scanner = DeepScanner(platform=failing_platform)
    report = scanner.run_scan()

    assert report.steps[0].passed is False
    assert report.overall_health is False
    assert "فشل" in report.steps[0].details or "تعذر" in report.steps[0].details
