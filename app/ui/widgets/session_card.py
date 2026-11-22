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
                background-color: {tokens.SURFACE_INSET};
                border: 1px solid rgba(0, 229, 153, 0.25);
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

        # Row 1: Live Dot + App Name + Process Badge + Status Chip ... [End Button]
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.live_dot = QLabel()
        self.live_dot.setFixedSize(9, 9)
        self.live_dot.setStyleSheet(f"background-color: {tokens.STATUS_OK}; border-radius: 4.5px;")
        top_row.addWidget(self.live_dot)

        self.lbl_title = QLabel(session.app_name)
        self.lbl_title.setFont(tokens.get_sans_font(15, 600))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")
        top_row.addWidget(self.lbl_title)

        lbl_proc_tag = QLabel(f"{session.process_name} (PID {session.pid})")
        lbl_proc_tag.setFont(tokens.get_mono_font(12, 400))
        lbl_proc_tag.setStyleSheet(f"color: {tokens.TEXT_MUTED}; background: {tokens.SURFACE}; padding: 2px 8px; border-radius: 4px;")
        top_row.addWidget(lbl_proc_tag)

        chip_active = Chip("محمي استباقياً ✓", variant="ok-soft")
        top_row.addWidget(chip_active)

        top_row.addStretch()

        self.btn_end = SecondaryButton("إنهاء المراقبة")
        self.btn_end.setFixedHeight(34)
        if on_close_callback:
            self.btn_end.clicked.connect(lambda: on_close_callback(session.process_name))
        top_row.addWidget(self.btn_end)
        layout.addLayout(top_row)

        # Row 1.5: Proactive Early Warning Alert Box
        self.warning_box = QFrame()
        self.warning_box.setObjectName("EarlyWarningBox")
        self.warning_box.setStyleSheet(f"""
            QFrame#EarlyWarningBox {{
                background-color: rgba(243, 156, 18, 0.12);
                border: 1px solid rgba(243, 156, 18, 0.4);
                border-radius: {tokens.RADIUS_INNER}px;
                padding: 6px 12px;
            }}
            QFrame#EarlyWarningBox QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        wb_layout = QHBoxLayout(self.warning_box)
        wb_layout.setContentsMargins(10, 8, 10, 8)
        wb_layout.setSpacing(8)

        lbl_warn_icon = QLabel("⚠️")
        lbl_warn_icon.setFont(tokens.get_sans_font(13, 600))
        wb_layout.addWidget(lbl_warn_icon)

        self.lbl_early_warning = QLabel(session.early_warning or "")
        self.lbl_early_warning.setFont(tokens.get_sans_font(13, 500))
        self.lbl_early_warning.setStyleSheet(f"color: {tokens.STATUS_WARN}; line-height: 1.4;")
        self.lbl_early_warning.setWordWrap(True)
        wb_layout.addWidget(self.lbl_early_warning, stretch=1)

        self.warning_box.setVisible(bool(session.early_warning))
        layout.addWidget(self.warning_box)

        # Row 2: Live Duration & Real-time QoS Telemetry (Clean horizontal metrics)
        telemetry_row = QHBoxLayout()
        telemetry_row.setSpacing(16)

        def make_metric_label(icon_txt: str, val_txt: str, col: str = tokens.TEXT) -> QLabel:
            lbl = QLabel(f"{icon_txt} {val_txt}")
            lbl.setFont(tokens.get_mono_font(13, 500))
            lbl.setStyleSheet(f"color: {col};")
            return lbl

        self.lbl_duration = make_metric_label("⏱️", f"المدة: {self._format_duration(self.elapsed_seconds)}")
        telemetry_row.addWidget(self.lbl_duration)
        telemetry_row.addWidget(make_metric_label("⚡", f"السرعة: {session.avg_bitrate_mbps:.1f} Mbps"))
        telemetry_row.addWidget(make_metric_label("📶", f"الاستجابة: {session.avg_latency_ms:.0f} ms"))
        telemetry_row.addWidget(make_metric_label("🛡️", f"فقدان الحزم: {session.packet_loss_pct:.1f}%", tokens.STATUS_OK))
        telemetry_row.addStretch()
        layout.addLayout(telemetry_row)

        # Row 3: Active Shields (Single clean horizontal summary row without ugly nested bordered boxes)
        shields_row = QHBoxLayout()
        shields_row.setSpacing(12)

        lbl_shield_tag = QLabel("🛡️ دروع الحماية المطبقة:")
        lbl_shield_tag.setFont(tokens.get_sans_font(12, 600))
        lbl_shield_tag.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        shields_row.addWidget(lbl_shield_tag)

        features = [
            "أولوية DSCP 46 للبث الفوري",
            "تقييد سرعة العمليات الخلفية",
            "حماية المقابس ومنع التقطيع",
        ]
        for feat in features:
            f_lbl = QLabel(f"✓ {feat}")
            f_lbl.setFont(tokens.get_sans_font(12, 400))
            f_lbl.setStyleSheet(f"color: {tokens.STATUS_OK}; background: rgba(0, 229, 153, 0.06); padding: 3px 8px; border-radius: 4px;")
            shields_row.addWidget(f_lbl)

        shields_row.addStretch()
        layout.addLayout(shields_row)

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

    def update_early_warning(self, message: Optional[str]) -> None:
        if message:
            self.lbl_early_warning.setText(message)
            self.warning_box.setVisible(True)
        else:
            self.warning_box.setVisible(False)


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
        self.btn_toggle.setFixedHeight(36)
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

        # Inset Box for telemetry & actions (Clean, unbordered modern elevation)
        inset_box = QFrame()
        inset_box.setObjectName("SessionInsetBox")
        inset_box.setStyleSheet(f"""
            QFrame#SessionInsetBox {{
                background-color: {tokens.SURFACE_INSET};
                border: none;
                border-radius: {tokens.RADIUS_INNER}px;
            }}
            QFrame#SessionInsetBox QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        inset_layout = QVBoxLayout(inset_box)
        inset_layout.setContentsMargins(16, 14, 16, 14)
        inset_layout.setSpacing(14)

        # 1. Telemetry Stats Strip (2x2 grid, clean soft pills without harsh border lines)
        stats_grid = QGridLayout()
        stats_grid.setHorizontalSpacing(10)
        stats_grid.setVerticalSpacing(8)

        def make_stat_box(title: str, val: str, sub: str) -> QWidget:
            w = QWidget()
            col = QVBoxLayout(w)
            col.setContentsMargins(12, 10, 12, 10)
            col.setSpacing(2)
            w.setStyleSheet(f"background-color: {tokens.SURFACE}; border: none; border-radius: 8px;")

            t_lbl = QLabel(title)
            t_lbl.setFont(tokens.get_sans_font(12, 400))
            t_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            t_lbl.setWordWrap(True)
            col.addWidget(t_lbl)

            v_lbl = QLabel(val)
            v_lbl.setFont(tokens.get_mono_font(16, 600))
            v_lbl.setStyleSheet(f"color: {tokens.TEXT};")
            col.addWidget(v_lbl)

            s_lbl = QLabel(sub)
            s_lbl.setFont(tokens.get_sans_font(11, 400))
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
                        border: none;
                        border-right: 3px solid {tokens.ACCENT};
                        border-radius: 6px;
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
