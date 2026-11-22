"""Predictive Network Diagnostics & Root-Cause Isolation Widget for NetGuard AI.

Provides comprehensive visual representation of:
- Mathematical Network Health Score (0-100)
- Connection Stability Index (0-100%)
- Predicted Fault Probability (%) with derivative-based trend sensitivity
- Differential Root-Cause Source Isolation across 6 stations:
  (Local PC, Wi-Fi / Link, Home Gateway, ISP Hop 2, DNS Resolvers, Cloud / Global WAN)
- Automated Preventive Action Suggestions

Adheres strictly to NetGuard AI's design tokens and dark warm-neutral graphite theme.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any, Tuple
from collections import deque
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

from app.ui import tokens
from app.ui.widgets.chip import Chip
from app.ui.widgets.base_panel import Panel


class MetricKpiCard(QFrame):
    """Compact KPI metric display card with value, label, and status chip."""

    def __init__(
        self,
        title: str,
        initial_value: str = "—",
        unit: str = "",
        subtitle: str = "",
        chip_text: str = "جاهز",
        chip_variant: str = "neutral",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("MetricKpiCard")
        self.setStyleSheet(f"""
            QFrame#MetricKpiCard {{
                background-color: {tokens.SURFACE_INSET};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_INNER}px;
                padding: 14px 16px;
            }}
            QFrame#MetricKpiCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        top_h = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(tokens.get_sans_font(13, 500))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        top_h.addWidget(self.lbl_title)
        top_h.addStretch()

        self.chip = Chip(chip_text, variant=chip_variant)
        top_h.addWidget(self.chip)
        layout.addLayout(top_h)

        val_h = QHBoxLayout()
        val_h.setSpacing(4)
        self.lbl_val = QLabel(initial_value)
        self.lbl_val.setFont(tokens.get_mono_font(26, 700))
        self.lbl_val.setStyleSheet(f"color: {tokens.TEXT};")
        val_h.addWidget(self.lbl_val)

        if unit:
            self.lbl_unit = QLabel(unit)
            self.lbl_unit.setFont(tokens.get_sans_font(14, 500))
            self.lbl_unit.setStyleSheet(f"color: {tokens.TEXT_MUTED}; margin-bottom: 2px;")
            val_h.addWidget(self.lbl_unit, alignment=Qt.AlignBottom)
        else:
            self.lbl_unit = None

        val_h.addStretch()
        layout.addLayout(val_h)

        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setFont(tokens.get_sans_font(12, 400))
        self.lbl_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_sub.setWordWrap(True)
        layout.addWidget(self.lbl_sub)

    def set_value(
        self,
        val: str,
        color: Optional[str] = None,
        chip_txt: Optional[str] = None,
        chip_var: Optional[str] = None,
        sub_txt: Optional[str] = None,
    ) -> None:
        self.lbl_val.setText(val)
        if color:
            self.lbl_val.setStyleSheet(f"color: {color};")
        if chip_txt and chip_var:
            self.chip.set_variant(chip_var, chip_txt)
        if sub_txt is not None:
            self.lbl_sub.setText(sub_txt)


class RootCauseStationItem(QFrame):
    """Individual station in the differential root cause isolation matrix."""

    def __init__(
        self,
        station_id: str,
        station_name: str,
        status: str = "سليم",
        details: str = "الاتصال ضمن الحدود الطبيعية",
        variant: str = "ok-soft",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("RootCauseStationItem")
        self.setMinimumHeight(116)
        self.setStyleSheet(f"""
            QFrame#RootCauseStationItem {{
                background-color: {tokens.SURFACE_INSET};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_INNER}px;
                padding: 10px 12px;
            }}
            QFrame#RootCauseStationItem QLabel {{
                background: transparent;
                border: none;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header row: Station ID badge + Status Chip (Leaves full row below for title)
        top_h = QHBoxLayout()
        top_h.setSpacing(8)

        lbl_id = QLabel(f"محطة {station_id}")
        lbl_id.setFont(tokens.get_mono_font(11, 600))
        lbl_id.setStyleSheet(f"color: {tokens.TEXT_MUTED}; background: {tokens.SURFACE}; padding: 2px 7px; border-radius: 4px; border: 1px solid {tokens.LINE};")
        top_h.addWidget(lbl_id)

        top_h.addStretch()

        self.chip = Chip(status, variant=variant)
        top_h.addWidget(self.chip)
        layout.addLayout(top_h)

        # Full-width Station Title: never truncated or squished
        self.lbl_name = QLabel(station_name)
        self.lbl_name.setFont(tokens.get_sans_font(13, 600))
        self.lbl_name.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_name.setWordWrap(True)
        layout.addWidget(self.lbl_name)

        # Station Details / Metric text with ample breathing room
        self.lbl_desc = QLabel(details)
        self.lbl_desc.setFont(tokens.get_sans_font(12, 400))
        self.lbl_desc.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_desc.setWordWrap(True)
        layout.addWidget(self.lbl_desc)
        layout.addStretch()

    def set_station_state(self, status: str, variant: str, details: str) -> None:
        self.chip.set_variant(variant, status)
        self.lbl_desc.setText(details)
        if variant == "bad-soft":
            self.setStyleSheet(f"""
                QFrame#RootCauseStationItem {{
                    background-color: rgba(220, 38, 38, 0.08);
                    border: 1px solid {tokens.STATUS_BAD};
                    border-radius: {tokens.RADIUS_INNER}px;
                    padding: 10px 12px;
                }}
            """)
        elif variant == "tag-warn":
            self.setStyleSheet(f"""
                QFrame#RootCauseStationItem {{
                    background-color: rgba(234, 179, 8, 0.08);
                    border: 1px solid {tokens.STATUS_WARN};
                    border-radius: {tokens.RADIUS_INNER}px;
                    padding: 10px 12px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#RootCauseStationItem {{
                    background-color: {tokens.SURFACE_INSET};
                    border: 1px solid {tokens.LINE};
                    border-radius: {tokens.RADIUS_INNER}px;
                    padding: 10px 12px;
                }}
            """)


class PredictiveDiagnosticsPanel(Panel):
    """Interactive Predictive Network Diagnostics & Root Cause Analysis Panel."""

    def __init__(self, parent=None) -> None:
        super().__init__(
            title="التشخيص التنبؤي وعزل مصدر الأعطال (Predictive Fault Analysis)",
            subtitle="خوارزمية ذكية لمراقبة الاتجاهات والتنبؤ المبكر بالأعطال وعزل السبب الجذري",
            parent=parent,
        )
        self.setObjectName("PredictiveDiagnosticsPanel")

        # Rolling history for derivative trend calculations
        self._lat_history = deque(maxlen=12)
        self._loss_history = deque(maxlen=12)
        self._jitter_history = deque(maxlen=12)

        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 4, 0, 4)
        container_layout.setSpacing(16)

        # -------------------------------------------------------------
        # 1. Row of 3 KPI Cards
        # -------------------------------------------------------------
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)

        self.kpi_health = MetricKpiCard(
            title="مؤشر صحة الشبكة الشامل",
            initial_value="100",
            unit="/ 100",
            subtitle="حساب رياضي لجميع أزمنة الاستجابة ومعدل فقدان الحزم",
            chip_text="ممتاز",
            chip_variant="ok-soft",
            parent=self,
        )
        kpi_row.addWidget(self.kpi_health)

        self.kpi_stability = MetricKpiCard(
            title="معامل استقرار الاتصال",
            initial_value="98.5",
            unit="%",
            subtitle="انسيابية حركة الحزم وخلو المسار من التذبذب الحاد",
            chip_text="مستقر",
            chip_variant="ok-soft",
            parent=self,
        )
        kpi_row.addWidget(self.kpi_stability)

        self.kpi_fault_risk = MetricKpiCard(
            title="احتمالية حدوث خلل (15 دقيقة)",
            initial_value="3",
            unit="%",
            subtitle="تحليل المشتقة الأولى لاتجاهات التأخير وفقدان الحزم",
            chip_text="منخفض",
            chip_variant="ok-soft",
            parent=self,
        )
        kpi_row.addWidget(self.kpi_fault_risk)

        container_layout.addLayout(kpi_row)

        # -------------------------------------------------------------
        # 2. Differential Root-Cause Isolation Grid (6 Stations)
        # -------------------------------------------------------------
        iso_box = QFrame()
        iso_box.setObjectName("IsolationBox")
        iso_box.setStyleSheet(f"""
            QFrame#IsolationBox {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_INNER}px;
                padding: 14px;
            }}
            QFrame#IsolationBox QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        iso_layout = QVBoxLayout(iso_box)
        iso_layout.setContentsMargins(12, 10, 12, 10)
        iso_layout.setSpacing(10)

        iso_header = QHBoxLayout()
        lbl_iso_title = QLabel("عزل السبب الجذري وتحديد مصدر العطل بدقة")
        lbl_iso_title.setFont(tokens.get_sans_font(14, 600))
        lbl_iso_title.setStyleSheet(f"color: {tokens.TEXT};")
        iso_header.addWidget(lbl_iso_title)

        iso_header.addStretch()

        self.chip_isolated_verdict = Chip("كافة المحطات تعمل بانتظام", variant="ok-soft")
        iso_header.addWidget(self.chip_isolated_verdict)
        iso_layout.addLayout(iso_header)

        grid = QGridLayout()
        grid.setSpacing(10)

        self.st_local = RootCauseStationItem("S1", "جهاز الكمبيوتر وبطاقة الشبكة", "سليم", "بروتوكول TCP/IP وبطاقة الشبكة مستقرة", "ok-soft", self)
        self.st_wifi = RootCauseStationItem("S2", "الربط اللاسلكي والواي فاي", "سليم", "قوة الإشارة والتوصيل اللاسلكي مستقر", "ok-soft", self)
        self.st_gateway = RootCauseStationItem("S3", "بوابة الراوتر المنزلي", "سليم", "زمن الاستجابة للراوتر فوري ومنتظم", "ok-soft", self)
        self.st_isp = RootCauseStationItem("S4", "بنية مزود الخدمة وكابينة الألياف", "سليم", "مسار كابل الألياف ومقسم المزود متصل", "ok-soft", self)
        self.st_dns = RootCauseStationItem("S5", "خوادم ترجمة العناوين والنطاقات", "سليم", "استجابة استعلامات DNS فورية وسريعة", "ok-soft", self)
        self.st_cloud = RootCauseStationItem("S6", "الشبكات السحابية والإنترنت العالمي", "سليم", "الاتصال بالخوادم العالمية خالي من الفقد", "ok-soft", self)

        grid.addWidget(self.st_local, 0, 0)
        grid.addWidget(self.st_wifi, 0, 1)
        grid.addWidget(self.st_gateway, 0, 2)
        grid.addWidget(self.st_isp, 1, 0)
        grid.addWidget(self.st_dns, 1, 1)
        grid.addWidget(self.st_cloud, 1, 2)

        iso_layout.addLayout(grid)
        container_layout.addWidget(iso_box)

        # -------------------------------------------------------------
        # 3. Preventive Action Box
        # -------------------------------------------------------------
        self.action_box = QFrame()
        self.action_box.setObjectName("PreventiveActionBox")
        self.action_box.setStyleSheet(f"""
            QFrame#PreventiveActionBox {{
                background-color: {tokens.SURFACE_INSET};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_INNER}px;
                padding: 12px 16px;
            }}
            QFrame#PreventiveActionBox QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        action_layout = QHBoxLayout(self.action_box)
        action_layout.setContentsMargins(14, 10, 14, 10)
        action_layout.setSpacing(12)

        lbl_icon = QLabel("💡")
        lbl_icon.setFont(tokens.get_sans_font(18, 400))
        action_layout.addWidget(lbl_icon)

        v_act = QVBoxLayout()
        v_act.setSpacing(2)
        self.lbl_act_title = QLabel("التوصية الوقائية الذكية:")
        self.lbl_act_title.setFont(tokens.get_sans_font(13, 600))
        self.lbl_act_title.setStyleSheet(f"color: {tokens.TEXT};")
        v_act.addWidget(self.lbl_act_title)

        self.lbl_act_text = QLabel("كافة مؤشرات الشبكة تعمل بأداء مثالي. لا يتطلب النظام أي تدخل وقائي حالياً.")
        self.lbl_act_text.setFont(tokens.get_sans_font(12, 400))
        self.lbl_act_text.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_act_text.setWordWrap(True)
        v_act.addWidget(self.lbl_act_text)
        action_layout.addLayout(v_act, stretch=1)

        container_layout.addWidget(self.action_box)
        self.main_layout.addLayout(container_layout)

    def update_predictive_state(
        self,
        gw_lat: Optional[float] = None,
        ext_lat: Optional[float] = None,
        jitter_ms: Optional[float] = None,
        packet_loss_pct: Optional[float] = None,
        wifi_signal_pct: Optional[float] = None,
        dns_lat: Optional[float] = None,
        local_ip: Optional[str] = None,
        hop2_reachable: bool = True,
    ) -> None:
        """Update predictive health, stability, fault probability, and isolated root cause."""
        # Defaults for missing telemetry
        g_lat = gw_lat if (gw_lat is not None and gw_lat >= 0) else 5.0
        e_lat = ext_lat if (ext_lat is not None and ext_lat >= 0) else 45.0
        jit = jitter_ms if (jitter_ms is not None and jitter_ms >= 0) else 3.0
        loss = packet_loss_pct if (packet_loss_pct is not None and packet_loss_pct >= 0) else 0.0
        sig = wifi_signal_pct if (wifi_signal_pct is not None and wifi_signal_pct > 0) else 80.0
        d_lat = dns_lat if (dns_lat is not None and dns_lat > 0) else 25.0

        # Append to rolling history
        self._lat_history.append(e_lat)
        self._loss_history.append(loss)
        self._jitter_history.append(jit)

        # 1. Health Score Calculation (0 - 100)
        # Gateway factor (20%): penalty if > 25ms
        gw_pen = min(20.0, max(0.0, (g_lat - 15.0) * 0.8))
        # External latency factor (25%): penalty if > 80ms
        ext_pen = min(25.0, max(0.0, (e_lat - 70.0) * 0.35))
        # Packet loss factor (30%): severe penalty
        loss_pen = min(30.0, loss * 6.0)
        # Jitter factor (15%): penalty if > 15ms
        jit_pen = min(15.0, max(0.0, (jit - 10.0) * 1.0))
        # DNS factor (10%): penalty if > 85ms
        dns_pen = min(10.0, max(0.0, (d_lat - 70.0) * 0.15))

        total_penalty = gw_pen + ext_pen + loss_pen + jit_pen + dns_pen
        health_score = max(5.0, min(100.0, 100.0 - total_penalty))

        # 2. Stability Index Calculation (0 - 100%)
        # Based on variance in latency and jitter
        if len(self._lat_history) >= 2:
            lat_diffs = [abs(self._lat_history[i] - self._lat_history[i-1]) for i in range(1, len(self._lat_history))]
            avg_diff = sum(lat_diffs) / len(lat_diffs)
            stability = max(20.0, min(100.0, 100.0 - (avg_diff * 1.5) - (jit * 1.2) - (loss * 8.0)))
        else:
            stability = max(20.0, min(100.0, 100.0 - (jit * 1.5) - (loss * 10.0)))

        # 3. Fault Probability Calculation (0 - 100%)
        # Derivative: check if latency is trending upwards
        derivative_risk = 0.0
        if len(self._lat_history) >= 4:
            recent_delta = self._lat_history[-1] - self._lat_history[0]
            if recent_delta > 10.0:
                derivative_risk += min(35.0, recent_delta * 1.5)
        if loss > 0.5:
            derivative_risk += min(45.0, loss * 12.0)
        if g_lat > 40.0:
            derivative_risk += 20.0

        fault_risk = max(1.0, min(95.0, 4.0 + derivative_risk))

        # Update KPI UI
        # Health
        h_col = tokens.STATUS_OK if health_score >= 85 else (tokens.STATUS_WARN if health_score >= 60 else tokens.STATUS_BAD)
        h_chip = "ممتاز" if health_score >= 85 else ("مقبول" if health_score >= 60 else "حرج")
        h_var = "ok-soft" if health_score >= 85 else ("tag-warn" if health_score >= 60 else "bad-soft")
        self.kpi_health.set_value(f"{health_score:.0f}", color=h_col, chip_txt=h_chip, chip_var=h_var)

        # Stability
        s_col = tokens.STATUS_OK if stability >= 85 else (tokens.STATUS_WARN if stability >= 65 else tokens.STATUS_BAD)
        s_chip = "مستقر جداً" if stability >= 85 else ("متذبذب" if stability >= 65 else "غير مستقر")
        s_var = "ok-soft" if stability >= 85 else ("tag-warn" if stability >= 65 else "bad-soft")
        self.kpi_stability.set_value(f"{stability:.1f}", color=s_col, chip_txt=s_chip, chip_var=s_var)

        # Fault Risk
        r_col = tokens.STATUS_OK if fault_risk < 15 else (tokens.STATUS_WARN if fault_risk < 45 else tokens.STATUS_BAD)
        r_chip = "منخفض" if fault_risk < 15 else ("متوسط" if fault_risk < 45 else "مرتفع!")
        r_var = "ok-soft" if fault_risk < 15 else ("tag-warn" if fault_risk < 45 else "bad-soft")
        self.kpi_fault_risk.set_value(f"{fault_risk:.0f}", color=r_col, chip_txt=r_chip, chip_var=r_var)

        # 4. Differential Root-Cause Isolation
        isolated_station = None
        recommendation = "كافة مؤشرات الشبكة تعمل بأداء مثالي. لا يتطلب النظام أي تدخل وقائي حالياً."

        # S1: Local PC
        if local_ip is not None and (local_ip.startswith("127.") or local_ip == "—"):
            self.st_local.set_station_state("خلل معزول", "bad-soft", "محول الشبكة غير قادر على الحصول على عنوان IP")
            isolated_station = "جهاز الكمبيوتر"
            recommendation = "أعد تشغيل محول الشبكة وافحص تعريفات كرت الشبكة."
        else:
            self.st_local.set_station_state("سليم", "ok-soft", "بروتوكول TCP/IP وبطاقة الشبكة مستقرة")

        # S2: Wi-Fi Link
        if sig < 40.0:
            st = "خلل معزول" if g_lat > 40.0 else "إشارة ضعيفة"
            var = "bad-soft" if g_lat > 40.0 else "tag-warn"
            self.st_wifi.set_station_state(st, var, f"قوة الإشارة {sig:.0f}% مع تشويش محتمل في القناة اللاسلكية")
            if not isolated_station and g_lat > 40.0:
                isolated_station = "الربط اللاسلكي"
                recommendation = "اقترب من الراوتر أو قم بالتحويل إلى تردد 5GHz لتجنب تداخل الإشارة."
        else:
            self.st_wifi.set_station_state("سليم", "ok-soft", f"قوة الإشارة {sig:.0f}% والتوصيل اللاسلكي مستقر")

        # S3: Gateway
        if g_lat > 50.0:
            self.st_gateway.set_station_state("خلل معزول", "bad-soft", f"تأخر ملحوظ في استجابة الراوتر: {g_lat:.1f} ms")
            if not isolated_station:
                isolated_station = "بوابة الراوتر"
                recommendation = "أعد تشغيل الراوتر المنزلي لتفريغ الذاكرة المؤقتة وحل الاختناق الداخلي."
        elif g_lat > 25.0:
            self.st_gateway.set_station_state("يحتاج متابعة", "tag-warn", f"استجابة مقبولة للراوتر: {g_lat:.1f} ms")
        else:
            self.st_gateway.set_station_state("سليم", "ok-soft", f"استجابة الراوتر فورية وممتازة: {g_lat:.1f} ms")

        # S4: ISP Hop 2
        if not hop2_reachable or (g_lat < 20.0 and e_lat > 140.0):
            self.st_isp.set_station_state("خلل معزول", "bad-soft", "تأخر أو انقطاع في بنية مقسم مزود الخدمة")
            if not isolated_station:
                isolated_station = "مزود الخدمة (ISP)"
                recommendation = "يوجد ضغط أو صيانة في كابينة مزود الخدمة الخارجي، يفضل التواصل مع الدعم الفني للمزود."
        else:
            self.st_isp.set_station_state("سليم", "ok-soft", "مسار كابل الألياف متصل بسلاسة دون اختناق")

        # S5: DNS
        if d_lat > 160.0:
            self.st_dns.set_station_state("خلل معزول", "bad-soft", f"خادم DNS بطيء: {d_lat:.0f} ms")
            if not isolated_station:
                isolated_station = "خوادم ترجمة العناوين (DNS)"
                recommendation = "بدّل إلى خادم DNS أسرع (مثل Cloudflare أو Google) وتفريغ الكاش لتحسين سرعة التصفح."
        elif d_lat > 90.0:
            self.st_dns.set_station_state("بطيء نسبياً", "tag-warn", f"استجابة DNS مقبولة: {d_lat:.0f} ms")
            if not isolated_station and fault_risk > 20:
                recommendation = "ينصح بتبديل خادم DNS الحالي بخادم استجابة أسرع."
        else:
            self.st_dns.set_station_state("سليم", "ok-soft", f"استجابة خوادم DNS فورية: {d_lat:.0f} ms")

        # S6: Cloud / WAN
        if loss > 2.0 or (g_lat < 20.0 and e_lat > 180.0):
            self.st_cloud.set_station_state("خلل معزول", "bad-soft", f"فقدان {loss:.1f}% أو تأخر مع الخوادم السحابية")
            if not isolated_station:
                isolated_station = "الشبكات السحابية العالمية"
                recommendation = "يوجد مسار بطيء عبر الكابلات البحرية أو الخوادم الدولية."
        else:
            self.st_cloud.set_station_state("سليم", "ok-soft", "الاتصال بالخوادم العالمية خالي من الفقدان")

        # Update Overall Isolation Chip
        if isolated_station:
            self.chip_isolated_verdict.set_variant("bad-soft", f"مصدر الخلل المعزول: {isolated_station}")
        elif fault_risk > 30:
            self.chip_isolated_verdict.set_variant("tag-warn", "انحراف طفيف تحت المراقبة")
        else:
            self.chip_isolated_verdict.set_variant("ok-soft", "كافة المحطات تعمل بانتظام")

        self.lbl_act_text.setText(recommendation)

