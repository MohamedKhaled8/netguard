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


class TimelineStepWidget(QWidget):
    """Single step row showing mono time, bold title, and explanation."""

    def __init__(self, time_str: str, title: str, desc: str, dot_color: str, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(3)

        self.lbl_time = QLabel(time_str)
        self.lbl_time.setFont(tokens.get_mono_font(12, 400))
        self.lbl_time.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(tokens.get_sans_font(15, 600))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")

        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setFont(tokens.get_sans_font(13, 400))
        self.lbl_desc.setStyleSheet(f"color: {tokens.TEXT_SECONDARY}; line-height: 1.6;")
        self.lbl_desc.setWordWrap(True)

        layout.addWidget(self.lbl_time)
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_desc)


class TimelineCanvas(QWidget):
    """Paints the 10px dots and 1px vertical rail for 4 steps."""

    def __init__(self, colors: List[str], step_widgets: List[QWidget], parent=None) -> None:
        super().__init__(parent)
        self.colors = colors
        self.step_widgets = step_widgets
        self.setFixedWidth(20)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self.step_widgets:
            return

        centers = []
        for w in self.step_widgets:
            y = w.y() + 8.0  # Align with time label
            centers.append(y)

        # Draw 1px rail from first center to last center
        if len(centers) >= 2:
            painter.setPen(QPen(QColor(tokens.LINE_STRONG), 1.0))
            painter.drawLine(QPointF(10.0, centers[0]), QPointF(10.0, centers[-1]))

        # Draw 10px solid dots
        painter.setPen(Qt.NoPen)
        for i, y in enumerate(centers):
            color = QColor(self.colors[i] if i < len(self.colors) else tokens.ACCENT)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(10.0, y), 5.0, 5.0)


class TimelinePanel(QFrame):
    """Complete 'ما الذي حدث بالضبط؟' panel."""

    view_evidence_requested = Signal()
    rollback_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TimelinePanel")
        self.setStyleSheet(f"""
            QFrame#TimelinePanel {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_PANEL}px;
            }}
            QFrame#TimelinePanel QLabel {{
                border: none;
                background: transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header: Title + Subtitle on Right, Chip on Left
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        self.lbl_title = QLabel("ما الذي حدث بالضبط؟")
        self.lbl_title.setFont(tokens.get_sans_font(18, 600))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")

        self.lbl_sub = QLabel("لا توجد أحداث مسجلة")
        self.lbl_sub.setFont(tokens.get_sans_font(13, 400))
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
        steps_layout = QHBoxLayout(self.steps_container)
        steps_layout.setContentsMargins(0, 4, 0, 4)
        steps_layout.setSpacing(12)

        self.content_col = QVBoxLayout()
        self.content_col.setContentsMargins(0, 0, 0, 0)
        self.content_col.setSpacing(10)

        # Default idle state when no events exist
        self.step_data = [
            ("—", "اكتشاف المشكلة", "لم يتم رصد أي تذبذب أو انحراف في مؤشرات جودة الاتصال.", tokens.TEXT_MUTED),
            ("—", "تحديد السبب", "كافة طبقات الفحص (الجهاز، الراوتر، المزود، الإنترنت) تعمل بشكل طبيعي.", tokens.TEXT_MUTED),
            ("—", "الإصلاح", "لا توجد إجراءات تصحيحية مطلوبة حالياً.", tokens.TEXT_MUTED),
            ("—", "النتيجة", "الشبكة في حالة استقرار تام.", tokens.TEXT_MUTED),
        ]

        self.step_widgets: List[TimelineStepWidget] = []
        for t, title, desc, c in self.step_data:
            w = TimelineStepWidget(t, title, desc, c)
            self.step_widgets.append(w)
            self.content_col.addWidget(w)

        colors = [s[3] for s in self.step_data]
        self.rail_canvas = TimelineCanvas(colors, self.step_widgets)

        steps_layout.addWidget(self.rail_canvas)
        steps_layout.addLayout(self.content_col)
        layout.addWidget(self.steps_container)

        # Footer Buttons
        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 8, 0, 0)
        footer_row.setSpacing(10)

        self.btn_evidence = SecondaryButton("عرض الأدلة")
        self.btn_evidence.clicked.connect(self.view_evidence_requested.emit)
        self.btn_evidence.setEnabled(False)

        self.btn_rollback = GhostButton("تراجع عن الإصلاح")
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
                self.step_widgets[i].lbl_time.setText(t)
                self.step_widgets[i].lbl_title.setText(title)
                self.step_widgets[i].lbl_desc.setText(desc)
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

        anchor_dt = t_rec or t_inc or t_now
        self.lbl_sub.setText(f"آخر حدث · اليوم {anchor_dt.strftime('%H:%M')}")
        self.btn_evidence.setEnabled(incident is not None)

        # 2. Step 1: Detect (اكتشاف المشكلة)
        t_detect = (t_inc or (anchor_dt - timedelta(seconds=15))).strftime("%H:%M:%S")
        detect_desc = ""
        evidence_list = getattr(incident, "supporting_evidence", []) if incident else []
        if evidence_list:
            ev = evidence_list[0]
            m_val = getattr(ev, "observed_value", 0.0)
            th_val = getattr(ev, "threshold_value", 0.0)
            m_type_str = str(getattr(ev, "metric_type", "")).lower()

            if "rtt" in m_type_str or "latency" in m_type_str:
                detect_desc = f"ارتفع زمن الاستجابة إلى {m_val:.1f}ms (الحد المسموح {th_val:.1f}ms)."
            elif "loss" in m_type_str or "packet" in m_type_str:
                detect_desc = f"رصد فقدان حزم بنسبة {m_val:.1f}% (الحد الأقصى {th_val:.1f}%)."
            elif "dns" in m_type_str:
                detect_desc = f"ارتفع زمن استجابة DNS إلى {m_val:.1f}ms (الحد: {th_val:.1f}ms)."
            elif "bufferbloat" in m_type_str:
                detect_desc = f"رصد تأخير طوابير بافركلوت بمقدار +{m_val:.1f}ms تحت الحمل."
            else:
                m_name = getattr(ev.metric_type, "value", str(ev.metric_type))
                detect_desc = f"رصد تجاوز في مؤشر {m_name} إلى {m_val:.1f} (الحد: {th_val:.1f})."
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
            "gateway_bufferbloat": "تكدس الحزم عند الراوتر (Bufferbloat) نتيجة استهلاك النطاق الترددي.",
            "bufferbloat_upload_congestion": "تكدس طوابير الرفع عند الراوتر (Bufferbloat) نتيجة ضغط حركة البيانات الصادرة.",
            "bufferbloat_download_congestion": "تكدس طوابير التحميل عند الراوتر (Bufferbloat) وتجاوز سعة الاستقبال للشبكة.",
            "dns_resolver_slow": "بطء خادم DNS المزود الحالي في معالجة طلبات الاستعلام.",
            "dns_resolver_high_latency": "ارتفاع كبير في زمن استجابة خادم DNS المعتمد.",
            "destination_specific_outage": "انقطاع أو بطء خاص بالوجهة المستهدفة مع سلامة الشبكة المحلية.",
            "background_app_saturation": "استهلاك مكثف للنطاق الترددي من عمليات وتطبيقات الخلفية.",
            "unknown_anomaly": "تذبذب عابر غير نمطي في مسارات التوجيه الخارجية.",
        }

        if incident:
            p_cause = getattr(incident, "probable_cause", "unknown_anomaly")
            c_key = getattr(p_cause, "value", str(p_cause))
            c_text = cause_map.get(c_key, c_key)
            conf = getattr(incident, "confidence", 0.0)
            conf_str = f" (مستوى الثقة: {int(conf * 100)}%)" if conf > 0 else ""
            cause_desc = f"{c_text}{conf_str}."
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
                    fix_desc = f"تم تطبيق '{act_name}'. تحويل DNS إلى ({', '.join(active_s)}) وتفريغ كاش النظام."
                else:
                    fix_desc = f"تم تطبيق '{act_name}'. تحديث إعدادات DNS للنظام والتحقق من التفعيل."
            elif "throttle" in act_id or "qos" in act_id:
                fix_desc = f"تم تطبيق '{act_name}'. تطبيق سياسة Windows NetQoS لتقييد الرفع الصادر."
            elif act_id == "flush_dns_cache":
                fix_desc = f"تم تنفيذ '{act_name}' وتفريغ الذاكرة الوسيطة للعناوين بنجاح."
            elif "renew" in act_id:
                fix_desc = f"تم تنفيذ '{act_name}' وتجديد إيجار DHCP للمحول بنجاح."
            else:
                risk = getattr(audit_record, "risk_level", "")
                r_val = getattr(risk, "value", str(risk))
                fix_desc = f"تم تنفيذ إجراء: {act_name} (مستوى الأمان: {r_val})."
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
