"""Observability Engine and Asynchronous Probe Scheduler."""

from __future__ import annotations
import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from app.core.config.models import ProbingConfig
from app.core.bus import EventBus, EventTopics
from app.core.models.metrics import Measurement, MetricType, ProbeStatus
from app.monitoring.models.probe_result import ProbeResult
from app.monitoring.probes.base import BaseProbe
from app.monitoring.probes.gateway_probe import GatewayProbe
from app.monitoring.probes.external_probe import ExternalConnectivityProbe
from app.monitoring.probes.dns_probe import DNSResolutionProbe
from app.monitoring.probes.interface_probe import InterfaceStatsCollector
from app.monitoring.probes.wifi_probe import WifiMetricsCollector
from app.monitoring.probes.socket_probe import ActiveConnectionCollector
from app.platform.interfaces import IPlatformAdapter
from app.storage.repositories.measurement_repo import MeasurementRepository

logger = logging.getLogger("netguard.monitoring.engine")


class ObservabilityEngine:
    """Coordinates asynchronous probes, normalizes metrics, persists data, and streams to bus."""

    def __init__(
        self,
        config: ProbingConfig,
        event_bus: EventBus,
        platform_adapter: IPlatformAdapter,
        measurement_repo: MeasurementRepository,
        window_size: int = 30,
    ) -> None:
        self.config = config
        self.event_bus = event_bus
        self.platform = platform_adapter
        self.repo = measurement_repo
        self.window_size = window_size

        self._probes: List[BaseProbe] = []
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._sliding_windows: Dict[MetricType, deque[Measurement]] = {
            m: deque(maxlen=window_size) for m in MetricType
        }
        self._probe_health: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

        self._initialize_probes()

    def _initialize_probes(self) -> None:
        """Instantiate configured probes."""
        self._probes = [
            GatewayProbe(
                platform_adapter=self.platform,
                interval_sec=self.config.gateway_interval_sec,
                timeout_sec=self.config.icmp_timeout_sec,
            ),
            ExternalConnectivityProbe(
                platform_adapter=self.platform,
                targets=self.config.external_targets,
                interval_sec=self.config.external_interval_sec,
                timeout_sec=self.config.tcp_timeout_sec,
            ),
            DNSResolutionProbe(
                platform_adapter=self.platform,
                domains=self.config.dns_test_domains,
                interval_sec=self.config.dns_interval_sec,
                timeout_sec=self.config.dns_timeout_sec,
            ),
            InterfaceStatsCollector(
                platform_adapter=self.platform,
                interval_sec=self.config.interface_stats_interval_sec,
            ),
            WifiMetricsCollector(
                platform_adapter=self.platform,
                interval_sec=getattr(self.config, "wifi_interval_sec", 3.0),
            ),
            ActiveConnectionCollector(
                platform_adapter=self.platform,
                interval_sec=self.config.active_connections_interval_sec,
            ),
        ]

    def register_probe(self, probe: BaseProbe) -> None:
        """Register custom probe (e.g. for mock testing or cellular modem)."""
        self._probes.append(probe)

    async def start(self) -> None:
        """Start asynchronous probing loops for all registered probes."""
        if self._running:
            return
        self._running = True
        logger.info("Starting Observability Engine with %d probes...", len(self._probes))

        for probe in self._probes:
            task = asyncio.create_task(self._probe_worker(probe), name=f"worker_{probe.name}")
            self._tasks.append(task)

    async def stop(self) -> None:
        """Gracefully stop all probe workers."""
        if not self._running:
            return
        self._running = False
        logger.info("Stopping Observability Engine workers...")

        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Observability Engine stopped cleanly.")

    async def run_single_cycle(self) -> List[Measurement]:
        """Runs one sample cycle of all registered probes immediately (useful for testing or on-demand)."""
        all_measurements: List[Measurement] = []
        tasks = [probe.run() for probe in self._probes]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        for probe, results in zip(self._probes, results_lists):
            if isinstance(results, Exception):
                self._update_probe_health(probe.name, [], error=results)
            elif isinstance(results, list):
                self._update_probe_health(probe.name, results)
                for pr in results:
                    m = pr.to_measurement()
                    await self._record_measurement(m)
                    all_measurements.append(m)
        return all_measurements

    async def _probe_worker(self, probe: BaseProbe) -> None:
        """Infinite loop worker for an individual probe with interval pacing."""
        while self._running:
            try:
                results = await probe.run()
                self._update_probe_health(probe.name, results)
                for pr in results:
                    m = pr.to_measurement()
                    await self._record_measurement(m)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in probe worker %s: %s", probe.name, exc, exc_info=True)
                self._update_probe_health(probe.name, [], error=exc)

            try:
                await asyncio.sleep(probe.interval_sec)
            except asyncio.CancelledError:
                break

    async def _record_measurement(self, m: Measurement) -> None:
        """Buffers measurement in sliding window, persists to SQLite, and broadcasts to event bus."""
        async with self._lock:
            # Store in sliding window
            if m.metric_type not in self._sliding_windows:
                self._sliding_windows[m.metric_type] = deque(maxlen=self.window_size)
            self._sliding_windows[m.metric_type].append(m)

        # Persist to database asynchronously (via thread executor to prevent blocking async loop)
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self.repo.save, m)
        except Exception as exc:
            logger.warning("Failed to persist measurement %s: %s", m.metric_type.value, exc)

        # Publish event
        topic = f"{EventTopics.TELEMETRY_PREFIX}{m.metric_type.value}"
        await self.event_bus.publish(topic, m)

    def get_sliding_window(self, metric_type: MetricType) -> List[Measurement]:
        """Returns a snapshot of the most recent measurements for the given metric."""
        if metric_type in self._sliding_windows:
            return list(self._sliding_windows[metric_type])
        return []

    def get_latest_measurement(self, metric_type: MetricType) -> Optional[Measurement]:
        """Returns the single most recent measurement for the given metric."""
        window = self._sliding_windows.get(metric_type)
        if window and len(window) > 0:
            return window[-1]
        return None

    def update_probing_interval(self, interval_sec: float) -> None:
        """Dynamically updates the polling interval for running probes live."""
        val = float(interval_sec)
        if val <= 0.0:
            raise ValueError(f"Probing interval must be > 0, got {val}")
        logger.info("Updating observability probing interval to %.2fs", val)
        if hasattr(self.config, "gateway_interval_sec"):
            self.config.gateway_interval_sec = val
        for probe in self._probes:
            if isinstance(probe, (GatewayProbe, ExternalConnectivityProbe, DNSResolutionProbe)):
                probe.interval_sec = val
            elif hasattr(probe, "interval_sec"):
                probe.interval_sec = max(val, getattr(probe, "interval_sec", val))

    def _update_probe_health(
        self,
        probe_name: str,
        results: List[ProbeResult],
        error: Optional[Exception] = None,
    ) -> None:
        """Tracks consecutive failures and categorizes network probe errors."""
        if probe_name not in self._probe_health:
            self._probe_health[probe_name] = {
                "consecutive_failures": 0,
                "error_code": None,
                "error_message": None,
                "severity": "info",
                "last_success": None,
                "last_failure": None,
            }

        rec = self._probe_health[probe_name]
        now = datetime.now(timezone.utc)

        if error is not None:
            rec["consecutive_failures"] += 1
            rec["error_code"] = "probe_exception"
            rec["error_message"] = f"خطأ في مسبار {probe_name}: {error}"
            rec["severity"] = "warning"
            rec["last_failure"] = now
            return

        if probe_name == "gateway_probe":
            reach_results = [r for r in results if r.metric_type == MetricType.GATEWAY_REACHABILITY]
            gw_ok = any(r.status == ProbeStatus.SUCCESS and r.raw_value > 0.0 for r in reach_results)
            if gw_ok:
                rec["consecutive_failures"] = 0
                rec["error_code"] = None
                rec["error_message"] = None
                rec["last_success"] = now
            else:
                rec["consecutive_failures"] += 1
                rec["error_code"] = "cannot_reach_gateway"
                rec["error_message"] = "تعذر الوصول إلى الراوتر (Cannot reach gateway)"
                rec["severity"] = "critical"
                rec["last_failure"] = now

        elif probe_name == "external_probe":
            icmp_results = [r for r in results if r.metric_type == MetricType.EXTERNAL_LATENCY and r.metadata.get("icmp")]
            tcp_results = [r for r in results if r.metric_type == MetricType.EXTERNAL_TCP_CONNECT]
            icmp_ok = any(r.status == ProbeStatus.SUCCESS for r in icmp_results)
            tcp_ok = any(r.status == ProbeStatus.SUCCESS and r.raw_value > 0.0 for r in tcp_results)

            if icmp_ok:
                rec["consecutive_failures"] = 0
                rec["error_code"] = None
                rec["error_message"] = None
                rec["last_success"] = now
            elif tcp_ok:
                # Ping blocked: TCP connects cleanly, but ICMP echo blocked by firewall/ISP
                rec["consecutive_failures"] += 1
                rec["error_code"] = "ping_blocked"
                rec["error_message"] = "حظر بروتوكول البنج (Ping blocked by firewall/ISP)"
                rec["severity"] = "warning"
                rec["last_failure"] = now
            else:
                rec["consecutive_failures"] += 1
                rec["error_code"] = "external_down"
                rec["error_message"] = "تعذر الاتصال الخارجي بالإنترنت (External network unreachable)"
                rec["severity"] = "critical"
                rec["last_failure"] = now

        elif probe_name == "dns_probe":
            dns_results = [r for r in results if r.metric_type == MetricType.DNS_LATENCY]
            dns_ok = any(r.status == ProbeStatus.SUCCESS for r in dns_results)
            if dns_ok:
                rec["consecutive_failures"] = 0
                rec["error_code"] = None
                rec["error_message"] = None
                rec["last_success"] = now
            else:
                rec["consecutive_failures"] += 1
                rec["error_code"] = "dns_failed"
                rec["error_message"] = "تعذر استجابة خادم DNS (DNS resolution failed)"
                rec["severity"] = "warning"
                rec["last_failure"] = now

        elif probe_name == "wifi_metrics_collector":
            if not results:
                # If Ethernet is primary, Wi-Fi probe returns [] legitimately
                pass
            else:
                wifi_ok = any(r.status in (ProbeStatus.SUCCESS, ProbeStatus.DEGRADED) for r in results)
                if wifi_ok:
                    rec["consecutive_failures"] = 0
                    rec["error_code"] = None
                    rec["error_message"] = None
                    rec["last_success"] = now
                else:
                    rec["consecutive_failures"] += 1
                    rec["error_code"] = "wifi_error"
                    rec["error_message"] = "تعذر قراءة بيانات محول Wi-Fi (Wi-Fi adapter unreachable)"
                    rec["severity"] = "warning"
                    rec["last_failure"] = now
        else:
            any_fail = any(r.status in (ProbeStatus.FAILED, ProbeStatus.TIMEOUT) for r in results)
            if any_fail or not results:
                rec["consecutive_failures"] += 1
                rec["error_code"] = "probe_failure"
                rec["error_message"] = f"فشل مسبار {probe_name}"
                rec["severity"] = "warning"
                rec["last_failure"] = now
            else:
                rec["consecutive_failures"] = 0
                rec["error_code"] = None
                rec["error_message"] = None
                rec["last_success"] = now

    def get_active_probe_errors(self, threshold: int = 3) -> List[Dict[str, Any]]:
        """Returns list of active persistent probe errors whose consecutive failures >= threshold."""
        errors: List[Dict[str, Any]] = []
        for name, data in self._probe_health.items():
            if data["consecutive_failures"] >= threshold and data.get("error_message"):
                errors.append({
                    "probe_name": name,
                    "code": data["error_code"],
                    "message": data["error_message"],
                    "severity": data["severity"],
                    "consecutive_failures": data["consecutive_failures"],
                    "last_failure": data["last_failure"],
                })
        return errors

    def get_primary_probe_error(self, threshold: int = 3) -> Optional[Dict[str, Any]]:
        """Returns the highest priority active persistent probe error, or None if healthy."""
        active = self.get_active_probe_errors(threshold=threshold)
        if not active:
            return None

        priority_map = {
            "cannot_reach_gateway": 1,
            "external_down": 2,
            "ping_blocked": 3,
            "dns_failed": 4,
            "wifi_error": 5,
            "probe_exception": 6,
            "probe_failure": 7,
        }
        active.sort(key=lambda x: priority_map.get(x["code"], 99))
        return active[0]

    def get_primary_probe_error_message(self, threshold: int = 3) -> Optional[str]:
        """Returns the human-readable message of the primary active probe error, or None."""
        err = self.get_primary_probe_error(threshold=threshold)
        return err["message"] if err else None
