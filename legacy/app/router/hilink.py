"""Huawei HiLink Cellular Router Adapter."""

from __future__ import annotations
import asyncio
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional
from app.router.base import BaseRouterAdapter
from app.cellular.models import CellularMetrics, SignalQualityCategory


class HuaweiHiLinkAdapter(BaseRouterAdapter):
    """Adapter for routers using standard Huawei HiLink XML REST endpoints."""

    async def detect_model(self) -> Optional[str]:
        loop = asyncio.get_running_loop()

        def _check_hilink():
            try:
                url = f"http://{self.gateway_ip}/api/monitoring/status"
                req = urllib.request.Request(url, headers={"User-Agent": "NetGuard-Probe/1.0"})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    if resp.status == 200:
                        return "Huawei HiLink 4G/5G Router"
            except Exception:
                pass
            return None

        return await loop.run_in_executor(None, _check_hilink)

    async def get_cellular_metrics(self) -> Optional[CellularMetrics]:
        loop = asyncio.get_running_loop()

        def _fetch_metrics():
            try:
                url = f"http://{self.gateway_ip}/api/device/signal"
                req = urllib.request.Request(url, headers={"User-Agent": "NetGuard-Probe/1.0"})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    tree = ET.fromstring(resp.read().decode("utf-8"))
                    pci = tree.findtext("pci")
                    cell_id = tree.findtext("cell_id")
                    rsrp_str = tree.findtext("rsrp", "").replace("dBm", "").strip()
                    rsrq_str = tree.findtext("rsrq", "").replace("dB", "").strip()
                    sinr_str = tree.findtext("sinr", "").replace("dB", "").strip()
                    band_str = tree.findtext("band", "")

                    rsrp = float(rsrp_str) if rsrp_str else None
                    rsrq = float(rsrq_str) if rsrq_str else None
                    sinr = float(sinr_str) if sinr_str else None

                    quality = CellularMetrics.classify_quality(rsrp, sinr)

                    return CellularMetrics(
                        technology="LTE",
                        band=band_str or None,
                        cell_id=cell_id or pci or None,
                        rsrp_dbm=rsrp,
                        rsrq_db=rsrq,
                        sinr_db=sinr,
                        quality_category=quality,
                    )
            except Exception:
                return None

        return await loop.run_in_executor(None, _fetch_metrics)

    async def get_device_info(self) -> Dict[str, Any]:
        return {
            "gateway_ip": self.gateway_ip,
            "detected_model": "Huawei HiLink 4G/5G Router",
            "cellular_api_supported": True,
        }
