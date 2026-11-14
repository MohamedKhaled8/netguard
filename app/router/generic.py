"""Generic Router Diagnostic Adapter with non-destructive discovery."""

from __future__ import annotations
import asyncio
import urllib.request
import re
from typing import Any, Dict, Optional
from app.router.base import BaseRouterAdapter
from app.cellular.models import CellularMetrics, SignalQualityCategory


class GenericRouterAdapter(BaseRouterAdapter):
    """Probes router gateway web interface headers and titles without hardcoded proprietary assumptions."""

    async def detect_model(self) -> Optional[str]:
        loop = asyncio.get_running_loop()

        def _probe():
            try:
                url = f"http://{self.gateway_ip}/"
                req = urllib.request.Request(url, headers={"User-Agent": "NetGuard-Probe/1.0"})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    headers = dict(resp.headers)
                    body = resp.read(2048).decode("utf-8", errors="ignore")

                    server = headers.get("Server", "")
                    title_match = re.search(r"<title>(.*?)</title>", body, re.IGNORECASE)
                    title = title_match.group(1).strip() if title_match else ""

                    if "Huawei" in title or "HiLink" in title or "Huawei" in server:
                        return "Huawei HiLink Router"
                    elif "ZTE" in title or "ZTE" in server:
                        return "ZTE Cellular CPE"
                    elif "TP-Link" in title or "TP-LINK" in server:
                        return "TP-Link Router"
                    elif "Orange" in title or "Livebox" in title:
                        return "Orange Cellular Home Router"
                    return title or server or "Generic IP Gateway"
            except Exception:
                return None

        return await loop.run_in_executor(None, _probe)

    async def get_cellular_metrics(self) -> Optional[CellularMetrics]:
        # If router does not expose an unauthenticated cellular telemetry endpoint,
        # return None or classified state to indicate unavailable
        return None

    async def get_device_info(self) -> Dict[str, Any]:
        detected = await self.detect_model()
        return {
            "gateway_ip": self.gateway_ip,
            "detected_model": detected or "Unknown Gateway",
            "cellular_api_supported": False,
        }
