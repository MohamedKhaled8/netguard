"""Process Consumer Bar and DNS Recommendation components for NetGuard AI.

Precision components for Row B:
1. ProcessBarRow: Process name + optional tag chip + mono rate + 6px proportional bar
2. TrafficConsumersPanel: Top 5 bandwidth consumers list
3. DNSRecommendationPanel: DNS speed benchmark comparison with 8px horizontal bars & 1-click apply
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QWidget,
)
from PySide6.QtGui import QPainter, QColor, QBrush
from PySide6.QtCore import Qt, QRectF, Signal
from app.ui import tokens
from app.ui.widgets.chip import Chip
from app.ui.widgets.buttons import PrimaryButton


class HorizontalProgressBar(QWidget):
    """Custom flat horizontal progress bar (6px or 8px height)."""

    def __init__(self, height: int = 6, fill_color: str = tokens.ACCENT, parent=None) -> None:
        super().__init__(parent)
        self.bar_height = height
        self.fill_color = fill_color
        self.fraction = 0.0  # 0.0 to 1.0
        self.setFixedHeight(height)

    def set_fraction(self, frac: float, fill_color: Optional[str] = None) -> None:
        self.fraction = max(0.0, min(1.0, frac))
        if fill_color:
            self.fill_color = fill_color
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        radius = h / 2.0

        # Background track #25292C
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(tokens.BAR_FUTURE)))
        painter.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        # Fill bar
        fill_w = max(radius * 2, w * self.fraction)
        if self.fraction > 0.01:
            painter.setBrush(QBrush(QColor(self.fill_color)))
            painter.drawRoundedRect(QRectF(0, 0, fill_w, h), radius, radius)


class ProcessBarRow(QWidget):
    """Single row showing Process Name, optional tag, mono rate, and 6px bar."""

    def __init__(
        self,
        name: str,
        rate_str: str,
        fraction: float,
        tag_text: Optional[str] = None,
        tag_variant: str = "tag-warn",
        fill_color: str = tokens.ACCENT,
        parent=None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(6)

        # Top line: Name + optional Tag on right (RTL), Rate on left
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        self.lbl_name = QLabel(name)
        self.lbl_name.setFont(tokens.get_sans_font(14, 500))
        self.lbl_name.setStyleSheet(f"color: {tokens.TEXT};")
        top_row.addWidget(self.lbl_name)

        if tag_text:
            self.tag_chip = Chip(tag_text, variant=tag_variant, radius=6, font_size=11)
            top_row.addWidget(self.tag_chip)
        else:
            self.tag_chip = None

        top_row.addStretch()

        self.lbl_rate = QLabel(rate_str)
        self.lbl_rate.setFont(tokens.get_mono_font(13, 500))
        self.lbl_rate.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        top_row.addWidget(self.lbl_rate)

        layout.addLayout(top_row)

        # 6px Bar
        self.bar = HorizontalProgressBar(height=6, fill_color=fill_color, parent=self)
        self.bar.set_fraction(fraction)
        layout.addWidget(self.bar)

    def update_data(self, rate_str: str, fraction: float, fill_color: str = None) -> None:
        self.lbl_rate.setText(rate_str)
        self.bar.set_fraction(fraction, fill_color)


class TrafficConsumersPanel(QFrame):
    """Panel 'من يستهلك الإنترنت الآن' showing top 5 processes."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TrafficConsumersPanel")
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(f"""
            QFrame#TrafficConsumersPanel {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_PANEL}px;
            }}
            QFrame#TrafficConsumersPanel QLabel {{
                background: transparent;
                border: 0px solid transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Header
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        self.lbl_title = QLabel("من يستهلك الإنترنت الآن")
        self.lbl_title.setFont(tokens.get_sans_font(15, 600))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")

        self.lbl_sub = QLabel("أكثر البرامج استهلاكاً للشبكة (حسب الاتصالات النشطة المقاسة - تقديري)")
        self.lbl_sub.setFont(tokens.get_sans_font(12, 400))
        self.lbl_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        title_col.addWidget(self.lbl_title)
        title_col.addWidget(self.lbl_sub)
        layout.addLayout(title_col)

        # 5 Process Rows (Initialized to honest unmeasured states)
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(10)

        self.row1 = ProcessBarRow("—", "—", 0.0, fill_color=tokens.ACCENT)
        self.row2 = ProcessBarRow("—", "—", 0.0, fill_color=tokens.ACCENT)
        self.row3 = ProcessBarRow("—", "—", 0.0, fill_color=tokens.ACCENT)
        self.row4 = ProcessBarRow("—", "—", 0.0, fill_color=tokens.ACCENT)
        self.row5 = ProcessBarRow("—", "—", 0.0, fill_color=tokens.ACCENT)

        self.rows_layout.addWidget(self.row1)
        self.rows_layout.addWidget(self.row2)
        self.rows_layout.addWidget(self.row3)
        self.rows_layout.addWidget(self.row4)
        self.rows_layout.addWidget(self.row5)
        layout.addLayout(self.rows_layout)

    def update_processes(self, profiles) -> None:
        """Update top 5 consumers from live process network profiles."""
        rows = [self.row1, self.row2, self.row3, self.row4, self.row5]
        if not profiles:
            for r in rows:
                r.lbl_name.setText("—")
                r.update_data("—", 0.0)
            return
        sorted_p = sorted(profiles, key=lambda p: getattr(p, "active_socket_count", 0), reverse=True)[:5]
        max_sockets = max((getattr(p, "active_socket_count", 1) for p in sorted_p), default=1)
        for i in range(len(rows)):
            if i < len(sorted_p):
                p = sorted_p[i]
                pname = getattr(p, "name", "").replace(".exe", "").title() or "مجهول"
                s_cnt = getattr(p, "active_socket_count", 0)
                frac = min(1.0, max(0.08, s_cnt / max(1, max_sockets)))
                color = tokens.STATUS_OK if getattr(p.category, "value", str(getattr(p, "category", ""))) in ("conferencing", "critical") else tokens.ACCENT
                rows[i].lbl_name.setText(pname)
                est_mb = getattr(p, "estimated_bandwidth_mbps", None)
                conn_txt = tokens.format_arabic_connections(s_cnt)
                if est_mb and est_mb > 0.05:
                    text_data = f"{conn_txt} · {tokens.bidi_isolate(f'~{est_mb:.1f}M')} (تقديري)"
                else:
                    text_data = f"{conn_txt} (مقاسة)"
                rows[i].update_data(text_data, frac, color)
            else:
                rows[i].lbl_name.setText("—")
                rows[i].update_data("—", 0.0)


class DNSRecommendationPanel(QFrame):
    """DNS recommendation panel comparing current DNS with the fastest benchmark."""

    apply_clicked = Signal()
    revert_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("DNSRecommendationPanel")
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(f"""
            QFrame#DNSRecommendationPanel {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_PANEL}px;
            }}
            QFrame#DNSRecommendationPanel QLabel {{
                background: transparent;
                border: 0px solid transparent;
            }}
        """)
        self.is_applied = False
        self.is_optimal = False
        self.is_autonomous = True
        self._target_best_ip = "1.1.1.1"
        self._target_best_name = "Cloudflare"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Caption 'توصية'
        self.lbl_tag = QLabel("جاهز للفحص")
        self.lbl_tag.setFont(tokens.get_sans_font(12, 500))
        self.lbl_tag.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        layout.addWidget(self.lbl_tag)

        # Title & Subtitle
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        self.lbl_title = QLabel("فحص وتسريع خوادم DNS")
        self.lbl_title.setFont(tokens.get_sans_font(15, 600))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_title.setWordWrap(True)

        self.lbl_sub = QLabel("اضغط 'فحص خوادم DNS الآن' لقياس سرعة الخوادم مقارنة بالخادم الحالي.")
        self.lbl_sub.setFont(tokens.get_sans_font(12, 400))
        self.lbl_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_sub.setWordWrap(True)

        title_col.addWidget(self.lbl_title)
        title_col.addWidget(self.lbl_sub)
        layout.addLayout(title_col)

        # Two 8px horizontal comparison bars
        bars_col = QVBoxLayout()
        bars_col.setSpacing(12)

        # Current DNS Row
        curr_row = QVBoxLayout()
        curr_row.setSpacing(4)
        curr_top = QHBoxLayout()
        self.lbl_curr_name = QLabel("خادم DNS المعتمد بجهازك حالياً")
        self.lbl_curr_name.setFont(tokens.get_sans_font(13, 500))
        self.lbl_curr_name.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_curr_name.setWordWrap(True)
        self.lbl_curr_ms = QLabel("—")
        self.lbl_curr_ms.setFont(tokens.get_mono_font(13, 500))
        self.lbl_curr_ms.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_curr_ms.setFixedWidth(75)
        curr_top.addWidget(self.lbl_curr_name, stretch=1)
        curr_top.addWidget(self.lbl_curr_ms)
        curr_row.addLayout(curr_top)

        self.bar_curr = HorizontalProgressBar(height=8, fill_color=tokens.TEXT_MUTED)
        self.bar_curr.set_fraction(0.0)
        curr_row.addWidget(self.bar_curr)

        # Clear explanation note under Current DNS
        self.lbl_curr_clarification = QLabel("هذا هو خادم DNS الذي يستخدمه جهازك حالياً، وليس مجرد خادم DNS مقترح.")
        self.lbl_curr_clarification.setFont(tokens.get_sans_font(11, 400))
        self.lbl_curr_clarification.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_curr_clarification.setWordWrap(True)
        curr_row.addWidget(self.lbl_curr_clarification)
        bars_col.addLayout(curr_row)

        # Fastest DNS Row
        self.fast_row_container = QWidget()
        fast_row = QVBoxLayout(self.fast_row_container)
        fast_row.setContentsMargins(0, 0, 0, 0)
        fast_row.setSpacing(4)
        fast_top = QHBoxLayout()
        self.lbl_fast_name = QLabel("—")
        self.lbl_fast_name.setFont(tokens.get_sans_font(13, 500))
        self.lbl_fast_name.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_fast_name.setWordWrap(True)
        self.lbl_fast_ms = QLabel("—")
        self.lbl_fast_ms.setFont(tokens.get_mono_font(13, 500))
        self.lbl_fast_ms.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_fast_ms.setFixedWidth(75)
        fast_top.addWidget(self.lbl_fast_name, stretch=1)
        fast_top.addWidget(self.lbl_fast_ms)
        fast_row.addLayout(fast_top)

        self.bar_fast = HorizontalProgressBar(height=8, fill_color=tokens.STATUS_OK)
        self.bar_fast.set_fraction(0.0)
        fast_row.addWidget(self.bar_fast)
        bars_col.addWidget(self.fast_row_container)

        layout.addLayout(bars_col)

        # Footer Row: Caption on right (RTL), Primary button on left
        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 4, 0, 0)

        self.lbl_note = QLabel("يمكنك التراجع في أي وقت.")
        self.lbl_note.setFont(tokens.get_sans_font(12, 400))
        self.lbl_note.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_note.setWordWrap(True)
        footer_row.addWidget(self.lbl_note, stretch=1)

        footer_row.addStretch()

        self.btn_action = PrimaryButton("طبّق التغيير")
        self.btn_action.setEnabled(False)
        self.btn_action.clicked.connect(self._on_action_clicked)
        footer_row.addWidget(self.btn_action)

        layout.addLayout(footer_row)

    def update_dns_state(
        self,
        curr_name: str,
        curr_ms: Optional[float],
        best_name: str,
        best_ip: str,
        best_ms: float,
        is_optimal: bool,
        is_autonomous: bool = True,
        auto_applied: bool = False,
    ) -> None:
        """Dynamically update recommendation panel to show real live status and autonomous healing."""
        self.is_optimal = is_optimal
        self.is_autonomous = is_autonomous
        self._target_best_ip = best_ip
        self._target_best_name = best_name

        if auto_applied:
            self.is_applied = True
            diff = max(1, int(round(curr_ms)) - int(round(best_ms))) if (curr_ms and curr_ms > best_ms) else 0
            self.lbl_tag.setText("تم الإصلاح الذاتي تلقائياً ✓")
            self.lbl_tag.setStyleSheet(f"color: {tokens.STATUS_OK};")
            self.lbl_title.setText(f"تم اعتماد خادم {best_name} تلقائياً ({int(round(best_ms))} ms)")
            diff_text = f" (تحسن +{diff} ms)" if diff > 0 else ""
            self.lbl_sub.setText(f"تم التبديل الفوري بنجاح في وضع الحماية الذاتية{diff_text}.")
            self.lbl_curr_name.setText(f"خادم DNS المعتمد ({best_name})")
            self.lbl_curr_ms.setText(f"{int(round(best_ms))} ms")
            self.lbl_curr_ms.setStyleSheet(f"color: {tokens.STATUS_OK};")
            self.bar_curr.set_fraction(max(0.12, min(1.0, best_ms / 80.0)), fill_color=tokens.STATUS_OK)
            self.fast_row_container.setVisible(False)
            self.lbl_note.setText("المراقبة الذاتية تعمل: تم اعتماد الخادم الأسرع بنجاح.")
            self.btn_action.setText("تراجع عن التغيير")
            self.btn_action.setEnabled(True)
            return

        if curr_ms is None or curr_ms < 1.0 or "جاري" in curr_name:
            self.lbl_tag.setText("جاري الفحص والتقييم...")
            self.lbl_tag.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            self.lbl_title.setText("جاري قياس استجابة خوادم DNS...")
            self.lbl_sub.setText("يتم إرسال استعلامات فعلية للتحقق من سرعة الخادم الحالي والبدائل المتاحة.")
            self.lbl_curr_name.setText(f"خادم DNS الحالي ({curr_name})")
            self.lbl_curr_ms.setText("جاري القياس...")
            self.lbl_curr_ms.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            self.bar_curr.set_fraction(0.08, fill_color=tokens.TEXT_MUTED)
            self.fast_row_container.setVisible(False)
            self.lbl_note.setText("المراقبة الذاتية تعمل: جاري القياس الميداني.")
            self.btn_action.setText("معتمد حالياً")
            self.btn_action.setEnabled(False)
            return

        curr_ms_safe = max(0.0, curr_ms)
        curr_color = tokens.STATUS_OK if curr_ms_safe <= 55.0 else (tokens.STATUS_WARN if curr_ms_safe <= 85.0 else tokens.STATUS_BAD)
        fast_color = tokens.STATUS_OK if best_ms <= 55.0 else (tokens.STATUS_WARN if best_ms <= 85.0 else tokens.STATUS_BAD)

        if best_ms <= 55.0:
            ms_color = tokens.STATUS_OK
            tag_text = "إصلاح ذاتي نشط ✓"
            tag_color = tokens.STATUS_OK
            note_text = "المراقبة الذاتية تعمل: لا يتطلب أي إجراء منك."
        elif best_ms <= 85.0:
            ms_color = tokens.STATUS_WARN
            tag_text = "استجابة مقبولة"
            tag_color = tokens.STATUS_WARN
            note_text = "الخادم يعمل بكفاءة مقبولة في ظل ظروف الشبكة الحالية."
        else:
            ms_color = tokens.STATUS_BAD
            tag_text = "استجابة بطيئة"
            tag_color = tokens.STATUS_BAD
            note_text = f"الخادم يعاني من بطء في الاستجابة ({best_ms:.0f} ms). جاري المتابعة."

        if is_optimal:
            self.lbl_tag.setText("الخادم الحالي هو الأسرع ✓ (مستقر وسريع)")
            self.lbl_tag.setStyleSheet(f"color: {tokens.STATUS_OK};")
            self.lbl_title.setText(f"خادم DNS الحالي ({curr_name}) هو الأسرع لجهازك حالياً")
            self.lbl_sub.setText(f"يقدم خادم {curr_name} أعلى سرعة استجابة واستقرار تم قياسه ({curr_ms:.0f} ms).")
            self.lbl_curr_name.setText(f"خادم DNS الحالي ({curr_name})")
            self.lbl_curr_ms.setText(f"{curr_ms:.0f} ms")
            self.lbl_curr_ms.setStyleSheet(f"color: {curr_color};")
            self.bar_curr.set_fraction(max(0.12, min(1.0, curr_ms / 80.0)), fill_color=curr_color)
            self.fast_row_container.setVisible(False)
            self.lbl_note.setText(note_text)
            self.btn_action.setText("معتمد حالياً ✓")
            self.btn_action.setEnabled(False)
            self.is_applied = False
        else:
            diff = max(1, int(round(curr_ms)) - int(round(best_ms)))

            if is_autonomous:
                self.lbl_tag.setText("جاري التحسين التلقائي...")
                self.lbl_tag.setStyleSheet(f"color: {tokens.STATUS_WARN};")
                self.lbl_title.setText(f"جاري التبديل التلقائي إلى {best_name} ({int(round(best_ms))} ms)")
                self.lbl_sub.setText(f"تم رصد فارق +{diff} ms لصالح {best_name}. جاري تطبيق التحسين الذاتي فوراً.")
                self.btn_action.setText("جاري التحسين...")
                self.btn_action.setEnabled(False)
            else:
                self.lbl_tag.setText("توصية بتحسين DNS")
                self.lbl_tag.setStyleSheet(f"color: {tokens.STATUS_WARN};")
                self.lbl_title.setText(f"الخادم الحالي: {curr_name} ({int(round(curr_ms))} ms) — الأسرع: {best_name} ({int(round(best_ms))} ms)")
                self.lbl_sub.setText(f"الفارق: +{diff} ms لصالح {best_name}. يمكنك التبديل لتسريع فتح الروابط والمواقع.")
                self.btn_action.setText("طبّق التغيير الآن")
                self.btn_action.setEnabled(True)
                self.is_applied = False

            self.lbl_curr_name.setText(f"خادم DNS الحالي ({curr_name})")
            self.lbl_curr_ms.setText(f"{int(round(curr_ms))} ms")
            self.lbl_curr_ms.setStyleSheet(f"color: {curr_color};")
            self.bar_curr.set_fraction(max(0.2, min(1.0, curr_ms / 80.0)), fill_color=curr_color)

            self.fast_row_container.setVisible(True)
            self.lbl_fast_name.setText(f"الخادم المقترح: {best_name} · {best_ip}")
            self.lbl_fast_ms.setText(f"{int(round(best_ms))} ms")
            self.lbl_fast_ms.setStyleSheet(f"color: {fast_color};")
            self.bar_fast.set_fraction(max(0.12, min(1.0, best_ms / 80.0)), fill_color=fast_color)
            self.lbl_note.setText("يمكنك التراجع واستعادة إعدادات محول الشبكة الأصلية (DHCP) في أي وقت.")

    def set_remediation_result(self, before_ms: float, after_ms: float, new_name: str, success: bool = True) -> None:
        """Display verifiable before vs after evidence post-remediation."""
        if success:
            gain_ms = max(0.0, before_ms - after_ms)
            pct = (gain_ms / before_ms * 100.0) if before_ms > 0 else 0.0
            self.lbl_tag.setText("تم الإصلاح بنجاح ✓")
            self.lbl_tag.setStyleSheet(f"color: {tokens.STATUS_OK};")
            self.lbl_title.setText(f"تم اعتماد خادم {new_name} بنجاح")
            self.lbl_sub.setText(f"تم التحقق الفعلي: انخفض زمن الاستجابة من {before_ms:.0f} ms إلى {after_ms:.0f} ms (تحسن {pct:.0f}%).")
            self.btn_action.setText("تراجع عن التغيير")
            self.btn_action.setEnabled(True)
            self.is_applied = True
        else:
            self.lbl_tag.setText("فشل التحقق — تم التراجع")
            self.lbl_tag.setStyleSheet(f"color: {tokens.STATUS_BAD};")
            self.lbl_title.setText("تعذر التحقق من الخادم الجديد")
            self.lbl_sub.setText("لم يستجب الخادم الجديد بالشكل المطلوب، وتمت استعادة الإعدادات السابقة فوراً.")
            self.btn_action.setText("طبّق التغيير")
            self.btn_action.setEnabled(True)
            self.is_applied = False

    def _on_action_clicked(self) -> None:
        if not self.is_applied:
            self.btn_action.setEnabled(False)
            self.btn_action.setText("جاري التطبيق...")
            self.lbl_tag.setText("جاري التطبيق والتحقق...")
            self.lbl_tag.setStyleSheet(f"color: {tokens.STATUS_WARN};")
            self.lbl_title.setText(f"جاري تطبيق خادم {self._target_best_name} على بطاقة الشبكة...")
            self.lbl_sub.setText("يتم إرسال الأمر بصلاحيات المدير والتأكد من تسجيل العناوين واختبار الترجمة.")
            self.apply_clicked.emit()
        else:
            self.btn_action.setEnabled(False)
            self.btn_action.setText("جاري الاستعادة...")
            self.lbl_tag.setText("جاري استعادة الإعدادات...")
            self.lbl_tag.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            self.lbl_title.setText("جاري استعادة إعدادات DNS السابقة...")
            self.lbl_sub.setText("يتم إرجاع خوادم DNS السابقة أو تفعيل التعيين التلقائي (DHCP).")
            self.revert_clicked.emit()
