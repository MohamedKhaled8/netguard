"""Quality of Experience (QoE) Calculation Engine."""

from __future__ import annotations
import logging
from typing import Dict, List, Optional
from app.core.events.bus import EventBus
from app.core.models.metrics import Measurement, MetricType
from app.qoe.models import QoEAssessment, QoECategoryScore

logger = logging.getLogger("netguard.qoe.engine")


class QoEEngine:
    """Computes transparent QoE scores for conferencing, gaming, streaming, browsing, and downloads."""

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self._last_assessment: Optional[QoEAssessment] = None

    @staticmethod
    def _rating(score: float) -> str:
        if score >= 90.0:
            return "Excellent"
        elif score >= 75.0:
            return "Good"
        elif score >= 50.0:
            return "Fair"
        return "Poor"

    def calculate_qoe(
        self,
        latency_ms: float,
        jitter_ms: float,
        packet_loss_ratio: float,
        dns_latency_ms: float,
        rx_bytes_sec: float = 0.0,
    ) -> QoEAssessment:
        bottlenecks: List[str] = []

        # 1. Video Conferencing (Sensitive to Jitter and Loss)
        # Loss penalty: 1% loss = -15 pts
        # Jitter penalty: >20ms = -0.8 pts/ms
        # Latency penalty: >100ms = -0.3 pts/ms
        conf_score = 100.0
        conf_score -= (packet_loss_ratio * 100.0) * 15.0
        if jitter_ms > 20.0:
            conf_score -= (jitter_ms - 20.0) * 0.8
            bottlenecks.append(f"Elevated Jitter ({jitter_ms:.1f}ms) degrades video conference audio")
        if latency_ms > 120.0:
            conf_score -= (latency_ms - 120.0) * 0.3
        conf_score = max(0.0, min(100.0, conf_score))
        conf_factor = "Jitter" if jitter_ms > 30 else ("Packet Loss" if packet_loss_ratio > 0.02 else "None")

        # 2. Competitive Gaming (Extremely sensitive to Latency & Packet Loss)
        # Latency: <30ms ideal. >60ms starts degrading.
        game_score = 100.0
        if latency_ms > 35.0:
            game_score -= (latency_ms - 35.0) * 0.7
        game_score -= (packet_loss_ratio * 100.0) * 25.0
        if jitter_ms > 15.0:
            game_score -= (jitter_ms - 15.0) * 1.2
            bottlenecks.append(f"Jitter ({jitter_ms:.1f}ms) causes game stutter/desync")
        game_score = max(0.0, min(100.0, game_score))
        game_factor = "Latency" if latency_ms > 60.0 else ("Jitter" if jitter_ms > 20 else "None")

        # 3. Media Streaming (Buffer absorbs jitter, but loss hurts)
        stream_score = 100.0 - ((packet_loss_ratio * 100.0) * 10.0)
        if latency_ms > 200.0:
            stream_score -= 15.0
        stream_score = max(0.0, min(100.0, stream_score))
        stream_factor = "Packet Loss" if packet_loss_ratio > 0.05 else "None"

        # 4. Web Browsing (Driven by DNS and initial TCP latency)
        browse_score = 100.0
        if dns_latency_ms > 60.0:
            browse_score -= (dns_latency_ms - 60.0) * 0.3
            bottlenecks.append(f"Slow DNS ({dns_latency_ms:.1f}ms) delays page loading")
        if latency_ms > 100.0:
            browse_score -= (latency_ms - 100.0) * 0.25
        browse_score -= (packet_loss_ratio * 100.0) * 8.0
        browse_score = max(0.0, min(100.0, browse_score))
        browse_factor = "DNS Latency" if dns_latency_ms > 100.0 else "None"

        # 5. File Downloads (High tolerance for latency, sensitive to packet loss)
        dl_score = 100.0 - ((packet_loss_ratio * 100.0) * 12.0)
        if latency_ms > 250.0:
            dl_score -= 10.0
        dl_score = max(0.0, min(100.0, dl_score))
        dl_factor = "Packet Loss" if packet_loss_ratio > 0.03 else "None"

        # Overall composite score
        overall = (conf_score * 0.3) + (game_score * 0.25) + (browse_score * 0.2) + (stream_score * 0.15) + (dl_score * 0.1)

        assessment = QoEAssessment(
            overall_score=overall,
            overall_rating=self._rating(overall),
            conferencing=QoECategoryScore(
                score=conf_score,
                rating=self._rating(conf_score),
                primary_limiting_factor=conf_factor,
            ),
            gaming=QoECategoryScore(
                score=game_score,
                rating=self._rating(game_score),
                primary_limiting_factor=game_factor,
            ),
            streaming=QoECategoryScore(
                score=stream_score,
                rating=self._rating(stream_score),
                primary_limiting_factor=stream_factor,
            ),
            browsing=QoECategoryScore(
                score=browse_score,
                rating=self._rating(browse_score),
                primary_limiting_factor=browse_factor,
            ),
            downloads=QoECategoryScore(
                score=dl_score,
                rating=self._rating(dl_score),
                primary_limiting_factor=dl_factor,
            ),
            bottlenecks=bottlenecks,
            measured_inputs={
                "latency_ms": latency_ms,
                "jitter_ms": jitter_ms,
                "packet_loss_ratio": packet_loss_ratio,
                "dns_latency_ms": dns_latency_ms,
            },
        )
        self._last_assessment = assessment
        return assessment

    @property
    def latest_assessment(self) -> Optional[QoEAssessment]:
        return self._last_assessment
