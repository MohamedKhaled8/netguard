"""Redesigned Master Autonomous Cockpit for NetGuard AI Desktop.

Follows unslop, minimalist-ui, and ui-ux-pro-max engineering standards:
- 100% Autonomous Autopilot experience (zero manual buttons or labor required from user).
- Bespoke central hero: HealthRadarWidget with live circular score and pulsating status.
- SmartDiagnosisCard: Answers What happened? Root cause? User impact? Autonomous fix?
- Bento Telemetry Cards for Gateway, Internet, and DNS.
- Real-Time Latency Wave + Live Autonomous Activity Stream.
"""

from __future__ import annotations
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QGridLayout,
)
from PySide6.QtCore import Qt

from app.ui.widgets.health_radar import HealthRadarWidget
from app.ui.widgets.smart_diagnosis_card import SmartDiagnosisCard
from app.ui.widgets.activity_feed import ActivityFeedWidget
from app.ui.widgets.realtime_chart import RealTimePlotWidget
from app.ui.widgets.status_card import StatusCard
from app.core.models.metrics import Diagnosis, ProbableCause, MetricType


class DashboardView(QWidget):
    """Executive Autonomous Command Cockpit."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 1. Top Section: Hero Health Radar + Smart Diagnosis Card
        top_hero_layout = QHBoxLayout()
        top_hero_layout.setSpacing(16)

        # Central Health Radar
        self.radar = HealthRadarWidget()
        top_hero_layout.addWidget(self.radar)

        # Smart Diagnostic & Autonomous Resolution Card
        self.diag_card = SmartDiagnosisCard()
        top_hero_layout.addWidget(self.diag_card, stretch=1)

        layout.addLayout(top_hero_layout)

        # 2. Middle Section: 3 Bento Telemetry Metric Cards
        bento_layout = QHBoxLayout()
        bento_layout.setSpacing(14)

        self.card_gateway = StatusCard(
            title="بوابة الراوتر المنزلي (Gateway Link)",
            initial_value="1.2",
            unit="ms",
            desc="يقيس جودة اتصال جهازك بالراوتر عبر الواي فاي أو الكابل، ومعدل فقد الحزم.",
        )
        self.card_external = StatusCard(
            title="سرعة استجابة الإنترنت (Internet Ping)",
            initial_value="38.0",
            unit="ms",
            desc="يقيس سرعة استجابة السيرفرات الخارجية وسيرفرات الألعاب والتصفح العالمي.",
        )
        self.card_dns = StatusCard(
            title="خوادم فتح المواقع (DNS Resolver)",
            initial_value="22.0",
            unit="ms",
            desc="يقيس سرعة ترجمة أسماء المواقع وتجاوب المتصفح مع الروابط الجديدة.",
        )

        bento_layout.addWidget(self.card_gateway)
        bento_layout.addWidget(self.card_external)
        bento_layout.addWidget(self.card_dns)
        layout.addLayout(bento_layout)

        # 3. Bottom Section: Real-Time Plot + Autonomous Activity Feed
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(16)

        # Live Latency Wave Plot
        self.chart = RealTimePlotWidget(title="مخطط البنج واستقرار الاتصال لحظة بلحظة", y_label="ms")
        bottom_layout.addWidget(self.chart, stretch=1)

        # Autonomous Live Feed
        self.activity_feed = ActivityFeedWidget()
        self.activity_feed.setMinimumWidth(420)
        bottom_layout.addWidget(self.activity_feed)

        layout.addLayout(bottom_layout, stretch=1)

        # Initial feed entries
        now_str = datetime.now().strftime("%H:%M:%S")
        self.activity_feed.add_event(
            now_str,
            "بدء تشغيل الحارس الذكي للشبكة",
            "تم تشغيل محرك الرصد المستقل وحماية اتصالك بالإنترنت بنجاح.",
            level="info",
        )

    def update_telemetry(self, obs, last_diag: Diagnosis | None) -> None:
        """Called every second by MainWindow timer to refresh UI without user intervention."""
        # 1. Update KPI Cards
        gw_sample = obs.get_latest_measurement(MetricType.GATEWAY_LATENCY)
        if gw_sample:
            is_high = gw_sample.raw_value >= 40.0
            stat_text = "تذبذب أو بطء" if is_high else "متصل وممتاز"
            self.card_gateway.update_metric(f"{gw_sample.raw_value:.1f}", stat_text, is_warning=is_high)

        ext_sample = obs.get_latest_measurement(MetricType.EXTERNAL_LATENCY)
        if ext_sample:
            is_high = ext_sample.raw_value >= 80.0
            stat_text = "بطء استجابة" if is_high else "سريع ومستقر"
            self.card_external.update_metric(f"{ext_sample.raw_value:.1f}", stat_text, is_warning=is_high)

        dns_sample = obs.get_latest_measurement(MetricType.DNS_LATENCY)
        if dns_sample:
            is_slow = dns_sample.raw_value >= 60.0
            stat_text = "تصفح متثاقل" if is_slow else "استجابة فورية"
            self.card_dns.update_metric(f"{dns_sample.raw_value:.1f}", stat_text, is_warning=is_slow)

        # 2. Update Live Chart
        ext_window = obs.get_sliding_window(MetricType.EXTERNAL_LATENCY)
        if ext_window:
            y_vals = [s.raw_value for s in ext_window]
            self.chart.update_data(y_vals)

        # 3. Update Health Radar & Smart Diagnosis Card
        if last_diag:
            self.diag_card.update_with_diagnosis(last_diag)
            
            if last_diag.probable_cause == ProbableCause.HEALTHY:
                self.radar.set_health(
                    99,
                    "الشبكة محمية ومستقرة",
                    "المراقبة التنبؤية نشطة · الإصلاح الذاتي التلقائي مفعل",
                    "#2ea043",
                )
            elif last_diag.probable_cause in (ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY, ProbableCause.DNS_HIGH_LATENCY):
                self.radar.set_health(
                    78,
                    "تنبيه: تم رصد بطء في الاتصال",
                    "يقوم NetGuard بمتابعة الحالة ومعالجة المسار ذاتياً",
                    "#e3b341",
                )
            else:
                self.radar.set_health(
                    45,
                    "عطل في الشبكة قيد المعالجة",
                    "جاري تطبيق بروتوكول التعافي الذاتي الآمن",
                    "#f85149",
                )

    def log_autonomous_action(self, title: str, description: str, level: str = "success") -> None:
        """Public method to push live autonomous actions to the activity stream."""
        time_str = datetime.now().strftime("%H:%M:%S")
        self.activity_feed.add_event(time_str, title, description, level=level)
