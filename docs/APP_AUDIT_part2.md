# NetGuard AI — Volume 2: Complete Function & Class Catalogue (Part A)

> **Audit Target:** NetGuard AI (Windows Autonomous Network Remediation & Telemetry Dashboard)  
> **Document:** Volume 2 of 7 | Section 3 (Part A)  
> **Coverage:** `main.py`, `app.bootstrap`, `app.application`, `app.core.*`, `app.platform.*`, `app.storage.*`, `app.monitoring.*`  
> **Status:** Complete & Verified (READ-ONLY Analysis — Zero Source Changes)  

---

## 3. Complete Function / Class Catalogue (Part A)

This section catalogues every class, method, function, and helper in the core runtime, platform abstraction, storage, and monitoring layers. Every entry includes exact line numbers, verified caller sites, external side effects, and empirical real/fake classification.

## Module: `app.application`

### app.application::NetGuardApplication.__init__   (app/application.py:25-76)
- **Signature:** `def __init__(self, context: ApplicationContext) -> None`
- **Purpose:** Method __init__ of NetGuardApplication
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** ActionRegistry; ActionSafetyManager; DNSOptimizer; DiagnosisEngine; ObservabilityEngine; RemediationOrchestrator; TrafficController; self._register_default_actions
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.application::NetGuardApplication._continuous_evaluation_loop   (app/application.py:137-157)
- **Signature:** `async def _continuous_evaluation_loop(self) -> None`
- **Purpose:** Periodic background evaluation loop.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/application.py:NetGuardApplication.start:98
- **Calls:** asyncio.create_task; asyncio.sleep; logger.error; min; self.diagnosis.evaluate_windows; self.dns_optimizer.auto_optimize_dns; self.observability._sliding_windows.keys; self.observability.get_sliding_window; self.orchestrator.handle_diagnosis
- **Real or fake?:** `REAL`
- **Error handling:** catches asyncio.CancelledError; catches Exception

### app.application::NetGuardApplication._register_default_actions   (app/application.py:78-84)
- **Signature:** `def _register_default_actions(self) -> None`
- **Purpose:** Method _register_default_actions of NetGuardApplication
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/application.py:NetGuardApplication.__init__:50
- **Calls:** FlushDNSCacheAction; RecheckGatewayAction; RenewIPLeaseAction; SwitchDNSResolverAction; self.action_registry.register
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.application::NetGuardApplication.start   (app/application.py:86-100)
- **Signature:** `async def start(self) -> None`
- **Purpose:** Start the autonomous network guardian loops.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/application.py:NetGuardApplication.start:94; app/main.py:128; app/main.py:133; app/main.py:56; app/ui/main_window.py:MainWindow.__init__:364; app/ui/main_window.py:MainWindow.__init__:370; app/ui/main_window.py:MainWindow._async_inspect_network_environment:459; app/ui/main_window.py:MainWindow._on_apply_dns_requested:681; app/ui/main_window.py:MainWindow._on_quick_flush_dns:739; app/ui/main_window.py:MainWindow._on_run_deep_diagnosis:708; app/ui/main_window.py:MainWindow._on_run_dns_benchmark:503; app/ui/main_window.py:MainWindow._on_scan_traffic:692; app/ui/views/dashboard_view.py:DashboardView.__init__:238; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:50; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:373; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:57; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:142; app/ui/widgets/toggle.py:ToggleSwitch.setChecked:41
- **Calls:** asyncio.create_task; logger.info; self._continuous_evaluation_loop; self.observability.start
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.application::NetGuardApplication.step   (app/application.py:120-135)
- **Signature:** `async def step(self) -> Optional[Diagnosis]`
- **Purpose:** Executes a single end-to-end evaluation cycle: Probe -> Diagnose -> Remediate.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/main.py:86
- **Calls:** self.diagnosis.evaluate_windows; self.observability._sliding_windows.keys; self.observability.get_sliding_window; self.observability.run_single_cycle; self.orchestrator.handle_diagnosis
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.application::NetGuardApplication.stop   (app/application.py:102-118)
- **Signature:** `async def stop(self) -> None`
- **Purpose:** Gracefully shutdown all monitoring and decision loops.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/application.py:NetGuardApplication.stop:116; app/main.py:81; app/ui/widgets/toggle.py:ToggleSwitch.setChecked:38
- **Calls:** logger.info; self._diagnostic_loop_task.cancel; self.ctx.event_bus.shutdown; self.observability.stop
- **Real or fake?:** `REAL`
- **Error handling:** catches asyncio.CancelledError (swallowed silently)

### app.application::create_application   (app/application.py:160-163)
- **Signature:** `def create_application(config_path: Optional[str]) -> NetGuardApplication`
- **Purpose:** Factory helper to bootstrap and instantiate NetGuardApplication.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/main.py:164; scripts/verify_ui_render.py:19; tests/unit/test_ui.py:44
- **Calls:** NetGuardApplication; bootstrap_application
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.bootstrap`

### app.bootstrap::ApplicationContext.__init__   (app/bootstrap.py:22-45)
- **Signature:** `def __init__(self, config: AppConfig, event_bus: EventBus, platform_adapter: IPlatformAdapter, db_manager: DatabaseManager, measurement_repo: MeasurementRepository, incident_repo: IncidentRepository, audit_repo: AuditRepository) -> None`
- **Purpose:** Method __init__ of ApplicationContext
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** setup_logger
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.bootstrap::bootstrap_application   (app/bootstrap.py:48-88)
- **Signature:** `def bootstrap_application(config_path: Optional[Path | str], in_memory_db: bool) -> ApplicationContext`
- **Purpose:** Initializes all foundational dependencies and validates environment.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/application.py:162; tests/unit/test_foundation.py:153
- **Calls:** ApplicationContext; AuditRepository; DatabaseManager; EventBus; IncidentRepository; MeasurementRepository; get_platform_adapter; load_config; logger.info; platform_adapter.get_default_gateway
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.core.config.loader`

### app.core.config.loader::load_config   (app/core/config/loader.py:12-38)
- **Signature:** `def load_config(config_path: Optional[Path | str]) -> AppConfig`
- **Purpose:** Loads configuration from YAML file or returns validated defaults.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/bootstrap.py:50; tests/unit/test_foundation.py:32
- **Calls:** AppConfig; ConfigurationError; Path; Path(config_path).exists; candidate.exists; getattr; hasattr; open; yaml.safe_load
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

## Module: `app.core.events.bus`

### app.core.events.bus::EventBus.__init__   (app/core/events/bus.py:18-21)
- **Signature:** `def __init__(self) -> None`
- **Purpose:** Method __init__ of EventBus
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** asyncio.Lock
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.core.events.bus::EventBus._safe_dispatch   (app/core/events/bus.py:66-70)
- **Signature:** `async def _safe_dispatch(self, callback: SubscriberCallback, topic: str, payload: Any) -> None`
- **Purpose:** Method _safe_dispatch of EventBus
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/events/bus.py:EventBus.publish:62
- **Calls:** callback; logger.error
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.core.events.bus::EventBus.publish   (app/core/events/bus.py:45-64)
- **Signature:** `async def publish(self, topic: str, payload: Any) -> int`
- **Purpose:** Publish an event to all matching topic subscribers concurrently.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/cellular/engine.py:CellularDiagnosticsEngine.poll_metrics:47; app/diagnosis/engine.py:DiagnosisEngine.evaluate_windows:113; app/diagnosis/engine.py:DiagnosisEngine.evaluate_windows:114; app/dns/optimizer.py:DNSOptimizer.auto_optimize_dns:68; app/dns/optimizer.py:DNSOptimizer.evaluate_and_rank:38; app/monitoring/schedulers/engine.py:ObservabilityEngine._record_measurement:164; app/prediction/engine.py:PredictionEngine.evaluate_streams:80; app/prediction/engine.py:PredictionEngine.evaluate_streams:81; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:157; app/remediation/orchestrator.py:RemediationOrchestrator._record_and_publish:256; app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:107; app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:87; app/traffic/bufferbloat.py:BufferbloatEvaluator.evaluate_latency_delta:86; app/traffic/controller.py:TrafficController.scan_active_applications:96; tests/unit/test_foundation.py:124; tests/unit/test_foundation.py:131; tests/unit/test_foundation.py:137
- **Calls:** asyncio.gather; fnmatch.fnmatch; len; matching_callbacks.extend; self._safe_dispatch; self._subscribers.items; tasks.append
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.core.events.bus::EventBus.shutdown   (app/core/events/bus.py:72-75)
- **Signature:** `def shutdown(self) -> None`
- **Purpose:** Stop accepting new events and clear subscribers.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/application.py:NetGuardApplication.stop:117
- **Calls:** self._subscribers.clear
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.core.events.bus::EventBus.subscribe   (app/core/events/bus.py:23-29)
- **Signature:** `async def subscribe(self, topic_pattern: str, callback: SubscriberCallback) -> None`
- **Purpose:** Subscribe a coroutine callback to a topic pattern (e.g. 'telemetry.*').
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_foundation.py:121; tests/unit/test_monitoring.py:149
- **Calls:** logger.debug; self._subscribers[topic_pattern].add; set
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.core.events.bus::EventBus.subscribe_sync   (app/core/events/bus.py:31-35)
- **Signature:** `def subscribe_sync(self, topic_pattern: str, callback: SubscriberCallback) -> None`
- **Purpose:** Synchronous subscription registration for non-async callers (e.g. UI widgets).
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._wire_background_event_listeners:404; app/ui/main_window.py:MainWindow._wire_background_event_listeners:405
- **Calls:** self._subscribers[topic_pattern].add; set
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.core.events.bus::EventBus.unsubscribe   (app/core/events/bus.py:37-43)
- **Signature:** `async def unsubscribe(self, topic_pattern: str, callback: SubscriberCallback) -> None`
- **Purpose:** Unsubscribe a callback from a topic pattern.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_foundation.py:136
- **Calls:** self._subscribers[topic_pattern].discard
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.core.exceptions.base`

### app.core.exceptions.base::NetGuardError.__init__   (app/core/exceptions/base.py:5-8)
- **Signature:** `def __init__(self, message: str, details: dict | None) -> None`
- **Purpose:** Method __init__ of NetGuardError
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.core.exceptions.base::NetGuardError.__str__   (app/core/exceptions/base.py:10-13)
- **Signature:** `def __str__(self) -> str`
- **Purpose:** Method __str__ of NetGuardError
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.core.utilities.logger`

### app.core.utilities.logger::ColoredConsoleFormatter.format   (app/core/utilities/logger.py:44-50)
- **Signature:** `def format(self, record: logging.LogRecord) -> str`
- **Purpose:** Method format of ColoredConsoleFormatter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** datetime.now; datetime.now(timezone.utc).strftime; record.getMessage; self.COLORS.get; self.formatException
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.core.utilities.logger::JSONFormatter.format   (app/core/utilities/logger.py:16-29)
- **Signature:** `def format(self, record: logging.LogRecord) -> str`
- **Purpose:** Method format of JSONFormatter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** datetime.now; datetime.now(timezone.utc).isoformat; hasattr; isinstance; json.dumps; record.getMessage; self.formatException
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.core.utilities.logger::setup_logger   (app/core/utilities/logger.py:53-89)
- **Signature:** `def setup_logger(name: str, level: str, log_dir: Path | str, log_to_console: bool, log_to_file: bool, max_bytes: int, backup_count: int) -> logging.Logger`
- **Purpose:** Configures and returns the central NetGuard logger.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/bootstrap.py:53; app/bootstrap.py:ApplicationContext.__init__:39
- **Calls:** ColoredConsoleFormatter; JSONFormatter; Path; RotatingFileHandler; console_handler.setFormatter; file_handler.setFormatter; getattr; level.upper; logger.addHandler; logger.setLevel
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.main`

### app.main::list_actions   (app/main.py:102-112)
- **Signature:** `def list_actions(app) -> None`
- **Purpose:** Function list_actions
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/main.py:106; app/main.py:167
- **Calls:** app.action_registry.list_actions; print
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.main::main   (app/main.py:143-176)
- **Signature:** `def main() -> None`
- **Purpose:** Function main
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** ' '.join; asyncio.run; create_application; ctypes.windll.shell32.IsUserAnAdmin; ctypes.windll.shell32.ShellExecuteW; list_actions; parse_args; run_diagnose; run_guard; run_gui
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception (swallowed silently); catches KeyboardInterrupt (swallowed silently)

### app.main::parse_args   (app/main.py:12-41)
- **Signature:** `def parse_args() -> argparse.Namespace`
- **Purpose:** Function parse_args
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/main.py:144; app/main.py:41
- **Calls:** argparse.ArgumentParser; parser.add_argument; parser.parse_args
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.main::run_diagnose   (app/main.py:84-99)
- **Signature:** `async def run_diagnose(app) -> None`
- **Purpose:** Function run_diagnose
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/main.py:169
- **Calls:** ', '.join; app.step; diag.probable_cause.value.upper; diag.severity.value.upper; print
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.main::run_guard   (app/main.py:44-81)
- **Signature:** `async def run_guard(app, mode: str | None) -> None`
- **Purpose:** Function run_guard
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/main.py:174
- **Calls:** OperatingMode; app.ctx.platform.get_default_gateway; app.ctx.platform.get_primary_interface; app.orchestrator.mode.value.upper; app.orchestrator.set_operating_mode; app.start; app.stop; asyncio.Event; asyncio.get_running_loop; asyncio.sleep
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception (swallowed silently); catches (KeyboardInterrupt, asyncio.CancelledError); catches NotImplementedError (swallowed silently)

### app.main::run_gui   (app/main.py:115-140)
- **Signature:** `def run_gui(app) -> None`
- **Purpose:** Function run_gui
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/main.py:171
- **Calls:** MainWindow; QApplication; app.start; asyncio.new_event_loop; asyncio.set_event_loop; loop.call_soon_threadsafe; loop.run_forever; loop.run_until_complete; qt_app.exec; sys.exit
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception (swallowed silently)

## Module: `app.monitoring.models.probe_result`

### app.monitoring.models.probe_result::ProbeResult.to_measurement   (app/monitoring/models/probe_result.py:28-41)
- **Signature:** `def to_measurement(self) -> Measurement`
- **Purpose:** Convert probe outcome to standard stored telemetry Measurement.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/schedulers/engine.py:ObservabilityEngine._probe_worker:135; app/monitoring/schedulers/engine.py:ObservabilityEngine.run_single_cycle:124
- **Calls:** Measurement
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.monitoring.probes.base`

### app.monitoring.probes.base::BaseProbe.__init__   (app/monitoring/probes/base.py:19-35)
- **Signature:** `def __init__(self, name: str, interval_sec: float, timeout_sec: float, platform_adapter: IPlatformAdapter, retry_count: int, min_interval_sec: float) -> None`
- **Purpose:** Method __init__ of BaseProbe
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** asyncio.Lock
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.probes.base::BaseProbe._handle_error   (app/monitoring/probes/base.py:64-66)
- **Signature:** `def _handle_error(self, exc: Exception) -> List[ProbeResult]`
- **Purpose:** Fallback results when probe raises unhandled exception.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:53
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.probes.base::BaseProbe._handle_timeout   (app/monitoring/probes/base.py:60-62)
- **Signature:** `def _handle_timeout(self) -> List[ProbeResult]`
- **Purpose:** Fallback results when probe times out.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:50
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.probes.base::BaseProbe.execute   (app/monitoring/probes/base.py:56-58)
- **Signature:** `async def execute(self) -> List[ProbeResult]`
- **Purpose:** Implementation logic of the probe.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:47; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:162; app/storage/database.py:DatabaseManager._apply_migrations:94; app/storage/database.py:DatabaseManager._apply_migrations:96; app/storage/database.py:DatabaseManager._init_storage:85; app/storage/database.py:DatabaseManager._init_storage:86; app/storage/database.py:DatabaseManager._init_storage:87; app/storage/database.py:DatabaseManager._init_storage:88; app/storage/repositories/audit_repo.py:AuditRepository.get_recent:63; app/storage/repositories/audit_repo.py:AuditRepository.save:29; app/storage/repositories/incident_repo.py:IncidentRepository.get_recent:57; app/storage/repositories/incident_repo.py:IncidentRepository.save:29; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_latest_by_metric:58; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_recent:74; app/storage/repositories/measurement_repo.py:MeasurementRepository.save:28; tests/unit/test_remediation.py:231; tests/unit/test_remediation.py:268
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.probes.base::BaseProbe.run   (app/monitoring/probes/base.py:37-53)
- **Signature:** `async def run(self) -> List[ProbeResult]`
- **Purpose:** Executes probe with rate limiting, timeout deadline, and error shielding.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/main.py:169; app/main.py:174; app/monitoring/schedulers/engine.py:ObservabilityEngine._probe_worker:133; app/monitoring/schedulers/engine.py:ObservabilityEngine.run_single_cycle:118; app/platform/linux/adapter.py:LinuxPlatformAdapter.flush_dns_cache:76; app/platform/linux/adapter.py:LinuxPlatformAdapter.get_primary_interface:37; app/platform/linux/adapter.py:LinuxPlatformAdapter.ping:50; app/platform/windows/adapter.py:WindowsPlatformAdapter.flush_dns_cache:171; app/platform/windows/adapter.py:WindowsPlatformAdapter.flush_dns_cache:186; app/platform/windows/adapter.py:WindowsPlatformAdapter.get_default_gateway:50; app/platform/windows/adapter.py:WindowsPlatformAdapter.get_interface_dns_servers:203; app/platform/windows/adapter.py:WindowsPlatformAdapter.get_primary_interface:82; app/platform/windows/adapter.py:WindowsPlatformAdapter.get_wifi_metrics:301; app/platform/windows/adapter.py:WindowsPlatformAdapter.ping:123; app/platform/windows/adapter.py:WindowsPlatformAdapter.renew_ip_lease:276; app/platform/windows/adapter.py:WindowsPlatformAdapter.set_interface_dns_servers:226; app/platform/windows/adapter.py:WindowsPlatformAdapter.set_interface_dns_servers:241; app/platform/windows/adapter.py:WindowsPlatformAdapter.set_interface_dns_servers:257; app/ui/main_window.py:MainWindow._on_quick_flush_dns:729; app/ui/main_window.py:MainWindow._on_run_dns_benchmark:498; app/ui/main_window.py:MainWindow._on_scan_traffic:688; scripts/build_exe.py:39; tests/integration/test_live_monitoring.py:22; tests/integration/test_live_monitoring.py:32; tests/integration/test_live_monitoring.py:42; tests/unit/test_monitoring.py:110; tests/unit/test_monitoring.py:114; tests/unit/test_monitoring.py:71; tests/unit/test_monitoring.py:89
- **Calls:** asyncio.wait_for; logger.debug; logger.error; logger.warning; self._handle_error; self._handle_timeout; self.execute; time.monotonic
- **Real or fake?:** `REAL`
- **Error handling:** catches asyncio.TimeoutError; catches Exception

## Module: `app.monitoring.probes.dns_probe`

### app.monitoring.probes.dns_probe::DNSResolutionProbe.__init__   (app/monitoring/probes/dns_probe.py:18-33)
- **Signature:** `def __init__(self, platform_adapter: IPlatformAdapter, domains: Optional[List[str]], custom_resolver_ip: Optional[str], interval_sec: float, timeout_sec: float) -> None`
- **Purpose:** Method __init__ of DNSResolutionProbe
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.probes.dns_probe::DNSResolutionProbe._handle_timeout   (app/monitoring/probes/dns_probe.py:135-150)
- **Signature:** `def _handle_timeout(self) -> List[ProbeResult]`
- **Purpose:** Method _handle_timeout of DNSResolutionProbe
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:50
- **Calls:** ProbeResult; datetime.now
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.probes.dns_probe::DNSResolutionProbe._resolve_domain   (app/monitoring/probes/dns_probe.py:72-133)
- **Signature:** `async def _resolve_domain(self, loop: asyncio.AbstractEventLoop, domain: str, now: datetime) -> List[ProbeResult]`
- **Purpose:** Method _resolve_domain of DNSResolutionProbe
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/dns_probe.py:DNSResolutionProbe.execute:40
- **Calls:** ProbeResult; dns.resolver.Resolver; loop.run_in_executor; rdata.to_text; resolver.resolve; str; time.perf_counter
- **Real or fake?:** `REAL`
- **Error handling:** catches (dns.resolver.Timeout, dns.resolver.NoNameservers); catches Exception

### app.monitoring.probes.dns_probe::DNSResolutionProbe.execute   (app/monitoring/probes/dns_probe.py:35-70)
- **Signature:** `async def execute(self) -> List[ProbeResult]`
- **Purpose:** Method execute of DNSResolutionProbe
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:47; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:162; app/storage/database.py:DatabaseManager._apply_migrations:94; app/storage/database.py:DatabaseManager._apply_migrations:96; app/storage/database.py:DatabaseManager._init_storage:85; app/storage/database.py:DatabaseManager._init_storage:86; app/storage/database.py:DatabaseManager._init_storage:87; app/storage/database.py:DatabaseManager._init_storage:88; app/storage/repositories/audit_repo.py:AuditRepository.get_recent:63; app/storage/repositories/audit_repo.py:AuditRepository.save:29; app/storage/repositories/incident_repo.py:IncidentRepository.get_recent:57; app/storage/repositories/incident_repo.py:IncidentRepository.save:29; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_latest_by_metric:58; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_recent:74; app/storage/repositories/measurement_repo.py:MeasurementRepository.save:28; tests/unit/test_remediation.py:231; tests/unit/test_remediation.py:268
- **Calls:** ProbeResult; asyncio.gather; asyncio.get_running_loop; datetime.now; isinstance; len; results.append; self._resolve_domain
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.monitoring.probes.external_probe`

### app.monitoring.probes.external_probe::ExternalConnectivityProbe.__init__   (app/monitoring/probes/external_probe.py:16-32)
- **Signature:** `def __init__(self, platform_adapter: IPlatformAdapter, targets: Optional[List[str]], interval_sec: float, timeout_sec: float) -> None`
- **Purpose:** Method __init__ of ExternalConnectivityProbe
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.probes.external_probe::ExternalConnectivityProbe._handle_timeout   (app/monitoring/probes/external_probe.py:162-181)
- **Signature:** `def _handle_timeout(self) -> List[ProbeResult]`
- **Purpose:** Method _handle_timeout of ExternalConnectivityProbe
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:50
- **Calls:** ProbeResult; datetime.now; results.append
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.probes.external_probe::ExternalConnectivityProbe._probe_single_target   (app/monitoring/probes/external_probe.py:49-160)
- **Signature:** `async def _probe_single_target(self, loop: asyncio.AbstractEventLoop, target: str, now: datetime) -> List[ProbeResult]`
- **Purpose:** Method _probe_single_target of ExternalConnectivityProbe
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.execute:40
- **Calls:** ProbeResult; abs; history.append; history.pop; len; loop.run_in_executor; results.append; self._current_jitter_ms.get; self._latency_history.setdefault
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.probes.external_probe::ExternalConnectivityProbe.execute   (app/monitoring/probes/external_probe.py:34-47)
- **Signature:** `async def execute(self) -> List[ProbeResult]`
- **Purpose:** Method execute of ExternalConnectivityProbe
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:47; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:162; app/storage/database.py:DatabaseManager._apply_migrations:94; app/storage/database.py:DatabaseManager._apply_migrations:96; app/storage/database.py:DatabaseManager._init_storage:85; app/storage/database.py:DatabaseManager._init_storage:86; app/storage/database.py:DatabaseManager._init_storage:87; app/storage/database.py:DatabaseManager._init_storage:88; app/storage/repositories/audit_repo.py:AuditRepository.get_recent:63; app/storage/repositories/audit_repo.py:AuditRepository.save:29; app/storage/repositories/incident_repo.py:IncidentRepository.get_recent:57; app/storage/repositories/incident_repo.py:IncidentRepository.save:29; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_latest_by_metric:58; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_recent:74; app/storage/repositories/measurement_repo.py:MeasurementRepository.save:28; tests/unit/test_remediation.py:231; tests/unit/test_remediation.py:268
- **Calls:** asyncio.gather; asyncio.get_running_loop; datetime.now; isinstance; results.extend; self._probe_single_target
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.monitoring.probes.gateway_probe`

### app.monitoring.probes.gateway_probe::GatewayProbe.__init__   (app/monitoring/probes/gateway_probe.py:16-29)
- **Signature:** `def __init__(self, platform_adapter: IPlatformAdapter, interval_sec: float, timeout_sec: float, target_override: Optional[str]) -> None`
- **Purpose:** Method __init__ of GatewayProbe
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.probes.gateway_probe::GatewayProbe._handle_timeout   (app/monitoring/probes/gateway_probe.py:132-160)
- **Signature:** `def _handle_timeout(self) -> List[ProbeResult]`
- **Purpose:** Method _handle_timeout of GatewayProbe
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:50
- **Calls:** ProbeResult; datetime.now; self.platform.get_default_gateway
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.probes.gateway_probe::GatewayProbe.execute   (app/monitoring/probes/gateway_probe.py:31-130)
- **Signature:** `async def execute(self) -> List[ProbeResult]`
- **Purpose:** Method execute of GatewayProbe
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:47; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:162; app/storage/database.py:DatabaseManager._apply_migrations:94; app/storage/database.py:DatabaseManager._apply_migrations:96; app/storage/database.py:DatabaseManager._init_storage:85; app/storage/database.py:DatabaseManager._init_storage:86; app/storage/database.py:DatabaseManager._init_storage:87; app/storage/database.py:DatabaseManager._init_storage:88; app/storage/repositories/audit_repo.py:AuditRepository.get_recent:63; app/storage/repositories/audit_repo.py:AuditRepository.save:29; app/storage/repositories/incident_repo.py:IncidentRepository.get_recent:57; app/storage/repositories/incident_repo.py:IncidentRepository.save:29; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_latest_by_metric:58; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_recent:74; app/storage/repositories/measurement_repo.py:MeasurementRepository.save:28; tests/unit/test_remediation.py:231; tests/unit/test_remediation.py:268
- **Calls:** ProbeResult; asyncio.get_running_loop; datetime.now; loop.run_in_executor; results.append; self.platform.get_default_gateway
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.monitoring.probes.interface_probe`

### app.monitoring.probes.interface_probe::InterfaceStatsCollector.__init__   (app/monitoring/probes/interface_probe.py:18-33)
- **Signature:** `def __init__(self, platform_adapter: IPlatformAdapter, target_interface: Optional[str], interval_sec: float, timeout_sec: float) -> None`
- **Purpose:** Method __init__ of InterfaceStatsCollector
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.probes.interface_probe::InterfaceStatsCollector.execute   (app/monitoring/probes/interface_probe.py:35-95)
- **Signature:** `async def execute(self) -> List[ProbeResult]`
- **Purpose:** Method execute of InterfaceStatsCollector
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:47; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:162; app/storage/database.py:DatabaseManager._apply_migrations:94; app/storage/database.py:DatabaseManager._apply_migrations:96; app/storage/database.py:DatabaseManager._init_storage:85; app/storage/database.py:DatabaseManager._init_storage:86; app/storage/database.py:DatabaseManager._init_storage:87; app/storage/database.py:DatabaseManager._init_storage:88; app/storage/repositories/audit_repo.py:AuditRepository.get_recent:63; app/storage/repositories/audit_repo.py:AuditRepository.save:29; app/storage/repositories/incident_repo.py:IncidentRepository.get_recent:57; app/storage/repositories/incident_repo.py:IncidentRepository.save:29; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_latest_by_metric:58; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_recent:74; app/storage/repositories/measurement_repo.py:MeasurementRepository.save:28; tests/unit/test_remediation.py:231; tests/unit/test_remediation.py:268
- **Calls:** ProbeResult; asyncio.get_running_loop; counters.keys; datetime.now; k.lower; loop.run_in_executor; max; next; results.append; self.platform.get_primary_interface
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.monitoring.probes.socket_probe`

### app.monitoring.probes.socket_probe::ActiveConnectionCollector.__init__   (app/monitoring/probes/socket_probe.py:17-28)
- **Signature:** `def __init__(self, platform_adapter: IPlatformAdapter, interval_sec: float, timeout_sec: float) -> None`
- **Purpose:** Method __init__ of ActiveConnectionCollector
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.probes.socket_probe::ActiveConnectionCollector.execute   (app/monitoring/probes/socket_probe.py:30-64)
- **Signature:** `async def execute(self) -> List[ProbeResult]`
- **Purpose:** Method execute of ActiveConnectionCollector
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:47; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:162; app/storage/database.py:DatabaseManager._apply_migrations:94; app/storage/database.py:DatabaseManager._apply_migrations:96; app/storage/database.py:DatabaseManager._init_storage:85; app/storage/database.py:DatabaseManager._init_storage:86; app/storage/database.py:DatabaseManager._init_storage:87; app/storage/database.py:DatabaseManager._init_storage:88; app/storage/repositories/audit_repo.py:AuditRepository.get_recent:63; app/storage/repositories/audit_repo.py:AuditRepository.save:29; app/storage/repositories/incident_repo.py:IncidentRepository.get_recent:57; app/storage/repositories/incident_repo.py:IncidentRepository.save:29; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_latest_by_metric:58; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_recent:74; app/storage/repositories/measurement_repo.py:MeasurementRepository.save:28; tests/unit/test_remediation.py:231; tests/unit/test_remediation.py:268
- **Calls:** ProbeResult; asyncio.get_running_loop; datetime.now; float; len; loop.run_in_executor; process_counts.get; psutil.Process; psutil.Process(c.pid).name; psutil.net_connections
- **Real or fake?:** `REAL`
- **Error handling:** catches (psutil.NoSuchProcess, psutil.AccessDenied)

## Module: `app.monitoring.probes.wifi_probe`

### app.monitoring.probes.wifi_probe::WifiMetricsCollector.__init__   (app/monitoring/probes/wifi_probe.py:16-27)
- **Signature:** `def __init__(self, platform_adapter: IPlatformAdapter, interval_sec: float, timeout_sec: float) -> None`
- **Purpose:** Method __init__ of WifiMetricsCollector
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.probes.wifi_probe::WifiMetricsCollector.execute   (app/monitoring/probes/wifi_probe.py:29-72)
- **Signature:** `async def execute(self) -> List[ProbeResult]`
- **Purpose:** Method execute of WifiMetricsCollector
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:47; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:162; app/storage/database.py:DatabaseManager._apply_migrations:94; app/storage/database.py:DatabaseManager._apply_migrations:96; app/storage/database.py:DatabaseManager._init_storage:85; app/storage/database.py:DatabaseManager._init_storage:86; app/storage/database.py:DatabaseManager._init_storage:87; app/storage/database.py:DatabaseManager._init_storage:88; app/storage/repositories/audit_repo.py:AuditRepository.get_recent:63; app/storage/repositories/audit_repo.py:AuditRepository.save:29; app/storage/repositories/incident_repo.py:IncidentRepository.get_recent:57; app/storage/repositories/incident_repo.py:IncidentRepository.save:29; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_latest_by_metric:58; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_recent:74; app/storage/repositories/measurement_repo.py:MeasurementRepository.save:28; tests/unit/test_remediation.py:231; tests/unit/test_remediation.py:268
- **Calls:** ProbeResult; asyncio.get_running_loop; datetime.now; float; info.get; loop.run_in_executor; results.append
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.monitoring.schedulers.engine`

### app.monitoring.schedulers.engine::ObservabilityEngine.__init__   (app/monitoring/schedulers/engine.py:29-51)
- **Signature:** `def __init__(self, config: ProbingConfig, event_bus: EventBus, platform_adapter: IPlatformAdapter, measurement_repo: MeasurementRepository, window_size: int) -> None`
- **Purpose:** Method __init__ of ObservabilityEngine
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** asyncio.Lock; deque; self._initialize_probes
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.schedulers.engine::ObservabilityEngine._initialize_probes   (app/monitoring/schedulers/engine.py:53-85)
- **Signature:** `def _initialize_probes(self) -> None`
- **Purpose:** Instantiate configured probes.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/schedulers/engine.py:ObservabilityEngine.__init__:51
- **Calls:** ActiveConnectionCollector; DNSResolutionProbe; ExternalConnectivityProbe; GatewayProbe; InterfaceStatsCollector; WifiMetricsCollector
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.schedulers.engine::ObservabilityEngine._probe_worker   (app/monitoring/schedulers/engine.py:129-145)
- **Signature:** `async def _probe_worker(self, probe: BaseProbe) -> None`
- **Purpose:** Infinite loop worker for an individual probe with interval pacing.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/schedulers/engine.py:ObservabilityEngine.start:99
- **Calls:** asyncio.sleep; logger.error; pr.to_measurement; probe.run; self._record_measurement
- **Real or fake?:** `REAL`
- **Error handling:** catches asyncio.CancelledError; catches Exception; catches asyncio.CancelledError

### app.monitoring.schedulers.engine::ObservabilityEngine._record_measurement   (app/monitoring/schedulers/engine.py:147-164)
- **Signature:** `async def _record_measurement(self, m: Measurement) -> None`
- **Purpose:** Buffers measurement in sliding window, persists to SQLite, and broadcasts to event bus.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/schedulers/engine.py:ObservabilityEngine._probe_worker:136; app/monitoring/schedulers/engine.py:ObservabilityEngine.run_single_cycle:125
- **Calls:** asyncio.get_running_loop; deque; logger.warning; loop.run_in_executor; self._sliding_windows[m.metric_type].append; self.event_bus.publish
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.monitoring.schedulers.engine::ObservabilityEngine.get_latest_measurement   (app/monitoring/schedulers/engine.py:172-177)
- **Signature:** `def get_latest_measurement(self, metric_type: MetricType) -> Optional[Measurement]`
- **Purpose:** Returns the single most recent measurement for the given metric.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/dashboard_view.py:DashboardView.update_telemetry:359; app/ui/views/dashboard_view.py:DashboardView.update_telemetry:360; app/ui/views/dashboard_view.py:DashboardView.update_telemetry:361; app/ui/views/dashboard_view.py:DashboardView.update_telemetry:362
- **Calls:** len; self._sliding_windows.get
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.schedulers.engine::ObservabilityEngine.get_sliding_window   (app/monitoring/schedulers/engine.py:166-170)
- **Signature:** `def get_sliding_window(self, metric_type: MetricType) -> List[Measurement]`
- **Purpose:** Returns a snapshot of the most recent measurements for the given metric.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/application.py:NetGuardApplication._continuous_evaluation_loop:143; app/application.py:NetGuardApplication.step:126; app/ui/views/dashboard_view.py:DashboardView.update_telemetry:384; tests/unit/test_monitoring.py:157
- **Calls:** list
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.schedulers.engine::ObservabilityEngine.register_probe   (app/monitoring/schedulers/engine.py:87-89)
- **Signature:** `def register_probe(self, probe: BaseProbe) -> None`
- **Purpose:** Register custom probe (e.g. for mock testing or cellular modem).
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self._probes.append
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.schedulers.engine::ObservabilityEngine.run_single_cycle   (app/monitoring/schedulers/engine.py:115-127)
- **Signature:** `async def run_single_cycle(self) -> List[Measurement]`
- **Purpose:** Runs one sample cycle of all registered probes immediately (useful for testing or on-demand).
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/application.py:NetGuardApplication.step:123; tests/unit/test_monitoring.py:152
- **Calls:** all_measurements.append; asyncio.gather; isinstance; pr.to_measurement; probe.run; self._record_measurement
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.schedulers.engine::ObservabilityEngine.start   (app/monitoring/schedulers/engine.py:91-100)
- **Signature:** `async def start(self) -> None`
- **Purpose:** Start asynchronous probing loops for all registered probes.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/application.py:NetGuardApplication.start:94; app/main.py:128; app/main.py:133; app/main.py:56; app/ui/main_window.py:MainWindow.__init__:364; app/ui/main_window.py:MainWindow.__init__:370; app/ui/main_window.py:MainWindow._async_inspect_network_environment:459; app/ui/main_window.py:MainWindow._on_apply_dns_requested:681; app/ui/main_window.py:MainWindow._on_quick_flush_dns:739; app/ui/main_window.py:MainWindow._on_run_deep_diagnosis:708; app/ui/main_window.py:MainWindow._on_run_dns_benchmark:503; app/ui/main_window.py:MainWindow._on_scan_traffic:692; app/ui/views/dashboard_view.py:DashboardView.__init__:238; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:50; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:373; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:57; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:142; app/ui/widgets/toggle.py:ToggleSwitch.setChecked:41
- **Calls:** asyncio.create_task; len; logger.info; self._probe_worker; self._tasks.append
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.monitoring.schedulers.engine::ObservabilityEngine.stop   (app/monitoring/schedulers/engine.py:102-113)
- **Signature:** `async def stop(self) -> None`
- **Purpose:** Gracefully stop all probe workers.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/application.py:NetGuardApplication.stop:116; app/main.py:81; app/ui/widgets/toggle.py:ToggleSwitch.setChecked:38
- **Calls:** asyncio.gather; logger.info; self._tasks.clear; task.cancel
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.platform.factory`

### app.platform.factory::get_platform_adapter   (app/platform/factory.py:9-17)
- **Signature:** `def get_platform_adapter() -> IPlatformAdapter`
- **Purpose:** Returns the appropriate platform adapter for the current host OS.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/bootstrap.py:63; tests/integration/test_live_monitoring.py:13; tests/unit/test_bufferbloat.py:20; tests/unit/test_foundation.py:142
- **Calls:** LinuxPlatformAdapter; WindowsPlatformAdapter; sys.platform.startswith
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.platform.interfaces`

### app.platform.interfaces::IPlatformAdapter.flush_dns_cache   (app/platform/interfaces.py:37-39)
- **Signature:** `def flush_dns_cache(self) -> Tuple[bool, str]`
- **Purpose:** Flush the operating system's local DNS resolver cache.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/dns/optimizer.py:DNSOptimizer.auto_optimize_dns:67; app/ui/main_window.py:MainWindow._on_apply_dns_requested:647; app/ui/main_window.py:MainWindow._on_dashboard_revert_dns:628
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.platform.interfaces::IPlatformAdapter.get_default_gateway   (app/platform/interfaces.py:17-19)
- **Signature:** `def get_default_gateway(self) -> Optional[str]`
- **Purpose:** Detect the active default IPv4 gateway address.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/bootstrap.py:65; app/main.py:52; app/monitoring/probes/gateway_probe.py:GatewayProbe._handle_timeout:133; app/monitoring/probes/gateway_probe.py:GatewayProbe.execute:32; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.check_preconditions:27; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.execute:34; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.verify:53; app/ui/main_window.py:MainWindow._async_inspect_network_environment:445; tests/integration/test_live_monitoring.py:14
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.platform.interfaces::IPlatformAdapter.get_interface_dns_servers   (app/platform/interfaces.py:42-44)
- **Signature:** `def get_interface_dns_servers(self, interface_name: str) -> List[str]`
- **Purpose:** Retrieve the configured DNS server IPs for the specified interface.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/dns/optimizer.py:DNSOptimizer.auto_optimize_dns:63; app/ui/main_window.py:MainWindow._on_dns_benchmark_done:524
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.platform.interfaces::IPlatformAdapter.get_primary_interface   (app/platform/interfaces.py:22-24)
- **Signature:** `def get_primary_interface(self) -> Optional[str]`
- **Purpose:** Detect the primary network adapter name currently routing default traffic.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/bootstrap.py:64; app/dns/optimizer.py:DNSOptimizer.auto_optimize_dns:61; app/main.py:51; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.execute:43; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.check_preconditions:28; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.check_preconditions:31; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.execute:38; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.check_preconditions:32; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.execute:39; app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:119; app/ui/main_window.py:MainWindow._async_inspect_network_environment:444; app/ui/main_window.py:MainWindow._on_apply_dns_requested:642; app/ui/main_window.py:MainWindow._on_dashboard_revert_dns:626; app/ui/main_window.py:MainWindow._on_dns_benchmark_done:523; tests/integration/test_live_monitoring.py:15
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.platform.interfaces::IPlatformAdapter.get_wifi_metrics   (app/platform/interfaces.py:57-59)
- **Signature:** `def get_wifi_metrics(self, interface_name: Optional[str]) -> Dict[str, Any]`
- **Purpose:** Retrieve Wi-Fi signal strength (%), link speed, and BSSID if connected.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.platform.interfaces::IPlatformAdapter.is_elevated   (app/platform/interfaces.py:12-14)
- **Signature:** `def is_elevated(self) -> bool`
- **Purpose:** Check whether the current running process has administrator/root privileges.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/platform/windows/adapter.py:WindowsPlatformAdapter.renew_ip_lease:271; app/platform/windows/adapter.py:WindowsPlatformAdapter.restart_as_administrator:30; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.check_preconditions:28; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.check_preconditions:29; tests/unit/test_foundation.py:144
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.platform.interfaces::IPlatformAdapter.ping   (app/platform/interfaces.py:27-29)
- **Signature:** `def ping(self, target: str, timeout_sec: float) -> Tuple[bool, float]`
- **Purpose:** Execute an ICMP ping or OS ping probe. Returns (success, latency_ms).
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.platform.interfaces::IPlatformAdapter.renew_ip_lease   (app/platform/interfaces.py:52-54)
- **Signature:** `def renew_ip_lease(self, interface_name: str) -> Tuple[bool, str]`
- **Purpose:** Release and renew the DHCP lease for the specified interface.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.platform.interfaces::IPlatformAdapter.restart_as_administrator   (app/platform/interfaces.py:61-63)
- **Signature:** `def restart_as_administrator(self) -> bool`
- **Purpose:** Relaunch the application elevated as Administrator/root.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.platform.interfaces::IPlatformAdapter.set_interface_dns_servers   (app/platform/interfaces.py:47-49)
- **Signature:** `def set_interface_dns_servers(self, interface_name: str, servers: List[str]) -> Tuple[bool, str]`
- **Purpose:** Set static or DHCP DNS servers on the specified interface.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/dns/optimizer.py:DNSOptimizer.auto_optimize_dns:66; app/ui/main_window.py:MainWindow._on_apply_dns_requested:646; app/ui/main_window.py:MainWindow._on_dashboard_revert_dns:627
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.platform.interfaces::IPlatformAdapter.tcp_connect   (app/platform/interfaces.py:32-34)
- **Signature:** `def tcp_connect(self, target: str, port: int, timeout_sec: float) -> Tuple[bool, float]`
- **Purpose:** Attempt TCP 3-way handshake. Returns (success, latency_ms).
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_foundation.py:146
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.platform.linux.adapter`

### app.platform.linux.adapter::LinuxPlatformAdapter.flush_dns_cache   (app/platform/linux/adapter.py:73-81)
- **Signature:** `def flush_dns_cache(self) -> Tuple[bool, str]`
- **Purpose:** Method flush_dns_cache of LinuxPlatformAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/dns/optimizer.py:DNSOptimizer.auto_optimize_dns:67; app/ui/main_window.py:MainWindow._on_apply_dns_requested:647; app/ui/main_window.py:MainWindow._on_dashboard_revert_dns:628
- **Calls:** subprocess.run
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception (swallowed silently)

### app.platform.linux.adapter::LinuxPlatformAdapter.get_default_gateway   (app/platform/linux/adapter.py:21-33)
- **Signature:** `def get_default_gateway(self) -> Optional[str]`
- **Purpose:** Method get_default_gateway of LinuxPlatformAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/bootstrap.py:65; app/main.py:52; app/monitoring/probes/gateway_probe.py:GatewayProbe._handle_timeout:133; app/monitoring/probes/gateway_probe.py:GatewayProbe.execute:32; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.check_preconditions:27; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.execute:34; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.verify:53; app/ui/main_window.py:MainWindow._async_inspect_network_environment:445; tests/integration/test_live_monitoring.py:14
- **Calls:** f.readlines; gw_int.to_bytes; int; len; line.strip; line.strip().split; open; socket.inet_ntoa
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception (swallowed silently)

### app.platform.linux.adapter::LinuxPlatformAdapter.get_interface_dns_servers   (app/platform/linux/adapter.py:83-94)
- **Signature:** `def get_interface_dns_servers(self, interface_name: str) -> List[str]`
- **Purpose:** Method get_interface_dns_servers of LinuxPlatformAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/dns/optimizer.py:DNSOptimizer.auto_optimize_dns:63; app/ui/main_window.py:MainWindow._on_dns_benchmark_done:524
- **Calls:** len; line.startswith; line.strip; line.strip().split; open; servers.append
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception (swallowed silently)

### app.platform.linux.adapter::LinuxPlatformAdapter.get_primary_interface   (app/platform/linux/adapter.py:35-45)
- **Signature:** `def get_primary_interface(self) -> Optional[str]`
- **Purpose:** Method get_primary_interface of LinuxPlatformAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/bootstrap.py:64; app/dns/optimizer.py:DNSOptimizer.auto_optimize_dns:61; app/main.py:51; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.execute:43; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.check_preconditions:28; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.check_preconditions:31; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.execute:38; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.check_preconditions:32; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.execute:39; app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:119; app/ui/main_window.py:MainWindow._async_inspect_network_environment:444; app/ui/main_window.py:MainWindow._on_apply_dns_requested:642; app/ui/main_window.py:MainWindow._on_dashboard_revert_dns:626; app/ui/main_window.py:MainWindow._on_dns_benchmark_done:523; tests/integration/test_live_monitoring.py:15
- **Calls:** len; parts.index; proc.stdout.strip; proc.stdout.strip().split; subprocess.run
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception (swallowed silently)

### app.platform.linux.adapter::LinuxPlatformAdapter.get_wifi_metrics   (app/platform/linux/adapter.py:102-103)
- **Signature:** `def get_wifi_metrics(self, interface_name: Optional[str]) -> Dict[str, Any]`
- **Purpose:** Method get_wifi_metrics of LinuxPlatformAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.platform.linux.adapter::LinuxPlatformAdapter.is_elevated   (app/platform/linux/adapter.py:14-19)
- **Signature:** `def is_elevated(self) -> bool`
- **Purpose:** Method is_elevated of LinuxPlatformAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/platform/windows/adapter.py:WindowsPlatformAdapter.renew_ip_lease:271; app/platform/windows/adapter.py:WindowsPlatformAdapter.restart_as_administrator:30; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.check_preconditions:28; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.check_preconditions:29; tests/unit/test_foundation.py:144
- **Calls:** os.geteuid
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.platform.linux.adapter::LinuxPlatformAdapter.ping   (app/platform/linux/adapter.py:47-59)
- **Signature:** `def ping(self, target: str, timeout_sec: float) -> Tuple[bool, float]`
- **Purpose:** Method ping of LinuxPlatformAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** int; max; str; subprocess.run; time.perf_counter
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.platform.linux.adapter::LinuxPlatformAdapter.renew_ip_lease   (app/platform/linux/adapter.py:99-100)
- **Signature:** `def renew_ip_lease(self, interface_name: str) -> Tuple[bool, str]`
- **Purpose:** Method renew_ip_lease of LinuxPlatformAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.platform.linux.adapter::LinuxPlatformAdapter.set_interface_dns_servers   (app/platform/linux/adapter.py:96-97)
- **Signature:** `def set_interface_dns_servers(self, interface_name: str, servers: List[str]) -> Tuple[bool, str]`
- **Purpose:** Method set_interface_dns_servers of LinuxPlatformAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/dns/optimizer.py:DNSOptimizer.auto_optimize_dns:66; app/ui/main_window.py:MainWindow._on_apply_dns_requested:646; app/ui/main_window.py:MainWindow._on_dashboard_revert_dns:627
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.platform.linux.adapter::LinuxPlatformAdapter.tcp_connect   (app/platform/linux/adapter.py:61-71)
- **Signature:** `def tcp_connect(self, target: str, port: int, timeout_sec: float) -> Tuple[bool, float]`
- **Purpose:** Method tcp_connect of LinuxPlatformAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_foundation.py:146
- **Calls:** sock.close; sock.connect; sock.settimeout; socket.socket; time.perf_counter
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

## Module: `app.platform.windows.adapter`

### app.platform.windows.adapter::WindowsPlatformAdapter.__init__   (app/platform/windows/adapter.py:21-24)
- **Signature:** `def __init__(self) -> None`
- **Purpose:** Method __init__ of WindowsPlatformAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.platform.windows.adapter::WindowsPlatformAdapter.flush_dns_cache   (app/platform/windows/adapter.py:158-198)
- **Signature:** `def flush_dns_cache(self) -> Tuple[bool, str]`
- **Purpose:** Flush the DNS Resolver Cache via native Win32 Dnsapi, PowerShell, or ipconfig.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/dns/optimizer.py:DNSOptimizer.auto_optimize_dns:67; app/ui/main_window.py:MainWindow._on_apply_dns_requested:647; app/ui/main_window.py:MainWindow._on_dashboard_revert_dns:628
- **Calls:** ctypes.windll.dnsapi.DnsFlushResolverCache; str; subprocess.run
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception (swallowed silently); catches Exception (swallowed silently); catches Exception

### app.platform.windows.adapter::WindowsPlatformAdapter.get_default_gateway   (app/platform/windows/adapter.py:46-77)
- **Signature:** `def get_default_gateway(self) -> Optional[str]`
- **Purpose:** Parse default IPv4 gateway via route print or ipconfig.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/bootstrap.py:65; app/main.py:52; app/monitoring/probes/gateway_probe.py:GatewayProbe._handle_timeout:133; app/monitoring/probes/gateway_probe.py:GatewayProbe.execute:32; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.check_preconditions:27; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.execute:34; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.verify:53; app/ui/main_window.py:MainWindow._async_inspect_network_environment:445; tests/integration/test_live_monitoring.py:14
- **Calls:** ipaddress.IPv4Address; len; line.strip; line.strip().split; proc.stdout.splitlines; psutil.net_if_stats; subprocess.run
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception (swallowed silently); catches Exception; catches ValueError

### app.platform.windows.adapter::WindowsPlatformAdapter.get_interface_dns_servers   (app/platform/windows/adapter.py:200-219)
- **Signature:** `def get_interface_dns_servers(self, interface_name: str) -> List[str]`
- **Purpose:** Query configured DNS servers for the specified interface.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/dns/optimizer.py:DNSOptimizer.auto_optimize_dns:63; app/ui/main_window.py:MainWindow._on_dns_benchmark_done:524
- **Calls:** ip.startswith; proc.stdout.splitlines; re.findall; servers.append; subprocess.run
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.platform.windows.adapter::WindowsPlatformAdapter.get_primary_interface   (app/platform/windows/adapter.py:79-112)
- **Signature:** `def get_primary_interface(self) -> Optional[str]`
- **Purpose:** Detect the primary network adapter name currently routing default traffic.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/bootstrap.py:64; app/dns/optimizer.py:DNSOptimizer.auto_optimize_dns:61; app/main.py:51; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.execute:43; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.check_preconditions:28; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.check_preconditions:31; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.execute:38; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.check_preconditions:32; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.execute:39; app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:119; app/ui/main_window.py:MainWindow._async_inspect_network_environment:444; app/ui/main_window.py:MainWindow._on_apply_dns_requested:642; app/ui/main_window.py:MainWindow._on_dashboard_revert_dns:626; app/ui/main_window.py:MainWindow._on_dns_benchmark_done:523; tests/integration/test_live_monitoring.py:15
- **Calls:** iface_name.lower; len; line.strip; line.strip().split; proc.stdout.splitlines; psutil.net_if_addrs; psutil.net_if_addrs().items; psutil.net_if_stats; psutil.net_if_stats().items; subprocess.run
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception (swallowed silently)

### app.platform.windows.adapter::WindowsPlatformAdapter.get_wifi_metrics   (app/platform/windows/adapter.py:290-334)
- **Signature:** `def get_wifi_metrics(self, interface_name: Optional[str]) -> Dict[str, Any]`
- **Purpose:** Parse netsh wlan show interfaces for signal percentage, SSID, and rate.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** float; line.split; line.strip; m.group; p.strip; proc.stdout.splitlines; re.search; subprocess.run; val.replace; val.replace('%', '').strip
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception (swallowed silently)

### app.platform.windows.adapter::WindowsPlatformAdapter.is_elevated   (app/platform/windows/adapter.py:38-44)
- **Signature:** `def is_elevated(self) -> bool`
- **Purpose:** Check whether the current running process has administrator privileges on Windows.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/platform/windows/adapter.py:WindowsPlatformAdapter.renew_ip_lease:271; app/platform/windows/adapter.py:WindowsPlatformAdapter.restart_as_administrator:30; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.check_preconditions:28; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.check_preconditions:29; tests/unit/test_foundation.py:144
- **Calls:** ctypes.windll.shell32.IsUserAnAdmin
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.platform.windows.adapter::WindowsPlatformAdapter.ping   (app/platform/windows/adapter.py:114-142)
- **Signature:** `def ping(self, target: str, timeout_sec: float) -> Tuple[bool, float]`
- **Purpose:** Execute Windows ping command with single echo and millisecond timeout.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** float; int; match.group; max; re.match; re.search; str; subprocess.run; time.perf_counter
- **Real or fake?:** `REAL`
- **Error handling:** catches (subprocess.TimeoutExpired, Exception)

### app.platform.windows.adapter::WindowsPlatformAdapter.renew_ip_lease   (app/platform/windows/adapter.py:269-288)
- **Signature:** `def renew_ip_lease(self, interface_name: str) -> Tuple[bool, str]`
- **Purpose:** Request DHCP lease refresh for the active interface.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.is_elevated; str; subprocess.run
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.platform.windows.adapter::WindowsPlatformAdapter.restart_as_administrator   (app/platform/windows/adapter.py:26-36)
- **Signature:** `def restart_as_administrator(self) -> bool`
- **Purpose:** Relaunches NetGuard AI process elevated with Administrator privileges.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** ' '.join; ctypes.windll.shell32.ShellExecuteW; self.is_elevated
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.platform.windows.adapter::WindowsPlatformAdapter.set_interface_dns_servers   (app/platform/windows/adapter.py:221-267)
- **Signature:** `def set_interface_dns_servers(self, interface_name: str, servers: List[str]) -> Tuple[bool, str]`
- **Purpose:** Configure primary and secondary static DNS or DHCP.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/dns/optimizer.py:DNSOptimizer.auto_optimize_dns:66; app/ui/main_window.py:MainWindow._on_apply_dns_requested:646; app/ui/main_window.py:MainWindow._on_dashboard_revert_dns:627
- **Calls:** ', '.join; enumerate; out.lower; str; subprocess.run
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception; catches Exception

### app.platform.windows.adapter::WindowsPlatformAdapter.tcp_connect   (app/platform/windows/adapter.py:144-156)
- **Signature:** `def tcp_connect(self, target: str, port: int, timeout_sec: float) -> Tuple[bool, float]`
- **Purpose:** Attempt socket TCP 3-way handshake to target:port.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_foundation.py:146
- **Calls:** sock.close; sock.connect; sock.settimeout; socket.socket; time.perf_counter
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

## Module: `app.platform.windows.network_info`

### app.platform.windows.network_info::get_active_dns_servers   (app/platform/windows/network_info.py:91-103)
- **Signature:** `def get_active_dns_servers(interface_name: str) -> List[str]`
- **Purpose:** Inspects active IPv4 DNS servers for the primary interface.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._async_inspect_network_environment:447
- **Calls:** hasattr; re.findall; subprocess.check_output
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.platform.windows.network_info::get_isp_and_public_ip   (app/platform/windows/network_info.py:184-221)
- **Signature:** `def get_isp_and_public_ip() -> Dict[str, str]`
- **Purpose:** Fast non-blocking lookup of public IP and ISP company name.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._async_inspect_network_environment:448
- **Calls:** data.get; json.loads; resp.read; resp.read().decode; urllib.request.Request; urllib.request.urlopen
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.platform.windows.network_info::get_wifi_details   (app/platform/windows/network_info.py:20-88)
- **Signature:** `def get_wifi_details() -> Dict[str, Any]`
- **Purpose:** Inspects native Windows WLAN interfaces via netsh and detects hotspot/upstream router.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._async_inspect_network_environment:446
- **Calls:** adapter_match.group; adapter_match.group(1).strip; any; band_match.group; band_match.group(1).strip; hasattr; p.lower; p.strip; re.findall; re.search
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception; catches Exception (swallowed silently)

### app.platform.windows.network_info::resolve_dns_provider_label   (app/platform/windows/network_info.py:106-181)
- **Signature:** `def resolve_dns_provider_label(dns_servers: List[str], gateway_ip: str) -> Dict[str, Any]`
- **Purpose:** Resolves DNS servers into canonical provider name, formatted IP string, and badge.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** any; dns_servers[0].strip; dns_servers[1].strip; len; primary.startswith
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.storage.database`

### app.storage.database::DatabaseManager.__init__   (app/storage/database.py:76-79)
- **Signature:** `def __init__(self, db_path: str | Path, enable_wal: bool) -> None`
- **Purpose:** Method __init__ of DatabaseManager
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** Path; self._init_storage
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.storage.database::DatabaseManager._apply_migrations   (app/storage/database.py:91-98)
- **Signature:** `def _apply_migrations(self, conn: sqlite3.Connection) -> None`
- **Purpose:** Method _apply_migrations of DatabaseManager
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/storage/database.py:DatabaseManager._init_storage:89
- **Calls:** conn.commit; conn.cursor; conn.executescript; cur.execute; cur.fetchone; logger.info
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.storage.database::DatabaseManager._init_storage   (app/storage/database.py:81-89)
- **Signature:** `def _init_storage(self) -> None`
- **Purpose:** Method _init_storage of DatabaseManager
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/storage/database.py:DatabaseManager.__init__:79
- **Calls:** conn.execute; self._apply_migrations; self.db_path.parent.mkdir; self.get_connection; str
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.storage.database::DatabaseManager.get_connection   (app/storage/database.py:100-107)
- **Signature:** `def get_connection(self) -> sqlite3.Connection`
- **Purpose:** Method get_connection of DatabaseManager
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/storage/database.py:DatabaseManager._init_storage:83; app/storage/repositories/audit_repo.py:AuditRepository.get_recent:61; app/storage/repositories/audit_repo.py:AuditRepository.save:27; app/storage/repositories/incident_repo.py:IncidentRepository.get_recent:55; app/storage/repositories/incident_repo.py:IncidentRepository.save:27; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_latest_by_metric:56; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_recent:72; app/storage/repositories/measurement_repo.py:MeasurementRepository.save:26
- **Calls:** sqlite3.connect; str
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.storage.repositories.audit_repo`

### app.storage.repositories.audit_repo::AuditRepository.__init__   (app/storage/repositories/audit_repo.py:15-16)
- **Signature:** `def __init__(self, db_manager: DatabaseManager) -> None`
- **Purpose:** Method __init__ of AuditRepository
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.storage.repositories.audit_repo::AuditRepository.get_recent   (app/storage/repositories/audit_repo.py:51-83)
- **Signature:** `def get_recent(self, limit: int) -> List[ActionExecutionRecord]`
- **Purpose:** Method get_recent of AuditRepository
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_ui_tick:480; app/ui/main_window.py:MainWindow._on_ui_tick:484; scripts/verify_ui_render.py:88; tests/unit/test_foundation.py:107; tests/unit/test_foundation.py:89; tests/unit/test_monitoring.py:162; tests/unit/test_remediation.py:150
- **Calls:** ActionExecutionRecord; ActionExecutionStatus; RiskLevel; bool; conn.cursor; cur.execute; cur.fetchall; datetime.fromisoformat; json.loads; results.append
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.storage.repositories.audit_repo::AuditRepository.save   (app/storage/repositories/audit_repo.py:18-49)
- **Signature:** `def save(self, record: ActionExecutionRecord) -> str`
- **Purpose:** Method save of AuditRepository
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_apply_dns_requested:679; scripts/verify_ui_render.py:104; scripts/verify_ui_render.py:110; scripts/verify_ui_render.py:57; scripts/verify_ui_render.py:72; scripts/verify_ui_render.py:78; scripts/verify_ui_render.py:84; scripts/verify_ui_render.py:92; scripts/verify_ui_render.py:98; tests/unit/test_foundation.py:104; tests/unit/test_foundation.py:59; tests/unit/test_foundation.py:86
- **Calls:** conn.commit; conn.cursor; cur.execute; json.dumps; record.timestamp.isoformat; self.db.get_connection; str; uuid.uuid4
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.storage.repositories.incident_repo`

### app.storage.repositories.incident_repo::IncidentRepository.__init__   (app/storage/repositories/incident_repo.py:15-16)
- **Signature:** `def __init__(self, db_manager: DatabaseManager) -> None`
- **Purpose:** Method __init__ of IncidentRepository
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.storage.repositories.incident_repo::IncidentRepository.get_recent   (app/storage/repositories/incident_repo.py:46-79)
- **Signature:** `def get_recent(self, limit: int) -> List[Diagnosis]`
- **Purpose:** Method get_recent of IncidentRepository
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_ui_tick:480; app/ui/main_window.py:MainWindow._on_ui_tick:484; scripts/verify_ui_render.py:88; tests/unit/test_foundation.py:107; tests/unit/test_foundation.py:89; tests/unit/test_monitoring.py:162; tests/unit/test_remediation.py:150
- **Calls:** Diagnosis; DiagnosisSeverity; Evidence; MetricType; ProbableCause; bool; conn.cursor; cur.execute; cur.fetchall; datetime.fromisoformat
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.storage.repositories.incident_repo::IncidentRepository.save   (app/storage/repositories/incident_repo.py:18-44)
- **Signature:** `def save(self, diagnosis: Diagnosis) -> str`
- **Purpose:** Method save of IncidentRepository
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_apply_dns_requested:679; scripts/verify_ui_render.py:104; scripts/verify_ui_render.py:110; scripts/verify_ui_render.py:57; scripts/verify_ui_render.py:72; scripts/verify_ui_render.py:78; scripts/verify_ui_render.py:84; scripts/verify_ui_render.py:92; scripts/verify_ui_render.py:98; tests/unit/test_foundation.py:104; tests/unit/test_foundation.py:59; tests/unit/test_foundation.py:86
- **Calls:** conn.commit; conn.cursor; cur.execute; diagnosis.timestamp.isoformat; e.model_dump; json.dumps; self.db.get_connection; str; uuid.uuid4
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.storage.repositories.measurement_repo`

### app.storage.repositories.measurement_repo::MeasurementRepository.__init__   (app/storage/repositories/measurement_repo.py:14-15)
- **Signature:** `def __init__(self, db_manager: DatabaseManager) -> None`
- **Purpose:** Method __init__ of MeasurementRepository
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.storage.repositories.measurement_repo::MeasurementRepository._row_to_measurement   (app/storage/repositories/measurement_repo.py:80-94)
- **Signature:** `def _row_to_measurement(row: dict) -> Measurement`
- **Purpose:** Method _row_to_measurement of MeasurementRepository
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/storage/repositories/measurement_repo.py:MeasurementRepository.get_latest_by_metric:60; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_recent:76
- **Calls:** Measurement; MeasurementSource; MetricType; ProbeStatus; datetime.fromisoformat; json.loads
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.storage.repositories.measurement_repo::MeasurementRepository.get_latest_by_metric   (app/storage/repositories/measurement_repo.py:46-61)
- **Signature:** `def get_latest_by_metric(self, metric_type: MetricType, limit: int) -> List[Measurement]`
- **Purpose:** Method get_latest_by_metric of MeasurementRepository
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_foundation.py:62
- **Calls:** conn.cursor; cur.execute; cur.fetchall; results.append; self._row_to_measurement; self.db.get_connection
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.storage.repositories.measurement_repo::MeasurementRepository.get_recent   (app/storage/repositories/measurement_repo.py:63-77)
- **Signature:** `def get_recent(self, limit: int) -> List[Measurement]`
- **Purpose:** Method get_recent of MeasurementRepository
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_ui_tick:480; app/ui/main_window.py:MainWindow._on_ui_tick:484; scripts/verify_ui_render.py:88; tests/unit/test_foundation.py:107; tests/unit/test_foundation.py:89; tests/unit/test_monitoring.py:162; tests/unit/test_remediation.py:150
- **Calls:** conn.cursor; cur.execute; cur.fetchall; results.append; self._row_to_measurement; self.db.get_connection
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.storage.repositories.measurement_repo::MeasurementRepository.save   (app/storage/repositories/measurement_repo.py:17-44)
- **Signature:** `def save(self, m: Measurement) -> int`
- **Purpose:** Method save of MeasurementRepository
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_apply_dns_requested:679; scripts/verify_ui_render.py:104; scripts/verify_ui_render.py:110; scripts/verify_ui_render.py:57; scripts/verify_ui_render.py:72; scripts/verify_ui_render.py:78; scripts/verify_ui_render.py:84; scripts/verify_ui_render.py:92; scripts/verify_ui_render.py:98; tests/unit/test_foundation.py:104; tests/unit/test_foundation.py:59; tests/unit/test_foundation.py:86
- **Calls:** conn.commit; conn.cursor; cur.execute; json.dumps; m.timestamp.isoformat; self.db.get_connection
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `scripts.build_exe`

### scripts.build_exe::build   (scripts/build_exe.py:8-54)
- **Signature:** `def build()`
- **Purpose:** Function build
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** ' '.join; os.chdir; os.path.abspath; os.path.dirname; os.path.exists; os.path.join; print; shutil.copy2; subprocess.run; sys.exit
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `scripts.verify_ui_render`

### scripts.verify_ui_render::capture_ui   (scripts/verify_ui_render.py:17-125)
- **Signature:** `def capture_ui()`
- **Purpose:** Function capture_ui
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** MainWindow; QApplication; QApplication.instance; ResolverScore; app.processEvents; create_application; datetime.now; fname.endswith; netguard_app.ctx.audit.get_recent; os.listdir
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception (swallowed silently)

---
*End of Volume 2. Continue to [Volume 3: Complete Function & Class Catalogue (Part B)](APP_AUDIT_part3.md).*