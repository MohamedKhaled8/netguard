"""Internet Quality & Bufferbloat Testing Workspace View for NetGuard AI.

Features:
- 6-Stage Interactive Test Workflow Stepper (Preparing -> Idle Baseline -> Download -> Upload -> Loaded Latency -> Final Assessment)
- Explicit separation of Wi-Fi PHY Rate vs Local LAN Speed vs WAN Download/Upload
- Honest idle state ("—", "غير مُقاس بعد" / "Not measured", NEVER indefinite "بانتظار القياس...")
- Meeting Guard lock awareness (warns/blocks heavy bandwidth saturation during active calls)
- Bufferbloat Grade CircularGauge + Idle vs Download vs Upload Latency Comparison Chart
- Ping & Traceroute Sequence Table (Gateway, Public DNS, Internet Probe, Hop Breakdown)
"""

from __future__ import annotations

from typing import Any, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui import tokens
from app.ui.i18n import get_language, language_manager, tr
from app.ui.widgets.scroll_forwarder import fit_table_to_content
from app.ui.widgets.async_bridge import AsyncViewBridge
from app.ui.widgets.base_panel import Panel
from app.ui.widgets.buttons import PrimaryButton, SecondaryButton
from app.ui.widgets.circular_gauge import CircularGauge
from app.ui.widgets.status_badge import StatusBadge


class LoadedLatencyComparisonChart(QWidget):
    """Horizontal bar comparison for Idle vs Download Loaded vs Upload Loaded Latency (ms)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(140)
        self._bars: List[tuple[str, Optional[float], str]] = [
            ("Idle Latency", None, tokens.STATUS_OK),
            ("Under Download", None, tokens.SECONDARY_CYAN),
            ("Under Upload", None, tokens.SECONDARY_PURPLE),
        ]

    def set_latencies(
        self,
        idle_ms: Optional[float],
        dl_ms: Optional[float],
        ul_ms: Optional[float],
    ) -> None:
        self._bars = [
            ("كمون الخمول / Idle Latency", idle_ms, tokens.STATUS_OK),
            ("تحت التحميل / During Download", dl_ms, tokens.SECONDARY_CYAN),
            ("تحت الرفع / During Upload", ul_ms, tokens.SECONDARY_PURPLE),
        ]
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        vals = [v for _, v, _ in self._bars if v is not None]
        max_v = max(vals + [80.0])

        row_h = h / max(1, len(self._bars))
        for idx, (label, val, col) in enumerate(self._bars):
            y = idx * row_h + 10
            painter.setFont(tokens.get_sans_font(12, 500))
            painter.setPen(QPen(QColor(tokens.TEXT_MUTED)))
            painter.drawText(8, int(y + 14), label)

            bar_y = y + 22
            bar_w = max(60.0, w - 120.0)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(tokens.SURFACE_INSET)))
            painter.drawRoundedRect(8, int(bar_y), int(bar_w), 12, 6, 6)

            if val is not None:
                frac = max(0.03, min(1.0, val / max_v))
                painter.setBrush(QBrush(QColor(col)))
                painter.drawRoundedRect(8, int(bar_y), int(bar_w * frac), 12, 6, 6)
                txt = f"{val:.1f} ms"
                painter.setPen(QPen(QColor(tokens.TEXT)))
            else:
                txt = "—"
                painter.setPen(QPen(QColor(tokens.TEXT_MUTED)))
            painter.setFont(tokens.get_mono_font(12, 600))
            painter.drawText(int(bar_w + 18), int(bar_y + 11), txt)


class QualityWorkflowStepper(QFrame):
    """6-stage execution workflow bar for Internet Quality & Bufferbloat tests."""

    STAGES = [
        ("preparing", "التحضير / Preparing"),
        ("idle", "خط الأساس / Idle Baseline"),
        ("download", "اختبار التنزيل / Download"),
        ("upload", "اختبار الرفع / Upload"),
        ("loaded", "تحليل التضخم / Loaded Latency"),
        ("complete", "التقييم النهائي / Assessment"),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: {tokens.SURFACE}; border: 1px solid {tokens.LINE}; border-radius: {tokens.RADIUS_PANEL}px;"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)
        self._chips: dict[str, QLabel] = {}
        for sid, label in self.STAGES:
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFont(tokens.get_sans_font(12, 500))
            lbl.setWordWrap(True)
            lbl.setMinimumHeight(40)
            lay.addWidget(lbl, 1)
            self._chips[sid] = lbl
        self.set_stage("idle_wait")

    def set_stage(self, active_id: str) -> None:
        order = [s[0] for s in self.STAGES]
        active_idx = order.index(active_id) if active_id in order else -1
        for i, (sid, _) in enumerate(self.STAGES):
            lbl = self._chips[sid]
            if active_id == "complete":
                fg, bg, bd = tokens.STATUS_OK, tokens.OK_SOFT_BG, tokens.OK_SOFT_BORDER
            elif i < active_idx:
                fg, bg, bd = tokens.STATUS_OK, tokens.OK_SOFT_BG, tokens.OK_SOFT_BORDER
            elif i == active_idx:
                fg, bg, bd = tokens.ACCENT_BRIGHT, tokens.INFO_SOFT_BG, tokens.ACCENT
            else:
                fg, bg, bd = tokens.TEXT_MUTED, tokens.SURFACE_INSET, tokens.LINE
            lbl.setStyleSheet(
                f"color: {fg}; background-color: {bg}; border: 1px solid {bd}; border-radius: 8px; padding: 4px 8px;"
            )


class InternetQualityView(QScrollArea):
    """Testing & Performance Analysis Workspace (Speed, Bufferbloat, Ping & Traceroute)."""

    speed_test_completed = Signal(object)

    def __init__(self, app_core: Any = None, parent: Optional[QWidget] = None) -> None:
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
        hl.setSpacing(12)

        top = QHBoxLayout()
        tcol = QVBoxLayout()
        tcol.setSpacing(4)
        self.lbl_title = QLabel(tr("iq_title"))
        self.lbl_title.setFont(tokens.get_sans_font(20, 700))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_sub = QLabel(tr("iq_sub"))
        self.lbl_sub.setFont(tokens.get_sans_font(12, 400))
        self.lbl_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_sub.setWordWrap(True)
        tcol.addWidget(self.lbl_title)
        tcol.addWidget(self.lbl_sub)
        top.addLayout(tcol, 1)

        self.badge_status = StatusBadge(tokens.SystemStatus.WAITING, tr("iq.unmeasured"))
        top.addWidget(self.badge_status)
        hl.addLayout(top)

        opts = QGridLayout()
        opts.setSpacing(10)
        self.chk_include_upload = QCheckBox("تضمين اختبار الرفع")
        self.chk_include_upload.setFont(tokens.get_sans_font(12, 500))
        self.chk_include_upload.setChecked(True)
        self.chk_include_upload.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        self.btn_run_speed = PrimaryButton("تشغيل اختبار السرعة")
        self.btn_run_speed.clicked.connect(self.run_speed_test)
        self.btn_run_bufferbloat = SecondaryButton("اختبار Bufferbloat")
        self.btn_run_bufferbloat.clicked.connect(self.run_bufferbloat_test)
        self.btn_run_net_diag = SecondaryButton("فحص Ping والمسار")
        self.btn_run_net_diag.clicked.connect(self.run_network_sequence)

        opts.addWidget(self.chk_include_upload, 0, 0)
        opts.addWidget(self.btn_run_speed, 0, 1)
        opts.addWidget(self.btn_run_bufferbloat, 0, 2)
        opts.addWidget(self.btn_run_net_diag, 0, 3)
        hl.addLayout(opts)
        self.root.addWidget(hdr)

        # 2. 6-stage Test Workflow Stepper
        self.workflow_stepper = QualityWorkflowStepper()
        self.root.addWidget(self.workflow_stepper)

        # 3. Gauges & Separated Throughput Metrics (Wi-Fi PHY / LAN / WAN DL / WAN UL / Bufferbloat)
        gauges_panel = Panel(
            title="نتائج السرعة ومؤشر Bufferbloat / Throughput & Responsiveness",
            subtitle="تظهر القيم 'غير مُقاس بعد' حتى تبدأ الاختبار — ولا يُدمج معدل ربط الواي فاي PHY مع سرعة الإنترنت",
            padding=18,
        )
        g_row = QHBoxLayout()
        g_row.setSpacing(18)
        self.gauge_dl = CircularGauge(title="تنزيل WAN", unit="Mbps", size=128)
        self.gauge_ul = CircularGauge(title="رفع WAN", unit="Mbps", size=128)
        self.gauge_bloat = CircularGauge(title="درجة Bufferbloat", unit="", size=128, semicircular=True)
        for g in (self.gauge_dl, self.gauge_ul, self.gauge_bloat):
            g.set_value(None, subtitle=tr("iq.unmeasured"))
        g_row.addWidget(self.gauge_dl)
        g_row.addWidget(self.gauge_ul)
        g_row.addWidget(self.gauge_bloat)

        cards_grid = QGridLayout()
        cards_grid.setSpacing(10)
        unm = tr("iq.unmeasured")
        self.card_phy = self._metric_box("ربط الواي فاي (PHY)", "—", unm, tokens.ACCENT)
        self.card_lan = self._metric_box("الشبكة المحلية (LAN)", "غير متاح محلياً", unm, tokens.TEXT_MUTED)
        self.card_dl = self._metric_box("تنزيل WAN الفعلي", "— Mbps", unm, tokens.SECONDARY_CYAN)
        self.card_ul = self._metric_box("رفع WAN الفعلي", "— Mbps", unm, tokens.SECONDARY_PURPLE)
        self.card_idle_rtt = self._metric_box("الكمون بالخمول (Idle)", "— ms", unm, tokens.STATUS_OK)
        self.card_load_rtt = self._metric_box("الكمون تحت الحمل", "— ms", unm, tokens.STATUS_WARN)

        cards_grid.addWidget(self.card_phy[0], 0, 0)
        cards_grid.addWidget(self.card_lan[0], 0, 1)
        cards_grid.addWidget(self.card_dl[0], 1, 0)
        cards_grid.addWidget(self.card_ul[0], 1, 1)
        cards_grid.addWidget(self.card_idle_rtt[0], 2, 0)
        cards_grid.addWidget(self.card_load_rtt[0], 2, 1)
        g_row.addLayout(cards_grid, 1)
        gauges_panel.main_layout.addLayout(g_row)
        self.root.addWidget(gauges_panel)

        # 4. Loaded Latency Comparison + Sequential Diagnostics Table
        split_row = QGridLayout()
        split_row.setSpacing(14)

        p_cmp = Panel(
            title="مقارنة الكمون: الخمول مقابل التحميل والرفع",
            subtitle="يكشف تضخم الذاكرة الوسيطة (Bufferbloat) عند تشبع خط الاتصال",
            padding=16,
        )
        self.latency_cmp_chart = LoadedLatencyComparisonChart()
        p_cmp.main_layout.addWidget(self.latency_cmp_chart)
        self.lbl_bloat_summary = QLabel(tr("iq.unmeasured"))
        self.lbl_bloat_summary.setFont(tokens.get_sans_font(12, 400))
        self.lbl_bloat_summary.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_bloat_summary.setWordWrap(True)
        p_cmp.main_layout.addWidget(self.lbl_bloat_summary)

        p_hops = Panel(
            title="اختبار المسار والكمون (Ping & Traceroute)",
            subtitle="قياس البوابة المحلية، خادم DNS العام، والإنترنت الخارجي بالترتيب",
            padding=16,
        )
        self.table_hops = QTableWidget(0, 5)
        self.table_hops.setHorizontalHeaderLabels(["المرحلة / الوجهة", "العنوان", "المتوسط", "فقدان الحزم", "الحالة"])
        self.table_hops.verticalHeader().setVisible(False)
        self.table_hops.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_hops.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        p_hops.main_layout.addWidget(self.table_hops)

        split_row.addWidget(p_cmp, 0, 0)
        split_row.addWidget(p_hops, 0, 1)
        self.root.addLayout(split_row)

        language_manager().language_changed.connect(self.retranslate)

    @staticmethod
    def _metric_box(title: str, val: str, footer: str, accent: str) -> tuple[QFrame, QLabel, QLabel]:
        c = QFrame()
        c.setStyleSheet(
            f"background-color: {tokens.SURFACE_INSET}; border: 1px solid {tokens.LINE}; border-top: 3px solid {accent}; border-radius: 8px;"
        )
        l = QVBoxLayout(c)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(4)
        t = QLabel(title)
        t.setFont(tokens.get_sans_font(12, 500))
        t.setStyleSheet(f"color: {tokens.TEXT_MUTED}; border: none; background: transparent;")
        t.setWordWrap(True)
        v = QLabel(tokens.bidi_isolate(val))
        v.setFont(tokens.get_mono_font(15, 700))
        v.setStyleSheet(f"color: {tokens.TEXT}; border: none; background: transparent;")
        v.setWordWrap(True)
        f = QLabel(footer)
        f.setFont(tokens.get_sans_font(12, 400))
        f.setStyleSheet(f"color: {tokens.TEXT_MUTED}; border: none; background: transparent;")
        f.setWordWrap(True)
        l.addWidget(t)
        l.addWidget(v)
        l.addWidget(f)
        return c, v, f

    def retranslate(self) -> None:
        self.lbl_title.setText(tr("iq_title"))
        self.lbl_sub.setText(tr("iq_sub"))

    def _check_meeting_guard_safe(self) -> bool:
        if self.bundle and hasattr(self.bundle, "coordinator"):
            active, app_name = self.bundle.coordinator.is_meeting_active()
            if active:
                QMessageBox.warning(
                    self,
                    "Meeting Guard Protection",
                    f"لا يمكن تشغيل اختبار سرعة أو ضغط الشبكة أثناء مكالمة نشطة ({app_name}) لمنع تقطع الصوت/الصورة.",
                )
                return False
        return True

    def run_speed_test(self) -> None:
        if self.bundle is None or not self._check_meeting_guard_safe():
            return
        self.btn_run_speed.setEnabled(False)
        self.badge_status.set_status(tokens.SystemStatus.RUNNING, tr("status.running"))
        self.workflow_stepper.set_stage("preparing")
        run_ul = bool(self.chk_include_upload.isChecked())

        async def _work():
            return await self.bundle.speed_test.run_speed_test(run_upload=run_ul)

        def _done(rep: Any) -> None:
            self.btn_run_speed.setEnabled(True)
            self.workflow_stepper.set_stage("complete")
            self._render_speed_report(rep)
            self.speed_test_completed.emit(rep)

        def _err(err: str) -> None:
            self.btn_run_speed.setEnabled(True)
            self.badge_status.set_status(tokens.SystemStatus.FAILED, tr("status.failed"))
            self.lbl_bloat_summary.setText(tokens.bidi_isolate_mixed(err))

        self.bridge.run_coro(_work, _done, _err)

    def _render_speed_report(self, rep: Any) -> None:
        if rep is None:
            return
        dl = getattr(rep, "download_mbps", None)
        ul = getattr(rep, "upload_mbps", None)
        rx_phy = getattr(rep, "wifi_rx_link_rate_mbps", None)
        tx_phy = getattr(rep, "wifi_tx_link_rate_mbps", None)
        lan = getattr(rep, "local_lan_throughput_mbps", None)
        idle_ms = getattr(rep, "idle_latency_ms", None)
        load_dl = getattr(rep, "loaded_download_latency_ms", None)
        load_ul = getattr(rep, "loaded_upload_latency_ms", None)
        status = getattr(rep, "status", "completed")

        if status == "failed":
            self.badge_status.set_status(tokens.SystemStatus.FAILED, tr("status.failed"))
        else:
            self.badge_status.set_status(tokens.SystemStatus.HEALTHY, tr("status.healthy"))

        max_scale = max(100.0, float(dl or 0.0) * 1.25, float(ul or 0.0) * 1.25)
        self.gauge_dl.set_value(
            dl,
            max_value=max_scale,
            display_text=f"{dl:.1f}" if dl is not None else "—",
            subtitle=str(getattr(rep, "server_name", None) or "WAN"),
            color=tokens.SECONDARY_CYAN,
        )
        self.gauge_ul.set_value(
            ul,
            max_value=max_scale,
            display_text=f"{ul:.1f}" if ul is not None else "—",
            subtitle="WAN Upload" if ul is not None else tr("iq.unmeasured"),
            color=tokens.SECONDARY_PURPLE,
        )

        if rx_phy or tx_phy:
            self.card_phy[1].setText(tokens.bidi_isolate(f"{rx_phy or '—'} / {tx_phy or '—'} Mbps"))
            self.card_phy[2].setText(tokens.bidi_isolate_mixed(str(getattr(rep, "band", "Wi-Fi"))))
        if lan is not None:
            self.card_lan[1].setText(tokens.bidi_isolate(f"{lan:.1f} Mbps"))
            self.card_lan[2].setText("مقاس محلياً")
        else:
            self.card_lan[1].setText("غير متاح")
            self.card_lan[2].setText(str(getattr(rep, "local_lan_note", None) or "لا يوجد خادم LAN محلي"))

        if dl is not None:
            self.card_dl[1].setText(tokens.bidi_isolate(f"{dl:.1f} Mbps"))
            self.card_dl[2].setText(tokens.bidi_isolate(str(getattr(rep, "method_used", "HTTP"))))
        if ul is not None:
            self.card_ul[1].setText(tokens.bidi_isolate(f"{ul:.1f} Mbps"))
            self.card_ul[2].setText("اختبار رفع فعلي")
        if idle_ms is not None:
            self.card_idle_rtt[1].setText(tokens.bidi_isolate(f"{idle_ms:.1f} ms"))
            self.card_idle_rtt[2].setText("خط الأساس")
        load_peak = max([x for x in (load_dl, load_ul) if x is not None], default=None)
        if load_peak is not None:
            self.card_load_rtt[1].setText(tokens.bidi_isolate(f"{load_peak:.1f} ms"))
            self.card_load_rtt[2].setText("أقصى كمون تحت الحمل")

        self.latency_cmp_chart.set_latencies(idle_ms, load_dl, load_ul)

    def run_bufferbloat_test(self) -> None:
        if self.bundle is None or not self._check_meeting_guard_safe():
            return
        self.btn_run_bufferbloat.setEnabled(False)
        self.badge_status.set_status(tokens.SystemStatus.RUNNING, tr("status.running"))
        self.workflow_stepper.set_stage("loaded")

        async def _work():
            return await self.bundle.bufferbloat.run_bufferbloat_test(include_upload=True)

        def _done(rep: Any) -> None:
            self.btn_run_bufferbloat.setEnabled(True)
            self.workflow_stepper.set_stage("complete")
            grade = str(getattr(rep, "overall_grade", "—"))
            grade_map = {"A+": 98, "A": 90, "B": 76, "C": 58, "D": 38, "F": 18}
            score = grade_map.get(grade, None)
            col = tokens.STATUS_OK if grade in ("A+", "A", "B") else (tokens.STATUS_WARN if grade == "C" else tokens.STATUS_BAD)
            self.gauge_bloat.set_value(score, display_text=grade, subtitle="Bufferbloat", color=col)
            idle_p = getattr(rep, "idle_phase", None)
            dl_p = getattr(rep, "download_phase", None)
            ul_p = getattr(rep, "upload_phase", None)
            idle_v = getattr(idle_p, "avg_ms", None)
            dl_v = getattr(dl_p, "avg_ms", None)
            ul_v = getattr(ul_p, "avg_ms", None)
            self.latency_cmp_chart.set_latencies(idle_v, dl_v, ul_v)
            if idle_v is not None:
                self.card_idle_rtt[1].setText(tokens.bidi_isolate(f"{idle_v:.1f} ms"))
            peak_loaded = max([x for x in (dl_v, ul_v) if x is not None], default=None)
            if peak_loaded is not None:
                self.card_load_rtt[1].setText(tokens.bidi_isolate(f"{peak_loaded:.1f} ms"))
            self.lbl_bloat_summary.setText(tokens.bidi_isolate_mixed(str(getattr(rep, "summary", ""))))
            self.badge_status.set_status(tokens.SystemStatus.HEALTHY, tr("status.healthy"))

        def _err(err: str) -> None:
            self.btn_run_bufferbloat.setEnabled(True)
            self.badge_status.set_status(tokens.SystemStatus.FAILED, tr("status.failed"))
            self.lbl_bloat_summary.setText(tokens.bidi_isolate_mixed(err))

        self.bridge.run_coro(_work, _done, _err)

    def run_network_sequence(self) -> None:
        if self.bundle is None:
            return
        self.btn_run_net_diag.setEnabled(False)
        self.workflow_stepper.set_stage("idle")

        async def _work():
            return await self.bundle.network_diag.run_sequence()

        def _done(rep: Any) -> None:
            self.btn_run_net_diag.setEnabled(True)
            self.workflow_stepper.set_stage("complete")
            rows: List[tuple[str, str, str, str, str]] = []
            for label, key in (
                ("البوابة المحلية / Gateway", "gateway_ping"),
                ("الإنترنت الخارجي / Internet", "internet_ping"),
                ("IPv6 Probe", "ipv6_ping"),
            ):
                p = getattr(rep, key, None)
                if p:
                    rows.append(
                        (
                            label,
                            str(getattr(p, "target", "—")),
                            f"{getattr(p, 'avg_ms', 0):.1f} ms" if getattr(p, "avg_ms", None) is not None else "—",
                            f"{getattr(p, 'loss_pct', 0):.1f}%",
                            "OK" if getattr(p, "reachable", False) else "Unreachable",
                        )
                    )
            for h in (getattr(rep, "traceroute", []) or [])[:10]:
                rows.append(
                    (
                        f"Hop {getattr(h, 'hop', '?')}",
                        str(getattr(h, "ip", None) or getattr(h, "hostname", "*")),
                        f"{getattr(h, 'rtt_ms', 0):.1f} ms" if getattr(h, "rtt_ms", None) is not None else "—",
                        "—",
                        "Timed out" if getattr(h, "timed_out", False) else "Reached",
                    )
                )
            self.table_hops.setRowCount(len(rows))
            for r, vals in enumerate(rows):
                for c, v in enumerate(vals):
                    self.table_hops.setItem(r, c, QTableWidgetItem(tokens.bidi_isolate_mixed(v)))
            fit_table_to_content(self.table_hops)

        def _err(err: str) -> None:
            self.btn_run_net_diag.setEnabled(True)
            self.lbl_bloat_summary.setText(tokens.bidi_isolate_mixed(err))

        self.bridge.run_coro(_work, _done, _err)

    def _sync_content_width(self) -> None:
        vw = self.viewport().width()
        if vw > 0:
            self.content_holder.setFixedWidth(min(vw, tokens.MAX_CONTENT_WIDTH))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_content_width()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_content_width()

    def shutdown(self) -> None:
        self.bridge.shutdown()
