"""Design tokens for NetGuard AI.

Single source of truth for colors, typography, metrics, spacing, and radii.
Strictly adheres to dark, warm-neutral graphite palette (#0E1012).
No emoji, no neon, no glow, no gradients, flat surfaces separated by 1px hairlines.
"""

from __future__ import annotations
import os
import logging
from typing import Optional
from PySide6.QtGui import QFont, QFontDatabase

logger = logging.getLogger("netguard.tokens")

# -----------------------------------------------------------------------------
# Colors (Dark warm-neutral graphite palette)
# -----------------------------------------------------------------------------
BG = "#0E1012"
SIDEBAR = "#0A0B0C"
SURFACE = "#15181A"
SURFACE_INSET = "#101315"
RANGE_TRACK = "#0E1012"
SURFACE_HOVER = "#1B1F22"
SURFACE_SELECTED = "#1B1F22"

LINE = "#25292C"
LINE_STRONG = "#2C3033"
LINE_THRESHOLD = "#3A4044"

TEXT = "#ECEBE6"
TEXT_SECONDARY = "#B4B8BC"
TEXT_MUTED = "#9AA0A6"

# Single UI accent (ivory) - can be re-themed in one place
ACCENT = "#ECEBE6"

# Status colors (ONLY used to convey real status)
STATUS_OK = "#5FD38D"
STATUS_WARN = "#F5B942"
STATUS_BAD = "#FF6B5E"

# Bad soft (event chip)
BAD_SOFT_BG = "#2A1614"
BAD_SOFT_BORDER = "#5A2B27"
BAD_SOFT_TEXT = "#FF9A90"

# Ok soft (resolved chip)
OK_SOFT_BG = "#0F2218"
OK_SOFT_BORDER = "#2C5A42"
OK_SOFT_TEXT = "#5FD38D"

# Warn tags
WARN_BORDER = "#5A4A1C"

# Empty / future progress bar
BAR_FUTURE = "#2A2E31"

# Focus ring
FOCUS_RING = "#7AA2FF"

# -----------------------------------------------------------------------------
# Spacing & Radii
# -----------------------------------------------------------------------------
SPACING_SCALE = [4, 8, 12, 16, 20, 24, 28, 40]
PAGE_PADDING_DESKTOP = 40
PAGE_PADDING_NARROW = 16
SECTION_GAP = 28
PANEL_GAP = 20

RADIUS_PANEL = 16
RADIUS_BUTTON = 10
RADIUS_INNER = 12
RADIUS_CHIP = 999
RADIUS_BAR = 3

BORDER_WIDTH = 1

# Global animation kill-switch
ANIMATIONS_ENABLED = True

# -----------------------------------------------------------------------------
# Typography
# -----------------------------------------------------------------------------
FONT_FAMILY_SANS = "IBM Plex Sans Arabic"
FONT_FAMILY_MONO = "IBM Plex Mono"
FALLBACK_SANS = "Segoe UI"
FALLBACK_MONO = "Consolas"

_FONTS_INITIALIZED = False


def init_fonts() -> None:
    """Load bundled fonts into QFontDatabase."""
    global _FONTS_INITIALIZED
    if _FONTS_INITIALIZED:
        return

    import sys
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = os.path.join(sys._MEIPASS, "assets", "fonts")
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts"))
    if os.path.isdir(base_dir):
        for font_file in os.listdir(base_dir):
            if font_file.lower().endswith((".ttf", ".otf")):
                font_path = os.path.join(base_dir, font_file)
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id == -1:
                    logger.warning("Failed to load application font: %s", font_file)
    _FONTS_INITIALIZED = True


def get_sans_font(size: int = 14, weight: int = 400) -> QFont:
    """Create a sans-serif UI font (IBM Plex Sans Arabic -> Segoe UI)."""
    init_fonts()
    font = QFont(FONT_FAMILY_SANS, size)
    font.setWeight(QFont.Weight(weight))
    font.setStyleHint(QFont.StyleHint.SansSerif)
    return font


def get_mono_font(size: int = 13, weight: int = 400) -> QFont:
    """Create a monospace font (IBM Plex Mono -> Consolas)."""
    init_fonts()
    font = QFont(FONT_FAMILY_MONO, size)
    font.setWeight(QFont.Weight(weight))
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font
