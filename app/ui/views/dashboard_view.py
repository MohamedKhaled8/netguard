"""Master Autonomous Cockpit View for NetGuard AI Desktop.

High-craft, Dribbble-grade presentation:
- MasterShieldWidget: Tactical glowing connection shield and autonomous status.
- Bento Metric Row: Gateway latency, Internet Ping, and DNS Resolution.
- LatencyWaveWidget: Cinematic smooth gradient-filled latency wave plot.
- ActivityFeedWidget: Real-time autonomous action stream.
"""

from __future__ import annotations
from datetime import datetime
from typing import List
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)
from PySide6.QtCore import Qt

from app.ui.widgets.master_shield import MasterShieldWidget
from app.ui.widgets.latency_wave import LatencyWaveWidget
from app.ui.widgets.activity_feed import ActivityFeedWidget
from app.ui.widgets.status_card import StatusCard
from app.core.models.metrics import Diagnosis, ProbableCause, MetricType


class DashboardView(QWidget):
    """Executive Autonomous Command Cockpit."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # 1. Master Connection Shield Hero
        self.shield = MasterShieldWidget()
        layout.addWidget(self.shield)

        # 2. Bento Telemetry Cards Row
        bento_layout = QHBoxLayout()
        bento_layout.setSpacing(12)

        self.card_gateway = StatusCard(
            title="بوابة الراوتر المنزلي (Gateway Link)",
            initial_value="1.2",
            unit="ms",
            desc="يقيس جودة اتصال جهازك بالراوتر عبر الواي فاي أو الكابل، ومعدل فقد الحزم.",
        )
        self.card_external = StatusCard(
            title="سرعة استجابة الإنترنت (Internet Ping)",
            initial_value="24.0",
            unit="ms",
            desc="يقيس سرعة استجابة السيرفرات الخارجية وسيرفرات الألعاب والتصفح العالمي.",
        )
        self.card_dns = StatusCard(
            title="خوادم فتح المواقع (DNS Resolver)",
            initial_value="18.0",
            unit="ms",
            desc="يقيس سرعة ترجمة أسماء المواقع وتجاوب المتصفح مع الروابط الجديدة.",
        )

        bento_layout.addWidget(self.card_gateway)
        bento_layout.addWidget(self.card_external)
        bento_layout.addWidget(self.card_dns)
        layout.addLayout(bento_layout)

        # 3. Bottom Row: Latency Wave + Autonomous Feed
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(14)

        # Live Latency Wave Plot
        self.wave_chart = LatencyWaveWidget()
        bottom_layout.addWidget(self.wave_chart, stretch=3)

        # Autonomous Live Feed
        self.activity_feed = ActivityFeedWidget()
        self.activity_feed.setMinimumWidth(380)
        self.activity_feed.setMaximumWidth(460)
        bottom_layout.addWidget(self.activity_feed, stretch=2)

        layout.addLayout(bottom_layout, stretch=1)

        # Initial feed entry
        now_str = datetime.now().strftime("%H:%M:%S")
        self.activity_feed.add_event(
            now_str,
            "بدء الحماية الذاتية المستقلة",
            "تم تشغيل خوارزميات الرصد والتعافي التلقائي · الشبكة مؤمنة بالكامل.",
            level="success",
        )

    def update_telemetry(self, obs, last_diag: Diagnosis | None) -> None:
        """Called every second by MainWindow timer to refresh UI without user intervention."""
        # 1. Update KPI Cards
        gw_sample = obs.get_latest_measurement(MetricType.GATEWAY_LATENCY)
        gw_str = "1.2 ms"
        if gw_sample:
            gw_str = f"{gw_sample.raw_value:.1f} ms"
            is_high = gw_sample.raw_value >= 40.0
            stat_text = "تذبذب أو بطء" if is_high else "متصل وممتاز"
            self.card_gateway.update_metric(f"{gw_sample.raw_value:.1f}", stat_text, is_warning=is_high)

        ext_sample = obs.get_latest_measurement(MetricType.EXTERNAL_LATENCY)
        ping_str = "24.0 ms"
        if ext_sample:
            ping_str = f"{ext_sample.raw_value:.1f} ms"
            is_high = ext_sample.raw_value >= 80.0
            stat_text = "بطء استجابة" if is_high else "سريع ومستقر"
            self.card_external.update_metric(f"{ext_sample.raw_value:.1f}", stat_text, is_warning=is_high)

        dns_sample = obs.get_latest_measurement(MetricType.DNS_LATENCY)
        dns_str = "Cloudflare"
        if dns_sample:
            dns_str = f"{dns_sample.raw_value:.1f} ms"
            is_slow = dns_sample.raw_value >= 60.0
            stat_text = "تصفح متثاقل" if is_slow else "استجابة فورية"
            self.card_dns.update_metric(f"{dns_sample.raw_value:.1f}", stat_text, is_warning=is_slow)

        # 2. Update Live Wave Chart
        ext_window = obs.get_sliding_window(MetricType.EXTERNAL_LATENCY)
        jit_sample = obs.get_latest_measurement(MetricType.JITTER_MS)
        jitter_val = jit_sample.raw_value if jit_sample else 1.2
        if ext_window:
            y_vals = [s.raw_value for s in ext_window]
            self.wave_chart.update_samples(y_vals, jitter=jitter_val)

        # 3. Update Master Shield
        if last_diag:
            is_healthy = (last_diag.probable_cause == ProbableCause.HEALTHY)
            if is_healthy:
                title = "اتصالك بالإنترنت محمي ومستقر تماماً"
                desc = "يعمل NetGuard AI في الخلفية بمراقبة حزم البيانات والراوتر وخوادم DNS ذاتياً، والاتصال يعمل بأعلى سرعة."
            else:
                title = f"تنبيه: {last_diag.probable_cause.value.replace('_', ' ').upper()}"
                desc = last_diag.explanation

            self.shield.update_shield(
                is_healthy=is_healthy,
                title=title,
                desc=desc,
                gw_val=gw_str,
                ping_val=ping_str,
                dns_val=dns_str,
            )

    def log_autonomous_action(self, title: str, description: str, level: str = "success") -> None:
        """Public method to push live autonomous actions to the activity stream."""
        time_str = datetime.now().strftime("%H:%M:%S")
        self.activity_feed.add_event(time_str, title, description, level=level)
