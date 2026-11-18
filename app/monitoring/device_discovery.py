"""Local subnet device discovery via ARP/Neighbor table and OUI identification (Item E1)."""

from __future__ import annotations
import sys
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any


@dataclass
class DiscoveredDevice:
    """Device discovered on the local LAN."""
    ip: str
    mac: str
    vendor: str
    device_type: str  # "this_pc" | "gateway" | "lan_device"
    status: str       # "active" | "reachable" | "stale"
    interface: str
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class LocalNetworkScanner:
    """Discovers active local devices and identifies manufacturers from MAC OUIs."""

    OUI_DATABASE = {
        "F8:95:22": "ZTE Corporation",
        "E4:C3:2A": "Huawei Technologies",
        "CC:96:A0": "Huawei Technologies",
        "20:76:93": "TP-Link Corporation",
        "50:D4:F7": "TP-Link Corporation",
        "E8:48:B8": "TP-Link Corporation",
        "00:1A:2B": "Cisco Systems",
        "00:50:56": "VMware Virtual Device",
        "00:0C:29": "VMware Virtual Device",
        "F0:18:98": "Apple, Inc.",
        "3C:22:FB": "Apple, Inc.",
        "AC:BC:32": "Apple, Inc.",
        "80:ED:2C": "Apple, Inc.",
        "28:16:A8": "Apple, Inc.",
        "34:41:5D": "Samsung Electronics",
        "54:92:BE": "Samsung Electronics",
        "B4:F1:DA": "Samsung Electronics",
        "8C:B8:4A": "Intel Corporate",
        "00:15:00": "Intel Corporate",
        "D8:3B:BF": "Xiaomi Communications",
        "64:CC:2E": "Xiaomi Communications",
        "A4:77:33": "Google, Inc.",
        "D8:0D:17": "Amazon Technologies",
    }

    def __init__(self, platform_adapter: Optional[Any] = None) -> None:
        self.platform = platform_adapter

    def lookup_vendor(self, mac: str) -> str:
        """Resolve MAC address prefix (first 3 octets) to hardware manufacturer."""
        norm = mac.replace("-", ":").upper().strip()
        prefix = ":".join(norm.split(":")[:3])
        if prefix in self.OUI_DATABASE:
            return self.OUI_DATABASE[prefix]
        if norm.startswith("01:00:5E") or norm.startswith("FF:FF:FF"):
            return "بث شبكي (Broadcast / Multicast)"
        return "جهاز شبكة محلي (Local Device)"

    def scan_subnet(self) -> List[DiscoveredDevice]:
        """Query OS ARP / neighbor table and return active subnet devices."""
        devices: List[DiscoveredDevice] = []
        gateway = "192.168.1.1"
        primary_iface = "Wi-Fi"
        if self.platform:
            gateway = self.platform.get_default_gateway() or gateway
            primary_iface = self.platform.get_primary_interface() or primary_iface

        if sys.platform == "win32":
            try:
                cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-NetNeighbor -AddressFamily IPv4"]
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
                for line in out.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 4 and parts[0].isdigit():
                        ifindex = parts[0]
                        ip = parts[1]
                        mac = parts[2]
                        state = parts[3]
                        iface = primary_iface

                        # Filter out multicast / broadcast
                        if (
                            ip.startswith("224.")
                            or ip.startswith("239.")
                            or ip.startswith("255.")
                            or ip.endswith(".255")
                            or mac.replace("-", ":").upper() == "FF:FF:FF:FF:FF:FF"
                        ):
                            continue

                        if state.lower() in ("reachable", "permanent"):
                            dev_type = "gateway" if ip == gateway else "lan_device"
                            vendor = self.lookup_vendor(mac)
                            if dev_type == "gateway":
                                vendor = f"راوتر الشبكة — {vendor}"
                            devices.append(
                                DiscoveredDevice(
                                    ip=ip,
                                    mac=mac,
                                    vendor=vendor,
                                    device_type=dev_type,
                                    status="active",
                                    interface=iface,
                                )
                            )
            except Exception:
                pass

        # If empty (or non-Windows fallback), parse arp -a
        if not devices:
            try:
                out = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=4)
                for line in out.stdout.splitlines():
                    match = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F-]+)\s+(\w+)", line)
                    if match:
                        ip, mac, _ = match.groups()
                        if ip.startswith("224.") or ip.startswith("239.") or ip.endswith(".255"):
                            continue
                        dev_type = "gateway" if ip == gateway else "lan_device"
                        devices.append(
                            DiscoveredDevice(
                                ip=ip,
                                mac=mac,
                                vendor=self.lookup_vendor(mac),
                                device_type=dev_type,
                                status="active",
                                interface=primary_iface,
                            )
                        )
            except Exception:
                pass

        return devices
