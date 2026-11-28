"""Authoritative Global Network State model shared across NetGuard AI UI & diagnostics.

Separates physical adapter link, Wi-Fi association, gateway availability,
router reachability, internet connectivity, DNS availability, and diagnostic status
so the header, dashboard, and diagnostic views can never contradict each other.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import threading
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from app.core.thresholds import DEFAULT_THRESHOLDS


@dataclass
class GlobalNetworkState:
    """Single source of truth for multi-layer connectivity & diagnostic status."""

    # 1. Physical network adapter status
    adapter_connected: bool = False
    adapter_name: str = ""
    medium: str = "unknown"  # "wifi" | "ethernet" | "unknown"
    local_ip: Optional[str] = None

    # 2. Wi-Fi association status
    wifi_associated: bool = False
    ssid: Optional[str] = None
    bssid: Optional[str] = None
    band: Optional[str] = None
    channel: Optional[int] = None
    rssi_dbm: Optional[int] = None
    signal_quality_pct: Optional[float] = None
    rx_rate_mbps: Optional[float] = None
    tx_rate_mbps: Optional[float] = None

    # 3. Default gateway availability
    gateway_ip: Optional[str] = None
    gateway_reachable: Optional[bool] = None
    gateway_latency_ms: Optional[float] = None
    gateway_loss_pct: Optional[float] = None

    # 4. Router reachability
    router_reachable: Optional[bool] = None
    router_model: Optional[str] = None
    router_url: Optional[str] = None

    # 5. Internet connectivity
    internet_available: Optional[bool] = None
    external_latency_ms: Optional[float] = None
    external_packet_loss_pct: Optional[float] = None
    jitter_ms: Optional[float] = None
    public_ip: Optional[str] = None
    isp_name: Optional[str] = None

    # 6. DNS functionality
    dns_available: Optional[bool] = None
    dns_servers: List[str] = field(default_factory=list)
    dns_latency_ms: Optional[float] = None

    # 7. Overall diagnostic & freshness metadata
    diagnostic_status: str = "waiting"  # "healthy" | "degraded" | "incomplete" | "disconnected" | "waiting"
    last_updated_utc: Optional[datetime] = None

    @property
    def is_local_link_up(self) -> bool:
        """True if an adapter, Wi-Fi association, or non-loopback local IP/gateway exists."""
        has_local_ip = bool(self.local_ip and not str(self.local_ip).startswith("127."))
        return bool(self.adapter_connected or self.wifi_associated or self.gateway_ip or has_local_ip)

    def format_status_badge(self, lang: str = "ar") -> Tuple[Any, str]:
        """Return honest, compound top-bar / header status badge reflecting all 7 layers.

        Never reports 'Disconnected' when adapter/Wi-Fi is locally associated.
        """
        from app.ui.tokens import SystemStatus

        is_ar = (lang == "ar")
        if not self.is_local_link_up:
            return (
                SystemStatus.NOT_CONNECTED,
                "غير متصل بالشبكة" if is_ar else "Disconnected",
            )

        link_ar = "واي فاي متصل" if (self.wifi_associated or self.medium == "wifi") else "الشبكة متصلة"
        link_en = "Wi-Fi Connected" if (self.wifi_associated or self.medium == "wifi") else "Adapter Connected"

        if self.gateway_reachable is False:
            return (
                SystemStatus.WARNING,
                f"{link_ar} · البوابة غير مستجيبة" if is_ar else f"{link_en} · Gateway Unreachable",
            )

        if self.internet_available is False:
            return (
                SystemStatus.WARNING,
                f"{link_ar} · بدون إنترنت" if is_ar else f"{link_en} · No Internet",
            )

        if self.dns_available is False:
            return (
                SystemStatus.WARNING,
                f"{link_ar} · تعذر استجابة DNS" if is_ar else f"{link_en} · DNS Unavailable",
            )

        if self.internet_available is True and (self.gateway_reachable is True or self.gateway_ip):
            return (
                SystemStatus.HEALTHY,
                f"{link_ar} · الإنترنت متاح" if is_ar else f"{link_en} · Internet OK",
            )

        return (
            SystemStatus.RUNNING,
            f"{link_ar} · جاري التحقق" if is_ar else f"{link_en} · Verifying",
        )

    def evaluate_diagnostic_status(self) -> Tuple[Optional[int], Any, str]:
        """Compute deterministic, non-fabricated health score from current measured state.

        - If disconnected locally -> (0, FAILED, Disconnected).
        - If internet or gateway explicitly failed -> caps score strictly below healthy threshold
          and flags failure/degradation instead of reporting 97% Healthy.
        - If core probes are missing/unavailable -> returns (None, WAITING, Incomplete Measurement).
        """
        from app.ui.tokens import SystemStatus

        if not self.is_local_link_up:
            return 0, SystemStatus.FAILED, "لا يوجد اتصال نشط بمحول الشبكة أو الواي فاي."

        # Explicit link/internet outage overrides smooth numbers from unrelated probes
        if self.gateway_reachable is False:
            return 25, SystemStatus.FAILED, "الاتصال المحلي نشط لكن البوابة الافتراضية (الراوتر) لا تستجيب."

        if self.internet_available is False or (
            self.external_packet_loss_pct is not None and self.external_packet_loss_pct >= 99.0
        ):
            return 35, SystemStatus.FAILED, "الشبكة المحلية متصلة ولكن لا يوجد وصول فعلي إلى الإنترنت الخارجي."

        measured_count = sum(
            1
            for v in (
                self.gateway_latency_ms,
                self.external_latency_ms,
                self.external_packet_loss_pct,
                self.dns_latency_ms,
            )
            if v is not None
        )
        if measured_count < 2 and self.external_latency_ms is None:
            return None, SystemStatus.WAITING, "القياس غير مكتمل — بانتظار استكمال فحوصات البوابة والإنترنت."

        score = 100.0
        notes: List[str] = []

        if self.gateway_latency_ms is not None and self.gateway_latency_ms > 15.0:
            score -= min(22.0, (self.gateway_latency_ms - 15.0) * 0.5)
            if self.gateway_latency_ms >= 35.0:
                notes.append("كمون البوابة/الراوتر مرتفع")

        if self.external_latency_ms is not None:
            warn_ms = float(DEFAULT_THRESHOLDS.latency.external_warning_ms)
            if self.external_latency_ms > warn_ms:
                score -= min(30.0, (self.external_latency_ms - warn_ms) * 0.25)
                notes.append("استجابة الإنترنت بطيئة")

        if self.external_packet_loss_pct is not None and self.external_packet_loss_pct > 0.0:
            score -= min(45.0, self.external_packet_loss_pct * 4.0)
            notes.append(f"فقدان حزم {self.external_packet_loss_pct:.1f}%")

        if self.jitter_ms is not None and self.jitter_ms > 15.0:
            score -= min(15.0, (self.jitter_ms - 15.0) * 0.5)

        if self.dns_available is False:
            score -= 25.0
            notes.append("خدمة DNS غير مستجيبة")
        elif self.dns_latency_ms is not None and self.dns_latency_ms > 45.0:
            score -= min(14.0, (self.dns_latency_ms - 45.0) * 0.12)
            if self.dns_latency_ms >= 80.0:
                notes.append("استجابة DNS مرتفعة")

        if self.signal_quality_pct is not None and self.signal_quality_pct < 60.0:
            score -= min(18.0, (60.0 - self.signal_quality_pct) * 0.45)
            notes.append("إشارة الواي فاي ضعيفة")

        final = max(0, min(100, int(round(score))))
        if self.dns_available is False or final < 55:
            status = SystemStatus.FAILED if final < 55 else SystemStatus.WARNING
            summary = " · ".join(notes[:2]) if notes else "تم رصد خلل يؤثر على جودة الاتصال."
        elif final >= 80:
            status = SystemStatus.HEALTHY
            summary = "جميع المسارات (المحول، البوابة، الإنترنت، DNS) تعمل ضمن الحدود المستقرة."
        else:
            status = SystemStatus.WARNING
            summary = " · ".join(notes[:2]) if notes else "انخفاض جزئي في جودة الاتصال."
        return final, status, summary


def normalize_network_identity_payload(info: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize heterogeneous keys from Windows network probe (`iface` vs `interface_name`, etc.)."""
    raw = dict(info or {})
    iface = str(raw.get("interface_name") or raw.get("iface") or raw.get("adapter_name") or "").strip()
    gw = str(raw.get("gateway_ip") or raw.get("gateway") or raw.get("default_gateway") or "").strip()
    ssid = str(raw.get("ssid") or "").strip()
    if ssid.lower() in ("—", "-", "none", "غير متصل"):
        ssid = ""
    is_wifi = bool(raw.get("is_wifi", False) or ssid or ("wi-fi" in iface.lower()) or ("wlan" in iface.lower()))
    dns_list = list(raw.get("dns_servers") or raw.get("dns") or [])
    isp_data = raw.get("isp")
    isp_name = ""
    public_ip = str(raw.get("public_ip") or "").strip()
    if isinstance(isp_data, dict):
        isp_name = str(isp_data.get("company") or isp_data.get("isp") or "").strip()
        if not public_ip or public_ip == "—":
            public_ip = str(isp_data.get("ip") or "").strip()
    elif isinstance(isp_data, str):
        isp_name = isp_data.strip()
    if not isp_name:
        isp_name = str(raw.get("isp_company") or "").strip()

    raw["interface_name"] = iface
    raw["iface"] = iface or raw.get("iface")
    raw["gateway_ip"] = gw
    raw["gateway"] = gw or raw.get("gateway")
    raw["dns_servers"] = dns_list
    raw["dns"] = dns_list
    raw["is_wifi"] = is_wifi
    raw["connection_type"] = raw.get("connection_type") or ("Wi-Fi" if is_wifi else ("Ethernet" if iface else "Unknown"))
    raw["ssid"] = ssid or raw.get("ssid")
    if isp_name:
        raw["isp_company"] = isp_name
    if public_ip and public_ip != "—":
        raw["public_ip"] = public_ip
    return raw


class GlobalNetworkStateStore(QObject):
    """Singleton state store broadcasting synchronized connectivity state across views."""

    state_changed = Signal(object)

    _instance: Optional["GlobalNetworkStateStore"] = None
    _lock = threading.Lock()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._state = GlobalNetworkState()
        self._state_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "GlobalNetworkStateStore":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def current(self) -> GlobalNetworkState:
        with self._state_lock:
            return replace(self._state, dns_servers=list(self._state.dns_servers))

    def _emit_updated(self, new_state: GlobalNetworkState) -> GlobalNetworkState:
        new_state.last_updated_utc = datetime.now(timezone.utc)
        _, st, _ = new_state.evaluate_diagnostic_status()
        new_state.diagnostic_status = st.value if hasattr(st, "value") else str(st)
        with self._state_lock:
            self._state = new_state
            snapshot = replace(self._state, dns_servers=list(self._state.dns_servers))
        try:
            self.state_changed.emit(snapshot)
        except RuntimeError:
            pass
        return snapshot

    def update_from_network_info(self, info: Dict[str, Any]) -> GlobalNetworkState:
        norm = normalize_network_identity_payload(info)
        with self._state_lock:
            st = replace(self._state, dns_servers=list(self._state.dns_servers))

        iface = norm.get("interface_name") or ""
        gw = norm.get("gateway_ip") or ""
        local_ip = str(norm.get("local_ip") or "").strip()
        if local_ip in ("—", "-", ""):
            local_ip = ""
        ssid = str(norm.get("ssid") or "").strip()
        if ssid.lower() in ("—", "-", "none", "غير متصل"):
            ssid = ""

        st.adapter_name = iface or st.adapter_name
        st.medium = "wifi" if norm.get("is_wifi") else ("ethernet" if iface else st.medium)
        st.local_ip = local_ip or None
        st.gateway_ip = gw or None
        st.adapter_connected = bool(iface or gw or (local_ip and not local_ip.startswith("127.")))
        st.wifi_associated = bool(ssid or (st.wifi_associated and st.medium == "wifi" and st.adapter_connected))
        if ssid:
            st.ssid = ssid
        elif not st.adapter_connected:
            st.ssid = None

        band = str(norm.get("band") or "").strip()
        if band and band != "—":
            st.band = band
        sig_raw = str(norm.get("signal") or "").replace("%", "").strip()
        if sig_raw.isdigit():
            st.signal_quality_pct = float(sig_raw)

        dns_list = norm.get("dns_servers") or []
        if dns_list:
            st.dns_servers = list(dns_list)

        pub = norm.get("public_ip")
        isp = norm.get("isp_company")
        if pub and pub != "—":
            st.public_ip = str(pub)
            st.internet_available = True
        if isp and isp not in ("—", "غير متوفر", "غير متصل"):
            st.isp_name = str(isp)
        elif not st.adapter_connected:
            st.internet_available = False
            st.gateway_reachable = False
        return self._emit_updated(st)

    def update_from_wifi_telemetry(self, tel: Any) -> GlobalNetworkState:
        if tel is None:
            return self.current
        with self._state_lock:
            st = replace(self._state, dns_servers=list(self._state.dns_servers))

        conn_state = str(getattr(tel, "connection_state", "") or "").lower()
        ssid = getattr(tel, "ssid", None)
        connected = bool(getattr(tel, "connected", False)) or conn_state == "connected" or bool(ssid)
        st.wifi_associated = connected
        if connected:
            st.adapter_connected = True
            st.medium = "wifi"
        if getattr(tel, "interface_name", None):
            st.adapter_name = str(getattr(tel, "interface_name"))
        st.ssid = str(ssid) if ssid else (st.ssid if connected else None)
        st.bssid = getattr(tel, "bssid", None)
        st.band = getattr(tel, "band", None) or st.band
        st.channel = getattr(tel, "channel", None) or st.channel
        st.rssi_dbm = getattr(tel, "rssi_dbm", None)
        sig = getattr(tel, "signal_quality_pct", getattr(tel, "signal_percent", None))
        if sig is not None:
            st.signal_quality_pct = float(sig)
        st.rx_rate_mbps = getattr(tel, "rx_link_rate_mbps", getattr(tel, "rx_rate_mbps", None))
        st.tx_rate_mbps = getattr(tel, "tx_link_rate_mbps", getattr(tel, "tx_rate_mbps", None))
        return self._emit_updated(st)

    def update_from_measurements(
        self,
        *,
        gw_ms: Optional[float] = None,
        gw_loss_pct: Optional[float] = None,
        ext_ms: Optional[float] = None,
        ext_loss_pct: Optional[float] = None,
        jitter_ms: Optional[float] = None,
        dns_ms: Optional[float] = None,
        probe_error: Optional[str] = None,
    ) -> GlobalNetworkState:
        with self._state_lock:
            st = replace(self._state, dns_servers=list(self._state.dns_servers))

        if gw_ms is not None:
            st.gateway_latency_ms = float(gw_ms)
            st.gateway_reachable = True
        if gw_loss_pct is not None:
            st.gateway_loss_pct = float(gw_loss_pct)
            if gw_loss_pct >= 99.0 and gw_ms is None:
                st.gateway_reachable = False

        if ext_ms is not None:
            st.external_latency_ms = float(ext_ms)
        if ext_loss_pct is not None:
            st.external_packet_loss_pct = float(ext_loss_pct)
        if jitter_ms is not None:
            st.jitter_ms = float(jitter_ms)

        # Explicitly deduce internet availability without conflating local link
        if ext_loss_pct is not None and ext_loss_pct >= 99.0:
            st.internet_available = False
        elif ext_ms is not None and (ext_loss_pct is None or ext_loss_pct < 99.0):
            st.internet_available = True
        elif probe_error and ("gateway" in probe_error.lower() or "unreachable" in probe_error.lower()):
            if st.gateway_reachable is None:
                st.gateway_reachable = False

        if dns_ms is not None:
            st.dns_latency_ms = float(dns_ms)
            st.dns_available = dns_ms < 2500.0

        return self._emit_updated(st)

    def update_router_reachability(
        self,
        *,
        reachable: bool,
        model: Optional[str] = None,
        url: Optional[str] = None,
    ) -> GlobalNetworkState:
        with self._state_lock:
            st = replace(self._state, dns_servers=list(self._state.dns_servers))
        st.router_reachable = bool(reachable)
        if reachable:
            st.gateway_reachable = True
        if model:
            st.router_model = model
        if url:
            st.router_url = url
        return self._emit_updated(st)
