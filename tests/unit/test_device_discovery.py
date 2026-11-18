"""Unit tests for Local Subnet Device Discovery & OUI Resolution (Item E1)."""

import pytest
from unittest.mock import MagicMock, patch
from app.monitoring.device_discovery import LocalNetworkScanner, DiscoveredDevice


def test_oui_vendor_lookup():
    scanner = LocalNetworkScanner()
    assert scanner.lookup_vendor("F8-95-22-82-BF-63") == "ZTE Corporation"
    assert scanner.lookup_vendor("20:76:93:11:22:33") == "TP-Link Corporation"
    assert scanner.lookup_vendor("F0:18:98:AA:BB:CC") == "Apple, Inc."
    assert scanner.lookup_vendor("8C:B8:4A:12:34:56") == "Intel Corporate"
    assert scanner.lookup_vendor("00:50:56:C0:00:08") == "VMware Virtual Device"


def test_scan_subnet_parsing():
    platform = MagicMock()
    platform.get_default_gateway.return_value = "192.168.1.1"
    platform.get_primary_interface.return_value = "Wi-Fi"

    scanner = LocalNetworkScanner(platform)

    sample_output = """
ifIndex IPAddress                                          LinkLayerAddress      State       PolicyStore    
------- ---------                                          ----------------      -----       -----------    
7       239.255.255.250                                    01-00-5E-7F-FF-FA     Permanent   ActiveStore    
12      192.168.1.1                                        F8-95-22-82-BF-63     Reachable   ActiveStore    
12      192.168.1.50                                       20-76-93-11-22-33     Reachable   ActiveStore    
"""

    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value.stdout = sample_output
        mock_sub.return_value.returncode = 0

        devices = scanner.scan_subnet()
        assert len(devices) == 2

        # Gateway device
        gw = next((d for d in devices if d.ip == "192.168.1.1"), None)
        assert gw is not None
        assert gw.device_type == "gateway"
        assert "ZTE Corporation" in gw.vendor

        # LAN device
        lan = next((d for d in devices if d.ip == "192.168.1.50"), None)
        assert lan is not None
        assert lan.device_type == "lan_device"
        assert "TP-Link" in lan.vendor
