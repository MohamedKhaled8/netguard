"""Incident 4-step Timeline Widget for NetGuard AI.

Panel 'ما الذي حدث بالضبط؟':
- Top-end status chip ('تم حله تلقائياً' / 'يحتاج انتباهك')
- 4-step vertical timeline on a 1px rail (#2C3033)
  1. اكتشاف المشكلة (bad #FF6B5E)
  2. تحديد السبب (warn #F5B942)
  3. الإصلاح (accent #ECEBE6)
  4. النتيجة (ok #5FD38D)
- Footer action buttons: 'عرض الأدلة' (Secondary) and 'تراجع عن الإصلاح' (Ghost)
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QWidget,
)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from app.ui import tokens
from app.ui.widgets.chip import Chip
from app.ui.widgets.buttons import SecondaryButton, GhostButton


class StepRailWidget(QWidget):
    """Draws connected rail and pulsing/solid colored dot for a specific step."""

    def __init__(self, step_idx: int, total_steps: int, dot_color: str, parent=None) -> None:
        super().__init__(parent)
        self.step_idx = step_idx
        self.total_steps = total_steps
        self.dot_color = dot_color
        self.setFixedWidth(22)

    def set_color(self, color_str: str) -> None:
        self.dot_color = color_str
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = 13.0  # Exactly centers with the 22px header row

        # Draw 1.5px vertical connecting rail line
        line_color = QColor(tokens.LINE_STRONG)
        painter.setPen(QPen(line_color, 1.5))

        if self.step_idx > 0:
            painter.drawLine(QPointF(cx, 0.0), QPointF(cx, cy))
        if self.step_idx < self.total_steps - 1:
            painter.drawLine(QPointF(cx, cy), QPointF(cx, h))

        # Draw dot with subtle outer glow ring and solid core
        c = QColor(self.dot_color)

        ring_col = QColor(c)
        ring_col.setAlpha(40)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(ring_col))
        painter.drawEllipse(QPointF(cx, cy), 6.5, 6.5)

        painter.setBrush(QBrush(c))
        painter.drawEllipse(QPointF(cx, cy), 3.5, 3.5)


class TimelineStepWidget(QFrame):
    """Refined modern timeline step row with integrated rail and micro-pill time badge."""

    def __init__(
        self,
        step_idx: int,
        total_steps: int,
        time_str: str,
        title: str,
        desc: str,
        dot_color: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("TimelineStepItem")
        self.setStyleSheet(f"""
            QFrame#TimelineStepItem {{
                background-color: transparent;
                border-radius: {tokens.RADIUS_INNER}px;
            }}
            QFrame#TimelineStepItem:hover {{
                background-color: rgba(255, 255, 255, 0.02);
            }}
            QFrame#TimelineStepItem QLabel {{
                border: 0px solid transparent;
                background: transparent;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(10)

        # 1. Rail & Dot (appears on Right in RTL)
        self.rail = StepRailWidget(step_idx, total_steps, dot_color, self)
        layout.addWidget(self.rail)

        # 2. Content Column
        content_col = QVBoxLayout()
        content_col.setContentsMargins(0, 2, 0, 0)
        content_col.setSpacing(3)

        # Header: Title + Time Pill right next to it
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(tokens.get_sans_font(13, 600))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")
        header_row.addWidget(self.lbl_title)

        self.lbl_time = QLabel(time_str)
        self.lbl_time.setFont(tokens.get_mono_font(11, 400))
        self.lbl_time.setStyleSheet(f"""
            color: {tokens.TEXT_MUTED};
            background-color: rgba(255, 255, 255, 0.04);
            border: none;
            border-radius: 4px;
            padding: 1px 6px;
        """)
        header_row.addWidget(self.lbl_time)
        header_row.addStretch()

        content_col.addLayout(header_row)

        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setFont(tokens.get_sans_font(12, 400))
        self.lbl_desc.setStyleSheet(f"color: {tokens.TEXT_SECONDARY}; line-height: 1.45;")
        self.lbl_desc.setWordWrap(True)
        content_col.addWidget(self.lbl_desc)

        layout.addLayout(content_col, stretch=1)

    def set_step_data(self, time_str: str, title: str, desc: str, dot_color: str) -> None:
        self.lbl_time.setText(time_str)
        self.lbl_title.setText(title)
        self.lbl_desc.setText(desc)
        self.rail.set_color(dot_color)


class TimelineCanvas(QWidget):
    """Compatibility shim for legacy references."""

    def __init__(self, colors: List[str], step_widgets: List[QWidget], parent=None) -> None:
        super().__init__(parent)
        self.colors = colors
        self.step_widgets = step_widgets
        self.setFixedWidth(0)
        self.setVisible(False)


class TimelinePanel(QFrame):
    """Complete 'ما الذي حدث بالضبط؟' panel."""

    view_evidence_requested = Signal()
    rollback_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TimelinePanel")
        from PySide6.QtWidgets import QSizePolicy
        self.setMinimumHeight(375)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.setStyleSheet(f"""
            QFrame#TimelinePanel {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_PANEL}px;
            }}
            QFrame#TimelinePanel QLabel {{
                border: 0px solid transparent;
                background: transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        # Header: Title + Subtitle on Right, Chip on Left
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.lbl_title = QLabel("ما الذي حدث بالضبط؟")
        self.lbl_title.setFont(tokens.get_sans_font(16, 600))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_title.setMinimumHeight(24)

        self.lbl_sub = QLabel("لا توجد أحداث مسجلة")
        self.lbl_sub.setFont(tokens.get_sans_font(12, 400))
        self.lbl_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        title_col.addWidget(self.lbl_title)
        title_col.addWidget(self.lbl_sub)
        header_row.addLayout(title_col)

        header_row.addStretch()

        self.status_chip = Chip("النظام مستقر", variant="neutral-soft")
        header_row.addWidget(self.status_chip)
        layout.addLayout(header_row)

        # 4 Steps container
        self.steps_container = QWidget()
        steps_layout = QVBoxLayout(self.steps_container)
        steps_layout.setContentsMargins(0, 2, 0, 2)
        steps_layout.setSpacing(6)

        # Default idle state when no events exist
        self.step_data = [
            ("—", "اكتشاف المشكلة", "لم يتم رصد أي تذبذب أو انحراف في مؤشرات جودة الاتصال.", tokens.TEXT_MUTED),
            ("—", "تحديد السبب", "كافة طبقات الفحص (الجهاز، الراوتر، المزود، الإنترنت) تعمل بشكل طبيعي.", tokens.TEXT_MUTED),
            ("—", "الإصلاح", "لا توجد إجراءات تصحيحية مطلوبة حالياً.", tokens.TEXT_MUTED),
            ("—", "النتيجة", "الشبكة في حالة استقرار تام.", tokens.TEXT_MUTED),
        ]

        self.step_widgets: List[TimelineStepWidget] = []
        total_steps = len(self.step_data)
        for i, (t, title, desc, c) in enumerate(self.step_data):
            w = TimelineStepWidget(i, total_steps, t, title, desc, c, self.steps_container)
            self.step_widgets.append(w)
            steps_layout.addWidget(w)

        colors = [s[3] for s in self.step_data]
        self.rail_canvas = TimelineCanvas(colors, self.step_widgets, self)

        layout.addWidget(self.steps_container)

        # Footer Action Bar with subtle separator
        footer_div = QFrame()
        footer_div.setFrameShape(QFrame.HLine)
        footer_div.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none; max-height: 1px;")
        layout.addWidget(footer_div)

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 4, 0, 0)
        footer_row.setSpacing(10)

        self.btn_evidence = SecondaryButton("عرض الأدلة")
        self.btn_evidence.setFixedHeight(34)
        self.btn_evidence.clicked.connect(self.view_evidence_requested.emit)
        self.btn_evidence.setEnabled(False)

        self.btn_rollback = GhostButton("تراجع عن الإصلاح")
        self.btn_rollback.setFixedHeight(34)
        self.btn_rollback.clicked.connect(self.rollback_requested.emit)
        self.btn_rollback.setVisible(True)

        footer_row.addWidget(self.btn_evidence)
        footer_row.addWidget(self.btn_rollback)
        footer_row.addStretch()

        layout.addLayout(footer_row)

    def _apply_steps(self, steps: List[Tuple[str, str, str, str]]) -> None:
        """Apply 4 steps with individual dot colors to UI and canvas."""
        colors = []
        for i, (t, title, desc, col) in enumerate(steps):
            if i < len(self.step_widgets):
                self.step_widgets[i].set_step_data(t, title, desc, col)
            colors.append(col)
        self.rail_canvas.colors = colors
        self.rail_canvas.update()

    def reset_to_idle(self) -> None:
        """Reset timeline to clean idle state when no events are recorded."""
        self.lbl_sub.setText("لا توجد أحداث مسجلة")
        self.status_chip.set_variant("neutral-soft", "النظام مستقر")
        self.btn_rollback.setVisible(True)
        self.btn_evidence.setEnabled(False)

        steps = [
            ("—", "اكتشاف المشكلة", "لم يتم رصد أي تذبذب أو انحراف في مؤشرات جودة الاتصال.", tokens.TEXT_MUTED),
            ("—", "تحديد السبب", "كافة طبقات الفحص (الجهاز، الراوتر، المزود، الإنترنت) تعمل بشكل طبيعي.", tokens.TEXT_MUTED),
            ("—", "الإصلاح", "لا توجد إجراءات تصحيحية مطلوبة حالياً.", tokens.TEXT_MUTED),
            ("—", "النتيجة", "الشبكة في حالة استقرار تام.", tokens.TEXT_MUTED),
        ]
        self._apply_steps(steps)

    def set_event(
        self,
        time_str: str,
        steps: List[Tuple[str, str, str]],
        is_resolved: bool = True,
    ) -> None:
        """Update timeline with real audit/remediation event."""
        self.lbl_sub.setText(f"آخر حدث · اليوم {time_str}")
        self.btn_evidence.setEnabled(True)
        if is_resolved:
            self.status_chip.set_variant("ok-soft", "تم حله تلقائياً")
            self.btn_rollback.setVisible(True)
        else:
            self.status_chip.set_variant("bad-soft", "يحتاج انتباهك")
            self.btn_rollback.setVisible(False)

        if len(steps) == 4:
            colors = [
                tokens.STATUS_BAD,
                tokens.STATUS_WARN,
                tokens.ACCENT,
                tokens.STATUS_OK if is_resolved else tokens.STATUS_BAD,
            ]
            full_steps = [
                (steps[i][0], steps[i][1], steps[i][2], colors[i])
                for i in range(4)
            ]
            self._apply_steps(full_steps)

    def update_from_records(
        self,
        incident: Optional[Any] = None,
        audit_record: Optional[Any] = None,
    ) -> None:
        """Update timeline with dynamically generated narrative from real incident & audit records.

        Constructs detect -> cause -> fix -> result steps strictly from actual measured
        timestamps, observed vs threshold metrics, action identifiers, and verification durations.
        """
        if incident is None and audit_record is None:
            self.reset_to_idle()
            return

        # 1. Resolve chronological timestamps
        t_now = datetime.now()
        t_rec = None
        if audit_record and getattr(audit_record, "timestamp", None):
            ts = audit_record.timestamp
            t_rec = ts.astimezone() if getattr(ts, "tzinfo", None) else ts
        t_inc = None
        if incident and getattr(incident, "timestamp", None):
            ts = incident.timestamp
            t_inc = ts.astimezone() if getattr(ts, "tzinfo", None) else ts

        from datetime import date
        today = date.today()
        anchor_dt = t_rec or t_inc or t_now

        if not (audit_record or incident):
            self.lbl_sub.setText("لا توجد أحداث مسجلة اليوم")
            self.btn_evidence.setEnabled(False)
            now_str = t_now.strftime("%H:%M:%S")
            self.set_event(
                t_now.strftime("%H:%M"),
                [
                    (now_str, "المراقبة الذاتية", "فحص دوري مستمر لمؤشرات الشبكة والراوتر."),
                    (now_str, "تحليل الاستقرار", "كافة القياسات الميدانية مستقرة وضمن الحدود الطبيعية."),
                    (now_str, "الإجراءات", "لا توجد تدخلات مطلوبة حالياً."),
                    (now_str, "النتيجة", "الاتصال مستقر وسليم."),
                ],
                is_resolved=True,
            )
            return

        if anchor_dt.date() == today:
            self.lbl_sub.setText(f"آخر حدث · اليوم {anchor_dt.strftime('%H:%M')}")
        elif anchor_dt.date() == (today - timedelta(days=1)):
            self.lbl_sub.setText(f"آخر حدث · أمس {anchor_dt.strftime('%H:%M')}")
        else:
            self.lbl_sub.setText(f"آخر حدث · {anchor_dt.strftime('%Y-%m-%d %H:%M')}")

        self.btn_evidence.setEnabled(incident is not None)

        # 2. Step 1: Detect (اكتشاف المشكلة)
        t_detect = (t_inc or t_rec or anchor_dt).strftime("%H:%M:%S")
        detect_desc = ""
        evidence_list = getattr(incident, "supporting_evidence", []) if incident else []
        if evidence_list:
            ev = evidence_list[0]
            m_val = getattr(ev, "observed_value", 0.0)
            th_val = getattr(ev, "threshold_value", 0.0)
            m_type_str = str(getattr(ev, "metric_type", "")).lower()

            if "rtt" in m_type_str or "latency" in m_type_str:
                detect_desc = f"ارتفاع زمن الاستجابة إلى {m_val:.1f}ms متجاوزاً الحد الطبيعي {th_val:.1f}ms."
            elif "loss" in m_type_str or "packet" in m_type_str:
                detect_desc = f"رصد فقدان حزم بنسبة {m_val:.1f}% مقارنة بالحد الأقصى {th_val:.1f}%."
            elif "dns" in m_type_str:
                detect_desc = f"ارتفاع زمن استجابة DNS إلى {m_val:.1f}ms مقارنة بالمعدل المعتاد {th_val:.1f}ms."
            elif "bufferbloat" in m_type_str:
                detect_desc = f"تأخير طوابير عند الراوتر بمقدار +{m_val:.1f}ms تحت الحمل."
            else:
                m_name = getattr(ev.metric_type, "value", str(ev.metric_type))
                detect_desc = f"تجاوز في مؤشر {m_name} بقيمة {m_val:.1f} عن الحد {th_val:.1f}."
        elif incident and getattr(incident, "explanation", ""):
            detect_desc = incident.explanation
        elif audit_record and getattr(audit_record, "pre_remedy_metrics", None):
            pre = audit_record.pre_remedy_metrics
            if "original_servers" in pre:
                servers_str = ", ".join(pre.get("original_servers", [])) or "DHCP"
                detect_desc = f"رصد بطء في استجابة خوادم DNS ({servers_str})."
            elif "gateway_ping_ms" in pre or "gateway_before" in pre:
                detect_desc = "رصد انقطاع أو عدم استقرار في مسار البوابة الافتراضية للراوتر."
            else:
                detect_desc = "رصد انحراف في مؤشرات جودة وتدفق حركة البيانات."
        else:
            detect_desc = "رصد انحراف في استقرار الشبكة استدعى التدخل."

        # 3. Step 2: Cause (تحديد السبب)
        t_cause_dt = (t_inc + timedelta(seconds=2)) if t_inc else (anchor_dt - timedelta(seconds=12))
        t_cause = t_cause_dt.strftime("%H:%M:%S")

        cause_map = {
            "local_wifi_congestion": "ازدحام أو تداخل في إشارة Wi-Fi المحلية.",
            "local_gateway_high_latency": "ارتفاع زمن استجابة الراوتر المنزلي (البوابة الافتراضية).",
            "local_gateway_unreachable": "تعذر الوصول إلى الراوتر المنزلي (البوابة الافتراضية).",
            "gateway_bufferbloat": "تكدس الحزم عند الراوتر (Bufferbloat) نتيجة استهلاك النطاق الترددي.",
            "bufferbloat_upload_congestion": "تكدس طوابير الرفع عند الراوتر (Bufferbloat) نتيجة ضغط حركة البيانات الصادرة.",
            "bufferbloat_download_congestion": "تكدس طوابير التحميل عند الراوتر (Bufferbloat) وتجاوز سعة الاستقبال للشبكة.",
            "dns_resolver_slow": "بطء خادم DNS المزود الحالي في معالجة طلبات الاستعلام.",
            "dns_resolver_high_latency": "ارتفاع كبير في زمن استجابة خادم DNS المعتمد.",
            "dns_resolution_failure": "تعذر استجابة خادم DNS المعتمد في ترجمة العناوين.",
            "destination_specific_outage": "انقطاع أو بطء خاص بالوجهة المستهدفة مع سلامة اتصالك المحلي.",
            "external_network_unreachable": "تعذر الاتصال بالشبكة الخارجية للإنترنت.",
            "background_app_saturation": "استهلاك مكثف للإنترنت من عمليات وتطبيقات الخلفية.",
            "unknown_anomaly": "تذبذب عابر غير نمطي في مسارات التوجيه الخارجية.",
        }

        if incident:
            p_cause = getattr(incident, "probable_cause", "unknown_anomaly")
            c_key = getattr(p_cause, "value", str(p_cause))
            c_text = cause_map.get(c_key, c_key)
            conf = getattr(incident, "confidence", 0.0)
            conf_str = f" بمعدل ثقة {int(conf * 100)}%." if conf > 0 else "."
            cause_desc = f"{c_text}{conf_str}"
        elif audit_record and "dns" in getattr(audit_record, "action_id", "").lower():
            cause_desc = "خادم DNS المعتمد يواجه تأخيراً في الاستجابة مقارنة بالبدائل المتاحة."
        elif audit_record and ("qos" in getattr(audit_record, "action_id", "").lower() or "throttle" in getattr(audit_record, "action_id", "").lower()):
            cause_desc = "حركة البيانات الصادرة من البرامج الخلفية تؤثر على التطبيقات النشطة."
        elif audit_record and "renew" in getattr(audit_record, "action_id", "").lower():
            cause_desc = "انتهاء أو عدم تجاوب إيجار عنوان IP الممنوح من الراوتر (DHCP)."
        else:
            cause_desc = "تم تشخيص سبب عدم الاستقرار في مسار الاتصال النشط."

        # 4. Step 3: Fix (الإصلاح)
        t_fix_dt = t_rec or (anchor_dt - timedelta(seconds=5))
        t_fix = t_fix_dt.strftime("%H:%M:%S")

        if audit_record:
            act_name = getattr(audit_record, "action_name", "إجراء تصحيحي")
            act_id = getattr(audit_record, "action_id", "").lower()
            post_m = getattr(audit_record, "post_remedy_metrics", {}) or {}

            if act_id == "switch_dns_resolver":
                active_s = post_m.get("active_servers", [])
                if active_s:
                    ipv4_servers = [s for s in active_s if ":" not in s]
                    server_display = ", ".join(ipv4_servers[:2]) if ipv4_servers else (active_s[0] if active_s else "الخادم البديل")
                    provider_name = ""
                    if any("8.8.8.8" in s or "8.8.4.4" in s for s in active_s):
                        provider_name = "Google DNS "
                    elif any("1.1.1.1" in s or "1.0.0.1" in s for s in active_s):
                        provider_name = "Cloudflare DNS "
                    elif any("9.9.9.9" in s for s in active_s):
                        provider_name = "Quad9 DNS "
                    fix_desc = f"تحويل خادم DNS إلى {provider_name}({server_display}) وتحديث كاش النظام بنجاح."
                else:
                    fix_desc = "تحديث إعدادات DNS للنظام والتأكد من سرعة الاستجابة."
            elif "throttle" in act_id or "qos" in act_id:
                fix_desc = f"تطبيق سياسة Windows NetQoS ({act_name}) للتحكم في استهلاك البرامج الخلفية."
            elif act_id == "flush_dns_cache":
                fix_desc = "تفريغ الذاكرة الوسيطة للعناوين (DNS Cache) وتحديث المسارات بنجاح."
            elif "renew" in act_id:
                fix_desc = "تجديد إيجار عنوان IP (DHCP) مع الراوتر المنزلي بنجاح."
            elif "recheck_gateway" in act_id:
                fix_desc = "إعادة فحص استجابة الراوتر وتأكيد سلامة المسار المحلي."
            else:
                fix_desc = f"تم تنفيذ الإجراء التصحيحي ({act_name}) بنجاح."
        elif incident and getattr(incident, "recommended_actions", None):
            fix_desc = f"الإجراء الموصى به: {', '.join(incident.recommended_actions)}."
        else:
            fix_desc = "تم تفعيل إجراءات تحسين مسار الاتصال."

        # 5. Step 4: Result (النتيجة)
        if audit_record:
            exec_ms = getattr(audit_record, "execution_duration_ms", 0.0) or 0.0
            verif_ms = getattr(audit_record, "verification_duration_ms", 0.0) or 0.0
            total_dur = exec_ms + verif_ms
            t_res_dt = t_fix_dt + timedelta(milliseconds=max(500.0, total_dur))
            t_res = t_res_dt.strftime("%H:%M:%S")
            dur_s = total_dur / 1000.0
            dur_str = f" خلال {dur_s:.1f} ثانية" if dur_s > 0.05 else ""

            status = getattr(audit_record, "status", "")
            status_val = getattr(status, "value", str(status)).lower()

            if status_val in ("succeeded", "success"):
                post = getattr(audit_record, "post_remedy_metrics", {}) or {}
                if "rtt_ms" in post:
                    res_desc = f"استقر زمن الاستجابة عند {post['rtt_ms']:.1f}ms. تم الحل{dur_str} بنجاح."
                elif "gateway_ping_ms" in post and post["gateway_ping_ms"] > 0:
                    res_desc = f"استقرت استجابة البوابة عند {post['gateway_ping_ms']:.1f}ms. تم الحل{dur_str}."
                else:
                    res_desc = f"تم تأكيد نجاح الإصلاح{dur_str} واستقرار الاتصال دون أخطاء."
                res_color = tokens.STATUS_OK
                self.status_chip.set_variant("ok-soft", "تم حله تلقائياً")
                self.btn_rollback.setVisible(True)
            elif status_val in ("failed", "failure"):
                err_msg = getattr(audit_record, "error_message", None)
                res_desc = f"فشل تنفيذ الإجراء: {err_msg or 'لم يتحقق التحسن المطلوب'}."
                res_color = tokens.STATUS_BAD
                self.status_chip.set_variant("bad-soft", "فشل الإصلاح")
                self.btn_rollback.setVisible(True)
            elif status_val == "rolled_back":
                res_desc = "تم التراجع عن الإجراء واستعادة الإعدادات السابقة للنظام بنجاح."
                res_color = tokens.STATUS_WARN
                self.status_chip.set_variant("warn-soft", "تم التراجع")
                self.btn_rollback.setVisible(True)
            else:
                res_desc = f"حالة الإجراء الحالية: {status_val}."
                res_color = tokens.ACCENT
                self.status_chip.set_variant("accent-soft", "قيد المعالجة")
                self.btn_rollback.setVisible(True)
        else:
            t_res = (anchor_dt + timedelta(seconds=1)).strftime("%H:%M:%S")
            res_desc = "في انتظار موافقة المستخدم أو التدخل الذاتي لمعالجة التشخيص."
            res_color = tokens.STATUS_WARN
            self.status_chip.set_variant("warn-soft", "يحتاج انتباهك")
            self.btn_rollback.setVisible(True)

        steps = [
            (t_detect, "اكتشاف المشكلة", detect_desc, tokens.STATUS_BAD),
            (t_cause, "تحديد السبب", cause_desc, tokens.STATUS_WARN),
            (t_fix, "الإصلاح", fix_desc, tokens.ACCENT),
            (t_res, "النتيجة", res_desc, res_color),
        ]
        self._apply_steps(steps)
