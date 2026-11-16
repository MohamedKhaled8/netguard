# NetGuard AI — Volume 3: Complete Function & Class Catalogue (Part B)

> **Audit Target:** NetGuard AI (Windows Autonomous Network Remediation & Telemetry Dashboard)  
> **Document:** Volume 3 of 7 | Section 3 (Part B)  
> **Coverage:** `app.diagnosis.*`, `app.remediation.*`, `app.dns.*`, `app.traffic.*`, `app.ui.*`, and Dead Subsystems  
> **Status:** Complete & Verified (READ-ONLY Analysis — Zero Source Changes)  

---

## 3. Complete Function / Class Catalogue (Part B)

This section catalogues every class, method, function, and helper in the diagnosis, remediation, DNS benchmark, traffic tracking, and PySide6 UI views/widgets layers, as well as dead backend packages (`cellular`, `router`, `simulation`, `learning`, `prediction`, `qoe`).

## Module: `app.cellular.engine`

### app.cellular.engine::CellularDiagnosticsEngine.__init__   (app/cellular/engine.py:18-22)
- **Signature:** `def __init__(self, gateway_ip: str, event_bus: EventBus) -> None`
- **Purpose:** Method __init__ of CellularDiagnosticsEngine
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** GenericRouterAdapter
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.cellular.engine::CellularDiagnosticsEngine.auto_discover_adapter   (app/cellular/engine.py:24-38)
- **Signature:** `async def auto_discover_adapter(self) -> BaseRouterAdapter`
- **Purpose:** Tries known router adapters before falling back to generic.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** GenericRouterAdapter; HuaweiHiLinkAdapter; generic.detect_model; hilink.detect_model; logger.info
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.cellular.engine::CellularDiagnosticsEngine.latest_metrics   (app/cellular/engine.py:51-52)
- **Signature:** `def latest_metrics(self) -> Optional[CellularMetrics]`
- **Purpose:** Method latest_metrics of CellularDiagnosticsEngine
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.cellular.engine::CellularDiagnosticsEngine.poll_metrics   (app/cellular/engine.py:40-48)
- **Signature:** `async def poll_metrics(self) -> Optional[CellularMetrics]`
- **Purpose:** Poll cellular RF metrics and broadcast on event bus.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** len; metrics.model_dump; self._history.append; self._history.pop; self.adapter.get_cellular_metrics; self.event_bus.publish
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.cellular.models`

### app.cellular.models::CellularMetrics.classify_quality   (app/cellular/models.py:34-47)
- **Signature:** `def classify_quality(rsrp: Optional[float], sinr: Optional[float]) -> SignalQualityCategory`
- **Purpose:** Classify cellular signal based on 3GPP RSRP & SINR thresholds.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/router/hilink.py:HuaweiHiLinkAdapter.get_cellular_metrics:51; tests/unit/test_cellular.py:11; tests/unit/test_cellular.py:15; tests/unit/test_cellular.py:19; tests/unit/test_cellular.py:23
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.diagnosis.classifiers.base`

### app.diagnosis.classifiers.base::BaseClassifier.__init__   (app/diagnosis/classifiers/base.py:14-15)
- **Signature:** `def __init__(self, thresholds: DiagnosisThresholds) -> None`
- **Purpose:** Method __init__ of BaseClassifier
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.diagnosis.classifiers.base::BaseClassifier.evaluate   (app/diagnosis/classifiers/base.py:18-20)
- **Signature:** `def evaluate(self, summaries: Dict[MetricType, EvidenceSummary]) -> Optional[Diagnosis]`
- **Purpose:** Evaluate evidence summaries across all metrics and return a Diagnosis if an anomaly matches.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/diagnosis/engine.py:DiagnosisEngine.evaluate_windows:68
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.diagnosis.classifiers.destination_fault`

### app.diagnosis.classifiers.destination_fault::DestinationSpecificClassifier.evaluate   (app/diagnosis/classifiers/destination_fault.py:22-81)
- **Signature:** `def evaluate(self, summaries: Dict[MetricType, EvidenceSummary]) -> Optional[Diagnosis]`
- **Purpose:** Method evaluate of DestinationSpecificClassifier
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/diagnosis/engine.py:DiagnosisEngine.evaluate_windows:68
- **Calls:** Diagnosis; Evidence; datetime.now; failing_targets.append; healthy_targets.append; len; str; sum; summaries.get; target_statuses.items
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.diagnosis.classifiers.dns_fault`

### app.diagnosis.classifiers.dns_fault::DNSHealthClassifier.evaluate   (app/diagnosis/classifiers/dns_fault.py:21-99)
- **Signature:** `def evaluate(self, summaries: Dict[MetricType, EvidenceSummary]) -> Optional[Diagnosis]`
- **Purpose:** Method evaluate of DNSHealthClassifier
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/diagnosis/engine.py:DiagnosisEngine.evaluate_windows:68
- **Calls:** Diagnosis; Evidence; contradictory.append; datetime.now; str; summaries.get; uuid.uuid4
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.diagnosis.classifiers.gateway_fault`

### app.diagnosis.classifiers.gateway_fault::GatewayHealthClassifier.evaluate   (app/diagnosis/classifiers/gateway_fault.py:22-102)
- **Signature:** `def evaluate(self, summaries: Dict[MetricType, EvidenceSummary]) -> Optional[Diagnosis]`
- **Purpose:** Method evaluate of GatewayHealthClassifier
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/diagnosis/engine.py:DiagnosisEngine.evaluate_windows:68
- **Calls:** Diagnosis; Evidence; datetime.now; ev_list.append; str; summaries.get; uuid.uuid4
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.diagnosis.classifiers.upstream_isp_fault`

### app.diagnosis.classifiers.upstream_isp_fault::UpstreamISPClassifier.evaluate   (app/diagnosis/classifiers/upstream_isp_fault.py:21-123)
- **Signature:** `def evaluate(self, summaries: Dict[MetricType, EvidenceSummary]) -> Optional[Diagnosis]`
- **Purpose:** Method evaluate of UpstreamISPClassifier
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/diagnosis/engine.py:DiagnosisEngine.evaluate_windows:68
- **Calls:** Diagnosis; Evidence; datetime.now; len; str; summaries.get; target_losses.items; uuid.uuid4
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.diagnosis.classifiers.wifi_fault`

### app.diagnosis.classifiers.wifi_fault::WifiInstabilityClassifier.evaluate   (app/diagnosis/classifiers/wifi_fault.py:21-66)
- **Signature:** `def evaluate(self, summaries: Dict[MetricType, EvidenceSummary]) -> Optional[Diagnosis]`
- **Purpose:** Method evaluate of WifiInstabilityClassifier
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/diagnosis/engine.py:DiagnosisEngine.evaluate_windows:68
- **Calls:** Diagnosis; Evidence; datetime.now; str; summaries.get; supporting.append; uuid.uuid4
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.diagnosis.engine`

### app.diagnosis.engine::DiagnosisEngine.__init__   (app/diagnosis/engine.py:33-49)
- **Signature:** `def __init__(self, thresholds: DiagnosisThresholds, event_bus: EventBus, incident_repo: IncidentRepository) -> None`
- **Purpose:** Method __init__ of DiagnosisEngine
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** DNSHealthClassifier; DestinationSpecificClassifier; GatewayHealthClassifier; UpstreamISPClassifier; WifiInstabilityClassifier
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.diagnosis.engine::DiagnosisEngine.evaluate_windows   (app/diagnosis/engine.py:55-116)
- **Signature:** `async def evaluate_windows(self, windows: Dict[MetricType, List[Measurement]]) -> Diagnosis`
- **Purpose:** Evaluate sliding window measurements across all metrics.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/application.py:NetGuardApplication._continuous_evaluation_loop:144; app/application.py:NetGuardApplication.step:129; tests/unit/test_diagnosis.py:118; tests/unit/test_diagnosis.py:130; tests/unit/test_diagnosis.py:145; tests/unit/test_diagnosis.py:59; tests/unit/test_diagnosis.py:80; tests/unit/test_diagnosis.py:98
- **Calls:** Diagnosis; EvidenceAccumulator.summarize_window; asyncio.get_running_loop; candidate_diagnoses.append; candidate_diagnoses.sort; classifier.evaluate; datetime.now; logger.error; logger.warning; loop.run_in_executor
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception; catches Exception

### app.diagnosis.engine::DiagnosisEngine.last_diagnosis   (app/diagnosis/engine.py:119-120)
- **Signature:** `def last_diagnosis(self) -> Optional[Diagnosis]`
- **Purpose:** Method last_diagnosis of DiagnosisEngine
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.diagnosis.engine::DiagnosisEngine.register_classifier   (app/diagnosis/engine.py:51-53)
- **Signature:** `def register_classifier(self, classifier: BaseClassifier) -> None`
- **Purpose:** Allow registering additional or experimental classifiers.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.classifiers.append
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.diagnosis.evidence`

### app.diagnosis.evidence::EvidenceAccumulator.summarize_window   (app/diagnosis/evidence.py:37-40)
- **Signature:** `def summarize_window(samples: List[Measurement]) -> Optional[EvidenceSummary]`
- **Purpose:** Method summarize_window of EvidenceAccumulator
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/diagnosis/engine.py:DiagnosisEngine.evaluate_windows:60
- **Calls:** EvidenceSummary
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.diagnosis.evidence::EvidenceSummary.__init__   (app/diagnosis/evidence.py:13-30)
- **Signature:** `def __init__(self, metric_type: MetricType, samples: List[Measurement]) -> None`
- **Purpose:** Method __init__ of EvidenceSummary
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** len; max; min; statistics.mean; statistics.median; statistics.stdev; sum
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.dns.benchmark`

### app.dns.benchmark::DNSBenchmark.__init__   (app/dns/benchmark.py:47-55)
- **Signature:** `def __init__(self, resolvers: Optional[List[tuple[str, str]]], domains: Optional[List[str]], timeout_sec: float) -> None`
- **Purpose:** Method __init__ of DNSBenchmark
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.dns.benchmark::DNSBenchmark.benchmark_resolver   (app/dns/benchmark.py:57-108)
- **Signature:** `async def benchmark_resolver(self, ip: str, name: str) -> ResolverScore`
- **Purpose:** Run multiple queries against a specific resolver and calculate its composite score.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/dns/benchmark.py:DNSBenchmark.rank_all:112
- **Calls:** ResolverScore; asyncio.get_running_loop; dns.resolver.Resolver; latencies.append; len; loop.run_in_executor; max; min; res.resolve; statistics.mean
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.dns.benchmark::DNSBenchmark.rank_all   (app/dns/benchmark.py:110-115)
- **Signature:** `async def rank_all(self) -> List[ResolverScore]`
- **Purpose:** Benchmark all configured resolvers concurrently and return sorted by score descending.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/dns/optimizer.py:DNSOptimizer.evaluate_and_rank:33; app/ui/main_window.py:MainWindow._on_run_dns_benchmark:498; tests/unit/test_dns_optimizer.py:64
- **Calls:** asyncio.gather; self.benchmark_resolver; sorted
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.dns.optimizer`

### app.dns.optimizer::DNSOptimizer.__init__   (app/dns/optimizer.py:18-28)
- **Signature:** `def __init__(self, platform_adapter: IPlatformAdapter, event_bus: EventBus, orchestrator: Optional[RemediationOrchestrator]) -> None`
- **Purpose:** Method __init__ of DNSOptimizer
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** DNSBenchmark
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.dns.optimizer::DNSOptimizer.auto_optimize_dns   (app/dns/optimizer.py:41-80)
- **Signature:** `async def auto_optimize_dns(self) -> Optional[ResolverScore]`
- **Purpose:** Checks if current DNS is sub-optimal and switches to the best verified resolver.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/application.py:NetGuardApplication._continuous_evaluation_loop:153; tests/unit/test_dns_optimizer.py:85
- **Calls:** best_resolver.ip.split; len; logger.error; logger.info; logger.warning; next; r.ip.split; self.evaluate_and_rank; self.event_bus.publish; self.platform.flush_dns_cache
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.dns.optimizer::DNSOptimizer.evaluate_and_rank   (app/dns/optimizer.py:30-39)
- **Signature:** `async def evaluate_and_rank(self) -> List[ResolverScore]`
- **Purpose:** Runs benchmark across all resolvers and updates rankings.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/dns/optimizer.py:DNSOptimizer.auto_optimize_dns:43
- **Calls:** logger.info; r.model_dump; self.benchmark.rank_all; self.event_bus.publish
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.dns.optimizer::DNSOptimizer.latest_rankings   (app/dns/optimizer.py:83-84)
- **Signature:** `def latest_rankings(self) -> List[ResolverScore]`
- **Purpose:** Method latest_rankings of DNSOptimizer
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** list
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.learning.memory`

### app.learning.memory::NetworkMemory.__init__   (app/learning/memory.py:30-31)
- **Signature:** `def __init__(self) -> None`
- **Purpose:** Method __init__ of NetworkMemory
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.learning.memory::NetworkMemory.find_best_action_for_context   (app/learning/memory.py:59-94)
- **Signature:** `def find_best_action_for_context(self, probable_cause: ProbableCause, current_features: Dict[str, float]) -> Optional[Tuple[str, float]]`
- **Purpose:** Finds most successful action for matching contextual incidents. Returns (action_id, confidence).
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_learning_and_twin.py:33
- **Calls:** abs; action_scores.items; action_scores.setdefault; action_scores.setdefault(case.action_id, []).append; case.feature_vector.get; current_features.items; len; math.sqrt; max; min
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.learning.memory::NetworkMemory.record_case   (app/learning/memory.py:33-57)
- **Signature:** `def record_case(self, case_id: str, probable_cause: ProbableCause, feature_vector: Dict[str, float], action_id: str, was_successful: bool, improvement_delta_ms: float) -> None`
- **Purpose:** Method record_case of NetworkMemory
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_learning_and_twin.py:13; tests/unit/test_learning_and_twin.py:23
- **Calls:** IncidentResolutionCase; logger.info; self._cases.append
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.prediction.anomaly_detection`

### app.prediction.anomaly_detection::AnomalyDetector.__init__   (app/prediction/anomaly_detection.py:29-30)
- **Signature:** `def __init__(self, baseline_manager: BaselineManager) -> None`
- **Purpose:** Method __init__ of AnomalyDetector
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.prediction.anomaly_detection::AnomalyDetector.evaluate_anomaly   (app/prediction/anomaly_detection.py:32-72)
- **Signature:** `def evaluate_anomaly(self, metric_type: MetricType, recent_values: List[float]) -> Tuple[bool, float, str]`
- **Purpose:** Returns (is_anomaly, anomaly_score, explanation).
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/prediction/engine.py:PredictionEngine.evaluate_streams:63; tests/unit/test_prediction.py:45; tests/unit/test_prediction.py:49
- **Calls:** TrendAnalysis.calculate_slope; min; self.baselines.get_baseline
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.prediction.anomaly_detection::TrendAnalysis.calculate_slope   (app/prediction/anomaly_detection.py:14-23)
- **Signature:** `def calculate_slope(values: List[float]) -> float`
- **Purpose:** Computes rate of change per sample (slope m in y = mx + c).
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/prediction/anomaly_detection.py:AnomalyDetector.evaluate_anomaly:41; tests/unit/test_prediction.py:58
- **Calls:** float; len; np.arange; np.array; np.polyfit
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.prediction.baselines`

### app.prediction.baselines::BaselineManager.__init__   (app/prediction/baselines.py:30-32)
- **Signature:** `def __init__(self, min_samples: int) -> None`
- **Purpose:** Method __init__ of BaselineManager
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.prediction.baselines::BaselineManager.get_baseline   (app/prediction/baselines.py:62-63)
- **Signature:** `def get_baseline(self, metric_type: MetricType) -> Optional[MetricBaseline]`
- **Purpose:** Method get_baseline of BaselineManager
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/prediction/anomaly_detection.py:AnomalyDetector.evaluate_anomaly:38
- **Calls:** self._baselines.get
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.prediction.baselines::BaselineManager.update_baseline   (app/prediction/baselines.py:34-60)
- **Signature:** `def update_baseline(self, metric_type: MetricType, values: List[float]) -> Optional[MetricBaseline]`
- **Purpose:** Update metric baseline distribution from a sequence of raw observations.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/prediction/engine.py:PredictionEngine.evaluate_streams:60; tests/unit/test_prediction.py:30; tests/unit/test_prediction.py:40
- **Calls:** MetricBaseline; datetime.now; float; len; max; np.array; np.mean; np.median; np.percentile; np.std
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.prediction.engine`

### app.prediction.engine::PredictionEngine.__init__   (app/prediction/engine.py:36-40)
- **Signature:** `def __init__(self, event_bus: EventBus, min_samples_for_baseline: int) -> None`
- **Purpose:** Method __init__ of PredictionEngine
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** AnomalyDetector; BaselineManager
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.prediction.engine::PredictionEngine.evaluate_streams   (app/prediction/engine.py:42-84)
- **Signature:** `async def evaluate_streams(self, windows: Dict[MetricType, List[Measurement]]) -> List[PredictionWarning]`
- **Purpose:** Method evaluate_streams of PredictionEngine
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_prediction.py:75
- **Calls:** PredictionWarning; len; logger.info; self._recent_predictions.append; self._recent_predictions.pop; self.baselines.update_baseline; self.detector.evaluate_anomaly; self.event_bus.publish; warnings.append; windows.get
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.prediction.engine::PredictionEngine.recent_warnings   (app/prediction/engine.py:87-88)
- **Signature:** `def recent_warnings(self) -> List[PredictionWarning]`
- **Purpose:** Method recent_warnings of PredictionEngine
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** list
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.qoe.engine`

### app.qoe.engine::QoEEngine.__init__   (app/qoe/engine.py:16-18)
- **Signature:** `def __init__(self, event_bus: EventBus) -> None`
- **Purpose:** Method __init__ of QoEEngine
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.qoe.engine::QoEEngine._rating   (app/qoe/engine.py:21-28)
- **Signature:** `def _rating(score: float) -> str`
- **Purpose:** Method _rating of QoEEngine
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/qoe/engine.py:QoEEngine.calculate_qoe:104; app/qoe/engine.py:QoEEngine.calculate_qoe:109; app/qoe/engine.py:QoEEngine.calculate_qoe:114; app/qoe/engine.py:QoEEngine.calculate_qoe:119; app/qoe/engine.py:QoEEngine.calculate_qoe:96; app/qoe/engine.py:QoEEngine.calculate_qoe:99
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.qoe.engine::QoEEngine.calculate_qoe   (app/qoe/engine.py:30-131)
- **Signature:** `def calculate_qoe(self, latency_ms: float, jitter_ms: float, packet_loss_ratio: float, dns_latency_ms: float, rx_bytes_sec: float) -> QoEAssessment`
- **Purpose:** Method calculate_qoe of QoEEngine
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_qoe.py:13; tests/unit/test_qoe.py:27
- **Calls:** QoEAssessment; QoECategoryScore; bottlenecks.append; max; min; self._rating
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.qoe.engine::QoEEngine.latest_assessment   (app/qoe/engine.py:134-135)
- **Signature:** `def latest_assessment(self) -> Optional[QoEAssessment]`
- **Purpose:** Method latest_assessment of QoEEngine
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.remediation.actions.flush_dns`

### app.remediation.actions.flush_dns::FlushDNSCacheAction.__init__   (app/remediation/actions/flush_dns.py:15-25)
- **Signature:** `def __init__(self) -> None`
- **Purpose:** Method __init__ of FlushDNSCacheAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.flush_dns::FlushDNSCacheAction.check_preconditions   (app/remediation/actions/flush_dns.py:27-31)
- **Signature:** `def check_preconditions(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Tuple[bool, str]`
- **Purpose:** Method check_preconditions of FlushDNSCacheAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:120; tests/unit/test_remediation.py:253; tests/unit/test_remediation.py:257
- **Calls:** platform.get_primary_interface
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.flush_dns::FlushDNSCacheAction.execute   (app/remediation/actions/flush_dns.py:33-38)
- **Signature:** `async def execute(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Any`
- **Purpose:** Method execute of FlushDNSCacheAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:47; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:162; app/storage/database.py:DatabaseManager._apply_migrations:94; app/storage/database.py:DatabaseManager._apply_migrations:96; app/storage/database.py:DatabaseManager._init_storage:85; app/storage/database.py:DatabaseManager._init_storage:86; app/storage/database.py:DatabaseManager._init_storage:87; app/storage/database.py:DatabaseManager._init_storage:88; app/storage/repositories/audit_repo.py:AuditRepository.get_recent:63; app/storage/repositories/audit_repo.py:AuditRepository.save:29; app/storage/repositories/incident_repo.py:IncidentRepository.get_recent:57; app/storage/repositories/incident_repo.py:IncidentRepository.save:29; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_latest_by_metric:58; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_recent:74; app/storage/repositories/measurement_repo.py:MeasurementRepository.save:28; tests/unit/test_remediation.py:231; tests/unit/test_remediation.py:268
- **Calls:** RuntimeError; asyncio.get_running_loop; loop.run_in_executor; time.time
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.flush_dns::FlushDNSCacheAction.rollback   (app/remediation/actions/flush_dns.py:59-61)
- **Signature:** `async def rollback(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str]`
- **Purpose:** Method rollback of FlushDNSCacheAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:219; tests/unit/test_remediation.py:237
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.flush_dns::FlushDNSCacheAction.verify   (app/remediation/actions/flush_dns.py:40-57)
- **Signature:** `async def verify(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str, Dict[str, Any]]`
- **Purpose:** Method verify of FlushDNSCacheAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:197; tests/unit/test_remediation.py:271
- **Calls:** asyncio.get_running_loop; dns.resolver.Resolver; loop.run_in_executor; r.to_text; res.resolve; str; time.perf_counter
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

## Module: `app.remediation.actions.recheck_gateway`

### app.remediation.actions.recheck_gateway::RecheckGatewayAction.__init__   (app/remediation/actions/recheck_gateway.py:14-24)
- **Signature:** `def __init__(self) -> None`
- **Purpose:** Method __init__ of RecheckGatewayAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.recheck_gateway::RecheckGatewayAction.check_preconditions   (app/remediation/actions/recheck_gateway.py:26-30)
- **Signature:** `def check_preconditions(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Tuple[bool, str]`
- **Purpose:** Method check_preconditions of RecheckGatewayAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:120; tests/unit/test_remediation.py:253; tests/unit/test_remediation.py:257
- **Calls:** platform.get_default_gateway
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.recheck_gateway::RecheckGatewayAction.execute   (app/remediation/actions/recheck_gateway.py:32-44)
- **Signature:** `async def execute(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Any`
- **Purpose:** Method execute of RecheckGatewayAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:47; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:162; app/storage/database.py:DatabaseManager._apply_migrations:94; app/storage/database.py:DatabaseManager._apply_migrations:96; app/storage/database.py:DatabaseManager._init_storage:85; app/storage/database.py:DatabaseManager._init_storage:86; app/storage/database.py:DatabaseManager._init_storage:87; app/storage/database.py:DatabaseManager._init_storage:88; app/storage/repositories/audit_repo.py:AuditRepository.get_recent:63; app/storage/repositories/audit_repo.py:AuditRepository.save:29; app/storage/repositories/incident_repo.py:IncidentRepository.get_recent:57; app/storage/repositories/incident_repo.py:IncidentRepository.save:29; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_latest_by_metric:58; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_recent:74; app/storage/repositories/measurement_repo.py:MeasurementRepository.save:28; tests/unit/test_remediation.py:231; tests/unit/test_remediation.py:268
- **Calls:** asyncio.get_running_loop; asyncio.sleep; latencies.append; len; loop.run_in_executor; platform.get_default_gateway; range
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.recheck_gateway::RecheckGatewayAction.rollback   (app/remediation/actions/recheck_gateway.py:52-53)
- **Signature:** `async def rollback(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str]`
- **Purpose:** Method rollback of RecheckGatewayAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:219; tests/unit/test_remediation.py:237
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.recheck_gateway::RecheckGatewayAction.verify   (app/remediation/actions/recheck_gateway.py:46-50)
- **Signature:** `async def verify(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str, Dict[str, Any]]`
- **Purpose:** Method verify of RecheckGatewayAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:197; tests/unit/test_remediation.py:271
- **Calls:** pre_state.get
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.remediation.actions.renew_dhcp`

### app.remediation.actions.renew_dhcp::RenewIPLeaseAction.__init__   (app/remediation/actions/renew_dhcp.py:15-25)
- **Signature:** `def __init__(self) -> None`
- **Purpose:** Method __init__ of RenewIPLeaseAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.renew_dhcp::RenewIPLeaseAction.check_preconditions   (app/remediation/actions/renew_dhcp.py:27-34)
- **Signature:** `def check_preconditions(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Tuple[bool, str]`
- **Purpose:** Method check_preconditions of RenewIPLeaseAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:120; tests/unit/test_remediation.py:253; tests/unit/test_remediation.py:257
- **Calls:** context.get; platform.get_primary_interface; platform.is_elevated
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.renew_dhcp::RenewIPLeaseAction.execute   (app/remediation/actions/renew_dhcp.py:36-48)
- **Signature:** `async def execute(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Any`
- **Purpose:** Method execute of RenewIPLeaseAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:47; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:162; app/storage/database.py:DatabaseManager._apply_migrations:94; app/storage/database.py:DatabaseManager._apply_migrations:96; app/storage/database.py:DatabaseManager._init_storage:85; app/storage/database.py:DatabaseManager._init_storage:86; app/storage/database.py:DatabaseManager._init_storage:87; app/storage/database.py:DatabaseManager._init_storage:88; app/storage/repositories/audit_repo.py:AuditRepository.get_recent:63; app/storage/repositories/audit_repo.py:AuditRepository.save:29; app/storage/repositories/incident_repo.py:IncidentRepository.get_recent:57; app/storage/repositories/incident_repo.py:IncidentRepository.save:29; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_latest_by_metric:58; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_recent:74; app/storage/repositories/measurement_repo.py:MeasurementRepository.save:28; tests/unit/test_remediation.py:231; tests/unit/test_remediation.py:268
- **Calls:** RuntimeError; asyncio.get_running_loop; context.get; loop.run_in_executor; platform.get_primary_interface; time.time
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.renew_dhcp::RenewIPLeaseAction.rollback   (app/remediation/actions/renew_dhcp.py:62-63)
- **Signature:** `async def rollback(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str]`
- **Purpose:** Method rollback of RenewIPLeaseAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:219; tests/unit/test_remediation.py:237
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.renew_dhcp::RenewIPLeaseAction.verify   (app/remediation/actions/renew_dhcp.py:50-60)
- **Signature:** `async def verify(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str, Dict[str, Any]]`
- **Purpose:** Method verify of RenewIPLeaseAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:197; tests/unit/test_remediation.py:271
- **Calls:** asyncio.get_running_loop; loop.run_in_executor; platform.get_default_gateway
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.remediation.actions.switch_dns`

### app.remediation.actions.switch_dns::SwitchDNSResolverAction.__init__   (app/remediation/actions/switch_dns.py:15-26)
- **Signature:** `def __init__(self, fallback_resolvers: Optional[List[str]]) -> None`
- **Purpose:** Method __init__ of SwitchDNSResolverAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.switch_dns::SwitchDNSResolverAction.check_preconditions   (app/remediation/actions/switch_dns.py:28-35)
- **Signature:** `def check_preconditions(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Tuple[bool, str]`
- **Purpose:** Method check_preconditions of SwitchDNSResolverAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:120; tests/unit/test_remediation.py:253; tests/unit/test_remediation.py:257
- **Calls:** context.get; platform.get_primary_interface; platform.is_elevated
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.switch_dns::SwitchDNSResolverAction.execute   (app/remediation/actions/switch_dns.py:37-60)
- **Signature:** `async def execute(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Any`
- **Purpose:** Method execute of SwitchDNSResolverAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:47; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:162; app/storage/database.py:DatabaseManager._apply_migrations:94; app/storage/database.py:DatabaseManager._apply_migrations:96; app/storage/database.py:DatabaseManager._init_storage:85; app/storage/database.py:DatabaseManager._init_storage:86; app/storage/database.py:DatabaseManager._init_storage:87; app/storage/database.py:DatabaseManager._init_storage:88; app/storage/repositories/audit_repo.py:AuditRepository.get_recent:63; app/storage/repositories/audit_repo.py:AuditRepository.save:29; app/storage/repositories/incident_repo.py:IncidentRepository.get_recent:57; app/storage/repositories/incident_repo.py:IncidentRepository.save:29; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_latest_by_metric:58; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_recent:74; app/storage/repositories/measurement_repo.py:MeasurementRepository.save:28; tests/unit/test_remediation.py:231; tests/unit/test_remediation.py:268
- **Calls:** RuntimeError; asyncio.get_running_loop; context.get; loop.run_in_executor; platform.get_primary_interface; time.time
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.switch_dns::SwitchDNSResolverAction.rollback   (app/remediation/actions/switch_dns.py:88-104)
- **Signature:** `async def rollback(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str]`
- **Purpose:** Restore original DNS configuration from pre_state snapshot.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:219; tests/unit/test_remediation.py:237
- **Calls:** ', '.join; asyncio.get_running_loop; isinstance; loop.run_in_executor; pre_state.get
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.actions.switch_dns::SwitchDNSResolverAction.verify   (app/remediation/actions/switch_dns.py:62-86)
- **Signature:** `async def verify(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str, Dict[str, Any]]`
- **Purpose:** Method verify of SwitchDNSResolverAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:197; tests/unit/test_remediation.py:271
- **Calls:** asyncio.get_running_loop; dns.resolver.Resolver; len; loop.run_in_executor; r.to_text; res.resolve; str; time.perf_counter
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

## Module: `app.remediation.orchestrator`

### app.remediation.orchestrator::RemediationOrchestrator.__init__   (app/remediation/orchestrator.py:33-50)
- **Signature:** `def __init__(self, config: RemediationConfig, registry: ActionRegistry, safety_manager: ActionSafetyManager, platform_adapter: IPlatformAdapter, audit_repo: AuditRepository, event_bus: EventBus, meeting_guard_check: Optional[Callable[[], bool]]) -> None`
- **Purpose:** Method __init__ of RemediationOrchestrator
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** OperatingMode
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.orchestrator::RemediationOrchestrator._execute_and_verify   (app/remediation/orchestrator.py:140-247)
- **Signature:** `async def _execute_and_verify(self, action: RemediationAction, context: Dict[str, Any], diagnosis: Diagnosis) -> ActionExecutionRecord`
- **Purpose:** Executes action, conducts post-verification, and executes rollback if needed.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:138
- **Calls:** ActionExecutionRecord; action.execute; action.rollback; action.verify; asyncio.wait_for; logger.error; logger.info; logger.warning; self._record_and_publish; self.event_bus.publish
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception; catches Exception; catches Exception

### app.remediation.orchestrator::RemediationOrchestrator._record_and_publish   (app/remediation/orchestrator.py:249-256)
- **Signature:** `async def _record_and_publish(self, record: ActionExecutionRecord) -> None`
- **Purpose:** Method _record_and_publish of RemediationOrchestrator
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:188; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:246
- **Calls:** asyncio.get_running_loop; logger.warning; loop.run_in_executor; self.event_bus.publish
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.remediation.orchestrator::RemediationOrchestrator.handle_diagnosis   (app/remediation/orchestrator.py:57-138)
- **Signature:** `async def handle_diagnosis(self, diagnosis: Diagnosis) -> Optional[ActionExecutionRecord]`
- **Purpose:** Entry point for the 11-step remediation lifecycle.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/application.py:NetGuardApplication._continuous_evaluation_loop:146; app/application.py:NetGuardApplication.step:133; tests/unit/test_remediation.py:141; tests/unit/test_remediation.py:169; tests/unit/test_remediation.py:195; tests/unit/test_remediation.py:196; tests/unit/test_remediation.py:197; tests/unit/test_remediation.py:200; tests/unit/test_remediation.py:219; tests/unit/test_session_tracker.py:110
- **Calls:** diagnosis.model_dump; logger.error; logger.info; logger.warning; selected_action.check_preconditions; selected_action.is_os_supported; self._execute_and_verify; self.event_bus.publish; self.meeting_guard_check; self.platform.get_primary_interface
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.orchestrator::RemediationOrchestrator.set_operating_mode   (app/remediation/orchestrator.py:52-55)
- **Signature:** `def set_operating_mode(self, mode: OperatingMode) -> None`
- **Purpose:** Switch operating mode (Observation, Assisted, Autonomous Safe).
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/main.py:46; app/ui/main_window.py:MainWindow._on_apply_settings:775; app/ui/main_window.py:MainWindow._on_sidebar_mode_changed:391; tests/unit/test_remediation.py:207
- **Calls:** logger.info
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.remediation.registry`

### app.remediation.registry::ActionRegistry.__init__   (app/remediation/registry.py:71-72)
- **Signature:** `def __init__(self) -> None`
- **Purpose:** Method __init__ of ActionRegistry
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.registry::ActionRegistry.get   (app/remediation/registry.py:80-81)
- **Signature:** `def get(self, action_id: str) -> Optional[RemediationAction]`
- **Purpose:** Method get of ActionRegistry
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/utilities/logger.py:ColoredConsoleFormatter.format:45; app/diagnosis/classifiers/destination_fault.py:DestinationSpecificClassifier.evaluate:23; app/diagnosis/classifiers/dns_fault.py:DNSHealthClassifier.evaluate:22; app/diagnosis/classifiers/dns_fault.py:DNSHealthClassifier.evaluate:23; app/diagnosis/classifiers/dns_fault.py:DNSHealthClassifier.evaluate:24; app/diagnosis/classifiers/dns_fault.py:DNSHealthClassifier.evaluate:25; app/diagnosis/classifiers/gateway_fault.py:GatewayHealthClassifier.evaluate:23; app/diagnosis/classifiers/gateway_fault.py:GatewayHealthClassifier.evaluate:24; app/diagnosis/classifiers/gateway_fault.py:GatewayHealthClassifier.evaluate:25; app/diagnosis/classifiers/gateway_fault.py:GatewayHealthClassifier.evaluate:63; app/diagnosis/classifiers/upstream_isp_fault.py:UpstreamISPClassifier.evaluate:22; app/diagnosis/classifiers/upstream_isp_fault.py:UpstreamISPClassifier.evaluate:23; app/diagnosis/classifiers/upstream_isp_fault.py:UpstreamISPClassifier.evaluate:24; app/diagnosis/classifiers/upstream_isp_fault.py:UpstreamISPClassifier.evaluate:25; app/diagnosis/classifiers/upstream_isp_fault.py:UpstreamISPClassifier.evaluate:26; app/diagnosis/classifiers/wifi_fault.py:WifiInstabilityClassifier.evaluate:22; app/diagnosis/classifiers/wifi_fault.py:WifiInstabilityClassifier.evaluate:23; app/diagnosis/classifiers/wifi_fault.py:WifiInstabilityClassifier.evaluate:24; app/diagnosis/engine.py:DiagnosisEngine.evaluate_windows:85; app/learning/memory.py:NetworkMemory.find_best_action_for_context:74; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe._probe_single_target:125; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.execute:46; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.execute:34; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.execute:38; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.execute:39; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.execute:45; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.execute:52; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.execute:61; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.execute:68; app/monitoring/schedulers/engine.py:ObservabilityEngine.get_latest_measurement:174; app/platform/windows/network_info.py:197; app/platform/windows/network_info.py:210; app/platform/windows/network_info.py:211; app/prediction/baselines.py:BaselineManager.get_baseline:63; app/prediction/engine.py:PredictionEngine.evaluate_streams:54; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.verify:47; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.check_preconditions:31; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.execute:38; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.check_preconditions:32; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.execute:39; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.execute:40; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.rollback:93; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.rollback:94; app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:70; app/remediation/registry.py:ActionRegistry.get:81; app/remediation/safety.py:ActionSafetyManager.get_remaining_cooldown:70; app/remediation/safety.py:ActionSafetyManager.is_cooling_down:65; app/remediation/safety.py:ActionSafetyManager.record_failure:99; app/remediation/safety.py:ActionSafetyManager.record_success:94; app/router/generic.py:GenericRouterAdapter.detect_model:26; app/traffic/applications.py:ApplicationCatalog.classify:94; app/ui/i18n.py:290; app/ui/main_window.py:MainWindow._on_network_info_ready:462; app/ui/main_window.py:MainWindow._on_remediation_event_received:423; app/ui/main_window.py:MainWindow._on_sidebar_mode_changed:390; app/ui/main_window.py:SidebarWidget._on_mode_clicked:271; app/ui/widgets/day_strip.py:DayStripCanvas.mouseMoveEvent:122; tests/unit/test_dns_optimizer.py:50
- **Calls:** self._actions.get
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.registry::ActionRegistry.list_actions   (app/remediation/registry.py:83-84)
- **Signature:** `def list_actions(self) -> List[RemediationAction]`
- **Purpose:** Method list_actions of ActionRegistry
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/main.py:106; app/main.py:167
- **Calls:** list; self._actions.values
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.registry::ActionRegistry.register   (app/remediation/registry.py:74-78)
- **Signature:** `def register(self, action: RemediationAction) -> None`
- **Purpose:** Method register of ActionRegistry
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/application.py:NetGuardApplication._register_default_actions:79; app/application.py:NetGuardApplication._register_default_actions:80; app/application.py:NetGuardApplication._register_default_actions:81; app/application.py:NetGuardApplication._register_default_actions:84; tests/unit/test_remediation.py:131; tests/unit/test_remediation.py:159; tests/unit/test_remediation.py:184; tests/unit/test_remediation.py:209; tests/unit/test_session_tracker.py:82
- **Calls:** logger.info; logger.warning
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.registry::RemediationAction.__init__   (app/remediation/registry.py:17-35)
- **Signature:** `def __init__(self, action_id: str, name: str, description: str, risk_level: RiskLevel, supported_os: Optional[List[str]], timeout_sec: float, cooldown_sec: float, max_retries: int) -> None`
- **Purpose:** Method __init__ of RemediationAction
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.registry::RemediationAction.check_preconditions   (app/remediation/registry.py:46-48)
- **Signature:** `def check_preconditions(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Tuple[bool, str]`
- **Purpose:** Check all safety invariants and permissions before executing.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:120; tests/unit/test_remediation.py:253; tests/unit/test_remediation.py:257
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.registry::RemediationAction.execute   (app/remediation/registry.py:51-53)
- **Signature:** `async def execute(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Any`
- **Purpose:** Execute recovery action. Must return pre-state snapshot for potential rollback.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/monitoring/probes/base.py:BaseProbe.run:47; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:162; app/storage/database.py:DatabaseManager._apply_migrations:94; app/storage/database.py:DatabaseManager._apply_migrations:96; app/storage/database.py:DatabaseManager._init_storage:85; app/storage/database.py:DatabaseManager._init_storage:86; app/storage/database.py:DatabaseManager._init_storage:87; app/storage/database.py:DatabaseManager._init_storage:88; app/storage/repositories/audit_repo.py:AuditRepository.get_recent:63; app/storage/repositories/audit_repo.py:AuditRepository.save:29; app/storage/repositories/incident_repo.py:IncidentRepository.get_recent:57; app/storage/repositories/incident_repo.py:IncidentRepository.save:29; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_latest_by_metric:58; app/storage/repositories/measurement_repo.py:MeasurementRepository.get_recent:74; app/storage/repositories/measurement_repo.py:MeasurementRepository.save:28; tests/unit/test_remediation.py:231; tests/unit/test_remediation.py:268
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.registry::RemediationAction.is_os_supported   (app/remediation/registry.py:37-43)
- **Signature:** `def is_os_supported(self) -> bool`
- **Purpose:** Verify action is authorized and supported on current operating system.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:114
- **Calls:** current_platform.startswith
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.registry::RemediationAction.rollback   (app/remediation/registry.py:63-65)
- **Signature:** `async def rollback(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str]`
- **Purpose:** Restore previous configuration if verification fails or side effects occur.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:219; tests/unit/test_remediation.py:237
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.registry::RemediationAction.verify   (app/remediation/registry.py:56-60)
- **Signature:** `async def verify(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str, Dict[str, Any]]`
- **Purpose:** Empirically measure post-action network behavior.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:197; tests/unit/test_remediation.py:271
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.remediation.safety`

### app.remediation.safety::ActionSafetyManager.__init__   (app/remediation/safety.py:55-60)
- **Signature:** `def __init__(self, failure_threshold: int, reset_timeout_sec: float) -> None`
- **Purpose:** Method __init__ of ActionSafetyManager
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** asyncio.Lock
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.safety::ActionSafetyManager.can_execute   (app/remediation/safety.py:74-88)
- **Signature:** `def can_execute(self, action_id: str, cooldown_sec: float) -> Tuple[bool, str]`
- **Purpose:** Method can_execute of ActionSafetyManager
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:126; app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:134; app/remediation/safety.py:ActionSafetyManager.can_execute:80
- **Calls:** CircuitBreaker; breaker.can_execute; self._breakers.setdefault; self.get_remaining_cooldown; self.is_cooling_down
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.safety::ActionSafetyManager.get_remaining_cooldown   (app/remediation/safety.py:68-72)
- **Signature:** `def get_remaining_cooldown(self, action_id: str, cooldown_sec: float) -> float`
- **Purpose:** Method get_remaining_cooldown of ActionSafetyManager
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/safety.py:ActionSafetyManager.can_execute:85
- **Calls:** max; self._last_execution_time.get; time.monotonic
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.safety::ActionSafetyManager.is_cooling_down   (app/remediation/safety.py:62-66)
- **Signature:** `def is_cooling_down(self, action_id: str, cooldown_sec: float) -> bool`
- **Purpose:** Check if action is in cooldown since last execution.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/safety.py:ActionSafetyManager.can_execute:84
- **Calls:** self._last_execution_time.get; time.monotonic
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.safety::ActionSafetyManager.lock   (app/remediation/safety.py:104-105)
- **Signature:** `def lock(self) -> asyncio.Lock`
- **Purpose:** Method lock of ActionSafetyManager
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.safety::ActionSafetyManager.record_execution_start   (app/remediation/safety.py:90-91)
- **Signature:** `def record_execution_start(self, action_id: str) -> None`
- **Purpose:** Method record_execution_start of ActionSafetyManager
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:147
- **Calls:** time.monotonic
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.safety::ActionSafetyManager.record_failure   (app/remediation/safety.py:98-101)
- **Signature:** `def record_failure(self, action_id: str) -> None`
- **Purpose:** Method record_failure of ActionSafetyManager
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:171; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:213; app/remediation/safety.py:ActionSafetyManager.record_failure:101
- **Calls:** breaker.record_failure; self._breakers.get
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.safety::ActionSafetyManager.record_success   (app/remediation/safety.py:93-96)
- **Signature:** `def record_success(self, action_id: str) -> None`
- **Purpose:** Method record_success of ActionSafetyManager
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:209; app/remediation/safety.py:ActionSafetyManager.record_success:96
- **Calls:** breaker.record_success; self._breakers.get
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.safety::CircuitBreaker.__init__   (app/remediation/safety.py:18-23)
- **Signature:** `def __init__(self, failure_threshold: int, reset_timeout_sec: float) -> None`
- **Purpose:** Method __init__ of CircuitBreaker
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.safety::CircuitBreaker.can_execute   (app/remediation/safety.py:25-33)
- **Signature:** `def can_execute(self) -> bool`
- **Purpose:** Method can_execute of CircuitBreaker
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:126; app/remediation/orchestrator.py:RemediationOrchestrator.handle_diagnosis:134; app/remediation/safety.py:ActionSafetyManager.can_execute:80
- **Calls:** logger.info; time.monotonic
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.safety::CircuitBreaker.record_failure   (app/remediation/safety.py:39-49)
- **Signature:** `def record_failure(self) -> None`
- **Purpose:** Method record_failure of CircuitBreaker
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:171; app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:213; app/remediation/safety.py:ActionSafetyManager.record_failure:101
- **Calls:** logger.warning; time.monotonic
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.remediation.safety::CircuitBreaker.record_success   (app/remediation/safety.py:35-37)
- **Signature:** `def record_success(self) -> None`
- **Purpose:** Method record_success of CircuitBreaker
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/remediation/orchestrator.py:RemediationOrchestrator._execute_and_verify:209; app/remediation/safety.py:ActionSafetyManager.record_success:96
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.router.base`

### app.router.base::BaseRouterAdapter.__init__   (app/router/base.py:12-13)
- **Signature:** `def __init__(self, gateway_ip: str) -> None`
- **Purpose:** Method __init__ of BaseRouterAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.router.base::BaseRouterAdapter.detect_model   (app/router/base.py:16-18)
- **Signature:** `async def detect_model(self) -> Optional[str]`
- **Purpose:** Attempt non-intrusive auto-detection of the router hardware/firmware model.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/cellular/engine.py:CellularDiagnosticsEngine.auto_discover_adapter:27; app/cellular/engine.py:CellularDiagnosticsEngine.auto_discover_adapter:35; app/router/generic.py:GenericRouterAdapter.get_device_info:50
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.router.base::BaseRouterAdapter.get_cellular_metrics   (app/router/base.py:21-23)
- **Signature:** `async def get_cellular_metrics(self) -> Optional[CellularMetrics]`
- **Purpose:** Fetch real-time RF radio metrics (RSRP, RSRQ, SINR, Band, Cell ID) if exposed.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/cellular/engine.py:CellularDiagnosticsEngine.poll_metrics:42
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.router.base::BaseRouterAdapter.get_device_info   (app/router/base.py:26-28)
- **Signature:** `async def get_device_info(self) -> Dict[str, Any]`
- **Purpose:** Retrieve router model, firmware version, and uptime metadata.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_cellular.py:30
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.router.generic`

### app.router.generic::GenericRouterAdapter.detect_model   (app/router/generic.py:15-42)
- **Signature:** `async def detect_model(self) -> Optional[str]`
- **Purpose:** Method detect_model of GenericRouterAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/cellular/engine.py:CellularDiagnosticsEngine.auto_discover_adapter:27; app/cellular/engine.py:CellularDiagnosticsEngine.auto_discover_adapter:35; app/router/generic.py:GenericRouterAdapter.get_device_info:50
- **Calls:** asyncio.get_running_loop; dict; headers.get; loop.run_in_executor; re.search; resp.read; resp.read(2048).decode; title_match.group; title_match.group(1).strip; urllib.request.Request
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.router.generic::GenericRouterAdapter.get_cellular_metrics   (app/router/generic.py:44-47)
- **Signature:** `async def get_cellular_metrics(self) -> Optional[CellularMetrics]`
- **Purpose:** Method get_cellular_metrics of GenericRouterAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/cellular/engine.py:CellularDiagnosticsEngine.poll_metrics:42
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.router.generic::GenericRouterAdapter.get_device_info   (app/router/generic.py:49-55)
- **Signature:** `async def get_device_info(self) -> Dict[str, Any]`
- **Purpose:** Method get_device_info of GenericRouterAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_cellular.py:30
- **Calls:** self.detect_model
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.router.hilink`

### app.router.hilink::HuaweiHiLinkAdapter.detect_model   (app/router/hilink.py:15-29)
- **Signature:** `async def detect_model(self) -> Optional[str]`
- **Purpose:** Method detect_model of HuaweiHiLinkAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/cellular/engine.py:CellularDiagnosticsEngine.auto_discover_adapter:27; app/cellular/engine.py:CellularDiagnosticsEngine.auto_discover_adapter:35; app/router/generic.py:GenericRouterAdapter.get_device_info:50
- **Calls:** asyncio.get_running_loop; loop.run_in_executor; urllib.request.Request; urllib.request.urlopen
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception (swallowed silently)

### app.router.hilink::HuaweiHiLinkAdapter.get_cellular_metrics   (app/router/hilink.py:31-65)
- **Signature:** `async def get_cellular_metrics(self) -> Optional[CellularMetrics]`
- **Purpose:** Method get_cellular_metrics of HuaweiHiLinkAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/cellular/engine.py:CellularDiagnosticsEngine.poll_metrics:42
- **Calls:** CellularMetrics; CellularMetrics.classify_quality; ET.fromstring; asyncio.get_running_loop; float; loop.run_in_executor; resp.read; resp.read().decode; tree.findtext; tree.findtext('rsrp', '').replace
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.router.hilink::HuaweiHiLinkAdapter.get_device_info   (app/router/hilink.py:67-72)
- **Signature:** `async def get_device_info(self) -> Dict[str, Any]`
- **Purpose:** Method get_device_info of HuaweiHiLinkAdapter
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_cellular.py:30
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.simulation.twin`

### app.simulation.twin::NetworkDigitalTwin.simulate_background_throttling   (app/simulation/twin.py:48-67)
- **Signature:** `def simulate_background_throttling(current_loaded_latency_ms: float, estimated_idle_latency_ms: float, throttled_bandwidth_ratio: float) -> SimulationResult`
- **Purpose:** Simulate queue delay reduction when throttling aggressive background downloads.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_learning_and_twin.py:53
- **Calls:** SimulationResult; max
- **Real or fake?:** `SIMULATED`
- **Error handling:** No explicit try/except

### app.simulation.twin::NetworkDigitalTwin.simulate_dns_switch   (app/simulation/twin.py:29-45)
- **Signature:** `def simulate_dns_switch(current_mean_dns_latency: float, candidate_resolver_latency: float) -> SimulationResult`
- **Purpose:** Simulate impact of switching DNS resolvers.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_learning_and_twin.py:44
- **Calls:** SimulationResult; max
- **Real or fake?:** `SIMULATED`
- **Error handling:** No explicit try/except

## Module: `app.traffic.applications`

### app.traffic.applications::ApplicationCatalog.classify   (app/traffic/applications.py:88-98)
- **Signature:** `def classify(cls, process_name: str) -> tuple[WorkloadCategory, int, bool]`
- **Purpose:** Returns (category, priority, is_protected).
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/traffic/controller.py:TrafficController.scan_active_applications:44; tests/unit/test_traffic.py:11; tests/unit/test_traffic.py:16; tests/unit/test_traffic.py:20; tests/unit/test_traffic.py:25; tests/unit/test_traffic.py:30
- **Calls:** cls.SIGNATURES.get; process_name.lower
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.traffic.bufferbloat`

### app.traffic.bufferbloat::BufferbloatEvaluator.__init__   (app/traffic/bufferbloat.py:40-42)
- **Signature:** `def __init__(self, platform: IPlatformAdapter, event_bus: EventBus) -> None`
- **Purpose:** Method __init__ of BufferbloatEvaluator
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.traffic.bufferbloat::BufferbloatEvaluator.calculate_grade   (app/traffic/bufferbloat.py:45-56)
- **Signature:** `def calculate_grade(delta_ms: float) -> BufferbloatGrade`
- **Purpose:** Method calculate_grade of BufferbloatEvaluator
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/traffic/bufferbloat.py:BufferbloatEvaluator.evaluate_latency_delta:67; tests/unit/test_bufferbloat.py:10; tests/unit/test_bufferbloat.py:11; tests/unit/test_bufferbloat.py:12; tests/unit/test_bufferbloat.py:13; tests/unit/test_bufferbloat.py:14; tests/unit/test_bufferbloat.py:15
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.traffic.bufferbloat::BufferbloatEvaluator.evaluate_latency_delta   (app/traffic/bufferbloat.py:58-87)
- **Signature:** `async def evaluate_latency_delta(self, idle_latency_ms: float, loaded_latency_ms: float, target: str) -> BufferbloatReport`
- **Purpose:** Evaluate bufferbloat given idle baseline and loaded latency.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_bufferbloat.py:25
- **Calls:** BufferbloatReport; max; report.model_dump; self.calculate_grade; self.event_bus.publish
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.traffic.controller`

### app.traffic.controller::TrafficController.__init__   (app/traffic/controller.py:18-21)
- **Signature:** `def __init__(self, event_bus: EventBus) -> None`
- **Purpose:** Method __init__ of TrafficController
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** AppSessionTracker
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.traffic.controller::TrafficController.is_critical_meeting_active   (app/traffic/controller.py:107-112)
- **Signature:** `def is_critical_meeting_active(self) -> bool`
- **Purpose:** Safety check: Returns True if Zoom, Teams, or conferencing app has active sockets.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_scan_traffic:689; tests/unit/test_session_tracker.py:65; tests/unit/test_session_tracker.py:69; tests/unit/test_session_tracker.py:75
- **Calls:** any; self._last_profiles.values; self.session_tracker.has_active_conferencing
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.traffic.controller::TrafficController.scan_active_applications   (app/traffic/controller.py:23-105)
- **Signature:** `async def scan_active_applications(self) -> List[ProcessNetworkProfile]`
- **Purpose:** Scans all active TCP/UDP connections and builds workload profiles.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_scan_traffic:688; tests/unit/test_traffic.py:39
- **Calls:** ApplicationCatalog.classify; ProcessNetworkProfile; active_pids.items; active_pids.setdefault; active_pids.setdefault(conn.pid, []).append; active_session.process_name.lower; any; asyncio.get_running_loop; len; list
- **Real or fake?:** `REAL`
- **Error handling:** catches (psutil.NoSuchProcess, psutil.AccessDenied)

### app.traffic.controller::TrafficController.simulate_close_meeting_session   (app/traffic/controller.py:126-128)
- **Signature:** `def simulate_close_meeting_session(self, proc_name: str) -> Optional[AppSessionRecord]`
- **Purpose:** Helper to simulate closing a Zoom session and generating its final report.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_session_tracker.py:73
- **Calls:** self.session_tracker.close_session
- **Real or fake?:** `SIMULATED`
- **Error handling:** No explicit try/except

### app.traffic.controller::TrafficController.simulate_start_meeting_session   (app/traffic/controller.py:114-124)
- **Signature:** `def simulate_start_meeting_session(self, app_name: str, proc_name: str) -> AppSessionRecord`
- **Purpose:** Helper to simulate launching a protected Zoom session.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_session_tracker.py:68
- **Calls:** self.session_tracker.start_or_update_session
- **Real or fake?:** `SIMULATED`
- **Error handling:** No explicit try/except

## Module: `app.traffic.session_tracker`

### app.traffic.session_tracker::AppSessionRecord.duration_formatted   (app/traffic/session_tracker.py:55-64)
- **Signature:** `def duration_formatted(self) -> str`
- **Purpose:** Method duration_formatted of AppSessionRecord
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** int
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.traffic.session_tracker::AppSessionRecord.end_time_str   (app/traffic/session_tracker.py:71-74)
- **Signature:** `def end_time_str(self) -> str`
- **Purpose:** Method end_time_str of AppSessionRecord
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.end_time.strftime
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.traffic.session_tracker::AppSessionRecord.start_time_str   (app/traffic/session_tracker.py:67-68)
- **Signature:** `def start_time_str(self) -> str`
- **Purpose:** Method start_time_str of AppSessionRecord
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.start_time.strftime
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.traffic.session_tracker::AppSessionTracker.__init__   (app/traffic/session_tracker.py:80-83)
- **Signature:** `def __init__(self) -> None`
- **Purpose:** Method __init__ of AppSessionTracker
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** self._seed_default_history
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.traffic.session_tracker::AppSessionTracker._seed_default_history   (app/traffic/session_tracker.py:85-218)
- **Signature:** `def _seed_default_history(self) -> None`
- **Purpose:** Seed realistic completed sessions with rich technical prevention reports.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/traffic/session_tracker.py:AppSessionTracker.__init__:83
- **Calls:** AppSessionRecord; SessionPreventiveAction; datetime.now; timedelta
- **Real or fake?:** `SIMULATED`
- **Error handling:** No explicit try/except

### app.traffic.session_tracker::AppSessionTracker.add_preventive_action   (app/traffic/session_tracker.py:268-288)
- **Signature:** `def add_preventive_action(self, process_name: str, title: str, detail: str, impact: str) -> None`
- **Purpose:** Append a real-time preventive action to the session.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_session_tracker.py:40
- **Calls:** SessionPreventiveAction; datetime.now; datetime.now(timezone.utc).strftime; list; process_name.lower; session.model_copy
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.traffic.session_tracker::AppSessionTracker.close_session   (app/traffic/session_tracker.py:290-308)
- **Signature:** `def close_session(self, process_name: str) -> Optional[AppSessionRecord]`
- **Purpose:** Close an active session, compute final duration, and move to completed history.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/traffic/controller.py:TrafficController.scan_active_applications:88; app/traffic/controller.py:TrafficController.simulate_close_meeting_session:128; app/ui/views/traffic_view.py:TrafficView._close_session_by_name:259; app/ui/views/traffic_view.py:TrafficView._on_sim_zoom_clicked:241; tests/unit/test_session_tracker.py:50
- **Calls:** (now - session.start_time).total_seconds; datetime.now; max; process_name.lower; self._active_sessions.pop; self._completed_sessions.insert; session.model_copy
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.traffic.session_tracker::AppSessionTracker.get_active_sessions   (app/traffic/session_tracker.py:310-311)
- **Signature:** `def get_active_sessions(self) -> List[AppSessionRecord]`
- **Purpose:** Method get_active_sessions of AppSessionTracker
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/traffic/controller.py:TrafficController.scan_active_applications:101; app/traffic/controller.py:TrafficController.scan_active_applications:85; app/ui/views/traffic_view.py:TrafficView._on_sim_zoom_clicked:236; app/ui/views/traffic_view.py:TrafficView._refresh_sessions_ui:272; tests/unit/test_session_tracker.py:37; tests/unit/test_session_tracker.py:46; tests/unit/test_session_tracker.py:55; tests/unit/test_session_tracker.py:70
- **Calls:** list; self._active_sessions.values
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.traffic.session_tracker::AppSessionTracker.get_completed_sessions   (app/traffic/session_tracker.py:313-314)
- **Signature:** `def get_completed_sessions(self) -> List[AppSessionRecord]`
- **Purpose:** Method get_completed_sessions of AppSessionTracker
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/traffic/controller.py:TrafficController.scan_active_applications:102; app/ui/views/traffic_view.py:TrafficView._populate_session_reports:300; tests/unit/test_session_tracker.py:21; tests/unit/test_session_tracker.py:58
- **Calls:** list
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.traffic.session_tracker::AppSessionTracker.has_active_conferencing   (app/traffic/session_tracker.py:316-317)
- **Signature:** `def has_active_conferencing(self) -> bool`
- **Purpose:** Method has_active_conferencing of AppSessionTracker
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/traffic/controller.py:TrafficController.is_critical_meeting_active:111; app/traffic/controller.py:TrafficController.scan_active_applications:92; tests/unit/test_session_tracker.py:36; tests/unit/test_session_tracker.py:54
- **Calls:** any; self._active_sessions.values
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.traffic.session_tracker::AppSessionTracker.start_or_update_session   (app/traffic/session_tracker.py:220-266)
- **Signature:** `def start_or_update_session(self, app_name: str, process_name: str, pid: int, category: str, avg_bitrate: float, avg_latency: float) -> AppSessionRecord`
- **Purpose:** Start or update an active session.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/traffic/controller.py:TrafficController.scan_active_applications:77; app/traffic/controller.py:TrafficController.simulate_start_meeting_session:116; app/ui/views/traffic_view.py:TrafficView._on_sim_zoom_clicked:246; tests/unit/test_session_tracker.py:27
- **Calls:** (now - session.start_time).total_seconds; AppSessionRecord; SessionPreventiveAction; datetime.now; now.strftime; process_name.lower; session.model_copy
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.i18n`

### app.ui.i18n::get_friendly_diagnosis_explanation   (app/ui/i18n.py:293-321)
- **Signature:** `def get_friendly_diagnosis_explanation(cause_val: str, raw_explanation: str) -> str`
- **Purpose:** Converts internal diagnostic explanations into crisp, natural Arabic.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** any; cause_val.lower; isinstance; raw_explanation.lower; str; str(cause_val).lower
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.i18n::get_language   (app/ui/i18n.py:284-285)
- **Signature:** `def get_language() -> str`
- **Purpose:** Function get_language
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.i18n::set_language   (app/ui/i18n.py:278-281)
- **Signature:** `def set_language(lang: str) -> None`
- **Purpose:** Function set_language
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.i18n::tr   (app/ui/i18n.py:288-290)
- **Signature:** `def tr(key: str, default: str) -> str`
- **Purpose:** Retrieve localized string for the active language.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** STRINGS.get; STRINGS.get(_current_lang, {}).get
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.main_window`

### app.ui.main_window::MainWindow.__init__   (app/ui/main_window.py:278-372)
- **Signature:** `def __init__(self, application: Any, parent: Optional[QWidget]) -> None`
- **Purpose:** Method __init__ of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** DNSView; DashboardView; DiagnosisView; HistoryView; QApplication.instance; QApplication.instance().setLayoutDirection; QHBoxLayout; QStackedWidget; QTimer; QWidget
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._async_inspect_network_environment   (app/ui/main_window.py:437-459)
- **Signature:** `def _async_inspect_network_environment(self) -> None`
- **Purpose:** Method _async_inspect_network_environment of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow.__init__:359
- **Calls:** get_active_dns_servers; get_isp_and_public_ip; get_wifi_details; self.app_core.ctx.platform.get_default_gateway; self.app_core.ctx.platform.get_primary_interface; self.bridge.network_info_ready.emit; threading.Thread; threading.Thread(target=_worker, daemon=True).start
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_apply_dns_requested   (app/ui/main_window.py:638-681)
- **Signature:** `def _on_apply_dns_requested(self, primary_ip: str, secondary_ip: str, name: str) -> None`
- **Purpose:** Method _on_apply_dns_requested of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_dashboard_apply_dns:600; app/ui/main_window.py:MainWindow._on_dns_benchmark_done:561
- **Calls:** ActionExecutionRecord; datetime.now; datetime.now().strftime; self.app_core.ctx.audit.save; self.app_core.ctx.platform.flush_dns_cache; self.app_core.ctx.platform.get_primary_interface; self.app_core.ctx.platform.set_interface_dns_servers; self.view_dashboard.log_autonomous_action; servers.append; str
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_apply_settings   (app/ui/main_window.py:766-777)
- **Signature:** `def _on_apply_settings(self) -> None`
- **Purpose:** Method _on_apply_settings of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** QTimer.singleShot; self.app_core.orchestrator.set_operating_mode; self.view_settings.apply_btn.setText; self.view_settings.mode_combo.currentData; self.view_settings.mode_combo.currentText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_dashboard_apply_dns   (app/ui/main_window.py:595-623)
- **Signature:** `def _on_dashboard_apply_dns(self) -> None`
- **Purpose:** Method _on_dashboard_apply_dns of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** hasattr; self._on_apply_dns_requested; self.view_dashboard.update_dns_recommendation; self.view_diagnosis.update_dns_telemetry; self.view_dns.set_active_dns_info; self.view_dns.update_rankings; time.time
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_dashboard_revert_dns   (app/ui/main_window.py:625-636)
- **Signature:** `def _on_dashboard_revert_dns(self) -> None`
- **Purpose:** Method _on_dashboard_revert_dns of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self._on_run_dns_benchmark; self.app_core.ctx.platform.flush_dns_cache; self.app_core.ctx.platform.get_primary_interface; self.app_core.ctx.platform.set_interface_dns_servers; self.view_dashboard.log_autonomous_action; time.time
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_deep_diagnosis_finished   (app/ui/main_window.py:710-720)
- **Signature:** `def _on_deep_diagnosis_finished(self) -> None`
- **Purpose:** Method _on_deep_diagnosis_finished of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.view_dashboard.log_autonomous_action; self.view_diagnosis.btn_run_audit.setEnabled; self.view_diagnosis.btn_run_audit.setText; self.view_diagnosis.update_diagnosis
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_dns_benchmark_done   (app/ui/main_window.py:505-593)
- **Signature:** `def _on_dns_benchmark_done(self, scores) -> None`
- **Purpose:** Method _on_dns_benchmark_done of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** scripts/verify_ui_render.py:39
- **Calls:** any; best.name.replace; best.name.replace(' Primary', '').replace; getattr; matched_score.name.replace; matched_score.name.replace(' Primary', '').replace; max; self._on_apply_dns_requested; self.app_core.ctx.platform.get_interface_dns_servers; self.app_core.ctx.platform.get_primary_interface
- **Real or fake?:** `PARTIAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_network_info_ready   (app/ui/main_window.py:461-467)
- **Signature:** `def _on_network_info_ready(self, info: Dict[str, Any]) -> None`
- **Purpose:** Method _on_network_info_ready of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** QTimer.singleShot; getattr; info.get; self.view_dashboard.update_network_identity; self.view_dns.set_active_dns_info
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_quick_flush_dns   (app/ui/main_window.py:722-739)
- **Signature:** `def _on_quick_flush_dns(self) -> None`
- **Purpose:** Method _on_quick_flush_dns of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** QTimer.singleShot; hasattr; self._on_quick_flush_dns_done; self.view_remediation.btn_flush_now.setEnabled; self.view_remediation.btn_flush_now.setText; subprocess.run; threading.Thread; threading.Thread(target=_worker, daemon=True).start
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception (swallowed silently)

### app.ui.main_window::MainWindow._on_quick_flush_dns_done   (app/ui/main_window.py:741-749)
- **Signature:** `def _on_quick_flush_dns_done(self) -> None`
- **Purpose:** Method _on_quick_flush_dns_done of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_quick_flush_dns:737
- **Calls:** QTimer.singleShot; self.view_dashboard.log_autonomous_action; self.view_remediation.btn_flush_now.setEnabled; self.view_remediation.btn_flush_now.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_quick_renew_ip   (app/ui/main_window.py:751-754)
- **Signature:** `def _on_quick_renew_ip(self) -> None`
- **Purpose:** Method _on_quick_renew_ip of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** QTimer.singleShot; self.view_remediation.btn_renew_ip.setEnabled; self.view_remediation.btn_renew_ip.setText
- **Real or fake?:** `SIMULATED`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_quick_renew_ip_done   (app/ui/main_window.py:756-764)
- **Signature:** `def _on_quick_renew_ip_done(self) -> None`
- **Purpose:** Method _on_quick_renew_ip_done of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** QTimer.singleShot; self.view_dashboard.log_autonomous_action; self.view_remediation.btn_renew_ip.setEnabled; self.view_remediation.btn_renew_ip.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_remediation_event_received   (app/ui/main_window.py:422-435)
- **Signature:** `def _on_remediation_event_received(self, stage: str, data: Dict[str, Any]) -> None`
- **Purpose:** Method _on_remediation_event_received of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** data.get; self.view_dashboard.log_autonomous_action
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_run_deep_diagnosis   (app/ui/main_window.py:700-708)
- **Signature:** `def _on_run_deep_diagnosis(self) -> None`
- **Purpose:** Method _on_run_deep_diagnosis of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** QTimer.singleShot; self.view_diagnosis.btn_run_audit.setEnabled; self.view_diagnosis.btn_run_audit.setText; threading.Thread; threading.Thread(target=_worker, daemon=True).start; time.sleep
- **Real or fake?:** `SIMULATED`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_run_dns_benchmark   (app/ui/main_window.py:487-503)
- **Signature:** `def _on_run_dns_benchmark(self) -> None`
- **Purpose:** Method _on_run_dns_benchmark of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_dashboard_revert_dns:636; app/ui/main_window.py:MainWindow._switch_view:380
- **Calls:** DNSBenchmark; asyncio.run; bench.rank_all; getattr; self.bridge.dns_benchmark_done.emit; self.view_dns.benchmark_btn.setEnabled; self.view_dns.benchmark_btn.setText; threading.Thread; threading.Thread(target=_worker, daemon=True).start
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

### app.ui.main_window::MainWindow._on_scan_traffic   (app/ui/main_window.py:683-692)
- **Signature:** `def _on_scan_traffic(self) -> None`
- **Purpose:** Method _on_scan_traffic of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._switch_view:382
- **Calls:** asyncio.run; self.bridge.traffic_scan_done.emit; self.traffic_controller.is_critical_meeting_active; self.traffic_controller.scan_active_applications; self.view_traffic.btn_refresh.setEnabled; self.view_traffic.btn_refresh.setText; threading.Thread; threading.Thread(target=_worker, daemon=True).start
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_scan_traffic_done   (app/ui/main_window.py:694-698)
- **Signature:** `def _on_scan_traffic_done(self, profiles, is_conferencing: bool) -> None`
- **Purpose:** Method _on_scan_traffic_done of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.view_dashboard.consumers_panel.update_processes; self.view_traffic.btn_refresh.setEnabled; self.view_traffic.btn_refresh.setText; self.view_traffic.update_profiles
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_sidebar_mode_changed   (app/ui/main_window.py:384-391)
- **Signature:** `def _on_sidebar_mode_changed(self, idx: int) -> None`
- **Purpose:** Method _on_sidebar_mode_changed of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** mode_map.get; self.app_core.orchestrator.set_operating_mode
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._on_ui_tick   (app/ui/main_window.py:469-485)
- **Signature:** `def _on_ui_tick(self) -> None`
- **Purpose:** Periodic UI update polling in-memory telemetry completely autonomously.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_ui.py:50
- **Calls:** self.app_core.ctx.audit.get_recent; self.app_core.ctx.incidents.get_recent; self.stack.currentWidget; self.view_dashboard.update_telemetry; self.view_diagnosis.update_diagnosis; self.view_history.update_incidents; self.view_remediation.update_audit_log
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._switch_view   (app/ui/main_window.py:374-382)
- **Signature:** `def _switch_view(self, index: int, active_btn: QPushButton) -> None`
- **Purpose:** Method _switch_view of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow.__init__:341; scripts/verify_ui_render.py:101; scripts/verify_ui_render.py:107; scripts/verify_ui_render.py:65; scripts/verify_ui_render.py:75; scripts/verify_ui_render.py:87; tests/unit/test_ui.py:53; tests/unit/test_ui.py:55
- **Calls:** b.setChecked; self._on_run_dns_benchmark; self._on_scan_traffic; self.stack.setCurrentIndex; self.view_dns.table.rowCount
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow._wire_background_event_listeners   (app/ui/main_window.py:393-420)
- **Signature:** `def _wire_background_event_listeners(self) -> None`
- **Purpose:** Method _wire_background_event_listeners of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow.__init__:356
- **Calls:** event_bus.subscribe_sync; isinstance; self.bridge.remediation_event_received.emit; self.view_dashboard.dns_panel.apply_clicked.connect; self.view_dashboard.dns_panel.revert_clicked.connect; self.view_diagnosis.btn_run_audit.clicked.connect; self.view_dns.apply_dns_requested.connect; self.view_dns.benchmark_btn.clicked.connect; self.view_remediation.btn_flush_now.clicked.connect; self.view_remediation.btn_renew_ip.clicked.connect
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::MainWindow.resizeEvent   (app/ui/main_window.py:779-800)
- **Signature:** `def resizeEvent(self, event) -> None`
- **Purpose:** Method resizeEvent of MainWindow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow.resizeEvent:780; app/ui/views/dashboard_view.py:DashboardView.resizeEvent:435; app/ui/views/traffic_view.py:TrafficView.resizeEvent:344
- **Calls:** getattr; self.root_layout.addWidget; self.root_layout.removeWidget; self.root_layout.setDirection; self.sidebar.set_mode; self.width; super; super().resizeEvent
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::SidebarModeOption.__init__   (app/ui/main_window.py:65-87)
- **Signature:** `def __init__(self, index: int, label: str, parent) -> None`
- **Purpose:** Method __init__ of SidebarModeOption
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** QHBoxLayout; QLabel; layout.addStretch; layout.addWidget; layout.setContentsMargins; layout.setSpacing; self.dot.setFixedSize; self.lbl_text.setFont; self.setCursor; self.setFixedHeight
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::SidebarModeOption.mousePressEvent   (app/ui/main_window.py:123-126)
- **Signature:** `def mousePressEvent(self, event) -> None`
- **Purpose:** Method mousePressEvent of SidebarModeOption
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:SidebarModeOption.mousePressEvent:126; app/ui/views/remediation_view.py:ModeOptionCard.mousePressEvent:102; app/ui/widgets/flow_path.py:PathNodeButton.mousePressEvent:143; app/ui/widgets/toggle.py:ToggleSwitch.mousePressEvent:61
- **Calls:** event.button; self.clicked.emit; super; super().mousePressEvent
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::SidebarModeOption.set_selected   (app/ui/main_window.py:89-121)
- **Signature:** `def set_selected(self, selected: bool) -> None`
- **Purpose:** Method set_selected of SidebarModeOption
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:SidebarModeOption.__init__:87; app/ui/main_window.py:SidebarWidget._on_mode_clicked:264; app/ui/views/remediation_view.py:ModeOptionCard.__init__:65; app/ui/views/remediation_view.py:RemediationView._select_mode:322; app/ui/widgets/flow_path.py:FlowPathPanel._select_node:382
- **Calls:** self.dot.setStyleSheet; self.lbl_text.setStyleSheet; self.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::SidebarWidget.__init__   (app/ui/main_window.py:134-233)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of SidebarWidget
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** NavItem; QGridLayout; QHBoxLayout; QLabel; QVBoxLayout; QWidget; SidebarModeOption; brand_circle.setFixedSize; brand_circle.setStyleSheet; brand_col.addLayout
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::SidebarWidget._on_mode_clicked   (app/ui/main_window.py:262-272)
- **Signature:** `def _on_mode_clicked(self, idx: int) -> None`
- **Purpose:** Method _on_mode_clicked of SidebarWidget
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:SidebarWidget.__init__:233
- **Calls:** descs.get; enumerate; opt.set_selected; self.lbl_mode_desc.setText; self.mode_changed.emit
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.main_window::SidebarWidget.set_mode   (app/ui/main_window.py:235-260)
- **Signature:** `def set_mode(self, mode: str) -> None`
- **Purpose:** Method set_mode of SidebarWidget
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow.resizeEvent:791; app/ui/main_window.py:MainWindow.resizeEvent:800; app/ui/main_window.py:SidebarWidget.__init__:232
- **Calls:** enumerate; self.nav_grid.addWidget; self.nav_grid.removeWidget; self.setFixedWidth; self.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.tokens`

### app.ui.tokens::get_mono_font   (app/ui/tokens.py:123-129)
- **Signature:** `def get_mono_font(size: int, weight: int) -> QFont`
- **Purpose:** Create a monospace font (IBM Plex Mono -> Consolas).
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:SidebarWidget.__init__:160; app/ui/views/diagnosis_view.py:DiagnosisView._populate_evidence_table:236; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:71; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:83; app/ui/views/dns_view.py:DNSView.__init__:136; app/ui/views/dns_view.py:DNSView.__init__:156; app/ui/views/dns_view.py:DNSView._populate_default_table:222; app/ui/views/dns_view.py:DNSView._populate_default_table:232; app/ui/views/dns_view.py:DNSView.update_rankings:269; app/ui/views/dns_view.py:DNSView.update_rankings:280; app/ui/views/dns_view.py:RankedServerRow.__init__:42; app/ui/views/history_view.py:HistoryEventItem.__init__:68; app/ui/views/remediation_view.py:AuditEventRow.__init__:174; app/ui/views/traffic_view.py:ProcessTableCell.__init__:46; app/ui/views/traffic_view.py:TrafficView._populate_default_processes:323; app/ui/views/traffic_view.py:TrafficView._populate_default_processes:336; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:247; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:269; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:98; app/ui/widgets/day_strip.py:DayStripCanvas.paintEvent:87; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:348; app/ui/widgets/flow_path.py:PathNodeButton.__init__:60; app/ui/widgets/flow_path.py:PathNodeButton.__init__:85; app/ui/widgets/latency_chart.py:LatencyChart.__init__:354; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.paintEvent:140; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.paintEvent:174; app/ui/widgets/metric_cell.py:MetricCell.__init__:76; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:102; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:97; app/ui/widgets/session_card.py:SessionReportCard.__init__:193; app/ui/widgets/session_card.py:SessionReportCard.__init__:223; app/ui/widgets/session_card.py:SessionReportCard.__init__:274; app/ui/widgets/session_card.py:SessionReportCard.__init__:346; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:39
- **Calls:** QFont; QFont.Weight; font.setStyleHint; font.setWeight; init_fonts
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.tokens::get_sans_font   (app/ui/tokens.py:114-120)
- **Signature:** `def get_sans_font(size: int, weight: int) -> QFont`
- **Purpose:** Create a sans-serif UI font (IBM Plex Sans Arabic -> Segoe UI).
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:SidebarModeOption.__init__:83; app/ui/main_window.py:SidebarWidget.__init__:167; app/ui/main_window.py:SidebarWidget.__init__:211; app/ui/main_window.py:SidebarWidget.__init__:225; app/ui/views/dashboard_view.py:DashboardView.__init__:119; app/ui/views/dashboard_view.py:DashboardView.__init__:156; app/ui/views/dashboard_view.py:DashboardView.__init__:161; app/ui/views/dashboard_view.py:DashboardView.__init__:168; app/ui/views/dashboard_view.py:DashboardView.__init__:224; app/ui/views/dashboard_view.py:DashboardView._apply_layout_mode:272; app/ui/views/dashboard_view.py:DashboardView._apply_layout_mode:291; app/ui/views/dashboard_view.py:DashboardView._apply_layout_mode:308; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:138; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:144; app/ui/views/diagnosis_view.py:DiagnosisView._populate_evidence_table:238; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:76; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:92; app/ui/views/dns_view.py:DNSView.__init__:103; app/ui/views/dns_view.py:DNSView.__init__:133; app/ui/views/dns_view.py:DNSView.__init__:153; app/ui/views/dns_view.py:DNSView.__init__:99; app/ui/views/dns_view.py:DNSView._populate_default_table:227; app/ui/views/dns_view.py:DNSView._populate_default_table:242; app/ui/views/dns_view.py:DNSView.update_rankings:274; app/ui/views/history_view.py:HistoryEventItem.__init__:73; app/ui/views/history_view.py:HistoryEventItem.__init__:80; app/ui/views/history_view.py:HistoryEventItem.__init__:90; app/ui/views/history_view.py:HistoryEventItem.__init__:97; app/ui/views/history_view.py:HistoryView.__init__:137; app/ui/views/remediation_view.py:AuditEventRow.__init__:180; app/ui/views/remediation_view.py:AuditEventRow.__init__:185; app/ui/views/remediation_view.py:ModeOptionCard.__init__:54; app/ui/views/remediation_view.py:ModeOptionCard.__init__:60; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:132; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:136; app/ui/views/settings_view.py:SettingFormRow.__init__:55; app/ui/views/settings_view.py:SettingFormRow.__init__:59; app/ui/views/settings_view.py:SettingsView.__init__:101; app/ui/views/settings_view.py:SettingsView.__init__:136; app/ui/views/traffic_view.py:TrafficView.__init__:101; app/ui/views/traffic_view.py:TrafficView.__init__:145; app/ui/views/traffic_view.py:TrafficView.__init__:153; app/ui/views/traffic_view.py:TrafficView._populate_default_processes:318; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:216; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:224; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:228; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:244; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:266; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:288; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:85; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:140; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:144; app/ui/widgets/base_panel.py:Panel.__init__:59; app/ui/widgets/base_panel.py:Panel.__init__:66; app/ui/widgets/buttons.py:GhostButton.__init__:94; app/ui/widgets/buttons.py:PrimaryButton.__init__:20; app/ui/widgets/buttons.py:SecondaryButton.__init__:58; app/ui/widgets/chip.py:Chip.__init__:32; app/ui/widgets/day_strip.py:DayStrip.__init__:150; app/ui/widgets/day_strip.py:DayStrip.__init__:169; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:212; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:216; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:321; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:327; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:345; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:356; app/ui/widgets/flow_path.py:PathNodeButton.__init__:73; app/ui/widgets/flow_path.py:PathNodeButton.__init__:89; app/ui/widgets/latency_chart.py:LatencyChart.__init__:310; app/ui/widgets/latency_chart.py:LatencyChart.__init__:314; app/ui/widgets/latency_chart.py:LatencyChart.__init__:349; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.paintEvent:163; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.paintEvent:253; app/ui/widgets/metric_cell.py:MetricCell.__init__:107; app/ui/widgets/metric_cell.py:MetricCell.__init__:62; app/ui/widgets/metric_cell.py:MetricCell.__init__:81; app/ui/widgets/nav_item.py:NavItem.__init__:26; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:24; app/ui/widgets/segmented.py:SegmentedControl.__init__:41; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:130; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:64; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:85; app/ui/widgets/session_card.py:SessionReportCard.__init__:187; app/ui/widgets/session_card.py:SessionReportCard.__init__:216; app/ui/widgets/session_card.py:SessionReportCard.__init__:268; app/ui/widgets/session_card.py:SessionReportCard.__init__:279; app/ui/widgets/session_card.py:SessionReportCard.__init__:297; app/ui/widgets/session_card.py:SessionReportCard.__init__:309; app/ui/widgets/session_card.py:SessionReportCard.__init__:324; app/ui/widgets/session_card.py:SessionReportCard.__init__:351; app/ui/widgets/session_card.py:SessionReportCard.__init__:358; app/ui/widgets/session_card.py:SessionReportCard.__init__:364; app/ui/widgets/timeline.py:TimelinePanel.__init__:122; app/ui/widgets/timeline.py:TimelinePanel.__init__:126; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:43; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:47
- **Calls:** QFont; QFont.Weight; font.setStyleHint; font.setWeight; init_fonts
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.tokens::init_fonts   (app/ui/tokens.py:93-111)
- **Signature:** `def init_fonts() -> None`
- **Purpose:** Load bundled fonts into QFontDatabase.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow.__init__:288; app/ui/tokens.py:116; app/ui/tokens.py:125
- **Calls:** QFontDatabase.addApplicationFont; font_file.lower; font_file.lower().endswith; getattr; hasattr; logger.warning; os.listdir; os.path.abspath; os.path.dirname; os.path.isdir
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.views.dashboard_view`

### app.ui.views.dashboard_view::DashboardView.__init__   (app/ui/views/dashboard_view.py:84-248)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of DashboardView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** DNSRecommendationPanel; DayStrip; FlowPathPanel; LatencyChart; MetricsStrip; PrimaryButton; QGridLayout; QHBoxLayout; QLabel; QScrollArea
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dashboard_view::DashboardView._apply_layout_mode   (app/ui/views/dashboard_view.py:250-318)
- **Signature:** `def _apply_layout_mode(self, mode: str) -> None`
- **Purpose:** Method _apply_layout_mode of DashboardView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/dashboard_view.py:DashboardView.__init__:233; app/ui/views/dashboard_view.py:DashboardView.resizeEvent:440; app/ui/views/dashboard_view.py:DashboardView.resizeEvent:443; app/ui/views/dashboard_view.py:DashboardView.resizeEvent:446
- **Calls:** self.content_layout.setContentsMargins; self.hero_grid.addWidget; self.hero_grid.removeWidget; self.hero_grid.setColumnStretch; self.lbl_hero_title.setFont; self.metrics_strip.set_responsive_columns; self.row_a_grid.addWidget; self.row_a_grid.removeWidget; self.row_b_grid.addWidget; self.row_b_grid.removeWidget
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dashboard_view::DashboardView._on_scan_clicked   (app/ui/views/dashboard_view.py:332-337)
- **Signature:** `def _on_scan_clicked(self) -> None`
- **Purpose:** Method _on_scan_clicked of DashboardView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** QTimer.singleShot; self.btn_scan.setEnabled; self.btn_scan.setText; self.quick_scan_requested.emit
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dashboard_view::DashboardView._on_scan_completed   (app/ui/views/dashboard_view.py:339-341)
- **Signature:** `def _on_scan_completed(self) -> None`
- **Purpose:** Method _on_scan_completed of DashboardView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.btn_scan.setEnabled; self.btn_scan.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dashboard_view::DashboardView._on_second_tick   (app/ui/views/dashboard_view.py:320-330)
- **Signature:** `def _on_second_tick(self) -> None`
- **Purpose:** Method _on_second_tick of DashboardView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** datetime.now; now.strftime; now.weekday; self.lbl_status_line.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dashboard_view::DashboardView.log_autonomous_action   (app/ui/views/dashboard_view.py:424-432)
- **Signature:** `def log_autonomous_action(self, title: str, description: str, level: str) -> None`
- **Purpose:** Method log_autonomous_action of DashboardView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_apply_dns_requested:654; app/ui/main_window.py:MainWindow._on_dashboard_revert_dns:631; app/ui/main_window.py:MainWindow._on_deep_diagnosis_finished:716; app/ui/main_window.py:MainWindow._on_quick_flush_dns_done:745; app/ui/main_window.py:MainWindow._on_quick_renew_ip_done:760; app/ui/main_window.py:MainWindow._on_remediation_event_received:425; app/ui/main_window.py:MainWindow._on_remediation_event_received:431
- **Calls:** datetime.now; datetime.now().strftime; self.timeline_panel.set_event
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dashboard_view::DashboardView.resizeEvent   (app/ui/views/dashboard_view.py:434-446)
- **Signature:** `def resizeEvent(self, event) -> None`
- **Purpose:** Method resizeEvent of DashboardView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow.resizeEvent:780; app/ui/views/dashboard_view.py:DashboardView.resizeEvent:435; app/ui/views/traffic_view.py:TrafficView.resizeEvent:344
- **Calls:** self._apply_layout_mode; self.width; super; super().resizeEvent
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dashboard_view::DashboardView.update_dns_recommendation   (app/ui/views/dashboard_view.py:398-422)
- **Signature:** `def update_dns_recommendation(self, curr_name: str, curr_ms: float, best_name: str, best_ip: str, best_ms: float, is_optimal: bool, is_autonomous: bool) -> None`
- **Purpose:** Dynamically update recommendation card and flow path node from live benchmark.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_dashboard_apply_dns:601; app/ui/main_window.py:MainWindow._on_dns_benchmark_done:568
- **Calls:** self.dns_panel.update_dns_state; self.flow_path.update_dns_node
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dashboard_view::DashboardView.update_network_identity   (app/ui/views/dashboard_view.py:355-356)
- **Signature:** `def update_network_identity(self, info: Dict[str, Any]) -> None`
- **Purpose:** Method update_network_identity of DashboardView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_network_info_ready:463
- **Calls:** 
- **Real or fake?:** `STUB`
- **Error handling:** No explicit try/except

### app.ui.views.dashboard_view::DashboardView.update_shield   (app/ui/views/dashboard_view.py:343-353)
- **Signature:** `def update_shield(self, is_healthy: bool, title: str, desc: str) -> None`
- **Purpose:** Method update_shield of DashboardView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/dashboard_view.py:DashboardView.update_telemetry:396
- **Calls:** self.lbl_hero_caption.setStyleSheet; self.lbl_hero_caption.setText; self.lbl_hero_desc.setText; self.lbl_hero_title.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dashboard_view::DashboardView.update_telemetry   (app/ui/views/dashboard_view.py:358-396)
- **Signature:** `def update_telemetry(self, obs, last_diag: Optional[Diagnosis]) -> None`
- **Purpose:** Method update_telemetry of DashboardView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_ui_tick:474; app/ui/views/dashboard_view.py:DashboardView.update_telemetry:387
- **Calls:** int; len; max; obs.get_latest_measurement; obs.get_sliding_window; round; self.latency_chart.update_telemetry; self.metrics_strip.cell_jitter.update_metric; self.metrics_strip.cell_latency.update_metric; self.metrics_strip.cell_loss.update_metric
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dashboard_view::StatusIndicatorDot.__init__   (app/ui/views/dashboard_view.py:43-50)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of StatusIndicatorDot
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** QTimer; self._timer.start; self._timer.timeout.connect; self.setFixedSize; super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dashboard_view::StatusIndicatorDot._tick   (app/ui/views/dashboard_view.py:52-54)
- **Signature:** `def _tick(self) -> None`
- **Purpose:** Method _tick of StatusIndicatorDot
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.update
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dashboard_view::StatusIndicatorDot.paintEvent   (app/ui/views/dashboard_view.py:56-75)
- **Signature:** `def paintEvent(self, event) -> None`
- **Purpose:** Method paintEvent of StatusIndicatorDot
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/nav_item.py:NavItem.paintEvent:69
- **Calls:** QBrush; QColor; QPainter; QPen; int; max; min; painter.drawEllipse; painter.setBrush; painter.setPen
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.views.diagnosis_view`

### app.ui.views.diagnosis_view::DiagnosisView.__init__   (app/ui/views/diagnosis_view.py:110-220)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of DiagnosisView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** LayerChecklistRow; Panel; PrimaryButton; QHBoxLayout; QLabel; QScrollArea; QTableWidget; QVBoxLayout; QWidget; layers_panel.main_layout.addWidget
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.diagnosis_view::DiagnosisView._populate_evidence_table   (app/ui/views/diagnosis_view.py:222-241)
- **Signature:** `def _populate_evidence_table(self) -> None`
- **Purpose:** Method _populate_evidence_table of DiagnosisView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/diagnosis_view.py:DiagnosisView.__init__:215
- **Calls:** QColor; QTableWidgetItem; enumerate; item.setFont; item.setForeground; len; self.table.setItem; self.table.setRowCount; tokens.get_mono_font; tokens.get_sans_font
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.diagnosis_view::DiagnosisView.update_diagnosis   (app/ui/views/diagnosis_view.py:243-257)
- **Signature:** `def update_diagnosis(self, diag: Diagnosis) -> None`
- **Purpose:** Update live verdict from diagnosis engine.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_deep_diagnosis_finished:715; app/ui/main_window.py:MainWindow._on_ui_tick:477
- **Calls:** self.cause_lbl.setStyleSheet; self.cause_lbl.setText; self.explanation_lbl.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.diagnosis_view::DiagnosisView.update_dns_telemetry   (app/ui/views/diagnosis_view.py:259-282)
- **Signature:** `def update_dns_telemetry(self, dns_name: str, latency_ms: float, is_healthy: bool, is_optimal: bool) -> None`
- **Purpose:** Dynamically update Layer 04 (خوادم ترجمة العناوين) from live measurements.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_dashboard_apply_dns:610; app/ui/main_window.py:MainWindow._on_dns_benchmark_done:579
- **Calls:** QColor; eval_item.setText; item_metric.text; range; self.row_l4.update_status; self.table.item; self.table.rowCount; st_item.setForeground; st_item.setText; val_item.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.diagnosis_view::LayerChecklistRow.__init__   (app/ui/views/diagnosis_view.py:36-95)
- **Signature:** `def __init__(self, index_str: str, name: str, metric_str: str, desc: str, status: str, parent) -> None`
- **Purpose:** Method __init__ of LayerChecklistRow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** Chip; QHBoxLayout; QLabel; QVBoxLayout; layout.addLayout; layout.addWidget; layout.setContentsMargins; layout.setSpacing; lbl_idx.setFont; lbl_idx.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.diagnosis_view::LayerChecklistRow.update_status   (app/ui/views/diagnosis_view.py:97-104)
- **Signature:** `def update_status(self, metric_str: str, status: str, desc: str) -> None`
- **Purpose:** Method update_status of LayerChecklistRow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/diagnosis_view.py:DiagnosisView.update_dns_telemetry:267
- **Calls:** self.chip.set_variant; self.lbl_desc.setText; self.lbl_metric.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.views.dns_view`

### app.ui.views.dns_view::DNSView.__init__   (app/ui/views/dns_view.py:65-208)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of DNSView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** HorizontalProgressBar; Panel; PrimaryButton; QHBoxLayout; QLabel; QScrollArea; QTableWidget; QVBoxLayout; QWidget; bars_col.addLayout
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dns_view::DNSView._populate_default_table   (app/ui/views/dns_view.py:210-244)
- **Signature:** `def _populate_default_table(self) -> None`
- **Purpose:** Method _populate_default_table of DNSView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/dns_view.py:DNSView.__init__:205
- **Calls:** QTableWidgetItem; RankedServerRow; SecondaryButton; btn_apply.clicked.connect; btn_apply.setFixedHeight; btn_apply.setFont; enumerate; ip_item.setFont; len; n_item.setFont
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dns_view::DNSView.add_decision_entry   (app/ui/views/dns_view.py:348-349)
- **Signature:** `def add_decision_entry(self, time_str: str, action: str, server: str, latency: str, reason: str) -> None`
- **Purpose:** Method add_decision_entry of DNSView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `STUB`
- **Error handling:** No explicit try/except

### app.ui.views.dns_view::DNSView.set_active_dns_info   (app/ui/views/dns_view.py:342-346)
- **Signature:** `def set_active_dns_info(self, dns_list: List[str]) -> None`
- **Purpose:** Method set_active_dns_info of DNSView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_dashboard_apply_dns:616; app/ui/main_window.py:MainWindow._on_dns_benchmark_done:587; app/ui/main_window.py:MainWindow._on_network_info_ready:464
- **Calls:** ' · '.join; getattr; self.lbl_curr_name.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dns_view::DNSView.update_rankings   (app/ui/views/dns_view.py:246-340)
- **Signature:** `def update_rankings(self, scores: list, active_ms: Optional[float], active_name: str, is_optimal: bool) -> None`
- **Purpose:** Update ranked DNS table and comparison bars from real benchmark output.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_dashboard_apply_dns:618; app/ui/main_window.py:MainWindow._on_dns_benchmark_done:588
- **Calls:** QColor; QTableWidgetItem; RankedServerRow; SecondaryButton; _get_color; abs; any; best.name.replace; best.name.replace(' Primary', '').replace; btn_apply.clicked.connect
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.dns_view::RankedServerRow.__init__   (app/ui/views/dns_view.py:35-57)
- **Signature:** `def __init__(self, ms_val: float, is_top: bool, is_active: bool, max_ms: float, parent) -> None`
- **Purpose:** Method __init__ of RankedServerRow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** HorizontalProgressBar; QHBoxLayout; QLabel; bar.set_fraction; layout.addWidget; layout.setContentsMargins; layout.setSpacing; lbl_ms.setFixedWidth; lbl_ms.setFont; lbl_ms.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.views.history_view`

### app.ui.views.history_view::HistoryEventItem.__init__   (app/ui/views/history_view.py:31-100)
- **Signature:** `def __init__(self, time_str: str, title: str, cause: str, action: str, duration_str: str, is_resolved: bool, parent) -> None`
- **Purpose:** Method __init__ of HistoryEventItem
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** Chip; QHBoxLayout; QLabel; QVBoxLayout; layout.addLayout; layout.addWidget; layout.setContentsMargins; layout.setSpacing; lbl_action.setFont; lbl_action.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.history_view::HistoryView.__init__   (app/ui/views/history_view.py:106-201)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of HistoryView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** DayStrip; HistoryEventItem; Panel; QHBoxLayout; QLabel; QScrollArea; QVBoxLayout; QWidget; SecondaryButton; layout.addWidget
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.history_view::HistoryView.update_incidents   (app/ui/views/history_view.py:203-223)
- **Signature:** `def update_incidents(self, incidents: List[Any]) -> None`
- **Purpose:** Update incident list from real incident repository.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_ui_tick:481
- **Calls:** HistoryEventItem; datetime.now; datetime.now().strftime; getattr; item.widget; item.widget().deleteLater; self.events_list_layout.addWidget; self.events_list_layout.count; self.events_list_layout.takeAt
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.views.remediation_view`

### app.ui.views.remediation_view::AuditEventRow.__init__   (app/ui/views/remediation_view.py:150-190)
- **Signature:** `def __init__(self, time_str: str, cause_str: str, action_str: str, is_success: bool, parent) -> None`
- **Purpose:** Method __init__ of AuditEventRow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** Chip; QHBoxLayout; QLabel; layout.addWidget; layout.setContentsMargins; layout.setSpacing; lbl_action.setFont; lbl_action.setStyleSheet; lbl_cause.setFont; lbl_cause.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.remediation_view::ModeOptionCard.__init__   (app/ui/views/remediation_view.py:35-65)
- **Signature:** `def __init__(self, index: int, title: str, desc: str, is_selected: bool, parent) -> None`
- **Purpose:** Method __init__ of ModeOptionCard
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** QHBoxLayout; QLabel; QVBoxLayout; layout.addLayout; layout.addWidget; layout.setContentsMargins; layout.setSpacing; self.dot.setFixedSize; self.lbl_desc.setFont; self.lbl_desc.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.remediation_view::ModeOptionCard.mousePressEvent   (app/ui/views/remediation_view.py:99-102)
- **Signature:** `def mousePressEvent(self, event) -> None`
- **Purpose:** Method mousePressEvent of ModeOptionCard
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:SidebarModeOption.mousePressEvent:126; app/ui/views/remediation_view.py:ModeOptionCard.mousePressEvent:102; app/ui/widgets/flow_path.py:PathNodeButton.mousePressEvent:143; app/ui/widgets/toggle.py:ToggleSwitch.mousePressEvent:61
- **Calls:** event.button; self.clicked.emit; super; super().mousePressEvent
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.remediation_view::ModeOptionCard.set_selected   (app/ui/views/remediation_view.py:67-97)
- **Signature:** `def set_selected(self, selected: bool) -> None`
- **Purpose:** Method set_selected of ModeOptionCard
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:SidebarModeOption.__init__:87; app/ui/main_window.py:SidebarWidget._on_mode_clicked:264; app/ui/views/remediation_view.py:ModeOptionCard.__init__:65; app/ui/views/remediation_view.py:RemediationView._select_mode:322; app/ui/widgets/flow_path.py:FlowPathPanel._select_node:382
- **Calls:** self.dot.setStyleSheet; self.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.remediation_view::PolicyToggleRow.__init__   (app/ui/views/remediation_view.py:108-144)
- **Signature:** `def __init__(self, title: str, desc: str, checked: bool, parent) -> None`
- **Purpose:** Method __init__ of PolicyToggleRow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** QHBoxLayout; QLabel; QVBoxLayout; ToggleSwitch; layout.addLayout; layout.addWidget; layout.setContentsMargins; layout.setSpacing; lbl_desc.setFont; lbl_desc.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.remediation_view::RemediationView.__init__   (app/ui/views/remediation_view.py:198-318)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of RemediationView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** AuditEventRow; ModeOptionCard; Panel; PolicyToggleRow; QHBoxLayout; QScrollArea; QVBoxLayout; QWidget; SecondaryButton; card.clicked.connect
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.remediation_view::RemediationView._select_mode   (app/ui/views/remediation_view.py:320-323)
- **Signature:** `def _select_mode(self, idx: int) -> None`
- **Purpose:** Method _select_mode of RemediationView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** card.set_selected; enumerate; self.mode_changed.emit
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.remediation_view::RemediationView.update_audit_log   (app/ui/views/remediation_view.py:325-365)
- **Signature:** `def update_audit_log(self, audit_records: List[Any]) -> None`
- **Purpose:** Update audit ledger from real database records with authentic timestamps.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_ui_tick:485; scripts/verify_ui_render.py:89
- **Calls:** AuditEventRow; datetime.fromisoformat; dt.astimezone; dt.astimezone().strftime; getattr; isinstance; item.widget; item.widget().deleteLater; local_dt.strftime; self.events_layout.addWidget
- **Real or fake?:** `REAL`
- **Error handling:** catches Exception

## Module: `app.ui.views.settings_view`

### app.ui.views.settings_view::SettingFormRow.__init__   (app/ui/views/settings_view.py:31-66)
- **Signature:** `def __init__(self, title: str, desc: str, control_widget: QWidget, parent) -> None`
- **Purpose:** Method __init__ of SettingFormRow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** QHBoxLayout; QLabel; QVBoxLayout; layout.addLayout; layout.addWidget; layout.setContentsMargins; layout.setSpacing; lbl_desc.setFont; lbl_desc.setStyleSheet; lbl_title.setFont
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.settings_view::SettingsView.__init__   (app/ui/views/settings_view.py:72-171)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of SettingsView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** Panel; PrimaryButton; QComboBox; QHBoxLayout; QScrollArea; QVBoxLayout; QWidget; SettingFormRow; ToggleSwitch; actions_row.addStretch
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.views.traffic_view`

### app.ui.views.traffic_view::ProcessTableCell.__init__   (app/ui/views/traffic_view.py:39-54)
- **Signature:** `def __init__(self, speed_str: str, fraction: float, is_throttled: bool, parent) -> None`
- **Purpose:** Method __init__ of ProcessTableCell
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** HorizontalProgressBar; QHBoxLayout; QLabel; bar.set_fraction; layout.addWidget; layout.setContentsMargins; layout.setSpacing; lbl.setFixedWidth; lbl.setFont; lbl.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.traffic_view::TrafficView.__init__   (app/ui/views/traffic_view.py:63-232)
- **Signature:** `def __init__(self, session_tracker: Optional[AppSessionTracker], parent) -> None`
- **Purpose:** Method __init__ of TrafficView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** AppSessionTracker; Panel; PrimaryButton; QHBoxLayout; QLabel; QScrollArea; QTableWidget; QVBoxLayout; QWidget; SecondaryButton
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.traffic_view::TrafficView._close_session_by_name   (app/ui/views/traffic_view.py:257-262)
- **Signature:** `def _close_session_by_name(self, proc_name: str) -> None`
- **Purpose:** Callback from ActiveSessionCard to end a session and produce a report.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** proc_name.lower; self._refresh_sessions_ui; self.btn_sim_zoom.setText; self.session_tracker.close_session
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.traffic_view::TrafficView._on_sim_zoom_clicked   (app/ui/views/traffic_view.py:234-255)
- **Signature:** `def _on_sim_zoom_clicked(self) -> None`
- **Purpose:** Toggle a simulated Zoom meeting session to demonstrate real-time tracking & reports.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_ui.py:67; tests/unit/test_ui.py:72
- **Calls:** any; s.process_name.lower; self._refresh_sessions_ui; self.btn_sim_zoom.setText; self.session_tracker.close_session; self.session_tracker.get_active_sessions; self.session_tracker.start_or_update_session
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.traffic_view::TrafficView._populate_default_processes   (app/ui/views/traffic_view.py:306-337)
- **Signature:** `def _populate_default_processes(self) -> None`
- **Purpose:** Method _populate_default_processes of TrafficView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/traffic_view.py:TrafficView.__init__:229
- **Calls:** Chip; ProcessTableCell; QTableWidgetItem; enumerate; item_name.setFont; item_pid.setFont; item_sock.setFont; len; self.table.setCellWidget; self.table.setItem
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.traffic_view::TrafficView._populate_session_reports   (app/ui/views/traffic_view.py:292-304)
- **Signature:** `def _populate_session_reports(self) -> None`
- **Purpose:** Render all completed session reports.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/traffic_view.py:TrafficView.__init__:192; app/ui/views/traffic_view.py:TrafficView._refresh_sessions_ui:290
- **Calls:** SessionReportCard; item.widget; item.widget().deleteLater; self.report_cards.append; self.reports_list_layout.addWidget; self.reports_list_layout.count; self.reports_list_layout.takeAt; self.session_tracker.get_completed_sessions
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.traffic_view::TrafficView._refresh_sessions_ui   (app/ui/views/traffic_view.py:264-290)
- **Signature:** `def _refresh_sessions_ui(self) -> None`
- **Purpose:** Re-render active session cards and completed reports list.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/traffic_view.py:TrafficView._close_session_by_name:262; app/ui/views/traffic_view.py:TrafficView._on_sim_zoom_clicked:243; app/ui/views/traffic_view.py:TrafficView._on_sim_zoom_clicked:255; app/ui/views/traffic_view.py:TrafficView.update_profiles:341
- **Calls:** ActiveSessionCard; item.widget; item.widget().deleteLater; self._populate_session_reports; self.active_session_layout.addWidget; self.active_session_layout.count; self.active_session_layout.takeAt; self.meeting_dot.setStyleSheet; self.meeting_lbl.setStyleSheet; self.meeting_lbl.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.traffic_view::TrafficView.resizeEvent   (app/ui/views/traffic_view.py:343-357)
- **Signature:** `def resizeEvent(self, event) -> None`
- **Purpose:** Method resizeEvent of TrafficView
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow.resizeEvent:780; app/ui/views/dashboard_view.py:DashboardView.resizeEvent:435; app/ui/views/traffic_view.py:TrafficView.resizeEvent:344
- **Calls:** self.content_layout.setContentsMargins; self.table.setColumnHidden; self.width; super; super().resizeEvent
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.views.traffic_view::TrafficView.update_profiles   (app/ui/views/traffic_view.py:339-341)
- **Signature:** `def update_profiles(self, profiles: List[Any], conferencing_active: bool) -> None`
- **Purpose:** Update live processes from traffic controller.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_scan_traffic_done:697
- **Calls:** self._refresh_sessions_ui
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.bar_row`

### app.ui.widgets.bar_row::DNSRecommendationPanel.__init__   (app/ui/widgets/bar_row.py:190-298)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of DNSRecommendationPanel
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** HorizontalProgressBar; PrimaryButton; QHBoxLayout; QLabel; QVBoxLayout; QWidget; bars_col.addLayout; bars_col.addWidget; bars_col.setSpacing; curr_row.addLayout
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.bar_row::DNSRecommendationPanel._on_action_clicked   (app/ui/widgets/bar_row.py:377-387)
- **Signature:** `def _on_action_clicked(self) -> None`
- **Purpose:** Method _on_action_clicked of DNSRecommendationPanel
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.apply_clicked.emit; self.btn_action.setText; self.lbl_title.setText; self.revert_clicked.emit
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.bar_row::DNSRecommendationPanel.update_dns_state   (app/ui/widgets/bar_row.py:300-375)
- **Signature:** `def update_dns_state(self, curr_name: str, curr_ms: float, best_name: str, best_ip: str, best_ms: float, is_optimal: bool, is_autonomous: bool) -> None`
- **Purpose:** Dynamically update recommendation panel to show real live status and autonomous healing.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/dashboard_view.py:DashboardView.update_dns_recommendation:409
- **Calls:** int; max; min; round; self.bar_curr.set_fraction; self.bar_fast.set_fraction; self.btn_action.setEnabled; self.btn_action.setText; self.fast_row_container.setVisible; self.lbl_curr_ms.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.bar_row::HorizontalProgressBar.__init__   (app/ui/widgets/bar_row.py:28-33)
- **Signature:** `def __init__(self, height: int, fill_color: str, parent) -> None`
- **Purpose:** Method __init__ of HorizontalProgressBar
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** self.setFixedHeight; super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.bar_row::HorizontalProgressBar.paintEvent   (app/ui/widgets/bar_row.py:41-58)
- **Signature:** `def paintEvent(self, event) -> None`
- **Purpose:** Method paintEvent of HorizontalProgressBar
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/nav_item.py:NavItem.paintEvent:69
- **Calls:** QBrush; QColor; QPainter; QRectF; float; max; painter.drawRoundedRect; painter.setBrush; painter.setPen; painter.setRenderHint
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.bar_row::HorizontalProgressBar.set_fraction   (app/ui/widgets/bar_row.py:35-39)
- **Signature:** `def set_fraction(self, frac: float, fill_color: Optional[str]) -> None`
- **Purpose:** Method set_fraction of HorizontalProgressBar
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/dns_view.py:DNSView.__init__:144; app/ui/views/dns_view.py:DNSView.__init__:164; app/ui/views/dns_view.py:DNSView.update_rankings:326; app/ui/views/dns_view.py:DNSView.update_rankings:330; app/ui/views/dns_view.py:RankedServerRow.__init__:56; app/ui/views/traffic_view.py:ProcessTableCell.__init__:53; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:255; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:277; app/ui/widgets/bar_row.py:DNSRecommendationPanel.update_dns_state:340; app/ui/widgets/bar_row.py:DNSRecommendationPanel.update_dns_state:368; app/ui/widgets/bar_row.py:DNSRecommendationPanel.update_dns_state:374; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:106; app/ui/widgets/bar_row.py:ProcessBarRow.update_data:111
- **Calls:** max; min; self.update
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.bar_row::ProcessBarRow.__init__   (app/ui/widgets/bar_row.py:64-107)
- **Signature:** `def __init__(self, name: str, rate_str: str, fraction: float, tag_text: Optional[str], tag_variant: str, fill_color: str, parent) -> None`
- **Purpose:** Method __init__ of ProcessBarRow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** Chip; HorizontalProgressBar; QHBoxLayout; QLabel; QVBoxLayout; layout.addLayout; layout.addWidget; layout.setContentsMargins; layout.setSpacing; self.bar.set_fraction
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.bar_row::ProcessBarRow.update_data   (app/ui/widgets/bar_row.py:109-111)
- **Signature:** `def update_data(self, rate_str: str, fraction: float, fill_color: str) -> None`
- **Purpose:** Method update_data of ProcessBarRow
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/bar_row.py:TrafficConsumersPanel.update_processes:181; tests/unit/test_ui.py:39
- **Calls:** self.bar.set_fraction; self.lbl_rate.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.bar_row::TrafficConsumersPanel.__init__   (app/ui/widgets/bar_row.py:117-166)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of TrafficConsumersPanel
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** ProcessBarRow; QLabel; QVBoxLayout; layout.addLayout; layout.setContentsMargins; layout.setSpacing; self.lbl_sub.setFont; self.lbl_sub.setStyleSheet; self.lbl_title.setFont; self.lbl_title.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.bar_row::TrafficConsumersPanel.update_processes   (app/ui/widgets/bar_row.py:168-181)
- **Signature:** `def update_processes(self, profiles) -> None`
- **Purpose:** Update top 5 consumers from live process network profiles.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_scan_traffic_done:698
- **Calls:** enumerate; getattr; len; max; min; p.name.replace; p.name.replace('.exe', '').title; rows[i].lbl_name.setText; rows[i].update_data; sorted
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.base_panel`

### app.ui.widgets.base_panel::Panel.__init__   (app/ui/widgets/base_panel.py:24-80)
- **Signature:** `def __init__(self, title: str, subtitle: str, header_widget: Optional[QWidget], parent: Optional[QWidget], padding: int) -> None`
- **Purpose:** Method __init__ of Panel
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** QHBoxLayout; QLabel; QVBoxLayout; self.header_layout.addLayout; self.header_layout.addStretch; self.header_layout.addWidget; self.header_layout.setContentsMargins; self.header_layout.setSpacing; self.lbl_subtitle.setFont; self.lbl_subtitle.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.base_panel::Panel.set_header_widget   (app/ui/widgets/base_panel.py:82-84)
- **Signature:** `def set_header_widget(self, widget: QWidget) -> None`
- **Purpose:** Dynamically add or replace a header widget.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.header_layout.addWidget
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.base_panel::Panel.set_titles   (app/ui/widgets/base_panel.py:86-89)
- **Signature:** `def set_titles(self, title: str, subtitle: str) -> None`
- **Purpose:** Method set_titles of Panel
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.lbl_subtitle.setText; self.lbl_title.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.buttons`

### app.ui.widgets.buttons::GhostButton.__init__   (app/ui/widgets/buttons.py:90-115)
- **Signature:** `def __init__(self, text: str, parent) -> None`
- **Purpose:** Method __init__ of GhostButton
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** self.setCursor; self.setFixedHeight; self.setFont; self.setStyleSheet; super; super().__init__; tokens.get_sans_font
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.buttons::PrimaryButton.__init__   (app/ui/widgets/buttons.py:16-48)
- **Signature:** `def __init__(self, text: str, parent) -> None`
- **Purpose:** Method __init__ of PrimaryButton
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** self.setCursor; self.setFixedHeight; self.setFont; self.setStyleSheet; super; super().__init__; tokens.get_sans_font
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.buttons::SecondaryButton.__init__   (app/ui/widgets/buttons.py:54-84)
- **Signature:** `def __init__(self, text: str, parent) -> None`
- **Purpose:** Method __init__ of SecondaryButton
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** self.setCursor; self.setFixedHeight; self.setFont; self.setStyleSheet; super; super().__init__; tokens.get_sans_font
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.chip`

### app.ui.widgets.chip::Chip.__init__   (app/ui/widgets/chip.py:19-33)
- **Signature:** `def __init__(self, text: str, variant: str, parent, radius: int, font_size: int) -> None`
- **Purpose:** Method __init__ of Chip
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** self._apply_style; self.setAlignment; self.setFont; super; super().__init__; tokens.get_sans_font
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.chip::Chip._apply_style   (app/ui/widgets/chip.py:41-74)
- **Signature:** `def _apply_style(self) -> None`
- **Purpose:** Method _apply_style of Chip
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/chip.py:Chip.__init__:33; app/ui/widgets/chip.py:Chip.set_variant:39
- **Calls:** self.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.chip::Chip.set_variant   (app/ui/widgets/chip.py:35-39)
- **Signature:** `def set_variant(self, variant: str, text: str) -> None`
- **Purpose:** Method set_variant of Chip
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/diagnosis_view.py:LayerChecklistRow.update_status:102; app/ui/views/diagnosis_view.py:LayerChecklistRow.update_status:104; app/ui/widgets/timeline.py:TimelinePanel.set_event:196; app/ui/widgets/timeline.py:TimelinePanel.set_event:199
- **Calls:** self._apply_style; self.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.day_strip`

### app.ui.widgets.day_strip::DayStrip.__init__   (app/ui/widgets/day_strip.py:136-183)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of DayStrip
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** DayStripCanvas; QHBoxLayout; QLabel; QVBoxLayout; QWidget; dot.setFixedSize; dot.setStyleSheet; h_layout.addWidget; h_layout.setContentsMargins; h_layout.setSpacing
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.day_strip::DayStrip.set_data   (app/ui/widgets/day_strip.py:185-186)
- **Signature:** `def set_data(self, states: List[str]) -> None`
- **Purpose:** Method set_data of DayStrip
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/day_strip.py:DayStrip.set_data:186; app/ui/widgets/latency_chart.py:LatencyChart._on_range_changed:372; app/ui/widgets/latency_chart.py:LatencyChart.update_telemetry:376; app/ui/widgets/metric_cell.py:MetricCell.update_metric:130; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.update_data:36
- **Calls:** self.canvas.set_data
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.day_strip::DayStripCanvas.__init__   (app/ui/widgets/day_strip.py:23-28)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of DayStripCanvas
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** self._init_default_day; self.setFixedHeight; self.setMouseTracking; super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.day_strip::DayStripCanvas._get_slot_rect   (app/ui/widgets/day_strip.py:48-64)
- **Signature:** `def _get_slot_rect(self, index: int, total_width: float) -> QRectF`
- **Purpose:** Method _get_slot_rect of DayStripCanvas
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/day_strip.py:DayStripCanvas.paintEvent:74
- **Calls:** QRectF; max; min
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.day_strip::DayStripCanvas._init_default_day   (app/ui/widgets/day_strip.py:30-39)
- **Signature:** `def _init_default_day(self) -> None`
- **Purpose:** Method _init_default_day of DayStripCanvas
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/day_strip.py:DayStripCanvas.__init__:28
- **Calls:** datetime.now; min; range
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.day_strip::DayStripCanvas.mouseMoveEvent   (app/ui/widgets/day_strip.py:108-130)
- **Signature:** `def mouseMoveEvent(self, event) -> None`
- **Purpose:** Method mouseMoveEvent of DayStripCanvas
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/day_strip.py:DayStripCanvas.mouseMoveEvent:130
- **Calls:** QToolTip.showText; event.globalPosition; event.globalPosition().toPoint; event.position; event.position().x; float; int; max; min; self.width
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.day_strip::DayStripCanvas.paintEvent   (app/ui/widgets/day_strip.py:66-106)
- **Signature:** `def paintEvent(self, event) -> None`
- **Purpose:** Method paintEvent of DayStripCanvas
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/nav_item.py:NavItem.paintEvent:69
- **Calls:** QBrush; QColor; QPainter; QRectF; enumerate; float; max; painter.drawRoundedRect; painter.drawText; painter.setBrush
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.day_strip::DayStripCanvas.set_data   (app/ui/widgets/day_strip.py:41-46)
- **Signature:** `def set_data(self, states: List[str]) -> None`
- **Purpose:** Method set_data of DayStripCanvas
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/day_strip.py:DayStrip.set_data:186; app/ui/widgets/latency_chart.py:LatencyChart._on_range_changed:372; app/ui/widgets/latency_chart.py:LatencyChart.update_telemetry:376; app/ui/widgets/metric_cell.py:MetricCell.update_metric:130; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.update_data:36
- **Calls:** len; list; self.bar_states.append; self.update
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.flow_path`

### app.ui.widgets.flow_path::FlowPathPanel.__init__   (app/ui/widgets/flow_path.py:193-373)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of FlowPathPanel
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** PathConnector; PathNodeButton; QFrame; QHBoxLayout; QLabel; QScrollArea; QTimer; QVBoxLayout; QWidget; btn.clicked.connect
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.flow_path::FlowPathPanel._on_flow_tick   (app/ui/widgets/flow_path.py:375-378)
- **Signature:** `def _on_flow_tick(self) -> None`
- **Purpose:** Method _on_flow_tick of FlowPathPanel
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** conn.set_phase
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.flow_path::FlowPathPanel._select_node   (app/ui/widgets/flow_path.py:380-397)
- **Signature:** `def _select_node(self, index: int) -> None`
- **Purpose:** Method _select_node of FlowPathPanel
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/flow_path.py:FlowPathPanel.__init__:366; app/ui/widgets/flow_path.py:FlowPathPanel.update_dns_node:426; app/ui/widgets/flow_path.py:FlowPathPanel.update_node_latency:406
- **Calls:** enumerate; int; n.set_selected; self.lbl_detail_desc.setText; self.lbl_detail_name.setText; self.lbl_now.setStyleSheet; self.lbl_now.setText; self.lbl_st.setStyleSheet; self.lbl_st.setText; self.lbl_typ.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.flow_path::FlowPathPanel.update_dns_node   (app/ui/widgets/flow_path.py:408-426)
- **Signature:** `def update_dns_node(self, latency_ms: float, is_optimal: bool, dns_name: str) -> None`
- **Purpose:** Dynamically update Node 04 (خادم DNS) based on live benchmark and resolution.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/dashboard_view.py:DashboardView.update_dns_recommendation:418
- **Calls:** int; len; round; self._select_node; self.connectors[2].update; self.nodes[3].update_state
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.flow_path::FlowPathPanel.update_node_latency   (app/ui/widgets/flow_path.py:399-406)
- **Signature:** `def update_node_latency(self, index: int, latency_ms: float, status: str) -> None`
- **Purpose:** Method update_node_latency of FlowPathPanel
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** len; self._select_node; self.nodes[index].update_state
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.flow_path::PathConnector.__init__   (app/ui/widgets/flow_path.py:149-154)
- **Signature:** `def __init__(self, dest_status: str, parent) -> None`
- **Purpose:** Method __init__ of PathConnector
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** self.setFixedHeight; self.setMinimumWidth; super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.flow_path::PathConnector.paintEvent   (app/ui/widgets/flow_path.py:164-187)
- **Signature:** `def paintEvent(self, event) -> None`
- **Purpose:** Method paintEvent of PathConnector
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/nav_item.py:NavItem.paintEvent:69
- **Calls:** QBrush; QColor; QPainter; QPen; QPointF; float; painter.drawEllipse; painter.drawLine; painter.setBrush; painter.setPen
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.flow_path::PathConnector.set_dest_status   (app/ui/widgets/flow_path.py:160-162)
- **Signature:** `def set_dest_status(self, status: str) -> None`
- **Purpose:** Method set_dest_status of PathConnector
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.update
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.flow_path::PathConnector.set_phase   (app/ui/widgets/flow_path.py:156-158)
- **Signature:** `def set_phase(self, phase: float) -> None`
- **Purpose:** Method set_phase of PathConnector
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/flow_path.py:FlowPathPanel._on_flow_tick:378
- **Calls:** self.update
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.flow_path::PathNodeButton.__init__   (app/ui/widgets/flow_path.py:30-97)
- **Signature:** `def __init__(self, index: int, index_str: str, name: str, latency_ms: float, status: str, parent) -> None`
- **Purpose:** Method __init__ of PathNodeButton
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** QHBoxLayout; QLabel; QVBoxLayout; QWidget; int; lat_container.setLayoutDirection; lat_row.addStretch; lat_row.addWidget; lat_row.setContentsMargins; lat_row.setSpacing
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.flow_path::PathNodeButton.mousePressEvent   (app/ui/widgets/flow_path.py:140-143)
- **Signature:** `def mousePressEvent(self, event) -> None`
- **Purpose:** Method mousePressEvent of PathNodeButton
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:SidebarModeOption.mousePressEvent:126; app/ui/views/remediation_view.py:ModeOptionCard.mousePressEvent:102; app/ui/widgets/flow_path.py:PathNodeButton.mousePressEvent:143; app/ui/widgets/toggle.py:ToggleSwitch.mousePressEvent:61
- **Calls:** event.button; self.clicked.emit; super; super().mousePressEvent
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.flow_path::PathNodeButton.set_selected   (app/ui/widgets/flow_path.py:99-101)
- **Signature:** `def set_selected(self, selected: bool) -> None`
- **Purpose:** Method set_selected of PathNodeButton
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:SidebarModeOption.__init__:87; app/ui/main_window.py:SidebarWidget._on_mode_clicked:264; app/ui/views/remediation_view.py:ModeOptionCard.__init__:65; app/ui/views/remediation_view.py:RemediationView._select_mode:322; app/ui/widgets/flow_path.py:FlowPathPanel._select_node:382
- **Calls:** self.update_state
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.flow_path::PathNodeButton.update_state   (app/ui/widgets/flow_path.py:103-138)
- **Signature:** `def update_state(self, latency_ms: float, status: str, selected: bool) -> None`
- **Purpose:** Method update_state of PathNodeButton
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/flow_path.py:FlowPathPanel.update_dns_node:421; app/ui/widgets/flow_path.py:FlowPathPanel.update_node_latency:404; app/ui/widgets/flow_path.py:PathNodeButton.__init__:97; app/ui/widgets/flow_path.py:PathNodeButton.set_selected:101
- **Calls:** int; self.dot_widget.setStyleSheet; self.lbl_val.setText; self.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.latency_chart`

### app.ui.widgets.latency_chart::LatencyChart.__init__   (app/ui/widgets/latency_chart.py:289-369)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of LatencyChart
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** LatencyPlotCanvas; QFrame; QHBoxLayout; QLabel; QVBoxLayout; QWidget; SegmentedControl; col_l.addWidget; col_l.setAlignment; col_l.setContentsMargins
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.latency_chart::LatencyChart._on_range_changed   (app/ui/widgets/latency_chart.py:371-372)
- **Signature:** `def _on_range_changed(self, idx: int, label: str) -> None`
- **Purpose:** Method _on_range_changed of LatencyChart
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.canvas.set_data
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.latency_chart::LatencyChart.update_telemetry   (app/ui/widgets/latency_chart.py:374-379)
- **Signature:** `def update_telemetry(self, samples: List[float], avg_ms: float, max_ms: float, duration_str: str) -> None`
- **Purpose:** Method update_telemetry of LatencyChart
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow._on_ui_tick:474; app/ui/views/dashboard_view.py:DashboardView.update_telemetry:387
- **Calls:** len; self.canvas.set_data; self.lbl_avg.setText; self.lbl_dur.setText; self.lbl_max.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.latency_chart::LatencyPlotCanvas.__init__   (app/ui/widgets/latency_chart.py:42-57)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of LatencyPlotCanvas
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** QTimer; self._init_default_data; self._pulse_timer.start; self._pulse_timer.timeout.connect; self.setFixedHeight; super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.latency_chart::LatencyPlotCanvas._init_default_data   (app/ui/widgets/latency_chart.py:72-102)
- **Signature:** `def _init_default_data(self) -> None`
- **Purpose:** Method _init_default_data of LatencyPlotCanvas
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:52
- **Calls:** data.append; datetime.now; dt.strftime; math.cos; math.sin; range; timedelta; times.append
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.latency_chart::LatencyPlotCanvas._on_pulse_tick   (app/ui/widgets/latency_chart.py:68-70)
- **Signature:** `def _on_pulse_tick(self) -> None`
- **Purpose:** Method _on_pulse_tick of LatencyPlotCanvas
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.update
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.latency_chart::LatencyPlotCanvas.get_reveal_progress   (app/ui/widgets/latency_chart.py:59-60)
- **Signature:** `def get_reveal_progress(self) -> float`
- **Purpose:** Method get_reveal_progress of LatencyPlotCanvas
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.latency_chart::LatencyPlotCanvas.paintEvent   (app/ui/widgets/latency_chart.py:117-283)
- **Signature:** `def paintEvent(self, event) -> None`
- **Purpose:** Method paintEvent of LatencyPlotCanvas
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/nav_item.py:NavItem.paintEvent:69
- **Calls:** QBrush; QColor; QPainter; QPainterPath; QPen; QPointF; QRectF; bad_path.lineTo; bad_path.moveTo; bad_pen.setCapStyle
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.latency_chart::LatencyPlotCanvas.set_data   (app/ui/widgets/latency_chart.py:104-115)
- **Signature:** `def set_data(self, samples: List[float], incident_idx: Optional[int]) -> None`
- **Purpose:** Method set_data of LatencyPlotCanvas
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/day_strip.py:DayStrip.set_data:186; app/ui/widgets/latency_chart.py:LatencyChart._on_range_changed:372; app/ui/widgets/latency_chart.py:LatencyChart.update_telemetry:376; app/ui/widgets/metric_cell.py:MetricCell.update_metric:130; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.update_data:36
- **Calls:** len; list; max; self.samples.index; self.update
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.latency_chart::LatencyPlotCanvas.set_reveal_progress   (app/ui/widgets/latency_chart.py:62-64)
- **Signature:** `def set_reveal_progress(self, val: float) -> None`
- **Purpose:** Method set_reveal_progress of LatencyPlotCanvas
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.update
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.metric_cell`

### app.ui.widgets.metric_cell::MetricCell.__init__   (app/ui/widgets/metric_cell.py:29-113)
- **Signature:** `def __init__(self, title: str, initial_val: str, unit: str, footer_text: str, status_color: str, initial_samples: Optional[List[float]], parent) -> None`
- **Purpose:** Method __init__ of MetricCell
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** QHBoxLayout; QLabel; QVBoxLayout; QWidget; Sparkline; footer_row.addStretch; footer_row.addWidget; footer_row.setContentsMargins; footer_row.setSpacing; layout.addLayout
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.metric_cell::MetricCell.update_metric   (app/ui/widgets/metric_cell.py:115-133)
- **Signature:** `def update_metric(self, val_str: str, footer_text: str, is_warning: bool, samples: Optional[List[float]]) -> None`
- **Purpose:** Method update_metric of MetricCell
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/dashboard_view.py:DashboardView.update_telemetry:368; app/ui/views/dashboard_view.py:DashboardView.update_telemetry:373; app/ui/views/dashboard_view.py:DashboardView.update_telemetry:378; tests/unit/test_ui.py:33
- **Calls:** self.dot.setStyleSheet; self.footer_lbl.setText; self.sparkline.set_data; self.sparkline.update; self.val_lbl.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.metric_cell::MetricsStrip.__init__   (app/ui/widgets/metric_cell.py:139-197)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of MetricsStrip
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** MetricCell; QGridLayout; self._set_4x1_layout; self.grid_layout.setContentsMargins; self.grid_layout.setSpacing; self.setObjectName; self.setStyleSheet; super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.metric_cell::MetricsStrip._set_4x1_layout   (app/ui/widgets/metric_cell.py:199-201)
- **Signature:** `def _set_4x1_layout(self) -> None`
- **Purpose:** Method _set_4x1_layout of MetricsStrip
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/metric_cell.py:MetricsStrip.__init__:197
- **Calls:** enumerate; self.grid_layout.addWidget
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.metric_cell::MetricsStrip.set_responsive_columns   (app/ui/widgets/metric_cell.py:203-217)
- **Signature:** `def set_responsive_columns(self, cols: int) -> None`
- **Purpose:** Method set_responsive_columns of MetricsStrip
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/dashboard_view.py:DashboardView._apply_layout_mode:273; app/ui/views/dashboard_view.py:DashboardView._apply_layout_mode:292; app/ui/views/dashboard_view.py:DashboardView._apply_layout_mode:309
- **Calls:** enumerate; self.grid_layout.addWidget; self.grid_layout.removeWidget
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.nav_item`

### app.ui.widgets.nav_item::NavItem.__init__   (app/ui/widgets/nav_item.py:19-27)
- **Signature:** `def __init__(self, icon_name: str, label: str, index: int, parent) -> None`
- **Purpose:** Method __init__ of NavItem
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** self._update_style; self.setCheckable; self.setCursor; self.setFixedHeight; self.setFont; super; super().__init__; tokens.get_sans_font
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.nav_item::NavItem._update_style   (app/ui/widgets/nav_item.py:34-66)
- **Signature:** `def _update_style(self) -> None`
- **Purpose:** Method _update_style of NavItem
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/nav_item.py:NavItem.__init__:27; app/ui/widgets/nav_item.py:NavItem.setChecked:31
- **Calls:** self.isChecked; self.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.nav_item::NavItem.paintEvent   (app/ui/widgets/nav_item.py:68-157)
- **Signature:** `def paintEvent(self, event) -> None`
- **Purpose:** Method paintEvent of NavItem
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/nav_item.py:NavItem.paintEvent:69
- **Calls:** QColor; QPainter; QPainterPath; QPen; QPointF; float; painter.drawEllipse; painter.drawLine; painter.drawPath; painter.setBrush
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.nav_item::NavItem.setChecked   (app/ui/widgets/nav_item.py:29-32)
- **Signature:** `def setChecked(self, checked: bool) -> None`
- **Purpose:** Method setChecked of NavItem
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow.__init__:346; app/ui/main_window.py:MainWindow._switch_view:377; app/ui/widgets/nav_item.py:NavItem.setChecked:30; app/ui/widgets/toggle.py:ToggleSwitch.mousePressEvent:58
- **Calls:** self._update_style; self.update; super; super().setChecked
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.realtime_chart`

### app.ui.widgets.realtime_chart::RealTimePlotWidget.__init__   (app/ui/widgets/realtime_chart.py:17-30)
- **Signature:** `def __init__(self, title: str, y_label: str, parent) -> None`
- **Purpose:** Method __init__ of RealTimePlotWidget
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** QLabel; QVBoxLayout; Sparkline; layout.addWidget; layout.setContentsMargins; layout.setSpacing; self.sparkline.setFixedHeight; self.title_lbl.setFont; self.title_lbl.setStyleSheet; super
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.realtime_chart::RealTimePlotWidget.update_data   (app/ui/widgets/realtime_chart.py:32-36)
- **Signature:** `def update_data(self, y_values: List[float]) -> None`
- **Purpose:** Update curve with latest telemetry samples.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/bar_row.py:TrafficConsumersPanel.update_processes:181; tests/unit/test_ui.py:39
- **Calls:** self.sparkline.set_data
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.segmented`

### app.ui.widgets.segmented::SegmentedControl.__init__   (app/ui/widgets/segmented.py:20-48)
- **Signature:** `def __init__(self, options: List[str], initial_index: int, parent) -> None`
- **Purpose:** Method __init__ of SegmentedControl
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** QHBoxLayout; QPushButton; btn.clicked.connect; btn.setCursor; btn.setFixedHeight; btn.setFont; enumerate; layout.addWidget; layout.setContentsMargins; layout.setSpacing
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.segmented::SegmentedControl._on_button_clicked   (app/ui/widgets/segmented.py:50-54)
- **Signature:** `def _on_button_clicked(self, idx: int) -> None`
- **Purpose:** Method _on_button_clicked of SegmentedControl
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/segmented.py:SegmentedControl.__init__:44
- **Calls:** self._update_styles; self.current_changed.emit
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.segmented::SegmentedControl._update_styles   (app/ui/widgets/segmented.py:61-88)
- **Signature:** `def _update_styles(self) -> None`
- **Purpose:** Method _update_styles of SegmentedControl
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/segmented.py:SegmentedControl.__init__:48; app/ui/widgets/segmented.py:SegmentedControl._on_button_clicked:53; app/ui/widgets/segmented.py:SegmentedControl.set_selected_index:59
- **Calls:** btn.setStyleSheet; enumerate
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.segmented::SegmentedControl.set_selected_index   (app/ui/widgets/segmented.py:56-59)
- **Signature:** `def set_selected_index(self, idx: int) -> None`
- **Purpose:** Method set_selected_index of SegmentedControl
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** len; self._update_styles
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.session_card`

### app.ui.widgets.session_card::ActiveSessionCard.__init__   (app/ui/widgets/session_card.py:31-142)
- **Signature:** `def __init__(self, session: AppSessionRecord, on_close_callback, parent) -> None`
- **Purpose:** Method __init__ of ActiveSessionCard
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** Chip; QFrame; QGridLayout; QHBoxLayout; QLabel; QTimer; QVBoxLayout; SecondaryButton; b_lbl.setFont; b_lbl.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.session_card::ActiveSessionCard._format_duration   (app/ui/widgets/session_card.py:144-147)
- **Signature:** `def _format_duration(self, seconds: int) -> str`
- **Purpose:** Method _format_duration of ActiveSessionCard
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/session_card.py:ActiveSessionCard.__init__:96; app/ui/widgets/session_card.py:ActiveSessionCard._on_tick:151
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.session_card::ActiveSessionCard._on_tick   (app/ui/widgets/session_card.py:149-151)
- **Signature:** `def _on_tick(self) -> None`
- **Purpose:** Method _on_tick of ActiveSessionCard
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self._format_duration; self.lbl_duration.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.session_card::SessionReportCard.__init__   (app/ui/widgets/session_card.py:157-374)
- **Signature:** `def __init__(self, session: AppSessionRecord, parent) -> None`
- **Purpose:** Method __init__ of SessionReportCard
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** Chip; QFrame; QGridLayout; QHBoxLayout; QLabel; QVBoxLayout; QWidget; SecondaryButton; act_card.setStyleSheet; act_layout.addLayout
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.session_card::SessionReportCard._toggle_expand   (app/ui/widgets/session_card.py:376-379)
- **Signature:** `def _toggle_expand(self) -> None`
- **Purpose:** Method _toggle_expand of SessionReportCard
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** tests/unit/test_ui.py:80; tests/unit/test_ui.py:83
- **Calls:** self.btn_toggle.setText; self.detail_container.setVisible
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.sparkline`

### app.ui.widgets.sparkline::Sparkline.__init__   (app/ui/widgets/sparkline.py:18-28)
- **Signature:** `def __init__(self, samples: List[float], color: str, parent) -> None`
- **Purpose:** Method __init__ of Sparkline
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** self.setFixedHeight; super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.sparkline::Sparkline.get_reveal_progress   (app/ui/widgets/sparkline.py:30-31)
- **Signature:** `def get_reveal_progress(self) -> float`
- **Purpose:** Method get_reveal_progress of Sparkline
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.sparkline::Sparkline.paintEvent   (app/ui/widgets/sparkline.py:46-104)
- **Signature:** `def paintEvent(self, event) -> None`
- **Purpose:** Method paintEvent of Sparkline
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/nav_item.py:NavItem.paintEvent:69
- **Calls:** QColor; QPainter; QPainterPath; QPen; enumerate; float; len; max; min; painter.drawPath
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.sparkline::Sparkline.set_data   (app/ui/widgets/sparkline.py:39-44)
- **Signature:** `def set_data(self, samples: List[float], color: str) -> None`
- **Purpose:** Method set_data of Sparkline
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/day_strip.py:DayStrip.set_data:186; app/ui/widgets/latency_chart.py:LatencyChart._on_range_changed:372; app/ui/widgets/latency_chart.py:LatencyChart.update_telemetry:376; app/ui/widgets/metric_cell.py:MetricCell.update_metric:130; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.update_data:36
- **Calls:** list; self.update
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.sparkline::Sparkline.set_reveal_progress   (app/ui/widgets/sparkline.py:33-35)
- **Signature:** `def set_reveal_progress(self, val: float) -> None`
- **Purpose:** Method set_reveal_progress of Sparkline
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.update
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.status_card`

### app.ui.widgets.status_card::StatusCard.__init__   (app/ui/widgets/status_card.py:16-41)
- **Signature:** `def __init__(self, title: str, initial_value: str, unit: str, desc: str, icon: str, parent) -> None`
- **Purpose:** Method __init__ of StatusCard
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** self.setObjectName; self.setStyleSheet; super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.timeline`

### app.ui.widgets.timeline::TimelineCanvas.__init__   (app/ui/widgets/timeline.py:59-63)
- **Signature:** `def __init__(self, colors: List[str], step_widgets: List[QWidget], parent) -> None`
- **Purpose:** Method __init__ of TimelineCanvas
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** self.setFixedWidth; super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.timeline::TimelineCanvas.paintEvent   (app/ui/widgets/timeline.py:65-87)
- **Signature:** `def paintEvent(self, event) -> None`
- **Purpose:** Method paintEvent of TimelineCanvas
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/nav_item.py:NavItem.paintEvent:69
- **Calls:** QBrush; QColor; QPainter; QPen; QPointF; centers.append; enumerate; len; painter.drawEllipse; painter.drawLine
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.timeline::TimelinePanel.__init__   (app/ui/widgets/timeline.py:96-185)
- **Signature:** `def __init__(self, parent) -> None`
- **Purpose:** Method __init__ of TimelinePanel
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** Chip; GhostButton; QHBoxLayout; QLabel; QVBoxLayout; QWidget; SecondaryButton; TimelineCanvas; TimelineStepWidget; footer_row.addStretch
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.timeline::TimelinePanel.set_event   (app/ui/widgets/timeline.py:187-208)
- **Signature:** `def set_event(self, time_str: str, steps: List[Tuple[str, str, str]], is_resolved: bool) -> None`
- **Purpose:** Update timeline with real audit/remediation event.
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/views/dashboard_view.py:DashboardView.log_autonomous_action:432
- **Calls:** enumerate; len; self.btn_rollback.setVisible; self.lbl_sub.setText; self.rail_canvas.update; self.status_chip.set_variant; self.step_widgets[i].lbl_desc.setText; self.step_widgets[i].lbl_time.setText; self.step_widgets[i].lbl_title.setText
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.timeline::TimelineStepWidget.__init__   (app/ui/widgets/timeline.py:32-53)
- **Signature:** `def __init__(self, time_str: str, title: str, desc: str, dot_color: str, parent) -> None`
- **Purpose:** Method __init__ of TimelineStepWidget
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** QLabel; QVBoxLayout; layout.addWidget; layout.setContentsMargins; layout.setSpacing; self.lbl_desc.setFont; self.lbl_desc.setStyleSheet; self.lbl_desc.setWordWrap; self.lbl_time.setFont; self.lbl_time.setStyleSheet
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

## Module: `app.ui.widgets.toggle`

### app.ui.widgets.toggle::ToggleSwitch.__init__   (app/ui/widgets/toggle.py:20-29)
- **Signature:** `def __init__(self, checked: bool, parent) -> None`
- **Purpose:** Method __init__ of ToggleSwitch
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/core/exceptions/base.py:NetGuardError.__init__:6; app/monitoring/probes/dns_probe.py:DNSResolutionProbe.__init__:26; app/monitoring/probes/external_probe.py:ExternalConnectivityProbe.__init__:23; app/monitoring/probes/gateway_probe.py:GatewayProbe.__init__:23; app/monitoring/probes/interface_probe.py:InterfaceStatsCollector.__init__:25; app/monitoring/probes/socket_probe.py:ActiveConnectionCollector.__init__:23; app/monitoring/probes/wifi_probe.py:WifiMetricsCollector.__init__:22; app/remediation/actions/flush_dns.py:FlushDNSCacheAction.__init__:16; app/remediation/actions/recheck_gateway.py:RecheckGatewayAction.__init__:15; app/remediation/actions/renew_dhcp.py:RenewIPLeaseAction.__init__:16; app/remediation/actions/switch_dns.py:SwitchDNSResolverAction.__init__:16; app/ui/main_window.py:MainWindow.__init__:279; app/ui/main_window.py:SidebarModeOption.__init__:66; app/ui/main_window.py:SidebarWidget.__init__:135; app/ui/views/dashboard_view.py:DashboardView.__init__:85; app/ui/views/dashboard_view.py:StatusIndicatorDot.__init__:44; app/ui/views/diagnosis_view.py:DiagnosisView.__init__:111; app/ui/views/diagnosis_view.py:LayerChecklistRow.__init__:45; app/ui/views/dns_view.py:DNSView.__init__:66; app/ui/views/dns_view.py:RankedServerRow.__init__:36; app/ui/views/history_view.py:HistoryEventItem.__init__:41; app/ui/views/history_view.py:HistoryView.__init__:107; app/ui/views/remediation_view.py:AuditEventRow.__init__:151; app/ui/views/remediation_view.py:ModeOptionCard.__init__:36; app/ui/views/remediation_view.py:PolicyToggleRow.__init__:109; app/ui/views/remediation_view.py:RemediationView.__init__:199; app/ui/views/settings_view.py:SettingFormRow.__init__:32; app/ui/views/settings_view.py:SettingsView.__init__:73; app/ui/views/traffic_view.py:ProcessTableCell.__init__:40; app/ui/views/traffic_view.py:TrafficView.__init__:64; app/ui/widgets/bar_row.py:DNSRecommendationPanel.__init__:191; app/ui/widgets/bar_row.py:HorizontalProgressBar.__init__:29; app/ui/widgets/bar_row.py:ProcessBarRow.__init__:74; app/ui/widgets/bar_row.py:TrafficConsumersPanel.__init__:118; app/ui/widgets/base_panel.py:Panel.__init__:32; app/ui/widgets/buttons.py:GhostButton.__init__:91; app/ui/widgets/buttons.py:PrimaryButton.__init__:17; app/ui/widgets/buttons.py:SecondaryButton.__init__:55; app/ui/widgets/chip.py:Chip.__init__:27; app/ui/widgets/day_strip.py:DayStrip.__init__:137; app/ui/widgets/day_strip.py:DayStripCanvas.__init__:24; app/ui/widgets/flow_path.py:FlowPathPanel.__init__:194; app/ui/widgets/flow_path.py:PathConnector.__init__:150; app/ui/widgets/flow_path.py:PathNodeButton.__init__:39; app/ui/widgets/latency_chart.py:LatencyChart.__init__:290; app/ui/widgets/latency_chart.py:LatencyPlotCanvas.__init__:43; app/ui/widgets/metric_cell.py:MetricCell.__init__:39; app/ui/widgets/metric_cell.py:MetricsStrip.__init__:140; app/ui/widgets/nav_item.py:NavItem.__init__:20; app/ui/widgets/realtime_chart.py:RealTimePlotWidget.__init__:18; app/ui/widgets/segmented.py:SegmentedControl.__init__:21; app/ui/widgets/session_card.py:ActiveSessionCard.__init__:32; app/ui/widgets/session_card.py:SessionReportCard.__init__:158; app/ui/widgets/sparkline.py:Sparkline.__init__:24; app/ui/widgets/status_card.py:StatusCard.__init__:25; app/ui/widgets/timeline.py:TimelineCanvas.__init__:60; app/ui/widgets/timeline.py:TimelinePanel.__init__:97; app/ui/widgets/timeline.py:TimelineStepWidget.__init__:33; app/ui/widgets/toggle.py:ToggleSwitch.__init__:21; tests/unit/test_remediation.py:ControllableAction.__init__:72
- **Calls:** QPropertyAnimation; self._anim.setDuration; self._anim.setEasingCurve; self.setCursor; self.setFixedSize; super; super().__init__
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.toggle::ToggleSwitch.get_thumb_position   (app/ui/widgets/toggle.py:47-48)
- **Signature:** `def get_thumb_position(self) -> float`
- **Purpose:** Method get_thumb_position of ToggleSwitch
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.toggle::ToggleSwitch.isChecked   (app/ui/widgets/toggle.py:31-32)
- **Signature:** `def isChecked(self) -> bool`
- **Purpose:** Method isChecked of ToggleSwitch
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/nav_item.py:NavItem._update_style:35; app/ui/widgets/nav_item.py:NavItem.paintEvent:74
- **Calls:** 
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.toggle::ToggleSwitch.mousePressEvent   (app/ui/widgets/toggle.py:56-61)
- **Signature:** `def mousePressEvent(self, event) -> None`
- **Purpose:** Method mousePressEvent of ToggleSwitch
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:SidebarModeOption.mousePressEvent:126; app/ui/views/remediation_view.py:ModeOptionCard.mousePressEvent:102; app/ui/widgets/flow_path.py:PathNodeButton.mousePressEvent:143; app/ui/widgets/toggle.py:ToggleSwitch.mousePressEvent:61
- **Calls:** event.accept; event.button; self.setChecked; super; super().mousePressEvent
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.toggle::ToggleSwitch.paintEvent   (app/ui/widgets/toggle.py:63-85)
- **Signature:** `def paintEvent(self, event) -> None`
- **Purpose:** Method paintEvent of ToggleSwitch
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/widgets/nav_item.py:NavItem.paintEvent:69
- **Calls:** QBrush; QColor; QPainter; int; painter.drawEllipse; painter.drawRoundedRect; painter.setBrush; painter.setPen; painter.setRenderHint
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.toggle::ToggleSwitch.setChecked   (app/ui/widgets/toggle.py:34-45)
- **Signature:** `def setChecked(self, checked: bool) -> None`
- **Purpose:** Method setChecked of ToggleSwitch
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** app/ui/main_window.py:MainWindow.__init__:346; app/ui/main_window.py:MainWindow._switch_view:377; app/ui/widgets/nav_item.py:NavItem.setChecked:30; app/ui/widgets/toggle.py:ToggleSwitch.mousePressEvent:58
- **Calls:** self._anim.setEndValue; self._anim.setStartValue; self._anim.start; self._anim.stop; self.toggled.emit; self.update
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

### app.ui.widgets.toggle::ToggleSwitch.set_thumb_position   (app/ui/widgets/toggle.py:50-52)
- **Signature:** `def set_thumb_position(self, pos: float) -> None`
- **Purpose:** Method set_thumb_position of ToggleSwitch
- **Inputs:** runtime args
- **Output / side effects:** return value / state mutation
- **Called by:** NEVER CALLED
- **Calls:** self.update
- **Real or fake?:** `REAL`
- **Error handling:** No explicit try/except

---
*End of Volume 3. Continue to [Volume 4: Data Flow & Decision Logic](APP_AUDIT_part4.md).*