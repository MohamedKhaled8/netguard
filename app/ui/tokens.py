"""Design tokens for NetGuard AI.

Three layers: primitive hex values, semantic roles, then component use.
Dark operational surfaces, one warm action accent, status colors only for real state.
Arabic UI keeps IBM Plex Sans Arabic. Display faces without Arabic glyphs
(Playfair, Chakra Petch, Orbitron) are not used for labels.
"""

from __future__ import annotations
import os
import logging
from typing import Any, Optional
from PySide6.QtGui import QFont, QFontDatabase

logger = logging.getLogger("netguard.tokens")

# -----------------------------------------------------------------------------
# Colors
# Primitive surfaces stay near-black. Accent is the action color only.
# Status green / amber / red stay separate from the accent so health is not
# confused with a button.
# -----------------------------------------------------------------------------
BG = "#090B0E"
SIDEBAR = "#0C0E12"
SURFACE = "#161A1F"
SURFACE_INSET = "#101318"
RANGE_TRACK = "#090B0E"
SURFACE_HOVER = "#1E242B"
SURFACE_SELECTED = "#241910"

LINE = "#2A3138"
LINE_STRONG = "#3A434C"
LINE_THRESHOLD = "#4A545E"

TEXT = "#ECEBE6"
TEXT_SECONDARY = "#C5C9CE"
TEXT_MUTED = "#A7ADB4"

# Action accent. Dark text on this orange clears 4.5:1; white text does not.
ACCENT = "#FF5701"
ACCENT_HOVER = "#E64E00"
ACCENT_PRESSED = "#C44300"
ON_ACCENT = "#111827"

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

# Global animation switch and master clock parameters
# Energy-efficient 20 FPS (50ms) unified clock (< 0.1% CPU, ideal for low-end 2GB hardware)
ANIMATIONS_ENABLED = True
LOW_RESOURCE_MODE = False
ANIMATION_MASTER_FPS = 20
ANIMATION_MASTER_INTERVAL_MS = 50

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


def format_arabic_connections(count: int) -> str:
    """Format connection count according to Arabic dual and plural grammar rules."""
    if count == 0:
        return "لا توجد اتصالات"
    elif count == 1:
        return "اتصال واحد"
    elif count == 2:
        return "اتصالان"
    elif 3 <= count <= 10:
        return f"{count} اتصالات"
    else:
        return f"{count} اتصالاً"


def bidi_isolate(text: Any) -> str:
    """Wrap Latin tokens or numeric specs in Unicode LTR isolate so RTL punctuation never scrambles."""
    return f"\u2066{text}\u2069"


def _flatten_frame_style(style: str) -> str:
    """Windows still paints a black box when the stylesheet says border: none."""
    text = style or ""
    text = text.replace("border: none", "border: 0px solid transparent")
    text = text.replace("border:none", "border: 0px solid transparent")
    if "border" not in text and "{" not in text:
        body = text.rstrip().rstrip(";")
        text = (body + "; " if body else "") + "background: transparent; border: 0px solid transparent; padding: 0px;"
    return text


def _install_label_frame_fix() -> None:
    """QLabel/QFrame/QPushButton: Windows paints a black box when border: none."""
    from PySide6.QtWidgets import QFrame, QLabel, QPushButton

    for cls in (QLabel, QFrame, QPushButton):
        if getattr(cls, "_netguard_frame_fix", False):
            continue
        original = cls.setStyleSheet

        def set_style(self, style: str, original=original) -> None:
            original(self, _flatten_frame_style(style))

        cls.setStyleSheet = set_style
        cls._netguard_frame_fix = True


_install_label_frame_fix()
