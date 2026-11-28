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
    QGridLayout,
    QBoxLayout,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QScrollArea,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from app.ui import tokens
from app.ui.widgets.buttons import PrimaryButton, SecondaryButton
from app.ui.widgets.base_panel import Panel
from app.ui.widgets.bar_row import HorizontalProgressBar
from app.ui.widgets.chip import Chip
from app.core.thresholds import DEFAULT_THRESHOLDS
from app.ui.widgets.scroll_forwarder import make_scroll_transparent, fit_table_to_content
from app.dns.benchmark import generate_dns_analysis
from app.dns.ownership import DnsOwnershipEngine, DnsOwnershipReport, DnsOwnerType


class RankedServerRow(QWidget):
    """Container widget inside table cell showing mono ms and proportional bar."""

    def __init__(self, ms_val: float, is_top: bool = False, is_active: bool = False, max_ms: float = 80.0, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        if ms_val > 0:
            lbl_ms = QLabel(tokens.bidi_isolate(f"{ms_val:.1f} ms"))
            frac = max(0.12, min(1.0, ms_val / max(1.0, max_ms)))
            if is_top or ms_val <= DEFAULT_THRESHOLDS.dns.ui_fast_cutoff_ms:
                color = tokens.STATUS_OK
            elif ms_val <= DEFAULT_THRESHOLDS.dns.ui_warn_cutoff_ms:
                color = tokens.STATUS_WARN
            else:
                color = tokens.STATUS_BAD
        else:
            lbl_ms = QLabel("—")
            frac = 0.0
            color = tokens.STATUS_BAD

        lbl_ms.setFont(tokens.get_mono_font(13, 500))
        lbl_ms.setStyleSheet(f"color: {tokens.TEXT}; background: transparent; border: none;")
        lbl_ms.setFixedWidth(82)
        lbl_ms.setLayoutDirection(Qt.LeftToRight)
        layout.addWidget(lbl_ms)

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
        self._current_layout_mode = "desktop"

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet(f"QScrollArea {{ background-color: {tokens.BG}; border: none; }}")
        self.scroll.viewport().setAutoFillBackground(True)
        self.scroll.viewport().setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.scroll.viewport().setStyleSheet(f"background-color: {tokens.BG};")
        self.scroll.verticalScrollBar().setSingleStep(25)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(
            tokens.PAGE_PADDING_DESKTOP, 24, tokens.PAGE_PADDING_DESKTOP, 32
        )
        self.content_layout.setSpacing(tokens.SECTION_GAP)

        # -------------------------------------------------------------
        # 1. Header & Benchmark Trigger
        # -------------------------------------------------------------
        header_panel = Panel(
            title="خوادم DNS وتحسين سرعة التصفح",
            subtitle="مقارنة فورية لكافة خوادم أسماء المواقع وترتيب الأسرع لجهازك تلقائياً",
            parent=self,
        )

        # Plain language explainer banner (Item B8)
        self.lbl_dns_explainer = QLabel(
            "تغيير DNS يسرّع فتح المواقع الجديدة فقط، ولا يزيد سرعة التحميل. نغيّره تلقائياً إذا كان الخادم الحالي أبطأ بشكل واضح أو فشل."
        )
        self.lbl_dns_explainer.setFont(tokens.get_sans_font(12, 400))
        self.lbl_dns_explainer.setStyleSheet(f"color: {tokens.TEXT_MUTED}; background: transparent; border: none;")
        self.lbl_dns_explainer.setWordWrap(True)
        header_panel.main_layout.addWidget(self.lbl_dns_explainer)

        self.top_h = QBoxLayout(QBoxLayout.LeftToRight)
        self.top_h.setSpacing(12)
        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        self.lbl_last_evaluation = QLabel("آخر تقييم: جاري الفحص الدوري...")
        self.lbl_last_evaluation.setFont(tokens.get_sans_font(13, 400))
        self.lbl_last_evaluation.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_last_evaluation.setWordWrap(True)

        self.lbl_last_switch = QLabel("قرار DNS: جاري القياس")
        self.lbl_last_switch.setFont(tokens.get_sans_font(13, 400))
        self.lbl_last_switch.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_last_switch.setWordWrap(True)

        info_col.addWidget(self.lbl_last_evaluation)
        info_col.addWidget(self.lbl_last_switch)
        self.top_h.addLayout(info_col, stretch=1)

        self.benchmark_btn = PrimaryButton("فحص وترتيب الخوادم الآن")
        self.top_h.addWidget(self.benchmark_btn)

        header_panel.main_layout.addLayout(self.top_h)

        # Cached vs Uncached clarity & Meeting Freeze status strip
        self.lbl_cache_mode_note = QLabel(
            "منهجية القياس: يقارن الفحص استعلامات UDP غير المخزّنة بالكاش (Uncached Query) بنطاقات فريدة لقياس سرعة الخادم الفعلية، ويُجمَّد التبديل التلقائي أثناء المكالمات لحماية استقرار الجلسة."
        )
        self.lbl_cache_mode_note.setFont(tokens.get_sans_font(12, 400))
        self.lbl_cache_mode_note.setStyleSheet(
            f"color: {tokens.TEXT_SECONDARY}; background-color: {tokens.INFO_SOFT_BG}; border: 1px solid {tokens.INFO_BORDER}; border-radius: 6px; padding: 6px 10px;"
        )
        self.lbl_cache_mode_note.setWordWrap(True)
        header_panel.main_layout.addWidget(self.lbl_cache_mode_note)

        self.lbl_dns_freeze_banner = QLabel("")
        self.lbl_dns_freeze_banner.setVisible(False)
        self.lbl_dns_freeze_banner.setFont(tokens.get_sans_font(12, 600))
        self.lbl_dns_freeze_banner.setStyleSheet(
            f"color: {tokens.STATUS_WARN}; background-color: {tokens.WARN_SOFT_BG}; border: 1px solid {tokens.WARN_BORDER}; border-radius: 6px; padding: 6px 10px;"
        )
        self.lbl_dns_freeze_banner.setWordWrap(True)
        header_panel.main_layout.addWidget(self.lbl_dns_freeze_banner)
        self.content_layout.addWidget(header_panel)

        # -------------------------------------------------------------
        # 1.5 Current Active DNS Resolver Card (Authoritative Identity)
        # -------------------------------------------------------------
        self.active_dns_panel = Panel(
            title="خادم DNS المعتمد بجهازك حالياً",
            subtitle="البيانات المكتشفة فعلياً من بطاقة الشبكة النشطة وزمن استجابتها الحقيقي",
            parent=self,
        )

        curr_card_frame = QFrame()
        curr_card_frame.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border: none;
            }}
            QFrame QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        curr_card_layout = QVBoxLayout(curr_card_frame)
        curr_card_layout.setContentsMargins(18, 14, 18, 14)
        curr_card_layout.setSpacing(12)

        def _make_stat_box(title: str):
            frame = QFrame()
            frame.setStyleSheet("background: transparent; border: none;")
            box = QVBoxLayout(frame)
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(2)
            lbl_t = QLabel(title)
            lbl_t.setFont(tokens.get_sans_font(12, 400))
            lbl_t.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            lbl_t.setWordWrap(True)
            lbl_v = QLabel("—")
            lbl_v.setFont(tokens.get_sans_font(14, 600))
            lbl_v.setStyleSheet(f"color: {tokens.TEXT};")
            lbl_v.setWordWrap(True)
            box.addWidget(lbl_t)
            box.addWidget(lbl_v)
            return frame, lbl_v

        self.box_prov, self.lbl_active_provider = _make_stat_box("المزود")
        self.box_ip, self.lbl_active_ip = _make_stat_box("عنوان الخادم")
        self.lbl_active_ip.setFont(tokens.get_mono_font(14, 500))
        self.box_ms, self.lbl_active_ms_stat = _make_stat_box("زمن الاستجابة المقاس")
        self.lbl_active_ms_stat.setFont(tokens.get_mono_font(14, 600))
        self.box_st, self.lbl_active_status_stat = _make_stat_box("الحالة والنجاح")

        self.grid_curr = QGridLayout()
        self.grid_curr.setSpacing(14)
        self.grid_curr.addWidget(self.box_prov, 0, 0)
        self.grid_curr.addWidget(self.box_ip, 0, 1)
        self.grid_curr.addWidget(self.box_ms, 0, 2)
        self.grid_curr.addWidget(self.box_st, 0, 3)
        curr_card_layout.addLayout(self.grid_curr)

        lbl_distinct_note = QLabel("هذا هو خادم DNS الذي يستخدمه جهازك حالياً لترجمة أسماء النطاقات، وليس مجرد خادم DNS مقترح.")
        lbl_distinct_note.setFont(tokens.get_sans_font(12, 400))
        lbl_distinct_note.setStyleSheet(f"color: {tokens.TEXT_MUTED}; background: transparent; border: none;")
        lbl_distinct_note.setWordWrap(True)
        curr_card_layout.addWidget(lbl_distinct_note)

        self.active_dns_panel.main_layout.addWidget(curr_card_frame)
        self.content_layout.addWidget(self.active_dns_panel)

        # -------------------------------------------------------------
        # 1.6 DNS Ownership & Configuration Intelligence Panel (Phase 3 & 8.2)
        # -------------------------------------------------------------
        self.ownership_panel = Panel(
            title="من يتحكم في إعدادات DNS الآن",
            subtitle="مصدر الإعداد الفعلي: بطاقة الشبكة، الراوتر، أو سياسة النظام",
            parent=self,
        )

        own_card_frame = QFrame()
        own_card_frame.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border: none;
            }}
            QFrame QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        own_card_layout = QVBoxLayout(own_card_frame)
        own_card_layout.setContentsMargins(18, 14, 18, 14)
        own_card_layout.setSpacing(18)

        # Header inside card: Title + Chip + Confidence
        own_head = QHBoxLayout()
        self.lbl_owner_title = QLabel("جاري اكتشاف الجهة المتحكمة في DNS...")
        self.lbl_owner_title.setFont(tokens.get_sans_font(14, 600))
        self.lbl_owner_title.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_owner_title.setWordWrap(True)
        own_head.addWidget(self.lbl_owner_title, stretch=1)

        self.chip_owner_type = Chip(text="جاري الفحص", variant="tag-ok")
        own_head.addWidget(self.chip_owner_type)

        self.lbl_owner_confidence = QLabel("دقة التحقق: —")
        self.lbl_owner_confidence.setFont(tokens.get_sans_font(12, 400))
        self.lbl_owner_confidence.setStyleSheet(f"color: {tokens.TEXT_MUTED}; margin-right: 8px;")
        own_head.addWidget(self.lbl_owner_confidence)
        own_card_layout.addLayout(own_head)

        # Summary text
        self.lbl_owner_summary = QLabel("يتم جمع وتدقيق بيانات بطاقة الشبكة والراوتر وتطبيقات الأمان للتحقق من مصدر التكوين...")
        self.lbl_owner_summary.setFont(tokens.get_sans_font(13, 400))
        self.lbl_owner_summary.setStyleSheet(f"color: {tokens.TEXT_SECONDARY}; line-height: 1.5;")
        self.lbl_owner_summary.setWordWrap(True)
        own_card_layout.addWidget(self.lbl_owner_summary)

        # Grid of details
        self.box_own_ad, self.lbl_own_adapter = _make_stat_box("بطاقة الشبكة")
        self.box_own_md, self.lbl_own_modes = _make_stat_box("طريقة الإعداد")
        self.box_own_gw, self.lbl_own_gateway = _make_stat_box("البوابة والراوتر")
        self.box_own_ap, self.lbl_own_apps = _make_stat_box("التطبيقات والسياسات")
        for _box in (self.box_own_ad, self.box_own_md, self.box_own_gw, self.box_own_ap):
            _box.setMinimumHeight(76)
            _box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.grid_own = QGridLayout()
        self.grid_own.setSpacing(16)
        self.grid_own.addWidget(self.box_own_ad, 0, 0)
        self.grid_own.addWidget(self.box_own_md, 0, 1)
        self.grid_own.addWidget(self.box_own_gw, 1, 0)
        self.grid_own.addWidget(self.box_own_ap, 1, 1)
        own_card_layout.addLayout(self.grid_own)

        # Transparent Limitations & Scope Box
        self.lbl_own_limitations = QLabel("الحدود والشفافية التقنية: لا يمكن التحقق من الخادم الحقيقي خلف الراوتر دون صلاحيات دخول إدارية معتمدة.")
        self.lbl_own_limitations.setFont(tokens.get_sans_font(12, 400))
        self.lbl_own_limitations.setStyleSheet(f"color: {tokens.TEXT_MUTED}; background: transparent; border: none;")
        self.lbl_own_limitations.setWordWrap(True)
        self.lbl_own_limitations.setMinimumHeight(86)
        self.lbl_own_limitations.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        own_card_layout.addWidget(self.lbl_own_limitations)

        self.ownership_panel.main_layout.addWidget(own_card_frame)
        self.content_layout.addWidget(self.ownership_panel)

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
        self.lbl_curr_name.setWordWrap(True)
        self.lbl_curr_name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lbl_curr_ms = QLabel("—")
        self.lbl_curr_ms.setFont(tokens.get_mono_font(14, 500))
        self.lbl_curr_ms.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_curr_ms.setFixedWidth(112)
        self.lbl_curr_ms.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        curr_top.addWidget(self.lbl_curr_name)
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
        self.lbl_fast_name.setWordWrap(True)
        self.lbl_fast_name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lbl_fast_ms = QLabel("—")
        self.lbl_fast_ms.setFont(tokens.get_mono_font(14, 500))
        self.lbl_fast_ms.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_fast_ms.setFixedWidth(112)
        self.lbl_fast_ms.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        fast_top.addWidget(self.lbl_fast_name)
        fast_top.addWidget(self.lbl_fast_ms)
        fast_row.addLayout(fast_top)

        self.bar_fast = HorizontalProgressBar(height=8, fill_color=tokens.STATUS_OK)
        self.bar_fast.set_fraction(0.0)
        fast_row.addWidget(self.bar_fast)
        bars_col.addLayout(fast_row)

        comp_panel.main_layout.addLayout(bars_col)
        self.content_layout.addWidget(comp_panel)

        # -------------------------------------------------------------
        # 3. Ranked Server Table
        # -------------------------------------------------------------
        table_panel = Panel(
            title="جدول الترتيب والقياس الحي للخوادم العالمية",
            subtitle="يمكنك تطبيق أي خادم مباشرة إلى إعدادات بطاقة الشبكة بضغطة زر",
            parent=self,
        )

        self.table = QTableWidget(0, 8)
        self.table.setMinimumHeight(280)
        self.table.setHorizontalHeaderLabels([
            "الترتيب",
            "مزود DNS",
            "العنوان الأساسي",
            "العنوان الاحتياطي",
            "زمن الاستجابة",
            "حالة التوفر",
            "التكوين الحالي",
            "الإجراء",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 55)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setMinimumSectionSize(50)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 160)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 160)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 160)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 126)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 115)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 126)
        self.table.horizontalHeader().setMinimumHeight(46)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(54)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
                gridline-color: transparent;
                font-size: 14px;
            }}
            QTableWidget::item {{
                border: none;
                padding: 4px 6px;
                color: {tokens.TEXT};
                background: transparent;
            }}
            QTableWidget QWidget {{
                background: transparent;
                border: none;
            }}
        """)

        table_panel.main_layout.addWidget(self.table)
        self.content_layout.addWidget(table_panel)

        make_scroll_transparent(self.table, self.scroll)

        # -------------------------------------------------------------
        # 4. Intelligent DNS Analysis & Recommendation Panel
        # -------------------------------------------------------------
        self.analysis_panel = Panel(
            title="التحليل الذكي والتوصيات الفنية",
            subtitle="تقييم واقعي مبني على الاختبارات الفعلية للترجمة وسرعة الاستجابة",
            parent=self,
        )

        analysis_frame = QFrame()
        analysis_frame.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border: none;
            }}
            QFrame QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        an_layout = QVBoxLayout(analysis_frame)
        an_layout.setContentsMargins(18, 14, 18, 14)
        an_layout.setSpacing(10)

        self.lbl_an_curr_title = QLabel("تحليل خادم DNS الحالي")
        self.lbl_an_curr_title.setFont(tokens.get_sans_font(14, 600))
        self.lbl_an_curr_title.setStyleSheet(f"color: {tokens.TEXT};")
        an_layout.addWidget(self.lbl_an_curr_title)

        self.lbl_curr_analysis = QLabel("جاري تقييم استجابة ونسبة نجاح استعلامات خادم DNS الحالي...")
        self.lbl_curr_analysis.setFont(tokens.get_sans_font(13, 400))
        self.lbl_curr_analysis.setStyleSheet(f"color: {tokens.TEXT_SECONDARY}; line-height: 1.6;")
        self.lbl_curr_analysis.setWordWrap(True)
        an_layout.addWidget(self.lbl_curr_analysis)

        self.lbl_an_alt_title = QLabel("تحليل الخوادم البديلة")
        self.lbl_an_alt_title.setFont(tokens.get_sans_font(14, 600))
        self.lbl_an_alt_title.setStyleSheet(f"color: {tokens.TEXT}; margin-top: 6px;")
        an_layout.addWidget(self.lbl_an_alt_title)

        self.lbl_alt_analysis = QLabel("جاري فحص ومقارنة الخوادم البديلة المتاحة...")
        self.lbl_alt_analysis.setFont(tokens.get_sans_font(13, 400))
        self.lbl_alt_analysis.setStyleSheet(f"color: {tokens.TEXT_SECONDARY}; line-height: 1.6;")
        self.lbl_alt_analysis.setWordWrap(True)
        an_layout.addWidget(self.lbl_alt_analysis)

        self.lbl_smart_rec = QLabel("التوصية: الخادم الحالي قيد المراقبة.")
        self.lbl_smart_rec.setFont(tokens.get_sans_font(13, 600))
        self.lbl_smart_rec.setStyleSheet(f"color: {tokens.STATUS_OK}; background: transparent; border: none;")
        self.lbl_smart_rec.setWordWrap(True)
        self.lbl_smart_rec.setMinimumHeight(56)
        self.lbl_smart_rec.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        an_layout.addWidget(self.lbl_smart_rec)

        self.analysis_panel.main_layout.addWidget(analysis_frame)
        self.content_layout.addWidget(self.analysis_panel)

        # Decision & Benchmark History Ledger (populated by add_decision_entry)
        self.history_panel = Panel(
            title="سجل قرارات وتبديلات DNS / Benchmark & Rollback History",
            subtitle="توثيق فحوصات الاستجابة، التبديلات المعتمدة، وحالات التراجع الآمن",
            parent=self,
        )
        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["الوقت", "الإجراء", "الخادم", "الاستجابة", "السبب / التحقق"])
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setMaximumHeight(200)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_panel.main_layout.addWidget(self.history_table)
        self.content_layout.addWidget(self.history_panel)

        self._populate_default_table()

        # Connect to central DNS single source of truth
        try:
            from app.dns.state import DnsStateManager
            DnsStateManager.get_instance().state_changed.connect(self._on_dns_state_changed)
        except Exception:
            pass

        self.scroll.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll)

    def _populate_default_table(self) -> None:
        """Populate initial DNS resolver catalog awaiting benchmark evaluation."""
        from app.dns.benchmark import get_default_benchmark_resolvers
        from app.dns.detector import get_secondary_ip
        resolvers = get_default_benchmark_resolvers()
        self.table.clearContents()
        self.table.setRowCount(len(resolvers))
        active_ips = getattr(self, "_active_dns_ips", [])
        primary_ip = active_ips[0] if active_ips else ""

        for r, (ip, name) in enumerate(resolvers):
            sec_ip = get_secondary_ip(ip) or ""
            is_prim = bool(primary_ip and (ip == primary_ip or ip in primary_ip or primary_ip in ip))
            is_fall = bool(not is_prim and any(ip == a or ip in a for a in active_ips))

            # Col 0: Rank
            r_item = QTableWidgetItem(f"{r + 1:02d}")
            r_item.setFont(tokens.get_mono_font(14, 500))
            r_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 0, r_item)

            # Col 1: Provider Name
            n_item = QTableWidgetItem(tokens.bidi_isolate(name))
            n_item.setFont(tokens.get_sans_font(14, 600 if is_prim else 500))
            if is_prim:
                n_item.setForeground(QColor(tokens.STATUS_OK))
            elif is_fall:
                n_item.setForeground(QColor(tokens.TEXT_MUTED))
            self.table.setItem(r, 1, n_item)

            # Col 2: Primary IP
            p_item = QTableWidgetItem(tokens.bidi_isolate(ip))
            p_item.setFont(tokens.get_mono_font(14, 400))
            p_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 2, p_item)

            # Col 3: Secondary IP
            s_item = QTableWidgetItem(tokens.bidi_isolate(sec_ip) if sec_ip else "—")
            s_item.setFont(tokens.get_mono_font(14, 400))
            s_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 3, s_item)

            # Col 4: Latency placeholder
            lbl_pending = QLabel("بانتظار الفحص...")
            lbl_pending.setFont(tokens.get_sans_font(12, 400))
            lbl_pending.setStyleSheet(f"color: {tokens.TEXT_MUTED}; background: transparent; border: none; padding: 0 6px;")
            self.table.setCellWidget(r, 4, lbl_pending)

            # Col 5: Availability placeholder
            chip_box = QWidget()
            chip_box.setStyleSheet("background: transparent; border: none;")
            chip_layout = QHBoxLayout(chip_box)
            chip_layout.setContentsMargins(2, 2, 2, 2)
            chip_layout.setAlignment(Qt.AlignCenter)
            ch = Chip("بانتظار الفحص", variant="neutral")
            chip_layout.addWidget(ch)
            self.table.setCellWidget(r, 5, chip_box)

            # Col 6: Current Configuration
            if is_prim:
                cfg_text = "الأساسي المعتمد"
                cfg_color = tokens.STATUS_OK
            elif is_fall:
                cfg_text = "احتياطي مسجل"
                cfg_color = tokens.TEXT_MUTED
            else:
                cfg_text = "—"
                cfg_color = tokens.TEXT_MUTED
            cfg_item = QTableWidgetItem(cfg_text)
            cfg_item.setFont(tokens.get_sans_font(14, 500))
            cfg_item.setForeground(QColor(cfg_color))
            cfg_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 6, cfg_item)

            # Col 7: Action Button
            if is_prim:
                btn_apply = SecondaryButton("معتمد حالياً ✓")
                btn_apply.setFixedHeight(36)
                btn_apply.setFixedWidth(102)
                btn_apply.setEnabled(False)
                btn_apply.setStyleSheet(f"""
                    QPushButton {{
                        color: {tokens.STATUS_OK};
                        border: 1px solid rgba(46, 204, 113, 0.45);
                        background-color: transparent;
                        border-radius: {tokens.RADIUS_BUTTON}px;
                        font-size: 12px;
                        font-weight: 600;
                    }}
                """)
            elif is_fall:
                btn_apply = SecondaryButton("عيّن كأساسي")
                btn_apply.setFixedHeight(36)
                btn_apply.setFixedWidth(102)
                btn_apply.setEnabled(True)
                btn_apply.clicked.connect(lambda checked=False, p_ip=ip, s_ip=sec_ip, n_str=name: self._handle_apply_click(p_ip, s_ip, n_str))
            else:
                btn_apply = SecondaryButton("طبّق")
                btn_apply.setFixedHeight(36)
                btn_apply.setFixedWidth(102)
                btn_apply.setEnabled(True)
                btn_apply.clicked.connect(lambda checked=False, p_ip=ip, s_ip=sec_ip, n_str=name: self._handle_apply_click(p_ip, s_ip, n_str))

            btn_box = QWidget()
            btn_box.setStyleSheet("background: transparent; border: none;")
            btn_layout = QHBoxLayout(btn_box)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setAlignment(Qt.AlignCenter)
            btn_layout.addWidget(btn_apply)
            self.table.setCellWidget(r, 7, btn_box)

    def _handle_apply_click(self, p_ip: str, s_ip: str, name: str) -> None:
        """Handle apply button click: provide immediate visual feedback and emit signal."""
        sender = self.sender()
        if isinstance(sender, QPushButton):
            sender.setEnabled(False)
            sender.setText("جاري التطبيق...")
        self.apply_dns_requested.emit(p_ip, s_ip, name)

    def update_rankings(
        self,
        scores: list,
        active_ms: Optional[float] = None,
        active_name: str = "",
        is_optimal: bool = True,
    ) -> None:
        """Update ranked DNS table, comparison bars, and intelligent analysis from real benchmark."""
        if not scores:
            return

        active_ips = getattr(self, "_active_dns_ips", [])
        primary_ip = active_ips[0] if active_ips else ""
        active_ip_str = primary_ip
        fingerprint = (
            primary_ip,
            active_name,
            None if active_ms is None else round(float(active_ms), 1),
            bool(is_optimal),
            tuple(
                (
                    s.ip,
                    round(float(getattr(s, "median_latency_ms", 0.0) or s.mean_latency_ms), 1),
                    round(float(s.success_rate), 2),
                )
                for s in scores
            ),
        )
        if fingerprint == getattr(self, "_rank_fingerprint", None):
            return
        self._rank_fingerprint = fingerprint
        for old_r in range(self.table.rowCount()):
            for old_c in (4, 5):
                old_w = self.table.cellWidget(old_r, old_c)
                if old_w is not None:
                    self.table.removeCellWidget(old_r, old_c)
                    old_w.setParent(None)
                    old_w.deleteLater()
        self.table.clearContents()
        self.table.setRowCount(len(scores))
        max_ms = max((getattr(s, "median_latency_ms", 0.0) or s.mean_latency_ms) for s in scores) if scores else 60.0

        # Match primary score strictly by primary_ip
        matched_score = None
        if primary_ip:
            for s in scores:
                if s.ip == primary_ip:
                    matched_score = s
                    break

        for r, s in enumerate(scores):
            p_ip = getattr(s, "primary_ip", None) or s.ip
            s_ip = getattr(s, "secondary_ip", None) or ""
            if not s_ip:
                from app.dns.detector import get_secondary_ip
                s_ip = get_secondary_ip(p_ip) or ""

            is_prim_row = bool(primary_ip and (p_ip == primary_ip or p_ip in primary_ip or primary_ip in p_ip))
            is_fall_row = bool(not is_prim_row and any(p_ip == a or p_ip in a for a in active_ips))

            # Col 0: Rank
            rank_str = f"{r + 1:02d}"
            r_item = QTableWidgetItem(rank_str)
            r_item.setFont(tokens.get_mono_font(14, 500))
            r_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 0, r_item)

            # Col 1: Provider Name
            prov_name = getattr(s, "provider_name", None) or s.name
            short_name = (
                prov_name.replace(" Primary", "")
                .replace(" Secondary", "")
                .replace(" Secure", "")
            )

            n_item = QTableWidgetItem(tokens.bidi_isolate(short_name))
            n_item.setToolTip(s.name)
            n_item.setFont(tokens.get_sans_font(14, 600 if is_prim_row else 500))
            if is_prim_row:
                n_item.setForeground(QColor(tokens.STATUS_OK))
            elif is_fall_row:
                n_item.setForeground(QColor(tokens.TEXT_MUTED))
            self.table.setItem(r, 1, n_item)

            # Col 2: Primary IP
            p_item = QTableWidgetItem(tokens.bidi_isolate(p_ip))
            p_item.setFont(tokens.get_mono_font(14, 400))
            p_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 2, p_item)

            # Col 3: Secondary IP
            s_item = QTableWidgetItem(tokens.bidi_isolate(s_ip) if s_ip else "—")
            s_item.setFont(tokens.get_mono_font(14, 400))
            s_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 3, s_item)

            # Col 4: Latency Bar Row
            med_ms = getattr(s, "median_latency_ms", 0.0) or s.mean_latency_ms
            succ_pct = getattr(s, "success_rate", 1.0) * 100.0
            bar_w = RankedServerRow(med_ms, max_ms=max_ms)
            bar_w.setToolTip(f"الوسيط: {med_ms:.1f} ms · المتوسط: {s.mean_latency_ms:.1f} ms · النجاح: {succ_pct:.0f}%")
            self.table.setCellWidget(r, 4, bar_w)

            # Col 5: Availability Status Chip
            chip_box = QWidget()
            chip_box.setStyleSheet("background: transparent; border: none;")
            chip_layout = QHBoxLayout(chip_box)
            chip_layout.setContentsMargins(2, 2, 2, 2)
            chip_layout.setAlignment(Qt.AlignCenter)
            if succ_pct <= 0 or med_ms <= 0:
                ch = Chip("غير متاح", variant="tag-bad")
            elif succ_pct < 100:
                ch = Chip(f"فقد {100-succ_pct:.0f}%", variant="tag-warn")
            elif med_ms <= 45.0:
                ch = Chip("ممتاز وسريع", variant="ok-soft")
            elif med_ms <= 85.0:
                ch = Chip("مستقر", variant="neutral")
            else:
                ch = Chip("استجابة بطيئة", variant="tag-warn")
            chip_layout.addWidget(ch)
            self.table.setCellWidget(r, 5, chip_box)

            # Col 6: Current Configuration
            if is_prim_row:
                cfg_text = "الأساسي المعتمد"
                cfg_color = tokens.STATUS_OK
            elif is_fall_row:
                cfg_text = "احتياطي مسجل"
                cfg_color = tokens.TEXT_MUTED
            else:
                cfg_text = "—"
                cfg_color = tokens.TEXT_MUTED
            cfg_item = QTableWidgetItem(cfg_text)
            cfg_item.setFont(tokens.get_sans_font(14, 500))
            cfg_item.setForeground(QColor(cfg_color))
            cfg_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 6, cfg_item)

            # Col 7: Action Button
            if is_prim_row:
                btn_apply = SecondaryButton("معتمد حالياً ✓")
                btn_apply.setFixedHeight(36)
                btn_apply.setFixedWidth(102)
                btn_apply.setEnabled(False)
                btn_apply.setStyleSheet(f"""
                    QPushButton {{
                        color: {tokens.STATUS_OK};
                        border: 1px solid rgba(46, 204, 113, 0.45);
                        background-color: transparent;
                        border-radius: {tokens.RADIUS_BUTTON}px;
                        font-size: 12px;
                        font-weight: 600;
                    }}
                """)
            elif is_fall_row:
                btn_apply = SecondaryButton("عيّن كأساسي")
                btn_apply.setFixedHeight(36)
                btn_apply.setFixedWidth(102)
                btn_apply.setEnabled(True)
                btn_apply.clicked.connect(lambda checked=False, p=p_ip, sec=s_ip, n=short_name: self._handle_apply_click(p, sec, n))
            else:
                btn_apply = SecondaryButton("طبّق")
                btn_apply.setFixedHeight(36)
                btn_apply.setFixedWidth(102)
                btn_apply.setEnabled(True)
                btn_apply.clicked.connect(lambda checked=False, p=p_ip, sec=s_ip, n=short_name: self._handle_apply_click(p, sec, n))

            btn_box = QWidget()
            btn_box.setStyleSheet("background: transparent; border: none;")
            btn_layout = QHBoxLayout(btn_box)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setAlignment(Qt.AlignCenter)
            btn_layout.addWidget(btn_apply)
            self.table.setCellWidget(r, 7, btn_box)

        from app.dns.optimizer import select_best_resolver
        best = select_best_resolver(scores) or scores[0]
        best_ms = getattr(best, "median_latency_ms", 0.0) or best.mean_latency_ms

        # Determine authentic active latency without replacing with best_ms
        if active_ms is not None and active_ms > 0:
            act_ms = active_ms
        elif matched_score is not None:
            act_ms = getattr(matched_score, "median_latency_ms", 0.0) or matched_score.mean_latency_ms
        else:
            act_ms = 0.0

        if not active_name:
            if matched_score:
                active_name = matched_score.name.replace(" Primary", "").replace(" Secondary", "")
            else:
                active_name = "خادم مخصص"

        # Health color determinations
        def _get_color(ms_val: float) -> str:
            if ms_val <= 0.0:
                return tokens.TEXT_MUTED
            if ms_val <= DEFAULT_THRESHOLDS.dns.ui_fast_cutoff_ms:
                return tokens.STATUS_OK
            elif ms_val <= DEFAULT_THRESHOLDS.dns.ui_warn_cutoff_ms:
                return tokens.STATUS_WARN
            return tokens.STATUS_BAD

        curr_color = _get_color(act_ms)
        fast_color = _get_color(best_ms)

        # Update Current Active DNS Card
        self.lbl_active_provider.setText(active_name)
        self.lbl_active_ip.setText(active_ip_str or (matched_score.ip if matched_score else "—"))
        if act_ms > 0:
            self.lbl_active_ms_stat.setText(f"{act_ms:.1f} ms")
            self.lbl_active_ms_stat.setStyleSheet(f"color: {curr_color};")
            succ_r = (getattr(matched_score, "success_rate", 1.0) * 100.0) if matched_score else 100.0
            st_text = "يعمل بكفاءة" if act_ms < 60.0 else ("استجابة مقبولة" if act_ms < 120.0 else "استجابة بطيئة")
            self.lbl_active_status_stat.setText(f"{st_text} ({succ_r:.0f}% نجاح)")
            self.lbl_active_status_stat.setStyleSheet(f"color: {curr_color};")
        else:
            self.lbl_active_ms_stat.setText("—")
            self.lbl_active_status_stat.setText("غير مستجيب / غير مقاس")
            self.lbl_active_status_stat.setStyleSheet(f"color: {tokens.STATUS_BAD};")

        # Update Comparison Bars
        if act_ms > 0:
            self.lbl_curr_ms.setText(f"{act_ms:.1f} ms")
            self.lbl_curr_ms.setStyleSheet(f"color: {curr_color};")
            self.bar_curr.set_fraction(max(0.12, min(1.0, act_ms / DEFAULT_THRESHOLDS.latency.gateway_critical_ms)), fill_color=curr_color)
        else:
            self.lbl_curr_ms.setText("—")
            self.lbl_curr_ms.setStyleSheet(f"color: {tokens.STATUS_BAD};")
            self.bar_curr.set_fraction(0.0)

        self.lbl_fast_ms.setText(f"{best_ms:.1f} ms")
        self.lbl_fast_ms.setStyleSheet(f"color: {fast_color};")
        self.bar_fast.set_fraction(max(0.12, min(1.0, best_ms / DEFAULT_THRESHOLDS.latency.gateway_critical_ms)), fill_color=fast_color)

        self._has_benchmark_rankings = True
        diff_ms = act_ms - best_ms

        best_desc = f"{best.name} ({best.ip})"
        is_truly_fastest = (act_ms > 0 and act_ms <= best_ms)

        disp_act = f"{active_name} ({active_ip_str})" if active_ip_str else active_name
        if is_truly_fastest:
            self.lbl_curr_name.setText(f"خادمك الحالي ({disp_act}) — الأسرع حالياً ✓")
            self.lbl_fast_name.setText(f"أقرب خادم بديل: {best_desc}")
        elif diff_ms > 0:
            self.lbl_curr_name.setText(f"خادمك الحالي ({disp_act}) أبطأ بـ {diff_ms:.1f} ms")
            self.lbl_fast_name.setText(f"المقترح (هيتم التحويل): {best_desc}")
        else:
            self.lbl_curr_name.setText(f"خادمك الحالي ({disp_act})")
            self.lbl_fast_name.setText(best_desc)

        # Update Intelligent Analysis & Recommendation Panel
        try:
            analysis = generate_dns_analysis(active_ip_str, active_name, matched_score, scores)
            cur_an = analysis.get("current", {})
            alt_an = analysis.get("alternative", {})
            rec_an = analysis.get("recommendation", {})

            self.lbl_curr_analysis.setText(
                f"• الخادم المستخدم حالياً: {cur_an.get('name')} ({cur_an.get('ip')})\n"
                f"• متوسط زمن الاستجابة: {cur_an.get('mean_ms', 0):.1f} ms (أدنى: {cur_an.get('min_ms', 0):.1f} ms · أقصى: {cur_an.get('max_ms', 0):.1f} ms)\n"
                f"• الحالة: {cur_an.get('status_tag')} (نسبة نجاح الاستعلامات {cur_an.get('success_rate_pct', 100):.0f}%)\n"
                f"• النتيجة: {cur_an.get('verdict')}"
            )

            cand_ms = alt_an.get('candidate_ms') or 0.0
            cand_diff = alt_an.get('diff_ms') or 0.0
            self.lbl_alt_analysis.setText(
                f"• أفضل خادم بديل: {alt_an.get('candidate_name')} ({alt_an.get('candidate_ip')})\n"
                f"• متوسط الاستجابة: {cand_ms:.1f} ms (نسبة النجاح: {alt_an.get('candidate_success_pct', 100):.0f}%)\n"
                f"• فارق السرعة مع خادمك الحالي: {'+' if cand_diff > 0 else ''}{cand_diff:.1f} ms"
            )

            rec_text = rec_an.get("text", "")
            self.lbl_smart_rec.setText(f"التوصية الذكية: {rec_text}")
            if rec_an.get("should_switch"):
                self.lbl_smart_rec.setStyleSheet(f"color: {tokens.STATUS_WARN}; background: transparent; border: none;")
            else:
                self.lbl_smart_rec.setStyleSheet(f"color: {tokens.STATUS_OK}; background: transparent; border: none;")
        except Exception:
            pass

        self.table.doItemsLayout()
        self.table.updateGeometries()
        fit_table_to_content(self.table)

    def set_active_dns_info(self, dns_list: List[str]) -> None:
        self._active_dns_ips = dns_list
        if dns_list:
            ip_str = " · ".join(dns_list[:2])
            if hasattr(self, "lbl_active_ip"):
                self.lbl_active_ip.setText(ip_str)
            if hasattr(self, "lbl_active_provider"):
                from app.dns.detector import identify_provider
                prov = identify_provider(dns_list[0]) or f"خادم مخصص ({dns_list[0]})"
                self.lbl_active_provider.setText(prov)
            if hasattr(self, "lbl_active_ms_stat") and self.lbl_active_ms_stat.text() == "—":
                self.lbl_active_ms_stat.setText("جاري الفحص...")
                self.lbl_active_ms_stat.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            if hasattr(self, "lbl_active_status_stat") and self.lbl_active_status_stat.text() == "—":
                self.lbl_active_status_stat.setText("نشط قيد الفحص")
                self.lbl_active_status_stat.setStyleSheet(f"color: {tokens.STATUS_OK};")
            if not getattr(self, "_has_benchmark_rankings", False):
                self.lbl_curr_name.setText(f"الخادم النشط بجهازك ({ip_str})")
                primary_ip = dns_list[0] if dns_list else ""
                # Update initial table active indicator
                for r in range(self.table.rowCount()):
                    item_ip = self.table.item(r, 2)
                    if not item_ip:
                        continue
                    ip_val = item_ip.text()
                    is_prim = bool(primary_ip and (ip_val == primary_ip or ip_val in primary_ip or primary_ip in ip_val))
                    is_fall = bool(not is_prim and any(ip_val == a or ip_val in a for a in dns_list))
                    item_n = self.table.item(r, 1)
                    cfg_item = self.table.item(r, 6)
                    cell_w = self.table.cellWidget(r, 7)
                    btn = cell_w.findChild(QPushButton) if cell_w else None

                    if is_prim:
                        if item_n:
                            clean_n = item_n.text().replace(" (النشط حالياً)", "").replace(" (احتياطي مسجل)", "").replace(" (الأساسي النشط)", "")
                            item_n.setText(clean_n)
                            item_n.setForeground(QColor(tokens.STATUS_OK))
                        if cfg_item:
                            cfg_item.setText("الأساسي المعتمد")
                            cfg_item.setForeground(QColor(tokens.STATUS_OK))
                        if btn:
                            btn.setText("معتمد حالياً ✓")
                            btn.setEnabled(False)
                            btn.setStyleSheet(f"""
                                QPushButton {{
                                    color: {tokens.STATUS_OK};
                                    border: 1px solid rgba(46, 204, 113, 0.45);
                                    background-color: transparent;
                                    border-radius: {tokens.RADIUS_BUTTON}px;
                                    font-size: 12px;
                                    font-weight: 600;
                                }}
                            """)
                    elif is_fall:
                        if item_n:
                            clean_n = item_n.text().replace(" (النشط حالياً)", "").replace(" (الأساسي النشط)", "").replace(" (احتياطي مسجل)", "")
                            item_n.setText(clean_n)
                            item_n.setForeground(QColor(tokens.TEXT_MUTED))
                        if cfg_item:
                            cfg_item.setText("احتياطي مسجل")
                            cfg_item.setForeground(QColor(tokens.TEXT_MUTED))
                        if btn:
                            btn.setText("عيّن كأساسي")
                            btn.setEnabled(True)
                            btn.setStyleSheet("")
                    else:
                        if cfg_item:
                            cfg_item.setText("—")
                            cfg_item.setForeground(QColor(tokens.TEXT_MUTED))

    def set_benchmark_error(self, error_msg: str) -> None:
        """Display clear error state when DNS benchmark encounters an issue."""
        if hasattr(self, "lbl_last_evaluation"):
            self.lbl_last_evaluation.setText(f"آخر تقييم: تعذر الفحص ({error_msg})")
        if hasattr(self, "lbl_curr_analysis"):
            self.lbl_curr_analysis.setText(f"تعذر استكمال فحص خوادم DNS: {error_msg}. يرجى التحقق من اتصال الإنترنت.")

    def update_ownership_report(self, report: DnsOwnershipReport) -> None:
        """Update the DNS Configuration Intelligence panel with evidence-backed findings."""
        if not report:
            return

        if hasattr(self, "lbl_owner_title"):
            self.lbl_owner_title.setText(f"الجهة المتحكمة: {report.owner_title}")
        if hasattr(self, "lbl_owner_summary"):
            self.lbl_owner_summary.setText(report.summary_arabic)
        if hasattr(self, "lbl_owner_confidence"):
            self.lbl_owner_confidence.setText(f"دقة التحقق: {report.confidence_score * 100:.0f}%")

        if hasattr(self, "chip_owner_type"):
            if report.owner_type in (DnsOwnerType.STATIC_ADAPTER, DnsOwnerType.ISP_DHCP):
                chip_variant = "ok-soft"
                chip_text = "إعدادات بطاقة مباشرة"
            elif report.owner_type == DnsOwnerType.ROUTER_DHCP_RELAY:
                chip_variant = "tag-warn"
                chip_text = "راوتر منزلي (Relay)"
            elif report.owner_type in (DnsOwnerType.LOCAL_PROXY, DnsOwnerType.THIRD_PARTY_SECURITY):
                chip_variant = "tag-warn"
                chip_text = "وكيل محلي (Local Proxy)"
            elif report.owner_type == DnsOwnerType.VPN_TUNNEL:
                chip_variant = "tag-warn"
                chip_text = "نفق VPN مشفر"
            elif report.owner_type == DnsOwnerType.ENTERPRISE_NRPT:
                chip_variant = "tag-warn"
                chip_text = "سياسة مؤسسية (NRPT)"
            else:
                chip_variant = "neutral"
                chip_text = "غير محدد بدقة"
            self.chip_owner_type.set_variant(chip_variant, chip_text)

        if hasattr(self, "lbl_own_adapter"):
            v_type = "افتراضي" if report.is_virtual_adapter else "فيزيائي"
            self.lbl_own_adapter.setText(f"{report.interface_alias} ({v_type})")

        if hasattr(self, "lbl_own_modes"):
            m_v4 = "ثابت (Static)" if report.ipv4_mode == "static" else "تلقائي (DHCP)"
            m_v6 = "ثابت" if report.ipv6_mode == "static" else "تلقائي"
            self.lbl_own_modes.setText(f"IPv4: {m_v4} · IPv6: {m_v6}")

        if hasattr(self, "lbl_own_gateway"):
            gw_str = report.default_gateway or "—"
            dhcp_str = report.dhcp_server or gw_str
            self.lbl_own_gateway.setText(f"راوتر: {gw_str} · DHCP: {dhcp_str}")

        if hasattr(self, "lbl_own_apps"):
            apps_cnt = len(report.detected_third_party_apps)
            nrpt_str = f"NRPT: {report.nrpt_rules_count}" if report.has_nrpt_rules else "NRPT: 0"
            doh_str = "DoH: مفعّل" if report.windows_doh_configured else "DoH: معطل"
            self.lbl_own_apps.setText(f"تطبيقات: {apps_cnt} · {nrpt_str} · {doh_str}")

        if hasattr(self, "lbl_own_limitations"):
            if report.verification_limitations:
                lims_text = " • ".join(report.verification_limitations)
                self.lbl_own_limitations.setText(f"الحدود والشفافية التقنية: {lims_text}")
            else:
                self.lbl_own_limitations.setText("الحدود والشفافية التقنية: تم فحص وتأكيد إعدادات محول الشبكة بالكامل.")
        if hasattr(self, "ownership_panel"):
            self.ownership_panel.updateGeometry()
            if self.ownership_panel.layout() is not None:
                self.ownership_panel.layout().activate()
            self.ownership_panel.adjustSize()

    def set_meeting_freeze_state(self, active: bool, app_name: str = "") -> None:
        if active:
            app_txt = f" ({app_name})" if app_name else ""
            self.lbl_dns_freeze_banner.setText(
                tokens.bidi_isolate_mixed(
                    f"وضع حماية الاجتماع نشط{app_txt}: تم تجميد التبديل التلقائي لخادم DNS مؤقتاً لمنع انقطاع الجلسة."
                )
            )
            self.lbl_dns_freeze_banner.setVisible(True)
        else:
            self.lbl_dns_freeze_banner.setVisible(False)

    def add_decision_entry(self, time_str: str, action: str, server: str, latency: str, reason: str) -> None:
        if not hasattr(self, "history_table"):
            return
        self.history_table.insertRow(0)
        for col, val in enumerate((time_str, action, server, latency, reason)):
            item = QTableWidgetItem(tokens.bidi_isolate_mixed(str(val or "—")))
            self.history_table.setItem(0, col, item)
        while self.history_table.rowCount() > 25:
            self.history_table.removeRow(self.history_table.rowCount() - 1)

    def _sync_content_width(self) -> None:
        if hasattr(self, "scroll") and hasattr(self, "content_widget"):
            vw = self.scroll.viewport().width()
            if vw > 0:
                self.content_widget.setFixedWidth(vw)

    def _apply_layout_mode(self, mode: str) -> None:
        self._current_layout_mode = mode

        # 1. Page content padding
        if hasattr(self, "content_layout"):
            if mode == "desktop":
                self.content_layout.setContentsMargins(tokens.PAGE_PADDING_DESKTOP, 24, tokens.PAGE_PADDING_DESKTOP, 32)
            elif mode == "tablet":
                self.content_layout.setContentsMargins(20, 16, 20, 24)
            else:
                self.content_layout.setContentsMargins(tokens.PAGE_PADDING_NARROW, 12, tokens.PAGE_PADDING_NARROW, 16)

        # 2. Header layout direction
        if hasattr(self, "top_h") and hasattr(self, "benchmark_btn"):
            if mode in ("tablet", "mobile"):
                self.top_h.setDirection(QBoxLayout.TopToBottom)
                self.benchmark_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            else:
                self.top_h.setDirection(QBoxLayout.LeftToRight)
                self.benchmark_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 3. Active DNS 4 stat boxes reflow
        if hasattr(self, "grid_curr") and hasattr(self, "box_prov"):
            for box in (self.box_prov, self.box_ip, self.box_ms, self.box_st):
                self.grid_curr.removeWidget(box)
            if mode == "desktop":
                self.grid_curr.addWidget(self.box_prov, 0, 0)
                self.grid_curr.addWidget(self.box_ip, 0, 1)
                self.grid_curr.addWidget(self.box_ms, 0, 2)
                self.grid_curr.addWidget(self.box_st, 0, 3)
            elif mode == "tablet":
                self.grid_curr.addWidget(self.box_prov, 0, 0)
                self.grid_curr.addWidget(self.box_ip, 0, 1)
                self.grid_curr.addWidget(self.box_ms, 1, 0)
                self.grid_curr.addWidget(self.box_st, 1, 1)
            else:  # mobile
                self.grid_curr.addWidget(self.box_prov, 0, 0)
                self.grid_curr.addWidget(self.box_ip, 1, 0)
                self.grid_curr.addWidget(self.box_ms, 2, 0)
                self.grid_curr.addWidget(self.box_st, 3, 0)

        # 4. Ownership 4 stat boxes reflow
        if hasattr(self, "grid_own") and hasattr(self, "box_own_ad"):
            for box in (self.box_own_ad, self.box_own_md, self.box_own_gw, self.box_own_ap):
                self.grid_own.removeWidget(box)
            if mode == "desktop":
                self.grid_own.addWidget(self.box_own_ad, 0, 0)
                self.grid_own.addWidget(self.box_own_md, 0, 1)
                self.grid_own.addWidget(self.box_own_gw, 0, 2)
                self.grid_own.addWidget(self.box_own_ap, 0, 3)
            elif mode == "tablet":
                self.grid_own.addWidget(self.box_own_ad, 0, 0)
                self.grid_own.addWidget(self.box_own_md, 0, 1)
                self.grid_own.addWidget(self.box_own_gw, 1, 0)
                self.grid_own.addWidget(self.box_own_ap, 1, 1)
            else:  # mobile
                self.grid_own.addWidget(self.box_own_ad, 0, 0)
                self.grid_own.addWidget(self.box_own_md, 1, 0)
                self.grid_own.addWidget(self.box_own_gw, 2, 0)
                self.grid_own.addWidget(self.box_own_ap, 3, 0)

        # 5. Table responsive column visibility
        if hasattr(self, "table"):
            if mode == "desktop":
                self.table.setColumnHidden(2, False)  # Primary IP
                self.table.setColumnHidden(3, False)  # Secondary IP
                self.table.setColumnHidden(5, False)  # Availability Chip
                self.table.setColumnHidden(6, False)  # Current Config
            elif mode == "tablet":
                self.table.setColumnHidden(2, False)  # Primary IP
                self.table.setColumnHidden(3, True)   # Secondary IP (hidden)
                self.table.setColumnHidden(5, False)  # Availability Chip
                self.table.setColumnHidden(6, True)   # Current Config (hidden)
            else:  # mobile
                self.table.setColumnHidden(2, True)   # Primary IP (hidden)
                self.table.setColumnHidden(3, True)   # Secondary IP (hidden)
                self.table.setColumnHidden(5, True)   # Availability Chip (hidden)
                self.table.setColumnHidden(6, True)   # Current Config (hidden)

    def _on_dns_state_changed(self, state: Any) -> None:
        """Single source of truth synchronization for DNSView."""
        if not state:
            return

        # 1. Header Evaluation Status
        if hasattr(self, "lbl_last_evaluation"):
            l_state = getattr(state, "lifecycle_state", "idle")
            if l_state == "testing":
                self.lbl_last_evaluation.setText("آخر تقييم: جاري القياس الحي لخوادم DNS...")
            elif l_state == "applying":
                self.lbl_last_evaluation.setText("آخر تقييم: جاري تطبيق إعدادات DNS على ويندوز...")
            elif l_state == "verifying":
                self.lbl_last_evaluation.setText("آخر تقييم: جاري التحقق من إعدادات ويندوز والترجمة...")
            elif getattr(state, "last_measured_timestamp", None):
                ts = state.last_measured_timestamp
                self.lbl_last_evaluation.setText(f"آخر تقييم: {ts.strftime('%H:%M:%S')}")

        if hasattr(self, "lbl_last_switch") and getattr(state, "status_message", ""):
            self.lbl_last_switch.setText(f"قرار DNS: {state.status_message}")

        # 2. Benchmark Button State
        if hasattr(self, "benchmark_btn"):
            if getattr(state, "is_benchmarking", False) or getattr(state, "lifecycle_state", "") in ("testing", "applying", "verifying"):
                self.benchmark_btn.setEnabled(False)
                self.benchmark_btn.setText("جاري الفحص التلقائي...")
            else:
                self.benchmark_btn.setEnabled(True)
                self.benchmark_btn.setText("فحص وترتيب الخوادم الآن")

        # 3. Active DNS Card & Comparison Bars
        active_srv = getattr(state, "active_servers", [])
        if active_srv:
            self.set_active_dns_info(active_srv)

        # 4. Table and Analysis if scores are present
        scores = getattr(state, "scores", [])
        if scores:
            is_opt = not getattr(state, "is_recommended_different", False)
            self.update_rankings(
                scores=scores,
                active_ms=getattr(state, "last_measured_ms", None),
                active_name=getattr(state, "detected_provider", "") or "",
                is_optimal=is_opt,
            )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_content_width()
        w = self.width()
        if w >= 1050:
            if self._current_layout_mode != "desktop":
                self._apply_layout_mode("desktop")
        elif 680 <= w < 1050:
            if self._current_layout_mode != "tablet":
                self._apply_layout_mode("tablet")
        else:
            if self._current_layout_mode != "mobile":
                self._apply_layout_mode("mobile")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_content_width()
        w = self.width()
        if w >= 1050:
            self._apply_layout_mode("desktop")
        elif 680 <= w < 1050:
            self._apply_layout_mode("tablet")
        else:
            self._apply_layout_mode("mobile")
