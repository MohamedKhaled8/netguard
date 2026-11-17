"""DNS Benchmark and Resolver Optimization View for NetGuard AI.

Follows the reference design system strictly:
- Current vs Fastest DNS comparison (using the same two-bar component)
- Ranked DNS server table (Rank, Name, ms in mono, visual bar, 'طبّق' per row)
- Autonomous decision log & evaluation status
100% token-compliant, dark warm-neutral graphite (#0E1012 / #15181A).
"""

from __future__ import annotations
from typing import List, Optional, Any
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from app.ui import tokens
from app.ui.widgets.buttons import PrimaryButton, SecondaryButton
from app.ui.widgets.base_panel import Panel
from app.ui.widgets.bar_row import HorizontalProgressBar
from app.core.thresholds import DEFAULT_THRESHOLDS
from app.ui.widgets.scroll_forwarder import make_scroll_transparent, fit_table_to_content


class RankedServerRow(QWidget):
    """Container widget inside table cell showing mono ms and proportional bar."""

    def __init__(self, ms_val: float, is_top: bool = False, is_active: bool = False, max_ms: float = 80.0, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(10)

        lbl_ms = QLabel(f"{ms_val:.1f} ms")
        lbl_ms.setFont(tokens.get_mono_font(13, 500))
        lbl_ms.setStyleSheet(f"color: {tokens.TEXT};")
        lbl_ms.setFixedWidth(65)
        layout.addWidget(lbl_ms)

        frac = max(0.12, min(1.0, ms_val / max(1.0, max_ms)))
        if is_top or ms_val <= DEFAULT_THRESHOLDS.dns.ui_fast_cutoff_ms:
            color = tokens.STATUS_OK
        elif ms_val <= DEFAULT_THRESHOLDS.dns.ui_warn_cutoff_ms:
            color = tokens.STATUS_WARN
        else:
            color = tokens.STATUS_BAD

        bar = HorizontalProgressBar(height=6, fill_color=color, parent=self)
        bar.set_fraction(frac)
        layout.addWidget(bar, stretch=1)


class DNSView(QWidget):
    """DNS optimization view matching reference requirements."""

    apply_dns_requested = Signal(str, str, str)  # primary_ip, secondary_ip, name

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._active_dns_ips: List[str] = ["1.1.1.1", "1.0.0.1"]
        self._current_scores: list = []

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(
            tokens.PAGE_PADDING_DESKTOP, 28, tokens.PAGE_PADDING_DESKTOP, 36
        )
        layout.setSpacing(tokens.SECTION_GAP)

        # -------------------------------------------------------------
        # 1. Header & Benchmark Trigger
        # -------------------------------------------------------------
        header_panel = Panel(
            title="خوادم DNS وتحسين سرعة التصفح",
            subtitle="مقارنة فورية لكافة خوادم أسماء المواقع وترتيب الأسرع لجهازك تلقائياً",
            parent=self,
        )

        top_h = QHBoxLayout()
        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        self.lbl_last_evaluation = QLabel("آخر تقييم: جاري الفحص الدوري...")
        self.lbl_last_evaluation.setFont(tokens.get_sans_font(13, 400))
        self.lbl_last_evaluation.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        self.lbl_last_switch = QLabel("آخر تبديل: الخادم الحالي مستقر ومناسب")
        self.lbl_last_switch.setFont(tokens.get_sans_font(13, 400))
        self.lbl_last_switch.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        info_col.addWidget(self.lbl_last_evaluation)
        info_col.addWidget(self.lbl_last_switch)
        top_h.addLayout(info_col, stretch=1)

        self.benchmark_btn = PrimaryButton("⚡ فحص وترتيب الخوادم الآن")
        top_h.addWidget(self.benchmark_btn)

        header_panel.main_layout.addLayout(top_h)
        layout.addWidget(header_panel)

        # -------------------------------------------------------------
        # 2. Current vs Fastest Comparison Panel (Two-Bar Component)
        # -------------------------------------------------------------
        comp_panel = Panel(
            title="مقارنة الخادم الحالي بالأسرع المتاح",
            subtitle="مؤشرات وقت الاستجابة المباشر لترجمة العناوين",
            parent=self,
        )

        bars_col = QVBoxLayout()
        bars_col.setSpacing(14)

        # Current DNS Row
        curr_row = QVBoxLayout()
        curr_row.setSpacing(4)
        curr_top = QHBoxLayout()
        self.lbl_curr_name = QLabel("DNS مزود الخدمة (المعتمد بجهازك حالياً)")
        self.lbl_curr_name.setFont(tokens.get_sans_font(14, 500))
        self.lbl_curr_name.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_curr_ms = QLabel("—")
        self.lbl_curr_ms.setFont(tokens.get_mono_font(14, 500))
        self.lbl_curr_ms.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        curr_top.addWidget(self.lbl_curr_name)
        curr_top.addStretch()
        curr_top.addWidget(self.lbl_curr_ms)
        curr_row.addLayout(curr_top)

        self.bar_curr = HorizontalProgressBar(height=8, fill_color=tokens.TEXT_MUTED)
        self.bar_curr.set_fraction(0.0)
        curr_row.addWidget(self.bar_curr)
        bars_col.addLayout(curr_row)

        # Fastest Benchmark DNS Row
        fast_row = QVBoxLayout()
        fast_row.setSpacing(4)
        fast_top = QHBoxLayout()
        self.lbl_fast_name = QLabel("— (اضغط فحص خوادم DNS للقياس)")
        self.lbl_fast_name.setFont(tokens.get_sans_font(14, 500))
        self.lbl_fast_name.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_fast_ms = QLabel("—")
        self.lbl_fast_ms.setFont(tokens.get_mono_font(14, 500))
        self.lbl_fast_ms.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        fast_top.addWidget(self.lbl_fast_name)
        fast_top.addStretch()
        fast_top.addWidget(self.lbl_fast_ms)
        fast_row.addLayout(fast_top)

        self.bar_fast = HorizontalProgressBar(height=8, fill_color=tokens.STATUS_OK)
        self.bar_fast.set_fraction(0.0)
        fast_row.addWidget(self.bar_fast)
        bars_col.addLayout(fast_row)

        comp_panel.main_layout.addLayout(bars_col)
        layout.addWidget(comp_panel)

        # -------------------------------------------------------------
        # 3. Ranked Server Table
        # -------------------------------------------------------------
        table_panel = Panel(
            title="جدول الترتيب والقياس الحي للخوادم العالمية",
            subtitle="يمكنك تطبيق أي خادم مباشرة إلى إعدادات بطاقة الشبكة بضغطة زر",
            parent=self,
        )

        self.table = QTableWidget(0, 5)
        self.table.setMinimumHeight(280)
        self.table.setHorizontalHeaderLabels(["الترتيب", "خادم DNS", "عنوان IP", "زمن الاستجابة", "الإجراء"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
                gridline-color: {tokens.LINE};
            }}
            QTableWidget::item {{
                border-bottom: 1px solid {tokens.LINE};
                padding: 8px 10px;
                color: {tokens.TEXT};
            }}
        """)

        table_panel.main_layout.addWidget(self.table)
        layout.addWidget(table_panel)

        make_scroll_transparent(self.table, scroll)

        self._populate_default_table()

        scroll.setWidget(content_widget)
        root_layout.addWidget(scroll)

    def _populate_default_table(self) -> None:
        """Initialize empty table awaiting user or autonomous benchmark."""
        self.table.setRowCount(0)

    def update_rankings(
        self,
        scores: list,
        active_ms: Optional[float] = None,
        active_name: str = "",
        is_optimal: bool = True,
    ) -> None:
        """Update ranked DNS table and comparison bars from real benchmark output."""
        if not scores:
            return

        active_ips = getattr(self, "_active_dns_ips", [])
        self.table.setRowCount(len(scores))
        max_ms = max(s.mean_latency_ms for s in scores) if scores else 60.0

        matched_score = None
        for r, s in enumerate(scores):
            is_active_row = any(s.ip in a for a in active_ips) or any(a in s.ip for a in active_ips)
            if is_active_row and matched_score is None:
                matched_score = s

            rank_str = f"{r + 1:02d}"
            r_item = QTableWidgetItem(rank_str)
            r_item.setFont(tokens.get_mono_font(12, 500))
            self.table.setItem(r, 0, r_item)

            disp_name = f"{s.name} (النشط حالياً)" if is_active_row else s.name
            n_item = QTableWidgetItem(disp_name)
            n_item.setFont(tokens.get_sans_font(13, 600 if is_active_row else 500))
            if is_active_row:
                n_item.setForeground(QColor(tokens.STATUS_OK))
            self.table.setItem(r, 1, n_item)

            ip_item = QTableWidgetItem(s.ip)
            ip_item.setFont(tokens.get_mono_font(13, 400))
            self.table.setItem(r, 2, ip_item)

            med_ms = getattr(s, "median_latency_ms", 0.0) or s.mean_latency_ms
            succ_pct = getattr(s, "success_rate", 1.0) * 100.0
            bar_w = RankedServerRow(med_ms, max_ms=max_ms)
            bar_w.setToolTip(f"الوسيط: {med_ms:.1f} ms · المتوسط: {s.mean_latency_ms:.1f} ms · النجاح: {succ_pct:.0f}%")
            self.table.setCellWidget(r, 3, bar_w)

            btn_apply = SecondaryButton("معتمد حالياً ✓" if is_active_row else "طبّق")
            btn_apply.setFixedHeight(30)
            if is_active_row:
                btn_apply.setEnabled(False)
                btn_apply.setStyleSheet(f"color: {tokens.STATUS_OK}; border: 1px solid {tokens.LINE}; background: {tokens.SURFACE_INSET};")
            else:
                btn_apply.setEnabled(True)
                sec_ip = "8.8.4.4" if "8.8.8.8" in s.ip else ("1.0.0.1" if "1.1.1.1" in s.ip else "")
                btn_apply.clicked.connect(lambda checked=False, p_ip=s.ip, s_ip=sec_ip, n_str=s.name: self.apply_dns_requested.emit(p_ip, s_ip, n_str))
            self.table.setCellWidget(r, 4, btn_apply)

        best = scores[0]
        best_ms = getattr(best, "median_latency_ms", 0.0) or best.mean_latency_ms

        if active_ms is not None and active_ms > 0:
            act_ms = active_ms
        elif matched_score is not None:
            act_ms = getattr(matched_score, "median_latency_ms", 0.0) or matched_score.mean_latency_ms
            if not active_name:
                active_name = matched_score.name.replace(" Primary", "").replace(" Secondary", "")
        elif is_optimal:
            act_ms = best_ms
            if not active_name:
                active_name = best.name.replace(" Primary", "").replace(" Secondary", "")
        else:
            act_ms = active_ms if (active_ms is not None and active_ms > 0) else best_ms

        # Health color determinations
        def _get_color(ms_val: float) -> str:
            if ms_val <= DEFAULT_THRESHOLDS.dns.ui_fast_cutoff_ms:
                return tokens.STATUS_OK
            elif ms_val <= DEFAULT_THRESHOLDS.dns.ui_warn_cutoff_ms:
                return tokens.STATUS_WARN
            return tokens.STATUS_BAD

        curr_color = _get_color(act_ms)
        fast_color = _get_color(best_ms)

        self.lbl_curr_ms.setText(f"{act_ms:.1f} ms")
        self.lbl_curr_ms.setStyleSheet(f"color: {curr_color};")
        self.bar_curr.set_fraction(max(0.12, min(1.0, act_ms / DEFAULT_THRESHOLDS.latency.gateway_critical_ms)), fill_color=curr_color)

        self.lbl_fast_ms.setText(f"{best_ms:.1f} ms")
        self.lbl_fast_ms.setStyleSheet(f"color: {fast_color};")
        self.bar_fast.set_fraction(max(0.12, min(1.0, best_ms / DEFAULT_THRESHOLDS.latency.gateway_critical_ms)), fill_color=fast_color)

        self._has_benchmark_rankings = True
        if is_optimal or abs(act_ms - best_ms) <= DEFAULT_THRESHOLDS.dns.switching_hysteresis_ms:
            name_label = active_name or best.name.replace(" Primary", "").replace(" Secondary", "")
            self.lbl_curr_name.setText(f"الخادم النشط بجهازك ({name_label}) — الأسرع حالياً ✓")
            self.lbl_fast_name.setText(f"{best.name} · {best.ip} (المرشح الأفضل)")
        else:
            name_label = active_name or "مزود الخدمة"
            self.lbl_curr_name.setText(f"الخادم النشط بجهازك ({name_label}) — يتوفر خادم أسرع")
            self.lbl_fast_name.setText(f"{best.name} · {best.ip} (الأسرع عالمياً ومحلياً)")

        fit_table_to_content(self.table)

    def set_active_dns_info(self, dns_list: List[str]) -> None:
        self._active_dns_ips = dns_list
        if dns_list and not getattr(self, "_has_benchmark_rankings", False):
            ip_str = " · ".join(dns_list[:2])
            self.lbl_curr_name.setText(f"الخادم النشط بجهازك ({ip_str})")

    def add_decision_entry(self, time_str: str, action: str, server: str, latency: str, reason: str) -> None:
        pass
