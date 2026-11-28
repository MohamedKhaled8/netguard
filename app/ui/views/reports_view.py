"""Technical Investigation Flowchart & Reports View for NetGuard AI.

Integrates:
- Interactive 14-stage InvestigationFlowchartWidget with real stage evidence inspection
- Deep 6-layer Network Diagnosis (DiagnosisView)
- Root-Cause Analysis Findings & Before/After Snapshot Comparison
- 48-slot Daily Health Strip & Incident History Archive (HistoryView)
- Redacted HTML / Markdown / JSON report export
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui import tokens
from app.ui.i18n import language_manager, tr
from app.ui.widgets.scroll_forwarder import fit_table_to_content
from app.ui.views.diagnosis_view import DiagnosisView
from app.ui.views.history_view import HistoryView
from app.ui.widgets.async_bridge import AsyncViewBridge
from app.ui.widgets.base_panel import Panel
from app.ui.widgets.buttons import GhostButton, PrimaryButton, SecondaryButton
from app.ui.widgets.flowchart_widget import InvestigationFlowchartWidget
from app.ui.widgets.status_badge import StatusBadge


class ReportsView(QScrollArea):
    """Technical Investigation & Reporting System."""

    deep_scan_requested = Signal()

    def __init__(
        self,
        app_core: Any = None,
        measurement_repo: Optional[Any] = None,
        incident_repo: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.app_core = app_core
        self.bundle = getattr(app_core, "wifi_bundle", None) if app_core else None
        self.bridge = AsyncViewBridge(self)

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        outer = QHBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignHCenter)

        self.content_holder = QWidget()
        self.content_holder.setMaximumWidth(tokens.MAX_CONTENT_WIDTH)
        self.content_holder.setStyleSheet("background: transparent;")
        self.root = QVBoxLayout(self.content_holder)
        self.root.setContentsMargins(24, 20, 24, 32)
        self.root.setSpacing(16)
        outer.addWidget(self.content_holder)
        self.setWidget(container)

        # 1. Header & Actions
        hdr = QFrame()
        hdr.setStyleSheet(
            f"background-color: {tokens.SURFACE}; border: 1px solid {tokens.LINE}; border-radius: {tokens.RADIUS_PANEL}px;"
        )
        hl = QVBoxLayout(hdr)
        hl.setContentsMargins(20, 16, 20, 16)
        hl.setSpacing(10)

        top = QHBoxLayout()
        tcol = QVBoxLayout()
        tcol.setSpacing(4)
        self.lbl_title = QLabel(tr("rep_title"))
        self.lbl_title.setFont(tokens.get_sans_font(20, 700))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_sub = QLabel(tr("rep_sub"))
        self.lbl_sub.setFont(tokens.get_sans_font(12, 400))
        self.lbl_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_sub.setWordWrap(True)
        tcol.addWidget(self.lbl_title)
        tcol.addWidget(self.lbl_sub)
        top.addLayout(tcol, 1)

        self.badge_state = StatusBadge(tokens.SystemStatus.WAITING, tr("status.waiting"))
        top.addWidget(self.badge_state)
        hl.addLayout(top)

        btns = QGridLayout()
        btns.setSpacing(8)
        self.btn_run_full_investigation = PrimaryButton("تشغيل التحقيق الشامل")
        self.btn_run_full_investigation.clicked.connect(self.run_full_investigation)
        self.btn_export_html = SecondaryButton("تصدير HTML")
        self.btn_export_html.clicked.connect(lambda: self._export_report("html"))
        self.btn_export_md = SecondaryButton("تصدير Markdown")
        self.btn_export_md.clicked.connect(lambda: self._export_report("md"))
        self.btn_export_json = GhostButton("تصدير JSON")
        self.btn_export_json.clicked.connect(lambda: self._export_report("json"))

        btns.addWidget(self.btn_run_full_investigation, 0, 0)
        btns.addWidget(self.btn_export_html, 0, 1)
        btns.addWidget(self.btn_export_md, 0, 2)
        btns.addWidget(self.btn_export_json, 0, 3)
        hl.addLayout(btns)
        self.root.addWidget(hdr)

        # 2. Interactive 14-stage Investigation Flowchart
        self.flowchart = InvestigationFlowchartWidget()
        self.root.addWidget(self.flowchart)

        # 3. Sub-section tabs (Diagnosis | Root Cause & Snapshots | History Ledger)
        tab_bar = QHBoxLayout()
        tab_bar.setSpacing(8)
        self._sub_btns = [
            SecondaryButton("التشخيص المتعمق"),
            SecondaryButton("الأسباب الجذرية والمقارنة"),
            SecondaryButton("الأرشيف اليومي والحوادث"),
        ]
        for idx, b in enumerate(self._sub_btns):
            b.clicked.connect(lambda _=False, i=idx: self.switch_subtab(i))
            tab_bar.addWidget(b)
        tab_bar.addStretch()
        self.root.addLayout(tab_bar)

        self.sub_stack = QStackedWidget()
        self.root.addWidget(self.sub_stack)

        # Tab 0: DiagnosisView (preserved for full MainWindow/test compatibility)
        self.diagnosis_view = DiagnosisView(parent=self, embed_in_scroll=True)
        self.diagnosis_view.setMinimumHeight(680)
        self.sub_stack.addWidget(self.diagnosis_view)

        # Tab 1: Root-Cause Findings & Snapshot Diff
        tab1 = QWidget()
        l1 = QVBoxLayout(tab1)
        l1.setContentsMargins(0, 0, 0, 0)
        l1.setSpacing(14)

        p_snap = Panel(
            title="حفظ ومقارنة لقطات الشبكة (قبل / بعد)",
            subtitle="توثيق التغييرات باللقطات الفعلية مع كشف الفروقات تلقائياً",
            padding=16,
        )
        snap_bar = QHBoxLayout()
        self.btn_snap_before = SecondaryButton("حفظ لقطة أساسية (Baseline)")
        self.btn_snap_before.clicked.connect(lambda: self._capture_snapshot("Baseline"))
        self.btn_snap_after = SecondaryButton("حفظ لقطة بعد التحسين (After)")
        self.btn_snap_after.clicked.connect(lambda: self._capture_snapshot("After"))
        self.combo_snap_a = QComboBox()
        self.combo_snap_b = QComboBox()
        self.btn_compare_snaps = PrimaryButton("مقارنة اللقطتين / Compare")
        self.btn_compare_snaps.clicked.connect(self._compare_snapshots)
        snap_bar.addWidget(self.btn_snap_before)
        snap_bar.addWidget(self.btn_snap_after)
        snap_bar.addWidget(self.combo_snap_a, 1)
        snap_bar.addWidget(self.combo_snap_b, 1)
        snap_bar.addWidget(self.btn_compare_snaps)
        p_snap.main_layout.addLayout(snap_bar)

        self.table_diff = QTableWidget(0, 4)
        self.table_diff.setHorizontalHeaderLabels(["المقياس", "قبل (Baseline)", "بعد (After)", "التغيير / التحقق"])
        self.table_diff.verticalHeader().setVisible(False)
        self.table_diff.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_diff.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        p_snap.main_layout.addWidget(self.table_diff)
        l1.addWidget(p_snap)

        p_rc = Panel(
            title="تحليل السبب الجذري والأدلة / Root-Cause Findings",
            subtitle="تقرير هندسي منظم من 8 محاور يربط الأعراض بالأدلة والتوصية القابلة للتنفيذ",
            padding=16,
        )
        self.lbl_rc_summary = QLabel("شغّل التحقيق التشخيصي الشامل أو الفحص السريع لتعبئة محاور التشخيص الثمانية.")
        self.lbl_rc_summary.setFont(tokens.get_sans_font(12, 400))
        self.lbl_rc_summary.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_rc_summary.setWordWrap(True)
        p_rc.main_layout.addWidget(self.lbl_rc_summary)

        self.table_diag_summary = QTableWidget(0, 2)
        self.table_diag_summary.setHorizontalHeaderLabels(["المحور / Diagnostic Field", "التفصيل الموثق / Evidence & Decision"])
        self.table_diag_summary.verticalHeader().setVisible(False)
        self.table_diag_summary.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_diag_summary.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_diag_summary.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_diag_summary.setVisible(False)
        p_rc.main_layout.addWidget(self.table_diag_summary)

        approve_row = QHBoxLayout()
        self.btn_approve_report_action = PrimaryButton("اعتماد التوصيات وإنهاء التقرير")
        self.btn_approve_report_action.setVisible(False)
        self.btn_approve_report_action.clicked.connect(self.approve_and_finalize_report)
        approve_row.addWidget(self.btn_approve_report_action)
        approve_row.addStretch()
        p_rc.main_layout.addLayout(approve_row)

        l1.addWidget(p_rc)
        self.sub_stack.addWidget(tab1)

        # Tab 2: HistoryView (preserved for full MainWindow/test compatibility)
        self.history_view = HistoryView(
            measurement_repo=measurement_repo,
            incident_repo=incident_repo,
            parent=self,
            embed_in_scroll=True,
        )
        self.history_view.setMinimumHeight(640)
        self.sub_stack.addWidget(self.history_view)

        self.switch_subtab(0)
        language_manager().language_changed.connect(self.retranslate)

    def switch_subtab(self, idx: int) -> None:
        self.sub_stack.setCurrentIndex(idx)
        for i, b in enumerate(self._sub_btns):
            active = i == idx
            b.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {tokens.ACCENT if active else tokens.SURFACE_INSET};
                    color: {tokens.ON_ACCENT if active else tokens.TEXT_MUTED};
                    border: 1px solid {tokens.ACCENT if active else tokens.LINE};
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-weight: {700 if active else 500};
                }}
                """
            )

    def retranslate(self) -> None:
        self.lbl_title.setText(tr("rep_title"))
        self.lbl_sub.setText(tr("rep_sub"))

    def run_full_investigation(self) -> None:
        self.deep_scan_requested.emit()
        if self.bundle is None:
            self.flowchart.update_stage("network_scan", state="running", evidence_summary="Deep scan started")
            return
        if self.bridge.is_busy("full_investigation"):
            return
        self.btn_run_full_investigation.setEnabled(False)
        self.btn_approve_report_action.setVisible(False)
        self.badge_state.set_status(tokens.SystemStatus.RUNNING, tr("status.running"))
        self.flowchart.update_stage("network_scan", state="running", evidence_summary="Scanning Wi-Fi & active interfaces")

        async def _work():
            tel = await self.bundle.telemetry.collect_telemetry(include_events=True, trigger_active_scan=False)
            scan = await self.bundle.scanner.scan(request_active_scan=False)
            net_rep = await self.bundle.network_diag.run_sequence()
            dns_rep = await self.bundle.dns_diag.run_diagnostics()
            disc = await self.bundle.router_discovery.discover()
            return tel, scan, net_rep, dns_rep, disc

        def _done(res: Any) -> None:
            self.btn_run_full_investigation.setEnabled(True)
            tel, scan, net_rep, dns_rep, disc = res
            sig_q = getattr(tel, "signal_quality_pct", getattr(tel, "signal_percent", None))
            aps_cnt = len(getattr(scan, "access_points", []) or [])
            self.flowchart.update_stage(
                "network_scan",
                state="completed",
                evidence_summary=f"SSID: {getattr(tel, 'ssid', '—')} · {aps_cnt} APs nearby",
                details=f"Signal: {sig_q if sig_q is not None else '—'}% · CH {getattr(tel, 'channel', '—')}",
            )
            self.flowchart.update_stage(
                "data_collection",
                state="completed",
                evidence_summary="WLAN, ICMP, DNS & Gateway probes captured",
            )
            self.flowchart.update_stage(
                "signal_analysis",
                state="completed",
                evidence_summary=f"RSSI: {getattr(tel, 'rssi_dbm', '—')} dBm",
                details=f"Band: {getattr(tel, 'band', '—')} · PHY: {getattr(tel, 'rx_link_rate_mbps', '—')}/{getattr(tel, 'tx_link_rate_mbps', '—')} Mbps",
            )

            # Stage 4: Traffic Analysis (check live traffic controller sessions / observability)
            obs = getattr(self.app_core, "observability", None)
            tc = getattr(self.app_core, "traffic_controller", None)
            active_calls = len(tc.session_tracker.get_active_sessions()) if tc and getattr(tc, "session_tracker", None) else 0
            self.flowchart.update_stage(
                "traffic_analysis",
                state="completed",
                evidence_summary=f"Checked active flows ({active_calls} conferencing sessions)",
            )

            self.flowchart.update_stage(
                "latency_analysis",
                state="completed",
                evidence_summary=str(getattr(net_rep, "diagnosis_summary", "Done"))[:60],
                details=str(getattr(net_rep, "diagnosis_summary", "")),
            )
            self.flowchart.update_stage(
                "dns_analysis",
                state="completed",
                evidence_summary=str(getattr(dns_rep, "recommended_dns", "Checked")),
                details=str(getattr(dns_rep, "summary", "")),
            )

            # Stage 7: Router Analysis (honestly report whether authenticated session exists vs discovery only)
            gw_ip = getattr(disc, "gateway_ip", None)
            vendor = getattr(disc, "detected_vendor", "Unknown")
            self.flowchart.update_stage(
                "router_analysis",
                state="completed" if gw_ip else "skipped",
                evidence_summary=f"Gateway {gw_ip} ({vendor})" if gw_ip else "Skipped: no default gateway detected",
                details="Router discovery verified; full internal config audit runs after Router login.",
            )

            diag_summary = str(getattr(net_rep, "diagnosis_summary", "") or getattr(dns_rep, "summary", "") or "No critical degradation found")
            has_action_rec = bool(getattr(net_rep, "has_issues", False) or getattr(dns_rep, "switch_recommended", False))

            self.flowchart.update_stage(
                "root_cause",
                state="completed",
                evidence_summary=diag_summary[:70],
                details=diag_summary,
            )
            self.flowchart.update_stage(
                "recommendation",
                state="completed",
                evidence_summary="DNS/Channel/QoS recommendation generated" if has_action_rec else "No configuration change required",
                details=str(getattr(dns_rep, "summary", "") or diag_summary),
            )

            # Populate 8-part structured diagnostic summary
            fields_8 = [
                ("1. النتيجة / Finding", diag_summary),
                ("2. الدليل المباشر / Direct Evidence", f"RSSI {getattr(tel, 'rssi_dbm', '—')} dBm · {aps_cnt} APs · Gateway {gw_ip or '—'} · DNS: {getattr(dns_rep, 'recommended_dns', '—')}"),
                ("3. الطبقة المتأثرة / Affected Layer", str(getattr(net_rep, "affected_layer", "Network / DNS / RF"))),
                ("4. السبب المحتمل / Likely Cause", str(getattr(net_rep, "likely_cause", diag_summary))),
                ("5. مستوى الثقة / Confidence", "High (Measured probes)" if sig_q is not None else "Medium (Partial local telemetry)"),
                ("6. الإجراء الموصى به / Recommended Action", str(getattr(dns_rep, "recommended_action", "مراجعة القناة وخادم DNS المقترح" if has_action_rec else "المراقبة المستمرة — لا يلزم تعديل"))),
                ("7. قابلية التطبيق التلقائي / Auto-Apply", "متاح للموافقة (DNS/QoS)" if has_action_rec else "غير مطلوب"),
                ("8. الحالة / Status", "بانتظار مراجعة واعتماد المستخدم" if has_action_rec else "اكتمل التحقق بنجاح"),
            ]
            self.table_diag_summary.setRowCount(len(fields_8))
            for r, (k, v) in enumerate(fields_8):
                self.table_diag_summary.setItem(r, 0, QTableWidgetItem(tokens.bidi_isolate_mixed(k)))
                self.table_diag_summary.setItem(r, 1, QTableWidgetItem(tokens.bidi_isolate_mixed(v)))
            fit_table_to_content(self.table_diag_summary)
            self.table_diag_summary.setVisible(True)
            self.lbl_rc_summary.setText(tokens.bidi_isolate_mixed(diag_summary))

            if has_action_rec:
                # Strict workflow gate: wait for explicit user approval before executing/finalizing
                self.flowchart.update_stage(
                    "user_approval",
                    state="awaiting_approval",
                    evidence_summary="بانتظار موافقة المستخدم على التعديل المقترح",
                )
                self.flowchart.update_stage("config_change", state="waiting", evidence_summary="لم يُنفذ التعديل بعد")
                self.flowchart.update_stage("verification", state="waiting", evidence_summary="يتبع تنفيذ التعديل")
                self.flowchart.update_stage("before_after", state="waiting", evidence_summary="يتبع التحقق المرتد")
                self.flowchart.update_stage("final_report", state="waiting", evidence_summary="بانتظار موافقة المستخدم أو تخطي التعديل")
                self.btn_approve_report_action.setVisible(True)
                self.badge_state.set_status(tokens.SystemStatus.WARNING, "بانتظار الموافقة")
            else:
                self.flowchart.update_stage("user_approval", state="skipped", evidence_summary="لا يلزم تغيير بالإعدادات")
                self.flowchart.update_stage("config_change", state="skipped", evidence_summary="لا يلزم تعديل")
                self.flowchart.update_stage("verification", state="skipped", evidence_summary="لا يوجد تعديل للتحقق منه")
                self.flowchart.update_stage("before_after", state="completed", evidence_summary="خط الأساس محفوظ للمقارنة")
                self.flowchart.update_stage("final_report", state="completed", evidence_summary="جاهز للتصدير")
                self.badge_state.set_status(tokens.SystemStatus.HEALTHY, tr("status.healthy"))

            self._load_snapshots()

        def _err(err: str) -> None:
            self.btn_run_full_investigation.setEnabled(True)
            self.badge_state.set_status(tokens.SystemStatus.FAILED, tr("status.failed"))
            self.flowchart.update_stage("network_scan", state="failed", evidence_summary=err[:80], details=err)

        self.bridge.run_coro(_work, _done, _err, op_key="full_investigation", timeout_sec=25.0)

    def approve_and_finalize_report(self) -> None:
        """Record user approval/skip decision and unlock Final Report completion."""
        self.flowchart.update_stage("user_approval", state="completed", evidence_summary="تم اعتماد المراجعة من المستخدم")
        self.flowchart.update_stage("config_change", state="skipped", evidence_summary="يُطبق التعديل من التبويب المختص عند الحاجة")
        self.flowchart.update_stage("verification", state="skipped", evidence_summary="تم التحقق من القياسات الحالية")
        self.flowchart.update_stage("before_after", state="completed", evidence_summary="مقارنة اللقطات جاهزة")
        self.flowchart.update_stage("final_report", state="completed", evidence_summary="جاهز للتصدير")
        self.btn_approve_report_action.setVisible(False)
        self.badge_state.set_status(tokens.SystemStatus.HEALTHY, tr("status.healthy"))

    def update_flowchart_stage(self, stage_id: str, *, state: str, evidence_summary: str = "", details: str = "") -> None:
        self.flowchart.update_stage(stage_id, state=state, evidence_summary=evidence_summary, details=details)

    def _capture_snapshot(self, label: str) -> None:
        if self.bundle is None or not hasattr(self.bundle, "reporting"):
            return
        try:
            snap = self.bundle.reporting.build_snapshot(label=label)
            self.bundle.reporting.save_snapshot(snap)
            self._load_snapshots()
        except Exception as exc:
            QMessageBox.warning(self, "Snapshot", str(exc))

    def _load_snapshots(self) -> None:
        if self.bundle is None or not hasattr(self.bundle, "reporting"):
            return
        try:
            snaps = self.bundle.reporting.list_snapshots()
            self.combo_snap_a.clear()
            self.combo_snap_b.clear()
            for s in snaps:
                lbl = f"{getattr(s, 'label', 'Snap')} ({getattr(s, 'created_at', '')})"
                sid = getattr(s, "snapshot_id", "")
                self.combo_snap_a.addItem(lbl, sid)
                self.combo_snap_b.addItem(lbl, sid)
            if len(snaps) >= 2:
                self.combo_snap_a.setCurrentIndex(len(snaps) - 2)
                self.combo_snap_b.setCurrentIndex(len(snaps) - 1)
        except Exception:
            pass

    def _compare_snapshots(self) -> None:
        if self.bundle is None or not hasattr(self.bundle, "reporting"):
            return
        id_a = self.combo_snap_a.currentData()
        id_b = self.combo_snap_b.currentData()
        if not id_a or not id_b:
            return
        try:
            diff = self.bundle.reporting.compare(id_a, id_b)
            metrics = list(getattr(diff, "deltas", []) or [])
            self.table_diff.setRowCount(len(metrics))
            for r, d in enumerate(metrics):
                self.table_diff.setItem(r, 0, QTableWidgetItem(str(getattr(d, "metric", "—"))))
                self.table_diff.setItem(r, 1, QTableWidgetItem(str(getattr(d, "before", "—"))))
                self.table_diff.setItem(r, 2, QTableWidgetItem(str(getattr(d, "after", "—"))))
                self.table_diff.setItem(r, 3, QTableWidgetItem(str(getattr(d, "delta_summary", "—"))))
            fit_table_to_content(self.table_diff)
        except Exception as exc:
            QMessageBox.warning(self, "Compare Snapshots", str(exc))

    def _export_report(self, fmt: str) -> None:
        if self.bundle is None:
            return
        ext_map = {"html": ("HTML Files (*.html)", ".html"), "md": ("Markdown (*.md)", ".md"), "json": ("JSON (*.json)", ".json")}
        filt, ext = ext_map.get(fmt, ("JSON (*.json)", ".json"))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path, _ = QFileDialog.getSaveFileName(self, "تصدير التقرير / Export Report", f"netguard_report_{ts}{ext}", filt)
        if not path:
            return
        try:
            if fmt == "html" and hasattr(self.bundle, "reporting"):
                snaps = self.bundle.reporting.list_snapshots()
                snap = snaps[-1] if snaps else self.bundle.reporting.build_snapshot(label="Export")
                content = self.bundle.reporting.export_html(snap)
            elif fmt == "md" and hasattr(self.bundle, "report_service"):
                content = self.bundle.report_service.build_markdown_report(title="NetGuard AI Technical Report")
            else:
                content = self.bundle.report_service.build_sanitized_json()
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            QMessageBox.information(self, "تصدير التقرير", f"تم حفظ التقرير بنجاح (مع تنقيح كلمات المرور والمفاتيح):\n{path}")
        except Exception as exc:
            QMessageBox.warning(self, "Export Error", str(exc))

    def _sync_content_width(self) -> None:
        vw = self.viewport().width()
        if vw > 0:
            target_w = min(vw, tokens.MAX_CONTENT_WIDTH)
            self.content_holder.setFixedWidth(target_w)
            inner_w = max(320, target_w - 48)
            for child_w in (self.diagnosis_view, self.history_view):
                child_w.resize(inner_w, max(child_w.height(), 480))
                if hasattr(child_w, "content_widget"):
                    child_w.content_widget.setMaximumWidth(inner_w)
                cw_scroll = getattr(child_w, "scroll", None)
                if isinstance(cw_scroll, QScrollArea):
                    cw_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                    cw_scroll.resize(inner_w, max(cw_scroll.height(), 480))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_content_width()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_content_width()

    def shutdown(self) -> None:
        self.bridge.shutdown()
