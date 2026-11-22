# خط أنابيب الإصلاح الذاتي الكامل (11 خطوة) - NetGuard AI

> **توثيق تقني شامل** يشرح ما يحدث بالضبط داخل الكود من لحظة اكتشاف المشكلة حتى الإصلاح والتحقق والتسجيل.

---

## 📊 **نظرة عامة على الـ Pipeline**

```
Raw Measurements (Probes كل 1-3 ث)
    → Statistical Summaries (EvidenceAccumulator - نافذة 30 عينة)
        → Classifier Evaluation (5 مصنفات متوازية)
            → Diagnosis Selection (Diagnosis Engine - يختار الأسوأ)
                → Safety Gate + Policy Check (Orchestrator)
                    → Action Execution (Platform Adapter - PowerShell/Admin)
                        → Verification (Re-measure فوري)
                            → Rollback تلقائي لو فشل
                                → Audit Log (SQLite)
                                    → UI Notification (Dashboard Timeline)
```

---

## 🔬 **الخطوة 1: المراقبة المستمرة (Probes)**

**الملف:** `app/monitoring/schedulers/engine.py:99-101`  
**التردد:** كل 1-3 ثانية حسب نوع الـ Probe

```python
# في ObservabilityEngine.start()
for probe in self._probes:
    task = asyncio.create_task(self._probe_worker(probe), name=f"worker_{probe.name}")

# _probe_worker يشغل كل probe في حلقة لا نهائية:
async def _probe_worker(self, probe: BaseProbe):
    while self._running:
        results = await probe.run()           # ينفذ القياس الحقيقي
        self._update_probe_health(probe.name, results)
        for pr in results:
            m = pr.to_measurement()
            await self._record_measurement(m)  # يخزن + ينشر على Event Bus
        await asyncio.sleep(probe.interval_sec)
```

### **الـ 6 Probes الحقيقية:**

| Probe | التردد | ما يقيسه فعلياً | الكود |
|-------|---------|----------------|-------|
| **GatewayProbe** | 1 ثانية | Ping للراوتر (gateway IP) | `app/monitoring/probes/gateway_probe.py:31-130` |
| **ExternalConnectivityProbe** | 2 ثانية | Ping لـ 8.8.8.8, 1.1.1.1, cloudflare.com | `app/monitoring/probes/external_probe.py` |
| **DNSResolutionProbe** | 3 ثانية | استعلامات DNS حقيقية عبر `dns.resolver` | `app/monitoring/probes/dns_probe.py` |
| **InterfaceStatsCollector** | 5 ثانية | `psutil.net_io_counters()` لكل كرت شبكة | `app/monitoring/probes/interface_probe.py` |
| **WifiMetricsCollector** | 3 ثانية | `netsh wlan show interfaces` / WMI | `app/monitoring/probes/wifi_probe.py` |
| **ActiveConnectionCollector** | 10 ثانية | `psutil.net_connections(kind="inet")` | `app/monitoring/probes/socket_probe.py` |

### **مثال قياس Gateway حقيقي:**
```python
# app/monitoring/probes/gateway_probe.py:52-55
loop = asyncio.get_running_loop()
success, latency_ms = await loop.run_in_executor(
    None, self.platform.ping, gw, self.timeout_sec
)

# يرجع ProbeResult حقيقية:
ProbeResult(
    metric_type=GATEWAY_REACHABILITY, raw_value=1.0, latency_ms=2.3, status=SUCCESS
)
ProbeResult(
    metric_type=GATEWAY_LATENCY, raw_value=2.3, status=SUCCESS
)
ProbeResult(
    metric_type=GATEWAY_PACKET_LOSS, raw_value=0.0, status=SUCCESS
)
```

---

## 📈 **الخطوة 2: تجميع الأدلة الإحصائية (Evidence Accumulator)**

**الملف:** `app/monitoring/schedulers/engine.py:153-170` + `app/diagnosis/evidence.py:13-31`

```python
# في _record_measurement:
async def _record_measurement(self, m: Measurement):
    # 1. يخزن في Sliding Window (deque حجم 30)
    self._sliding_windows[m.metric_type].append(m)
    
    # 2. يحفظ في SQLite (background thread - لا يبلوك الـ event loop)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, self.repo.save, m)
    
    # 3. ينشر على Event Bus للمشتركين
    topic = f"{EventTopics.TELEMETRY_PREFIX}{m.metric_type.value}"
    await self.event_bus.publish(topic, m)
```

### **تحويل 30 عينة خام → ملخص إحصائي واحد:**

```python
# app/diagnosis/evidence.py:13-31
class EvidenceSummary:
    def __init__(self, metric_type: MetricType, samples: List[Measurement]):
        self.metric_type = metric_type
        self.count = len(samples)
        
        # القيم الصالحة فقط (SUCCESS + DEGRADED)
        valid_values = [s.raw_value for s in samples 
                       if s.status in (ProbeStatus.SUCCESS, ProbeStatus.DEGRADED)]
        self.valid_count = len(valid_values)
        
        # إحصائيات حقيقية
        self.mean = statistics.mean(valid_values) if valid_values else 0.0
        self.median = statistics.median(valid_values) if valid_values else 0.0
        self.min = min(valid_values) if valid_values else 0.0
        self.max = max(valid_values) if valid_values else 0.0
        self.stdev = statistics.stdev(valid_values) if len(valid_values) >= 2 else 0.0
        
        # إحصائيات الفشل
        failed_count = sum(1 for s in samples 
                          if s.status in (FAILED, TIMEOUT, UNREACHABLE))
        self.failure_ratio = failed_count / self.count if self.count > 0 else 0.0
        self.latest_value = samples[-1].raw_value if samples else 0.0
```

---

## 🎯 **الخطوة 3: تقييم التشخيص (Diagnosis Engine + 5 Classifiers)**

**الملف:** `app/diagnosis/engine.py:58-225` + `app/diagnosis/classifiers/*.py`

```python
# DiagnosisEngine.evaluate_windows()
async def evaluate_windows(self, windows: Dict[MetricType, List[Measurement]]) -> Diagnosis:
    # 1. يلخص كل النوافذ لـ EvidenceSummary
    summaries = {}
    for metric, samples in windows.items():
        summary = EvidenceAccumulator.summarize_window(samples)
        if summary:
            summaries[metric] = summary
    
    # 2. يشغل 5 Classifiers بالتوازي
    candidate_diagnoses = []
    for classifier in self.classifiers:
        try:
            diag = classifier.evaluate(summaries)
            if diag:
                candidate_diagnoses.append(diag)
        except Exception as exc:
            logger.error("Error running classifier %s: %s", classifier.__class__.__name__, exc)
    
    # 3. يختار الأسوأ: أعلى خطورة + أعلى ثقة
    if candidate_diagnoses:
        severity_order = {CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1, INFO: 0}
        candidate_diagnoses.sort(
            key=lambda d: (severity_order.get(d.severity, 0), d.confidence),
            reverse=True
        )
        selected = candidate_diagnoses[0]
    else:
        # منطق fallback لو مفيش بيانات كافية...
    
    # 4. لو مش HEALTHY → يحفظ في Incident DB
    if selected.probable_cause != ProbableCause.HEALTHY:
        inc_id = await loop.run_in_executor(None, self.repo.save_or_update, selected)
        selected.id = inc_id
        self._current_active_incident_id = inc_id
    
    return selected
```

### **الـ 5 Classifiers وما تفحصه:**

| Classifier | الملف | يفحص | الأسباب المحتملة |
|------------|-------|-------|------------------|
| **GatewayHealthClassifier** | `gateway_fault.py` | Gateway reachability + latency + loss | `LOCAL_GATEWAY_UNREACHABLE`, `LOCAL_GATEWAY_HIGH_LATENCY` |
| **DNSHealthClassifier** | `dns_fault.py` | DNS latency + success rate | `DNS_RESOLVER_UNRESPONSIVE`, `DNS_RESOLVER_HIGH_LATENCY` |
| **UpstreamISPClassifier** | `upstream_isp_fault.py` | External latency + packet loss | `ISP_UPSTREAM_HIGH_LATENCY`, `ISP_UPSTREAM_PACKET_LOSS` |
| **DestinationSpecificClassifier** | `destination_fault.py` | Target-specific failures | `DESTINATION_SPECIFIC_OUTAGE` |
| **WifiInstabilityClassifier** | `wifi_fault.py` | WiFi signal + retransmissions | `WIFI_SIGNAL_DEGRADED` |

### **مثال: Gateway Classifier Logic حقيقي:**

```python
# app/diagnosis/classifiers/gateway_fault.py:22-78
def evaluate(self, summaries) -> Optional[Diagnosis]:
    gw_reach = summaries.get(GATEWAY_REACHABILITY)
    gw_lat = summaries.get(GATEWAY_LATENCY)
    gw_loss = summaries.get(GATEWAY_PACKET_LOSS)
    
    # شرط 1: Gateway غير قابل للوصول (failure_ratio >= 50%)
    gw_unreachable_thresh = self.thresholds.loss.gateway_unreachable_ratio  # 0.50
    is_sustained_loss = (
        (gw_reach and gw_reach.failure_ratio >= gw_unreachable_thresh)
        or (gw_loss and gw_loss.failure_ratio >= self.thresholds.gateway_packet_loss_critical)
        or (gw_reach and gw_reach.latest_value == 0.0 and gw_reach.count == 1)
    )
    
    if is_sustained_loss:
        # يبني Evidence قائمة بأدلة حقيقية
        ev_list = []
        if gw_reach:
            ev_list.append(Evidence(
                metric_type=GATEWAY_REACHABILITY, target="gateway",
                observed_value=gw_reach.latest_value, threshold_value=1.0,
                condition="gateway_reachability == 0", weight=1.5
            ))
        
        # ثقة أعلى لو الـ External أيضاً down
        ext_loss = summaries.get(EXTERNAL_PACKET_LOSS)
        confidence = 0.95 if (ext_loss and ext_loss.latest_value >= gw_unreachable_thresh) else 0.85
        
        return Diagnosis(
            probable_cause=LOCAL_GATEWAY_UNREACHABLE,
            confidence=confidence,
            severity=CRITICAL,
            supporting_evidence=ev_list,
            recommended_actions=["recheck_gateway"],
            auto_remediation_permitted=True,
            explanation="Default gateway failed to respond to echo probes. Local link or router is offline."
        )
    
    # شرط 2: Latency حرجة (> threshold)
    if gw_lat and gw_lat.mean >= self.thresholds.gateway_latency_critical_ms:
        return Diagnosis(
            probable_cause=LOCAL_GATEWAY_HIGH_LATENCY,
            confidence=0.85,
            severity=HIGH,
            supporting_evidence=[Evidence(...)],
            recommended_actions=["inspect_wifi_interference", "check_local_link"],
            auto_remediation_permitted=False,
        )
    
    return None
```

---

## 🛡️ **الخطوة 4: Safety Gate - فحص الأمان (Orchestrator)**

**الملف:** `app/remediation/orchestrator.py:234-280`

```python
def _check_safety_gate(self, action, diagnosis) -> Tuple[bool, str]:
    # 1. Circuit Breaker - لو فشلت 3 مرات متتالية → ممنوع
    if self.safety.is_circuit_open(action.action_id):
        return False, f"Circuit breaker OPEN for {action.action_id}"
    
    # 2. Cooldown - لو اتنفذت من أقل من المدة المحددة → ممنوع
    cooldown = self.config.cooldowns.get(action.action_id, 45.0)
    last_exec = self._last_execution.get(action.action_id, 0)
    if time.time() - last_exec < cooldown:
        remaining = cooldown - (time.time() - last_exec)
        return False, f"Cooldown active ({remaining:.1f}s remaining)"
    
    # 3. Policy Toggle - المستخدم عطل الإجراء من الإعدادات
    policy_key = ACTION_TO_POLICY_MAP.get(action.action_id)
    if policy_key and not self.is_policy_allowed(policy_key):
        return False, f"Policy {policy_key} disabled by user"
    
    # 4. Operating Mode Check
    if self.mode == OperatingMode.WATCH and action.risk_level >= RiskLevel.LEVEL_2_CONTROLLED:
        return False, "Watch mode: no modifications allowed"
    
    return True, "OK"
```

### **إعدادات Safety (config):**
```yaml
# config.yaml - remediation section
remediation:
  circuit_breaker_failure_threshold: 3
  circuit_breaker_reset_timeout_sec: 300
  cooldowns:
    flush_dns_cache: 10
    switch_dns_resolver: 45
    renew_ip_lease: 120
    recheck_gateway: 30
```

---

## 📞 **الخطوة 5: Meeting Guard - حماية المكالمات**

**الملف:** `app/remediation/orchestrator.py:280-290` + `app/traffic/controller.py:189-194`

```python
# في handle_diagnosis():
if self.meeting_guard_check and self.meeting_guard_check():
    # TrafficController يرصد Zoom/Teams نشط
    if action.risk_level >= RiskLevel.LEVEL_2_CONTROLLED:
        logger.info("Meeting Guard: deferring action %s (meeting active)", action.action_id)
        return deferred_result

# TrafficController.is_critical_meeting_active():
def is_critical_meeting_active(self) -> bool:
    return (
        any(p.category == WorkloadCategory.CONFERENCING for p in self._last_profiles.values())
        or self.session_tracker.has_active_conferencing()
    )
```

**السياسة:** أثناء مكالمة Zoom/Teams نشطة → يمنع `switch_dns` و `renew_ip` و `recheck_gateway` (لأنها تسبب انقطاع لحظي). يسمح فقط بـ `flush_dns_cache`.

---

## 🎯 **الخطوة 6: اختيار الإجراء (Action Selection)**

**الملف:** `app/remediation/orchestrator.py:150-180` + `app/remediation/registry.py`

```python
async def handle_diagnosis(self, diagnosis) -> Optional[ActionExecutionRecord]:
    # يحصل على الإجراءات المسجلة لهذا التشخيص
    actions = self.registry.get_actions_for_diagnosis(diagnosis.probable_cause)
    
    # لـ LOCAL_GATEWAY_UNREACHABLE → يرجع [RecheckGatewayAction]
    # لـ DNS_RESOLVER_UNRESPONSIVE → يرجع [FlushDNSCacheAction, SwitchDNSResolverAction]
    
    # يختار الأول المسموح بالمرور من Safety Gate
    for action in actions:
        allowed, reason = self._check_safety_gate(action, diagnosis)
        if allowed:
            selected_action = action
            break
    else:
        # لا إجراء مسموح
        return None
```

### **الإجراءات المسجلة (Registry):**
```python
# app/application.py:105-111
def _register_default_actions(self):
    self.action_registry.register(RecheckGatewayAction())      # Ping مكثف للراوتر
    self.action_registry.register(FlushDNSCacheAction())       # ipconfig /flushdns
    self.action_registry.register(SwitchDNSResolverAction(...)) # تغيير DNS عبر PowerShell
    self.action_registry.register(RenewIPLeaseAction())        # ipconfig /release + /renew
```

---

## ⚡ **الخطوة 7: تنفيذ الإجراء فعلياً (Action Execution)**

**الملف:** `app/remediation/orchestrator.py:268-300` + `app/remediation/actions/*.py`

```python
# في Orchestrator - ينفذ الإجراء:
record = await selected_action.execute(self.platform, diagnosis)
```

### **مثال 1: Recheck Gateway (بسيط):**
```python
# app/remediation/actions/recheck_gateway.py
async def execute(self, platform, diagnosis) -> ActionExecutionRecord:
    gw = platform.get_default_gateway()
    results = []
    latencies = []
    
    for i in range(3):  # 3 محاولات
        success, latency = platform.ping(gw, timeout=2.0)
        results.append(success)
        if success:
            latencies.append(latency)
    
    success_count = sum(results)
    return ActionExecutionRecord(
        status=SUCCEEDED if success_count == 3 else FAILED,
        execution_duration_ms=sum(latencies) if latencies else 0,
        verification_duration_ms=latencies[-1] if latencies else 0,
    )
```

### **مثال 2: Switch DNS (معقد - يحتاج Admin):**
```python
# app/remediation/actions/switch_dns.py:80-180
async def execute(self, platform, diagnosis) -> ActionExecutionRecord:
    iface = platform.get_primary_interface()
    
    # 1. يقيس الـ DNS الحالي قبل التغيير
    pre_meas = await measure_dns_resolver_deep(current_dns_ip)
    before_ms = pre_meas.mean_latency_ms
    
    # 2. يطبق التغيير عبر PowerShell مرتفع الصلاحيات
    ps_cmd = f'Set-DnsClientServerAddress -InterfaceAlias "{iface}" -ServerAddresses {primary},{secondary}'
    ok, msg = await platform.run_elevated_ps(ps_cmd)
    platform.flush_dns_cache()
    
    # 3. تحقق فوري: استعلام DNS حقيقي
    post_meas = await measure_dns_resolver_deep(new_dns_ip)
    
    # 4. لو فشل التحقق → Rollback فوري
    if not ok or post_meas.success_rate == 0.0:
        if is_dhcp:
            platform.set_interface_dns_dhcp(iface)
        else:
            platform.set_interface_dns_servers(iface, prev_servers)
        platform.flush_dns_cache()
        return record_failed
    
    return record_success
```

---

## ✅ **الخطوة 8: التحقق (Verification) - يقيس مرة تانية**

**الملف:** `app/remediation/orchestrator.py:344-360`

```python
# بعد التنفيذ، يتحقق من نجاح الإصلاح:
verification = await selected_action.verify(self.platform, record)

# في Action.verify() - يعيد قياس نفس المترك:
async def verify(self, platform, record) -> VerificationResult:
    if self.action_id == "switch_dns_resolver":
        # استعلام DNS للـ google.com عبر الـ DNS الجديد
        meas = await measure_dns_resolver_deep(record.post_remedy_metrics["active_servers"][0])
        return VerificationResult(
            success=meas.success_rate > 0.9,
            latency_ms=meas.mean_latency_ms,
            message=f"DNS responds in {meas.mean_latency_ms:.1f}ms"
        )
    elif self.action_id == "recheck_gateway":
        # Ping 3 مرات تانية للراوتر
        success_count = 0
        for _ in range(3):
            ok, _ = platform.ping(gw, timeout=2.0)
            if ok: success_count += 1
        return VerificationResult(success=success_count == 3)
```

---

## 🔄 **الخطوة 9: التراجع التلقائي (Rollback) لو فشل التحقق**

**الملف:** `app/remediation/orchestrator.py:354-370` + `app/remediation/actions/switch_dns.py:1330-1336`

```python
if not verification.success:
    logger.warning("Action %s FAILED post-verification: %s. Initiating ROLLBACK...", 
                   action.action_id, verification.message)
    
    # يشغل rollback في الإجراء نفسه
    rollback_ok, rollback_msg = await action.rollback(self.platform, record)
    
    # يحدث السجل
    record.status = FAILED
    record.rollback_performed = True
    record.rollback_success = rollback_ok
    record.error_message = f"Verification failed: {verification.message}. Rollback: {rollback_msg}"
```

### **Rollback لـ DNS Switch:**
```python
# app/remediation/actions/switch_dns.py:1330-1336
async def rollback(self, platform, record) -> Tuple[bool, str]:
    rollback_performed = True
    if record.pre_remedy_metrics.get("is_dhcp"):
        ok, msg = platform.set_interface_dns_dhcp(iface)  # يرجع لـ DHCP
    else:
        ok, msg = platform.set_interface_dns_servers(iface, prev_servers)  # يرجع للقديم
    platform.flush_dns_cache()
    return ok, msg
```

---

## 📝 **الخطوة 10: تسجيل التدقيق (Audit Log) - في SQLite**

**الملف:** `app/remediation/orchestrator.py:410-420` + `app/storage/repositories/audit_repo.py`

```python
# يسجل كل شي في قاعدة البيانات:
record = ActionExecutionRecord(
    id=str(uuid.uuid4()),
    action_id="switch_dns_resolver",
    action_name="تحويل إلى Google DNS (8.8.8.8)",
    risk_level=RiskLevel.LEVEL_2_CONTROLLED,
    trigger_diagnosis_id=diagnosis.id,
    
    # مقاسات قبل الإصلاح
    pre_remedy_metrics={
        "interface": "Wi-Fi",
        "original_servers": ["192.168.1.1"],
        "latency_ms": 45.2,
        "is_dhcp": False
    },
    
    # مقاسات بعد الإصلاح
    post_remedy_metrics={
        "active_servers": ["8.8.8.8", "8.8.4.4"],
        "latency_ms": 32.1,
        "success_rate": 1.0,
        "status": "Configured successfully"
    },
    
    status=ActionExecutionStatus.SUCCEEDED,
    execution_duration_ms=1250.0,
    verification_duration_ms=45.0,
    rollback_performed=False,
    rollback_success=None,
)

# حفظ في SQLite (background thread)
await loop.run_in_executor(None, self.audit.save, record)
```

### **Schema الجدول (SQLite):**
```sql
CREATE TABLE action_audit (
    id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    action_name TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    trigger_diagnosis_id TEXT,
    pre_remedy_metrics TEXT,      -- JSON
    post_remedy_metrics TEXT,     -- JSON
    status TEXT NOT NULL,         -- SUCCEEDED/FAILED/ROLLED_BACK
    execution_duration_ms REAL,
    verification_duration_ms REAL,
    error_message TEXT,
    rollback_performed BOOLEAN,
    rollback_success BOOLEAN,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🖥️ **الخطوة 11: تحديث الواجهة (UI Notification)**

**الملف:** `app/ui/main_window.py:812-826` + `app/ui/views/dashboard_view.py:872-891`

```python
# في MainWindow - يستقبل أحداث من Event Bus:
def _wire_background_event_listeners(self):
    event_bus = self.app_core.ctx.event_bus
    
    async def _on_rem_started(topic, event_data):
        data = event_data.model_dump() if hasattr(event_data, "model_dump") else event_data
        self.bridge.remediation_event_received.emit("started", data)
    
    async def _on_rem_completed(topic, event_data):
        data = event_data.model_dump() if hasattr(event_data, "model_dump") else event_data
        self.bridge.remediation_event_received.emit("completed", data)
    
    event_bus.subscribe_sync(EventTopics.REMEDIATION_STARTED, _on_rem_started)
    event_bus.subscribe_sync(EventTopics.REMEDIATION_COMPLETED, _on_rem_completed)

# معالجة الحدث في UI Thread:
def _on_remediation_event_received(self, stage: str, data: Dict[str, Any]):
    action_name = data.get("action_name", "إجراء تعافي ذكي")
    
    if stage == "started":
        self.view_dashboard.log_autonomous_action(
            f"تدخل ذاتي تلقائي: {action_name}",
            "قام NetGuard برصد تذبذب وبدأ المعالجة التلقائية فوراً.",
            level="warning"
        )
    else:  # completed
        self.view_dashboard.log_autonomous_action(
            f"نجاح التعافي الذاتي: {action_name}",
            "تم تنفيذ الإجراء وتأكيد استقرار البنج وسرعة الاستجابة بنجاح.",
            level="success"
        )
        self._refresh_timeline_from_records()  # يحدث الـ Timeline
```

### **في Dashboard - يضيف للـ Timeline:**
```python
# app/ui/views/dashboard_view.py:872-891
def log_autonomous_action(self, title: str, description: str, level: str = "success"):
    now = datetime.now()
    steps = [
        ((now - timedelta(seconds=15)).strftime("%H:%M:%S"), "اكتشاف المشكلة", 
         "رصد انحراف في مؤشرات جودة التدفق."),
        ((now - timedelta(seconds=12)).strftime("%H:%M:%S"), "تحديد السبب", description),
        ((now - timedelta(seconds=5)).strftime("%H:%M:%S"), "الإصلاح", title),
        (now.strftime("%H:%M:%S"), "النتيجة", 
         "استعادة الاستقرار وانخفاض زمن الاستجابة." if level == "success" else 
         "تعذر الإكمال." if level == "error" else 
         "تم التدخل مع استمرار المراقبة.")
    ]
    self.timeline_panel.set_event(now.strftime("%H:%M"), steps, is_resolved=(level == "success"))
```

---

## 📋 **مثال حي من لوجز تطبيقك:**

| اللوج | الخطوة | الكود المنفذ |
|-------|--------|-------------|
| `Starting Observability Engine with 6 probes` | 1 | `engine.py:97` - `create_task(_probe_worker)` |
| `Retention prune completed: {'aggregates_created': 4904...}` | - | `application.py:209` - `prune_all()` |
| `Autonomous mode: automatically switching DNS to Google (8.8.8.8) — latency gain: +12.3 ms` | 3→7 | `optimizer.py:109` → `orchestrator.execute_action()` |
| `Action recheck_gateway SUCCEEDED and VERIFIED: Gateway verified responsive (3/3)` | 8 | `orchestrator.py:352` - `verification.success = True` |
| `Safety gate blocked action 'recheck_gateway': Cooldown (6.9s remaining)` | 4 | `orchestrator.py:245` - cooldown check |
| `Circuit breaker OPEN for action recheck_gateway` | 4 | `safety.py:44` - `failure_count >= 3` |

---

## 🔧 **كيف تختبر/تعدل الـ Pipeline:**

### **إضافة Probe جديد:**
```python
# 1. أنشئ Probe جديد في app/monitoring/probes/custom_probe.py
# 2. سجله في ObservabilityEngine:
engine.register_probe(CustomProbe(platform, interval_sec=5.0))
```

### **إضافة Classifier جديد:**
```python
# 1. أنشئ Classifier في app/diagnosis/classifiers/custom_fault.py
# 2. سجله في DiagnosisEngine:
diagnosis_engine.register_classifier(CustomFaultClassifier(thresholds))
```

### **إضافة Action جديد:**
```python
# 1. أنشئ Action في app/remediation/actions/custom_action.py
# 2. سجله في Application:
action_registry.register(CustomAction())
# 3. أضف mapping في Orchestrator:
ACTION_TO_POLICY_MAP["custom_action"] = "allow_custom_action"
```

### **تعديل Thresholds:**
```yaml
# config.yaml
thresholds:
  gateway_latency_warning_ms: 20
  gateway_latency_critical_ms: 50
  external_latency_warning_ms: 80
  external_latency_critical_ms: 150
  dns_latency_warning_ms: 50
  loss:
    gateway_packet_loss_critical: 0.10
    gateway_unreachable_ratio: 0.50
```

---

## 🎯 **الخلاصة**

**النظام لا "يخمن" - كل خطوة مبنية على:**
1. **Measurements حقيقية** (Ping, DNS Query, psutil, netsh, WMI)
2. **Statistical Evidence** (Mean, Median, Stdev, Failure Ratio على 30 عينة)
3. **Thresholds محددة** في Config (قابلة للتعديل)
4. **Safety Gates** متعددة الطبقات (Circuit Breaker, Cooldown, Policy, Meeting Guard)
5. **Verification فوري** بعد كل إصلاح (Re-measure نفس المترك)
6. **Rollback تلقائي** لو فشل التحقق
7. **Audit Trail كامل** في SQLite لكل تحقيق وإجراء
8. **UI Real-time** يعكس كل شي للمستخدم

---

*محدث: 2026-11-19 | NetGuard AI v1.0*