import pytest
from PySide6.QtWidgets import QApplication
from app.ui import tokens
from app.ui.widgets.network_info_strip import NetworkInfoStrip


def test_hairline_tokens_are_visible():
    assert tokens.LINE != "transparent"
    assert tokens.LINE.startswith("#")
    assert tokens.BORDER_WIDTH >= 1

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_network_info_strip_update(qapp):
    strip = NetworkInfoStrip()
    info = {
        "ssid": "MyWiFi_5G",
        "isp": "Telecom Egypt (WE)",
        "local_ip": "192.168.1.50",
        "public_ip": "197.52.36.240",
    }
    strip.update_info(info)
    assert strip.cell_ssid.lbl_val.text() == "MyWiFi_5G"
    assert strip.cell_isp.lbl_val.text() == "Telecom Egypt (WE)"
    assert strip.cell_local_ip.lbl_val.text() == "192.168.1.50"
    assert strip.cell_public_ip.lbl_val.text() == "197.52.36.240"

def test_network_info_strip_unavailable_handling(qapp):
    strip = NetworkInfoStrip()
    info = {
        "ssid": None,
        "isp": "غير متوفر",
        "local_ip": None,
        "public_ip": None,
    }
    strip.update_info(info)
    assert "غير متصل" in strip.cell_ssid.lbl_val.text() or "غير متوفر" in strip.cell_ssid.lbl_val.text()
    assert "غير متوفر" in strip.cell_isp.lbl_val.text()
    assert "—" in strip.cell_local_ip.lbl_val.text()
    assert "—" in strip.cell_public_ip.lbl_val.text()
