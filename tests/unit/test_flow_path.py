"""Unit tests verifying FlowPathPanel has zero hardcoded defaults and renders real telemetry."""

import pytest
from PySide6.QtWidgets import QApplication
from app.ui.widgets.flow_path import FlowPathPanel


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_flow_path_no_hardcoded_defaults(qapp):
    """Verify FlowPathPanel is not constructed with hardcoded latency numbers."""
    panel = FlowPathPanel()
    assert len(panel.nodes) == 5

    for i, node in enumerate(panel.nodes):
        info = panel.node_info[i]
        # Latency must be None upon construction (never 1.0, 3.0, 14.0, 27.0, 38.0)
        assert info["latency"] is None, f"Node {i} has hardcoded latency {info['latency']}"
        assert node.latency_ms is None, f"NodeButton {i} has hardcoded latency {node.latency_ms}"
        assert node.lbl_val.text() in ("—", " — "), f"NodeButton {i} label should be empty dash, got {node.lbl_val.text()}"
        assert info["status"] in ("none", "unknown"), f"Node {i} status should be neutral, got {info['status']}"


def test_flow_path_update_node_latency(qapp):
    """Verify update_node_latency sets real measured values correctly."""
    panel = FlowPathPanel()

    # Update router node (index 1) with real 12.4ms ping
    panel.update_node_latency(1, 12.4, status="ok", desc="الاتصال بالراوتر سليم")
    assert panel.node_info[1]["latency"] == 12.4
    assert panel.nodes[1].lbl_val.text() == "12"
    assert panel.node_info[1]["status"] == "ok"

    # Select node 1 and check detail box
    panel._select_node(1)
    assert "12 ms" in panel.lbl_now.text()
    assert panel.lbl_st.text() == "سليم"


def test_flow_path_disconnected_handles_none(qapp):
    """Verify update_node_latency handles None/unmeasured values with clean dashes."""
    panel = FlowPathPanel()
    panel.update_node_latency(4, None, status="bad", desc="الإنترنت غير متصل")
    assert panel.node_info[4]["latency"] is None
    assert panel.nodes[4].lbl_val.text() in ("—", " — ")
    panel._select_node(4)
    assert panel.lbl_now.text() in ("—", " — ")
