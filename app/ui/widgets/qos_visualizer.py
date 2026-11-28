"""Real QoS Policy Matrix & Meeting Lifecycle Stepper widgets for Meeting Guard."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from app.traffic.meeting_detector import MeetingModeState
from app.traffic.qos_config import AppQoSConfig, DSCPValue, QoSPolicySpec, build_meeting_qos_specs, compute_adaptive_upload_throttle
from app.ui import i18n, tokens
from app.ui.widgets.status_badge import StatusBadge


class MeetingLifecycleStepper(QFrame):
    """6-stage visual meeting guard lifecycle: Idle -> Detecting -> Calibrating -> Active -> Leaving -> Restored."""

    STAGES = (
        ("idle", "خامل", "Idle"),
        ("detecting", "رصد", "Detecting"),
        ("calibrating", "معايرة", "Calibrating"),
        ("active", "نشط", "Active"),
        ("leaving", "مغادرة", "Leaving"),
        ("restored", "مستعاد", "Restored"),
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("MeetingLifecycleStepper")
        self.setStyleSheet(
            f"QFrame#MeetingLifecycleStepper {{ background-color: {tokens.SURFACE_INSET}; border: 1px solid {tokens.LINE}; border-radius: {tokens.RADIUS_INNER}px; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        hdr_ro = QHBoxLayout()
        lbl_ro_title = QLabel(
            "تسلسل مراحل حماية الاجتماع (عرض الحالة فقط — للقراءة فقط)"
            if i18n.get_language() == "ar"
            else "Meeting Guard Lifecycle Timeline (Read-Only Status Indicator)"
        )
        lbl_ro_title.setFont(tokens.get_sans_font(12, 600))
        lbl_ro_title.setStyleSheet(f"color: {tokens.TEXT_MUTED}; border: none; background: transparent;")
        self._lbl_ro_title = lbl_ro_title
        hdr_ro.addWidget(lbl_ro_title)
        hdr_ro.addStretch()
        lay.addLayout(hdr_ro)

        row = QHBoxLayout()
        row.setSpacing(8)
        self._pills: Dict[str, QLabel] = {}
        for sid, ar, en in self.STAGES:
            lbl = QLabel(ar if i18n.get_language() == "ar" else en, self)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setMinimumHeight(30)
            lbl.setFont(tokens.get_sans_font(12, 600))
            lbl.setToolTip(
                "مؤشر مرحلة تلقائي (للقراءة فقط) — استخدم أزرار التشغيل أعلاه"
                if i18n.get_language() == "ar"
                else "Automatic lifecycle stage indicator (read-only) — use control buttons above"
            )
            self._pills[sid] = lbl
            row.addWidget(lbl, stretch=1)
        lay.addLayout(row)

        self.lbl_explanation = QLabel("", self)
        self.lbl_explanation.setFont(tokens.get_sans_font(12, 400))
        self.lbl_explanation.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_explanation.setWordWrap(True)
        lay.addWidget(self.lbl_explanation)

        self.set_stage("idle", "في انتظار رصد مكالمة صوتية أو مرئية مع إرسال UDP فعلي.")

    def set_stage(self, stage_id: str, explanation: str = "") -> None:
        norm = stage_id.lower()
        if norm == "entering":
            norm = "calibrating"
        elif norm == "cooldown":
            norm = "leaving"
        for sid, pill in self._pills.items():
            is_cur = sid == norm
            if is_cur:
                col = tokens.STATUS_OK if sid in ("active", "restored") else (tokens.STATUS_WARN if sid in ("detecting", "calibrating", "leaving") else tokens.ACCENT_BRIGHT)
                bg = tokens.OK_SOFT_BG if sid in ("active", "restored") else (tokens.WARN_SOFT_BG if sid in ("detecting", "calibrating", "leaving") else tokens.SURFACE_SELECTED)
                txt_col = col if sid in ("active", "restored", "detecting", "calibrating", "leaving") else tokens.TEXT
                pill.setStyleSheet(
                    f"color: {txt_col}; background-color: {bg}; border: 1.5px solid {col}; border-radius: 6px; padding: 4px 8px;"
                )
            else:
                pill.setStyleSheet(
                    f"color: {tokens.TEXT_MUTED}; background-color: {tokens.SURFACE}; border: 1px dashed {tokens.LINE}; border-radius: 6px; padding: 4px 8px;"
                )
        if explanation:
            self.lbl_explanation.setText(tokens.bidi_isolate_mixed(explanation))

    def retranslate(self) -> None:
        ar = i18n.get_language() == "ar"
        if hasattr(self, "_lbl_ro_title"):
            self._lbl_ro_title.setText(
                "تسلسل مراحل حماية الاجتماع (عرض الحالة فقط — للقراءة فقط)"
                if ar else "Meeting Guard Lifecycle Timeline (Read-Only Status Indicator)"
            )
        for sid, ar_lbl, en_lbl in self.STAGES:
            if sid in self._pills:
                self._pills[sid].setText(ar_lbl if ar else en_lbl)


class QoSPolicyMatrixWidget(QFrame):
    """Displays real QoS traffic classes from AppQoSConfig and Windows ActiveStore readback."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("QoSPolicyMatrixWidget")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        self.lbl_summary = QLabel("", self)
        self.lbl_summary.setFont(tokens.get_sans_font(12, 500))
        self.lbl_summary.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_summary.setWordWrap(True)
        hdr.addWidget(self.lbl_summary, stretch=1)

        self.badge_store = StatusBadge(tokens.SystemStatus.WAITING, i18n.tr("status_waiting"), self)
        hdr.addWidget(self.badge_store)
        lay.addLayout(hdr)

        self.table = QTableWidget(0, 7, self)
        self.table.setHorizontalHeaderLabels([
            "فئة الحركة / Policy Class",
            "التطبيق / الشروط",
            "البروتوكول والمنافذ",
            "DSCP",
            "تقييد الرفع",
            "الأولوية (Precedence)",
            "التحقق في Windows ActiveStore",
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.horizontalHeader().setMinimumHeight(46)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(250)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        lay.addWidget(self.table)

    def refresh_from_controller(
        self,
        *,
        qos_config: Optional[AppQoSConfig],
        active_specs: List[QoSPolicySpec],
        os_policies: List[Dict[str, Any]],
        meeting_active: bool,
        active_apps: Optional[List[str]] = None,
        uplink_mbps: float = 15.0,
    ) -> None:
        cfg = qos_config or AppQoSConfig()
        os_by_name: Dict[str, Dict[str, Any]] = {
            str(p.get("name") or p.get("Name") or "").lower(): p
            for p in (os_policies or [])
            if isinstance(p, dict)
        }

        # Use verified active specs when present, else build configured preview hierarchy
        has_real_active = bool(active_specs or active_apps)
        specs: List[QoSPolicySpec] = list(active_specs) if active_specs else build_meeting_qos_specs(
            active_meeting_apps=active_apps or ["zoom.exe"],
            active_bulk_apps=[],
            available_uplink_mbps=uplink_mbps,
            video_tier="1080p",
            config=cfg,
        )

        # Deduplicate & sort by precedence descending (highest priority first)
        specs_sorted = sorted(specs, key=lambda s: int(s.precedence or 0), reverse=True)
        self.table.setRowCount(len(specs_sorted))

        verified_count = 0
        for row_i, spec in enumerate(specs_sorted):
            os_match = os_by_name.get(spec.name.lower())
            if os_match is not None:
                verified_count += 1
            cls_label = self._classify_spec_label(spec)
            raw_app = spec.app_name or ("الكل (Default)" if spec.is_default else "كل التطبيقات")
            if not has_real_active and spec.app_name:
                app_cond = f"{raw_app} (قالب إعداد)"
            else:
                app_cond = raw_app
            proto_str = spec.protocol or "Any"
            if spec.port_start is not None and spec.port_end is not None:
                port_str = f"{proto_str} {spec.port_start}-{spec.port_end}"
            elif spec.port is not None:
                port_str = f"{proto_str} {spec.port}"
            else:
                port_str = proto_str
            dscp_str = f"DSCP {spec.dscp}" if spec.dscp is not None else "—"
            thr_str = (
                f"{spec.throttle_bps / 1_000_000:.2f} Mbps"
                if spec.throttle_bps
                else "غير مقيد"
            )
            prec_str = str(spec.precedence if spec.precedence is not None else "—")
            if os_match is not None:
                os_dscp = os_match.get("dscp_action", os_match.get("DSCPAction"))
                ver_str = f"متحقق في ActiveStore (DSCP {os_dscp})" if os_dscp is not None else "متحقق في ActiveStore"
            elif not cfg.master_enabled:
                ver_str = "الحماية معطّلة حالياً"
            elif meeting_active:
                ver_str = "غير مؤكد في ActiveStore"
            else:
                ver_str = "معدّ للتطبيق عند بدء الاجتماع (0 في ActiveStore)"

            vals = [cls_label, app_cond, port_str, dscp_str, thr_str, prec_str, ver_str]
            for col_i, val in enumerate(vals):
                item = QTableWidgetItem(tokens.bidi_isolate_mixed(val))
                if col_i in (2, 3, 4, 5):
                    item.setFont(tokens.get_mono_font(14, 500))
                else:
                    item.setFont(tokens.get_sans_font(14, 500 if col_i == 0 else 400))
                self.table.setItem(row_i, col_i, item)
            self.table.setRowHeight(row_i, 44)

        ar = i18n.get_language() == "ar"
        if verified_count > 0:
            self.badge_store.set_status(tokens.SystemStatus.ACTIVE, f"ActiveStore: {verified_count} متحقق" if ar else f"ActiveStore: {verified_count} verified")
            self.lbl_summary.setText(
                f"تم التحقق من وجود {verified_count} سياسة في مخزن Windows ActiveStore الفعلي — تأخذ وسائط الاجتماع الأولوية القصوى بينما تنخفض حركة الخلفية."
                if ar else f"Verified {verified_count} active Windows ActiveStore QoS policies prioritizing meeting media above background flows."
            )
        elif not cfg.master_enabled:
            self.badge_store.set_status(tokens.SystemStatus.NOT_CONNECTED, "التحكم معطّل" if ar else "QoS Disabled")
            self.lbl_summary.setText(
                "حماية QoS معطّلة في الإعدادات — لن يتم حقن أي سياسات في Windows ActiveStore حتى يتم تفعيل المفتاح الرئيسي أو الضغط على بدء المراقبة."
                if ar else "QoS protection is disabled — no Windows ActiveStore policies will be applied until Master QoS is enabled."
            )
        elif meeting_active:
            self.badge_store.set_status(tokens.SystemStatus.WARNING, "غير متحقق في ActiveStore" if ar else "Unverified in ActiveStore")
            self.lbl_summary.setText(
                "المكالمة نشطة ولكن لم يُؤكد وجود السياسات في Windows ActiveStore بعد (تحقق من صلاحيات المسؤول أو اضغط فحص ActiveStore)."
                if ar else "Meeting active, but policies are not yet confirmed by Windows ActiveStore readback."
            )
        else:
            self.badge_store.set_status(tokens.SystemStatus.WAITING, "مُعدّ — بانتظار مكالمة" if ar else "Configured (Idle)")
            self.lbl_summary.setText(
                f"الحالة: مفعّل بالإعدادات ومستعد ({len(specs_sorted)} فئات معدة)، ولا توجد مكالمة نشطة الآن (0 قواعد نشطة في ActiveStore)."
                if ar else f"State: Config enabled & standing by ({len(specs_sorted)} template classes); no active call detected (0 ActiveStore rules currently injected)."
            )

    @staticmethod
    def _classify_spec_label(spec: QoSPolicySpec) -> str:
        n = spec.name.lower()
        if "media" in n or (spec.dscp in (DSCPValue.AF41_VIDEO, DSCPValue.EF_VOICE)):
            return "وسائط الاجتماع (Meeting Media)"
        if "dns" in n:
            return "استعلامات DNS المحمية (Protected DNS)"
        if "netguard" in n:
            return "قياس تشخيص NetGuard"
        if "tcp" in n or "signal" in n:
            return "إشارات التحكم للاجتماع (Signaling)"
        if "throttle" in n or spec.throttle_bps:
            return "رفع الخلفية المجمّع (Bulk Upload)"
        if spec.is_default or spec.dscp == DSCPValue.CS1_BACKGROUND:
            return "الحركة الافتراضية بالخلفية (Default)"
        return spec.name
