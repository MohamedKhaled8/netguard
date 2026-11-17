"""StatusCard backwards-compatibility wrapper around MetricCell.

100% token-compliant, dark warm-neutral graphite (#15181A), 1px hairline border.
No colored top border, no emoji, no glowing neon.
"""

from __future__ import annotations
from typing import Optional
from app.ui import tokens
from app.ui.widgets.metric_cell import MetricCell


class StatusCard(MetricCell):
    """Token-compliant status card implementing MetricCell contract."""

    def __init__(
        self,
        title: str,
        initial_value: str = "--",
        unit: str = "",
        desc: str = "",
        icon: str = "",
        parent=None,
    ) -> None:
        super().__init__(
            title=title,
            initial_val=initial_value,
            unit=unit,
            footer_text=desc or "ممتاز · قيد المراقبة",
            status_color=tokens.STATUS_OK,
            parent=parent,
        )
        self.setObjectName("StatusCard")
        # Ensure hairline border when used as a standalone card
        self.setStyleSheet(f"""
            QFrame#StatusCard {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_INNER}px;
            }}
        """)
