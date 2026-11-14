"""Diagnostic Center View for NetGuard AI Desktop.

Deep inspection of root causes, confidence calculations, and differential evidence,
fully localized with human-understandable networking context.
"""

from __future__ import annotations
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
)
from PySide6.QtCore import Qt
from app.ui.i18n import tr


class DiagnosisView(QWidget):
    """Deep inspection of root causes, confidence calculations, and differential evidence."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header card
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #111625;
                border: 1px solid #1c253b;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        h_layout = QVBoxLayout(header)
        h_layout.setSpacing(10)

        top_row = QHBoxLayout()
        title_box = QVBoxLayout()
        self.title_lbl = QLabel(tr("diag_banner_title"))
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #58a6ff;")
        self.desc_lbl = QLabel(tr("diag_banner_desc"))
        self.desc_lbl.setStyleSheet("font-size: 12px; color: #8b949e;")
        title_box.addWidget(self.title_lbl)
        title_box.addWidget(self.desc_lbl)
        top_row.addLayout(title_box)
        top_row.addStretch()

        self.btn_run_audit = QPushButton(tr("diag_run_btn"))
        self.btn_run_audit.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                font-weight: 700;
                padding: 9px 18px;
                border-radius: 8px;
                border: 1px solid #388bfd;
            }
            QPushButton:hover { background-color: #388bfd; }
        """)
        top_row.addWidget(self.btn_run_audit)
        h_layout.addLayout(top_row)

        # Result Details Frame
        res_frame = QFrame()
        res_frame.setStyleSheet("background-color: #151d30; border-radius: 8px; padding: 12px;")
        res_layout = QVBoxLayout(res_frame)
        res_layout.setSpacing(6)

        self.cause_lbl = QLabel(tr("cause_healthy"))
        self.cause_lbl.setStyleSheet("font-size: 20px; font-weight: 800; color: #3fb950;")
        self.cause_lbl.setWordWrap(True)

        self.explanation_lbl = QLabel("جميع مؤشرات الاتصال تعمل بكفاءة طبيعية والشبكة مستقرة تماماً.")
        self.explanation_lbl.setStyleSheet("font-size: 13px; color: #c9d1d9; line-height: 1.4;")
        self.explanation_lbl.setWordWrap(True)

        self.conf_lbl = QLabel("الدقة: 100.0% | مستوى الخطورة: إرشادي (عادي) | الإصلاح التلقائي: غير مطلوب")
        self.conf_lbl.setStyleSheet("font-size: 11px; color: #8b949e; font-weight: 600;")

        res_layout.addWidget(self.cause_lbl)
        res_layout.addWidget(self.explanation_lbl)
        res_layout.addWidget(self.conf_lbl)
        h_layout.addWidget(res_frame)

        layout.addWidget(header)

        # Evidence Table Section
        self.sec_title = QLabel(tr("diag_evidence_title"))
        self.sec_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #e6edf3;")
        layout.addWidget(self.sec_title)

        self.table = QTableWidget(0, 5)
        self.apply_table_headers()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table, stretch=1)

    def apply_table_headers(self) -> None:
        self.table.setHorizontalHeaderLabels([
            "مؤشر القياس (Metric)",
            "الهدف / السيرفر",
            "القيمة المرصودة",
            "الحد المقبول (Threshold)",
            "تقييم الحالة",
        ])

    def apply_language(self) -> None:
        self.title_lbl.setText(tr("diag_banner_title"))
        self.desc_lbl.setText(tr("diag_banner_desc"))
        self.btn_run_audit.setText(tr("diag_run_btn"))
        self.sec_title.setText(tr("diag_evidence_title"))
        self.apply_table_headers()

    def update_diagnosis(self, diagnosis) -> None:
        cause_key = f"cause_{diagnosis.probable_cause.value}"
        cause_translated = tr(cause_key, diagnosis.probable_cause.value.replace("_", " ").upper())
        is_healthy = diagnosis.probable_cause.value == "healthy"
        color = "#3fb950" if is_healthy else "#f85149"

        self.cause_lbl.setText(f"النتيجة: {cause_translated}")
        self.cause_lbl.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {color};")
        self.explanation_lbl.setText(diagnosis.explanation)

        sev_trans = "عادي (منخفض)" if diagnosis.severity.value == "info" else ("متوسط" if diagnosis.severity.value == "warning" else "حرج (عالي)")
        self.conf_lbl.setText(
            f"دقة الفحص: {diagnosis.confidence * 100:.1f}% | "
            f"مستوى الخطورة: {sev_trans} | "
            f"التدخل الذاتي مصرح به: {'نعم' if diagnosis.auto_remediation_permitted else 'غير ضروري'}"
        )

        # Populate evidence
        self.table.setRowCount(0)
        for ev in diagnosis.supporting_evidence:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(ev.metric_type.value.replace("_", " ")))
            self.table.setItem(row, 1, QTableWidgetItem(ev.target))
            self.table.setItem(row, 2, QTableWidgetItem(f"{ev.observed_value:.1f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{ev.threshold_value:.1f}"))
            
            cond_item = QTableWidgetItem("سليم ✓" if ev.condition == "normal" else "تجاوز الحد ✗")
            cond_item.setForeground(Qt.green if ev.condition == "normal" else Qt.red)
            self.table.setItem(row, 4, cond_item)
