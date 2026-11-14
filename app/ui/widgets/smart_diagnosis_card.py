"""Smart Diagnostic & Autonomous Healing Breakdown Card.

Translates raw network faults into human-understandable terms:
- Exact detected condition
- Technical root cause in plain Egyptian/Arabic phrasing
- Practical impact on user's gaming, browsing, or video calls
- What NetGuard AI autonomously did to resolve it and the verified outcome.
"""

from __future__ import annotations
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
from PySide6.QtCore import Qt
from app.core.models.metrics import Diagnosis, ProbableCause, DiagnosisSeverity


class SmartDiagnosisCard(QFrame):
    """High-craft diagnostic explanation card answering: What happened? Why? Impact? NetGuard Action?"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #111624;
                border: 1px solid #1c253b;
                border-radius: 12px;
                padding: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header with Status Badge
        header_layout = QHBoxLayout()
        title_col = QVBoxLayout()
        self.status_title = QLabel("حالة الشبكة: ممتازة ومحمية بالكامل 🟢")
        self.status_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #3fb950;")
        
        self.status_sub = QLabel("جميع مؤشرات الاتصال تعمل بأعلى كفاءة ولا توجد أي مشاكل تعيق استخدامك.")
        self.status_sub.setStyleSheet("font-size: 12px; color: #8b949e;")
        title_col.addWidget(self.status_title)
        title_col.addWidget(self.status_sub)
        header_layout.addLayout(title_col)
        header_layout.addStretch()

        self.confidence_pill = QLabel("دقة الرصد: 100%")
        self.confidence_pill.setStyleSheet("""
            font-size: 11px;
            font-weight: 700;
            color: #58a6ff;
            background-color: #17243c;
            border: 1px solid #273e6b;
            border-radius: 10px;
            padding: 5px 12px;
        """)
        header_layout.addWidget(self.confidence_pill)
        layout.addLayout(header_layout)

        # 4 Explanatory Blocks (Grid)
        grid = QGridLayout()
        grid.setSpacing(12)

        # Block 1: The Issue
        self.box_issue = self._create_info_block("📌 المشكلة المرصودة", "الاتصال مستقر وسليم بنسبة 100% بدون أي انقطاع.", "#3fb950")
        # Block 2: Root Cause
        self.box_cause = self._create_info_block("🔍 السبب الجذري", "الراوتر متصل بنجاح، وخدمة مزود الإنترنت (Orange) مستقرة وسريعة.", "#8b949e")
        # Block 3: Practical Impact
        self.box_impact = self._create_info_block("👤 التأثير على استخدامك", "تصفح سلس، مكالمات فيديو نقية، وبنج منخفض للألعاب التنافسية.", "#8b949e")
        # Block 4: Autonomous Action
        self.box_action = self._create_info_block("🛡️ تصرف النظام الذاتي", "المراقبة الذاتية مستمرة في الخلفية ومستعدة للتدخل عند أي طارئ.", "#58a6ff")

        grid.addWidget(self.box_issue, 0, 0)
        grid.addWidget(self.box_cause, 0, 1)
        grid.addWidget(self.box_impact, 1, 0)
        grid.addWidget(self.box_action, 1, 1)

        layout.addLayout(grid)

    def _create_info_block(self, title: str, default_text: str, color_hex: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #141c2c;
                border: 1px solid #1c283f;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        f_layout = QVBoxLayout(frame)
        f_layout.setContentsMargins(10, 8, 10, 8)
        f_layout.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {color_hex};")
        v_lbl = QLabel(default_text)
        v_lbl.setWordWrap(True)
        v_lbl.setStyleSheet("font-size: 12px; color: #c9d1d9; line-height: 1.4;")
        v_lbl.setObjectName("ValLabel")

        f_layout.addWidget(t_lbl)
        f_layout.addWidget(v_lbl)
        return frame

    def update_with_diagnosis(self, diag: Diagnosis) -> None:
        """Update explanation blocks based on the latest diagnosis."""
        cause = diag.probable_cause
        conf = f"{diag.confidence * 100:.0f}%"
        self.confidence_pill.setText(f"دقة الرصد: {conf}")

        lbl_issue = self.box_issue.findChild(QLabel, "ValLabel")
        lbl_cause = self.box_cause.findChild(QLabel, "ValLabel")
        lbl_impact = self.box_impact.findChild(QLabel, "ValLabel")
        lbl_action = self.box_action.findChild(QLabel, "ValLabel")

        if cause == ProbableCause.HEALTHY:
            self.status_title.setText("حالة الشبكة: ممتازة ومحمية بالكامل 🟢")
            self.status_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #3fb950;")
            self.status_sub.setText("جميع مؤشرات الاتصال تعمل بأعلى كفاءة ولا توجد أي مشاكل تعيق استخدامك.")
            
            if lbl_issue: lbl_issue.setText("الاتصال مستقر وسليم بنسبة 100% بدون أي انقطاع.")
            if lbl_cause: lbl_cause.setText("الراوتر متصل بنجاح، وخدمة مزود الإنترنت (Orange) مستقرة وسريعة.")
            if lbl_impact: lbl_impact.setText("تصفح سلس، مكالمات فيديو نقية، وبنج منخفض للألعاب التنافسية.")
            if lbl_action: lbl_action.setText("المراقبة الذاتية مستمرة في الخلفية ومستعدة للتدخل عند أي طارئ.")

        elif cause == ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY:
            self.status_title.setText("تنبيه: بطء أو تشويش في الاتصال بالراوتر ⚠️")
            self.status_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #e3b341;")
            self.status_sub.setText("تم رصد تذبذب في الاتصال بين جهازك والراوتر المنزلي (Wi-Fi).")

            if lbl_issue: lbl_issue.setText("ارتفاع في زمن الاستجابة بين الكمبيوتر والراوتر عن المعدل الطبيعي.")
            if lbl_cause: lbl_cause.setText(diag.explanation)
            if lbl_impact: lbl_impact.setText("قد تشعر بتأخير لحظي في الألعاب أونلاين أو تقطيع بسيط في الصوت أثناء المكالمات.")
            if lbl_action: lbl_action.setText("يقوم NetGuard بمراقبة استقرار القناة وتفريغ مسارات العناوين وإعادة الفحص تلقائياً.")

        elif cause == ProbableCause.LOCAL_GATEWAY_UNREACHABLE:
            self.status_title.setText("خطر: انقطاع الاتصال بالراوتر المنزلي 🔴")
            self.status_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #f85149;")
            self.status_sub.setText("الكمبيوتر غير قادر على الوصول إلى الراوتر (192.168.1.1).")

            if lbl_issue: lbl_issue.setText("فقدان كامل لحزم البيانات مع الراوتر المنزلي.")
            if lbl_cause: lbl_cause.setText("فصل في كابل الشبكة أو انقطاع في إشارة شبكة الواي فاي المنزلية.")
            if lbl_impact: lbl_impact.setText("توقف تام لخدمة الإنترنت على هذا الجهاز.")
            if lbl_action: lbl_action.setText("يقوم NetGuard بإعادة فحص محول الشبكة والتحقق من سلامة البوابة تلقائياً.")

        elif cause in (ProbableCause.DNS_FAILURE, ProbableCause.DNS_HIGH_LATENCY):
            self.status_title.setText("تنبيه: بطء أو تعطل في خوادم فتح المواقع (DNS) ⚠️")
            self.status_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #e3b341;")
            self.status_sub.setText("المواقع تستغرق وقتاً طويلاً قبل أن تبدأ في التحميل.")

            if lbl_issue: lbl_issue.setText("تأخير في ترجمة أسماء النطاقات (مثل google.com).")
            if lbl_cause: lbl_cause.setText(diag.explanation)
            if lbl_impact: lbl_impact.setText("المتصفح يقف لبضع ثوانٍ قبل فتح أي صفحة جديدة، بينما البرامج المفتوحة مسبقاً تعمل عادي.")
            if lbl_action: lbl_action.setText("قام NetGuard تلقائياً بتنظيف كاش الـ DNS وتحويل المسار لأسرع خادم عام.")

        elif cause == ProbableCause.UPSTREAM_ISP_LOSS:
            self.status_title.setText("عطل خارجي: مشكلة لدى مزود خدمة الإنترنت (ISP Outage) 🔴")
            self.status_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #f85149;")
            self.status_sub.setText("الاتصال بالراوتر سليم، ولكن شركة الإنترنت (Orange) تواجه انقطاعاً في منطقتك.")

            if lbl_issue: lbl_issue.setText("توقف وصول الإنترنت من مصدر الشركة الخارجية.")
            if lbl_cause: lbl_cause.setText(diag.explanation)
            if lbl_impact: lbl_impact.setText("توقف المواقع الخارجية عن التحميل رغم أن الواي فاي متصل بنجاح.")
            if lbl_action: lbl_action.setText("يقوم NetGuard بمتابعة الخط ومحاولة إعادة الاتصال فور عودة الخدمة.")

        else:
            self.status_title.setText(f"رصد حالة شبكة: {diag.probable_cause.value.upper()} ⚠️")
            self.status_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #e3b341;")
            self.status_sub.setText(diag.explanation)
            if lbl_issue: lbl_issue.setText(diag.explanation)
            if lbl_cause: lbl_cause.setText("تحليل إحصائي للشبكة ومقارنة بالحدود الطبيعية.")
            if lbl_impact: lbl_impact.setText("تأثير متفاوت بحسب نوع العطل المرصود.")
            if lbl_action: lbl_action.setText("النظام يطبق سياسات الحماية الآمنة المعتمدة تلقائياً.")
