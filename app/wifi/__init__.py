"""Wi-Fi, Network, Speed/Bufferbloat, Root-Cause, Optimization, and Router Management suite for NetGuard AI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.wifi.bufferbloat_diagnostics import BufferbloatAnalyzer, BufferbloatDiagnosticsService
from app.wifi.channel_analysis import ChannelAnalysisEngine
from app.wifi.coordinator import DiagnosticCoordinator
from app.wifi.device_management import ConnectedDeviceDiscoveryService, DeviceManagementService
from app.wifi.dns_diagnostics import DnsDiagnosticsService
from app.wifi.network_diagnostics import NetworkDiagnosticsService
from app.wifi.nl_commands import NaturalLanguageCommandService
from app.wifi.optimization import (
    ActionHistoryStore,
    ConfigurationBackupService,
    ConfigurationVerificationService,
    OptimizationPlanner,
    RollbackManager,
    RouterConfigurationWriter,
)
from app.wifi.qos_compatibility import QoSCompatibilityAnalyzer
from app.wifi.recommendations import UnifiedDiagnosticAnalyzer
from app.wifi.report_service import NetworkHealthReportService
from app.wifi.reporting import BeforeAfterReportingService
from app.wifi.root_cause import RootCauseAnalysisService
from app.wifi.router.adapters.registry import RouterAdapterRegistry
from app.wifi.router.adapters.web_dom_inspector import RouterWebDomInspector
from app.wifi.router.analyzer import RouterConfigAnalyzer, RouterConfigurationAnalyzer
from app.wifi.router.auth import RouterAuthCoordinator
from app.wifi.router.discovery import RouterDiscoveryService
from app.wifi.router.fingerprint import RouterCapabilityDetector, RouterFingerprintService
from app.wifi.router.inspection import RouterPageInspectionService
from app.wifi.scanner import AccessPointScanner
from app.wifi.speed_test import InternetSpeedTestService, SpeedTestService
from app.wifi.telemetry import WifiRoamTracker, WifiTelemetryService


@dataclass
class WifiDiagnosticsBundle:
    """Coordinated bundle of all Wi-Fi, Network, DNS, Speed, Optimization, and Router services."""

    coordinator: DiagnosticCoordinator
    telemetry: WifiTelemetryService
    scanner: AccessPointScanner
    channel_analyzer: ChannelAnalysisEngine
    network_diag: NetworkDiagnosticsService
    dns_diag: DnsDiagnosticsService
    speed_test: SpeedTestService
    bufferbloat: BufferbloatDiagnosticsService
    router_registry: RouterAdapterRegistry
    router_discovery: RouterDiscoveryService
    router_auth: RouterAuthCoordinator
    router_analyzer: RouterConfigAnalyzer
    device_manager: DeviceManagementService
    recommender: UnifiedDiagnosticAnalyzer
    reporting: BeforeAfterReportingService
    router_fingerprint: RouterFingerprintService = field(default_factory=RouterFingerprintService)
    router_inspector: RouterPageInspectionService = field(default_factory=RouterPageInspectionService)
    root_cause: RootCauseAnalysisService = field(default_factory=RootCauseAnalysisService)
    qos_compat: QoSCompatibilityAnalyzer = field(default_factory=QoSCompatibilityAnalyzer)
    optimization: OptimizationPlanner = field(default_factory=OptimizationPlanner)
    nl_commands: NaturalLanguageCommandService = field(default_factory=NaturalLanguageCommandService)
    report_service: NetworkHealthReportService = field(default_factory=NetworkHealthReportService)
    dom_inspector: RouterWebDomInspector = field(default_factory=RouterWebDomInspector)


def build_wifi_bundle(app_core: Any = None, *, allow_loopback: bool = False) -> WifiDiagnosticsBundle:
    """Construct and attach Wi-Fi diagnostic services to app_core without breaking existing state."""
    existing = getattr(app_core, "wifi_bundle", None)
    if isinstance(existing, WifiDiagnosticsBundle):
        return existing

    ctx = getattr(app_core, "ctx", None) if app_core is not None else None
    platform = getattr(ctx, "platform", None) if ctx is not None else None
    event_bus = getattr(ctx, "event_bus", None) if ctx is not None else None
    db_manager = getattr(ctx, "db", None) if ctx is not None else None
    traffic_ctrl = getattr(app_core, "traffic_controller", None) if app_core is not None else None

    coordinator = DiagnosticCoordinator(
        traffic_controller=traffic_ctrl, platform=platform, event_bus=event_bus
    )
    telemetry = WifiTelemetryService(roam_tracker=WifiRoamTracker())
    scanner = AccessPointScanner(coordinator=coordinator)
    channel_analyzer = ChannelAnalysisEngine()
    network_diag = NetworkDiagnosticsService(
        platform=platform, coordinator=coordinator, wifi_telemetry=telemetry
    )
    dns_diag = DnsDiagnosticsService(platform=platform, coordinator=coordinator)
    speed_test = SpeedTestService(coordinator=coordinator, wifi_telemetry=telemetry)
    bufferbloat = BufferbloatDiagnosticsService(platform=platform, coordinator=coordinator)
    router_registry = RouterAdapterRegistry(allow_loopback=allow_loopback)
    router_discovery = RouterDiscoveryService(
        platform=platform, registry=router_registry, allow_loopback=allow_loopback
    )
    router_auth = RouterAuthCoordinator(allow_loopback=allow_loopback)
    router_analyzer = RouterConfigAnalyzer()
    device_manager = DeviceManagementService(platform=platform, coordinator=coordinator)
    recommender = UnifiedDiagnosticAnalyzer()
    reporting = BeforeAfterReportingService(db_manager=db_manager)
    optimization = OptimizationPlanner(coordinator=coordinator, auto_allowed_categories=set())

    bundle = WifiDiagnosticsBundle(
        coordinator=coordinator,
        telemetry=telemetry,
        scanner=scanner,
        channel_analyzer=channel_analyzer,
        network_diag=network_diag,
        dns_diag=dns_diag,
        speed_test=speed_test,
        bufferbloat=bufferbloat,
        router_registry=router_registry,
        router_discovery=router_discovery,
        router_auth=router_auth,
        router_analyzer=router_analyzer,
        device_manager=device_manager,
        recommender=recommender,
        reporting=reporting,
        optimization=optimization,
    )
    if app_core is not None:
        try:
            setattr(app_core, "wifi_bundle", bundle)
        except Exception:
            pass
    return bundle


__all__ = [
    "AccessPointScanner",
    "ActionHistoryStore",
    "BeforeAfterReportingService",
    "BufferbloatAnalyzer",
    "BufferbloatDiagnosticsService",
    "ChannelAnalysisEngine",
    "ConfigurationBackupService",
    "ConfigurationVerificationService",
    "ConnectedDeviceDiscoveryService",
    "DeviceManagementService",
    "DiagnosticCoordinator",
    "DnsDiagnosticsService",
    "InternetSpeedTestService",
    "NaturalLanguageCommandService",
    "NetworkDiagnosticsService",
    "NetworkHealthReportService",
    "OptimizationPlanner",
    "QoSCompatibilityAnalyzer",
    "RollbackManager",
    "RootCauseAnalysisService",
    "RouterAdapterRegistry",
    "RouterAuthCoordinator",
    "RouterCapabilityDetector",
    "RouterConfigAnalyzer",
    "RouterConfigurationAnalyzer",
    "RouterConfigurationWriter",
    "RouterDiscoveryService",
    "RouterFingerprintService",
    "RouterPageInspectionService",
    "RouterWebDomInspector",
    "SpeedTestService",
    "UnifiedDiagnosticAnalyzer",
    "WifiDiagnosticsBundle",
    "WifiRoamTracker",
    "WifiTelemetryService",
    "build_wifi_bundle",
]
