"""Cellular 4G/5G Radio Link Telemetry Models."""

from __future__ import annotations
from enum import Enum
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class SignalQualityCategory(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    NO_SIGNAL = "no_signal"


class CellularMetrics(BaseModel):
    """Normalized cellular modem physical layer telemetry."""
    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    technology: str = "LTE"  # LTE, 5G_NSA, 5G_SA, 3G
    band: Optional[str] = None  # e.g. B1, B3, B7, B20, B28, n78
    cell_id: Optional[str] = None
    rsrp_dbm: Optional[float] = None  # Reference Signal Received Power (-140 to -44 dBm)
    rsrq_db: Optional[float] = None   # Reference Signal Received Quality (-20 to -3 dB)
    sinr_db: Optional[float] = None   # Signal-to-Interference-plus-Noise Ratio (-20 to +30 dB)
    rssi_dbm: Optional[float] = None  # Received Signal Strength Indicator
    signal_bars: int = Field(default=0, ge=0, le=5)
    quality_category: SignalQualityCategory = SignalQualityCategory.FAIR

    @staticmethod
    def classify_quality(rsrp: Optional[float], sinr: Optional[float]) -> SignalQualityCategory:
        """Classify cellular signal based on 3GPP RSRP & SINR thresholds."""
        if rsrp is None:
            return SignalQualityCategory.FAIR

        if rsrp >= -80.0 and (sinr is None or sinr >= 20.0):
            return SignalQualityCategory.EXCELLENT
        elif rsrp >= -90.0 and (sinr is None or sinr >= 13.0):
            return SignalQualityCategory.GOOD
        elif rsrp >= -100.0 and (sinr is None or sinr >= 0.0):
            return SignalQualityCategory.FAIR
        elif rsrp < -100.0:
            return SignalQualityCategory.POOR
        return SignalQualityCategory.NO_SIGNAL
