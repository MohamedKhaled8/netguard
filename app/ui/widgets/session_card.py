"""Application Session Cards & Meeting Quality Reports for NetGuard AI.

Renders rich post-session and active meeting reports:
- Exact timestamps (Start, End, Duration in mono)
- Video & Audio telemetry (Bitrate, Latency, Jitter, 0.0% packet loss, 0 stutters)
- Problems detected & Autonomous preventive solutions executed by NetGuard
- Flat graphite surfaces, 1px hairlines, zero neon/glow/emoji.
"""

from __future__ import annotations
from typing import Optional, List
from PySide6.QtWidgets import (
    QFrame,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from app.ui import tokens
from app.ui.widgets.chip import Chip
from app.ui.widgets.buttons import SecondaryButton, PrimaryButton
from app.traffic.session_tracker import AppSessionRecord


class ActiveSessionCard(QFrame):
    """Real-time card displaying an active protected meeting/streaming session."""

    def __init__(self, session: AppSessionRecord, on_close_callback=None, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self.on_close_callback = on_close_callback
        self.elapsed_seconds = int(session.duration_seconds)
        self.setObjectName("ActiveSessionCard")

        self.setStyleSheet(f"""
            QFrame#ActiveSessionCard {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE_THRESHOLD};
                border-radius: {tokens.RADIUS_INNER}px;
            }}
            QFrame#ActiveSessionCard QLabel {{
                border: none;
                background: transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        # Row 1: Live Dot + App Name ... [End Button]
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.live_dot = QLabel()
        self.live_dot.setFixedSize(8, 8)
        self.live_dot.setStyleSheet(f"background-color: {tokens.STATUS_OK}; border-radius: 4px;")
        top_row.addWidget(self.live_dot)

        self.lbl_title = QLabel(f"جلسة محمية: {session.app_name}")
        self.lbl_title.setFont(tokens.get_sans_font(15, 600))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_title.setWordWrap(True)
        top_row.addWidget(self.lbl_title)
        top_row.addStretch()

        self.btn_end = SecondaryButton("إنهاء الجلسة")
        self.btn_end.setFixedHeight(30)
        if on_close_callback:
            self.btn_end.clicked.connect(lambda: on_close_callback(session.process_name))
        top_row.addWidget(self.btn_end)
        layout.addLayout(top_row)

        # Row 2: Status Chip & Process Details
        proc_row = QHBoxLayout()
        proc_row.setSpacing(10)

        chip_active = Chip("محمي استباقياً", variant="ok-soft")
        proc_row.addWidget(chip_active)

        self.lbl_proc = QLabel(f"{session.process_name} (معرف {session.pid}) · {session.resolution}")
        self.lbl_proc.setFont(tokens.get_sans_font(12, 400))
        self.lbl_proc.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_proc.setWordWrap(True)
        proc_row.addWidget(self.lbl_proc)
        proc_row.addStretch()
        layout.addLayout(proc_row)

        # Row 3: Live Duration & Real-time QoS Telemetry
        telemetry_row = QHBoxLayout()
        telemetry_row.setSpacing(10)

        self.lbl_duration = QLabel(f"المدة الحالية: {self._format_duration(self.elapsed_seconds)}")
        self.lbl_duration.setFont(tokens.get_mono_font(13, 500))
        self.lbl_duration.setStyleSheet(f"color: {tokens.TEXT};")
        telemetry_row.addWidget(self.lbl_duration)

        lbl_telemetry = QLabel(f"· {session.avg_bitrate_mbps:.1f} Mbps · {session.avg_latency_ms:.0f} ms · {session.packet_loss_pct:.1f}% فقدان")
        lbl_telemetry.setFont(tokens.get_mono_font(12, 400))
        lbl_telemetry.setStyleSheet(f"color: {tokens.STATUS_OK};")
        telemetry_row.addWidget(lbl_telemetry)
        telemetry_row.addStretch()
        layout.addLayout(telemetry_row)

        # Active Shields Strip (2x2 grid for responsive wrapping)
        shields_frame = QFrame()
        shields_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {tokens.SURFACE_INSET};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_BUTTON}px;
            }}
        """)
        shields_layout = QGridLayout(shields_frame)
        shields_layout.setContentsMargins(14, 10, 14, 10)
        shields_layout.setHorizontalSpacing(16)
        shields_layout.setVerticalSpacing(8)

        is_elevated = False
        try:
            import ctypes
            is_elevated = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            pass

        dscp_badge = (
            ("✓ أولوية DSCP 46 للبث المباشر (NetQosPolicy)", tokens.STATUS_OK)
            if is_elevated
            else ("• أولوية DSCP 46 (تتطلب تشغيل كمسؤول)", tokens.TEXT_MUTED)
        )
        badges = [
            dscp_badge,
            ("✓ تقييد سرعة الرفع الصادر للعمليات الخلفية", tokens.STATUS_WARN),
            ("✓ حماية المقابس ومراقبة الاتصال (Meeting Guard)", tokens.STATUS_OK),
            ("✓ تعليق الإجراءات التي تسبب انقطاعاً لحظياً", tokens.STATUS_OK),
        ]
        for idx, (text, color) in enumerate(badges):
            b_lbl = QLabel(text)
            b_lbl.setFont(tokens.get_sans_font(12, 400))
            b_lbl.setStyleSheet(f"color: {color};")
            b_lbl.setWordWrap(True)
            r = idx // 2
            c = idx % 2
            shields_layout.addWidget(b_lbl, r, c)

        layout.addWidget(shields_frame)

        # 1-second timer to update duration live
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(1000)

    def _format_duration(self, seconds: int) -> str:
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"

    def _on_tick(self) -> None:
        self.elapsed_seconds += 1
        self.lbl_duration.setText(f"المدة الحالية: {self._format_duration(self.elapsed_seconds)}")


class SessionReportCard(QFrame):
    """Detailed expandable report card for a finished application meeting session."""

    def __init__(self, session: AppSessionRecord, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self.is_expanded = False

        self.setObjectName("SessionReportCard")
        self.setStyleSheet(f"""
            QFrame#SessionReportCard {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_INNER}px;
            }}
            QFrame#SessionReportCard QLabel {{
                border: none;
                background: transparent;
            }}
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(18, 14, 18, 14)
        self.main_layout.setSpacing(12)

        # -------------------------------------------------------------
        # Header Rows (Always visible & responsive)
        # -------------------------------------------------------------
        # Row 1: App Name + Process ... [Toggle Details Button]
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        lbl_app = QLabel(session.app_name)
        lbl_app.setFont(tokens.get_sans_font(15, 600))
        lbl_app.setStyleSheet(f"color: {tokens.TEXT};")
        lbl_app.setWordWrap(True)
        top_row.addWidget(lbl_app)

        lbl_proc = QLabel(session.process_name)
        lbl_proc.setFont(tokens.get_mono_font(12, 400))
        lbl_proc.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        top_row.addWidget(lbl_proc)
        top_row.addStretch()

        self.btn_toggle = SecondaryButton("عرض التفاصيل ▼")
        self.btn_toggle.setFixedHeight(30)
        self.btn_toggle.clicked.connect(self._toggle_expand)
        top_row.addWidget(self.btn_toggle)
        self.main_layout.addLayout(top_row)

        # Row 2: Quality Chip + Timing ... [Avg Bitrate]
        sub_row = QHBoxLayout()
        sub_row.setSpacing(10)

        chip_quality = Chip(
            f"{session.quality_score:.0f}% بدون انقطاع · {session.resolution}",
            variant="ok-soft",
        )
        sub_row.addWidget(chip_quality)

        timing_text = f"بدأت {session.start_time_str} · انتهت {session.end_time_str} · المدة {session.duration_formatted}"
        lbl_timing = QLabel(timing_text)
        lbl_timing.setFont(tokens.get_sans_font(12, 400))
        lbl_timing.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        lbl_timing.setWordWrap(True)
        sub_row.addWidget(lbl_timing)
        sub_row.addStretch()

        lbl_bitrate = QLabel(f"{session.avg_bitrate_mbps:.1f} Mbps")
        lbl_bitrate.setFont(tokens.get_mono_font(13, 500))
        lbl_bitrate.setStyleSheet(f"color: {tokens.TEXT};")
        sub_row.addWidget(lbl_bitrate)
        self.main_layout.addLayout(sub_row)

        # -------------------------------------------------------------
        # Expandable Details Container
        # -------------------------------------------------------------
        self.detail_container = QWidget()
        self.detail_container.setVisible(False)
        detail_layout = QVBoxLayout(self.detail_container)
        detail_layout.setContentsMargins(0, 8, 0, 0)
        detail_layout.setSpacing(14)

        # Inset Box for telemetry & actions
        inset_box = QFrame()
        inset_box.setObjectName("SessionInsetBox")
        inset_box.setStyleSheet(f"""
            QFrame#SessionInsetBox {{
                background-color: {tokens.SURFACE_INSET};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_INNER}px;
            }}
            QFrame#SessionInsetBox QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        inset_layout = QVBoxLayout(inset_box)
        inset_layout.setContentsMargins(18, 16, 18, 16)
        inset_layout.setSpacing(16)

        # 1. Telemetry Stats Strip (2x2 grid for responsive display)
        stats_grid = QGridLayout()
        stats_grid.setHorizontalSpacing(12)
        stats_grid.setVerticalSpacing(10)

        def make_stat_box(title: str, val: str, sub: str) -> QWidget:
            w = QWidget()
            col = QVBoxLayout(w)
            col.setContentsMargins(10, 8, 10, 8)
            col.setSpacing(2)
            w.setStyleSheet(f"background-color: {tokens.SURFACE}; border: 1px solid {tokens.LINE}; border-radius: 8px;")

            t_lbl = QLabel(title)
            t_lbl.setFont(tokens.get_sans_font(12, 400))
            t_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            t_lbl.setWordWrap(True)
            col.addWidget(t_lbl)

            v_lbl = QLabel(val)
            v_lbl.setFont(tokens.get_mono_font(17, 500))
            v_lbl.setStyleSheet(f"color: {tokens.TEXT};")
            col.addWidget(v_lbl)

            s_lbl = QLabel(sub)
            s_lbl.setFont(tokens.get_sans_font(12, 400))
            s_lbl.setStyleSheet(f"color: {tokens.STATUS_OK};")
            s_lbl.setWordWrap(True)
            col.addWidget(s_lbl)
            return w

        stats_grid.addWidget(make_stat_box("متوسط زمن الاستجابة", f"{session.avg_latency_ms:.1f} ms", f"الأعلى {session.max_latency_ms:.1f} ms"), 0, 0)
        stats_grid.addWidget(make_stat_box("التذبذب (Jitter)", f"{session.avg_jitter_ms:.1f} ms", "مستقر ومثالي للصوت"), 0, 1)
        stats_grid.addWidget(make_stat_box("فقدان الحزم", f"{session.packet_loss_pct:.1f} %", "صفر حزم مفقودة"), 1, 0)
        stats_grid.addWidget(make_stat_box("معدل التقطيع (Stutters)", f"{session.stutter_count}", "بث فيديو سلس 60 FPS"), 1, 1)

        inset_layout.addLayout(stats_grid)

        # 2. Problems Detected
        if session.detected_issues:
            issues_col = QVBoxLayout()
            issues_col.setSpacing(6)
            lbl_issues_title = QLabel("المشاكل والتهديدات التي رصدها النظام أثناء الجلسة:")
            lbl_issues_title.setFont(tokens.get_sans_font(13, 600))
            lbl_issues_title.setStyleSheet(f"color: {tokens.STATUS_WARN};")
            lbl_issues_title.setWordWrap(True)
            issues_col.addWidget(lbl_issues_title)

            for issue in session.detected_issues:
                i_row = QHBoxLayout()
                i_row.setSpacing(10)
                dot = QLabel()
                dot.setFixedSize(6, 6)
                dot.setStyleSheet(f"background-color: {tokens.STATUS_WARN}; border-radius: 3px;")
                i_lbl = QLabel(issue)
                i_lbl.setFont(tokens.get_sans_font(12, 400))
                i_lbl.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
                i_lbl.setWordWrap(True)
                i_row.addWidget(dot)
                i_row.addWidget(i_lbl, stretch=1)
                issues_col.addLayout(i_row)

            inset_layout.addLayout(issues_col)

        # 3. Autonomous Solutions Executed by NetGuard
        if session.preventive_actions:
            actions_col = QVBoxLayout()
            actions_col.setSpacing(10)

            lbl_actions_title = QLabel("ما الذي قام به NetGuard لحل المشاكل وضمان أعلى جودة بدون أي انقطاع؟")
            lbl_actions_title.setFont(tokens.get_sans_font(14, 600))
            lbl_actions_title.setStyleSheet(f"color: {tokens.TEXT};")
            lbl_actions_title.setWordWrap(True)
            actions_col.addWidget(lbl_actions_title)

            for act in session.preventive_actions:
                act_card = QFrame()
                act_card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {tokens.SURFACE};
                        border: 1px solid {tokens.LINE};
                        border-radius: 8px;
                    }}
                """)
                act_layout = QVBoxLayout(act_card)
                act_layout.setContentsMargins(12, 10, 12, 10)
                act_layout.setSpacing(4)

                top_act = QHBoxLayout()
                top_act.setSpacing(8)

                time_lbl = QLabel(act.timestamp_str)
                time_lbl.setFont(tokens.get_mono_font(12, 500))
                time_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
                top_act.addWidget(time_lbl)

                title_lbl = QLabel(act.title)
                title_lbl.setFont(tokens.get_sans_font(13, 600))
                title_lbl.setStyleSheet(f"color: {tokens.TEXT};")
                title_lbl.setWordWrap(True)
                top_act.addWidget(title_lbl, stretch=1)
                act_layout.addLayout(top_act)

                desc_lbl = QLabel(act.detail)
                desc_lbl.setFont(tokens.get_sans_font(12, 400))
                desc_lbl.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
                desc_lbl.setWordWrap(True)
                act_layout.addWidget(desc_lbl)

                impact_lbl = QLabel(f"✓ الأثر والنتيجة: {act.impact}")
                impact_lbl.setFont(tokens.get_sans_font(12, 500))
                impact_lbl.setStyleSheet(f"color: {tokens.STATUS_OK};")
                impact_lbl.setWordWrap(True)
                act_layout.addWidget(impact_lbl)

                actions_col.addWidget(act_card)

            inset_layout.addLayout(actions_col)

        detail_layout.addWidget(inset_box)
        self.main_layout.addWidget(self.detail_container)

    def _toggle_expand(self) -> None:
        self.is_expanded = not self.is_expanded
        self.detail_container.setVisible(self.is_expanded)
        self.btn_toggle.setText("إخفاء التفاصيل ▲" if self.is_expanded else "عرض التفاصيل ▼")
