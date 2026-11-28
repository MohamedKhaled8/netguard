"""Design tokens for NetGuard AI.

Three layers: primitive hex values, semantic roles, then component use.
Deep navy & charcoal network engineering workstation palette with restrained
electric blue accent, green healthy, amber warning, red critical, and purple
secondary/upload metrics.
Arabic UI keeps IBM Plex Sans Arabic; technical values use IBM Plex Mono + LTR isolation.
"""

from __future__ import annotations
import os
import re
import logging
from enum import Enum
from typing import Any, Dict, Tuple
from PySide6.QtGui import QFont, QFontDatabase

logger = logging.getLogger("netguard.tokens")

# -----------------------------------------------------------------------------
# Layer 1 & 2: Deep Navy / Charcoal Surfaces & Semantic Palette
# -----------------------------------------------------------------------------
BG = "#0A0F1A"
SIDEBAR = "#0D1322"
SURFACE = "#121A2D"
SURFACE_ELEVATED = "#172138"
SURFACE_INSET = "#0E1525"
RANGE_TRACK = "#090E18"
SURFACE_HOVER = "#1C2742"
SURFACE_SELECTED = "#182848"

LINE = "#1F2B44"
LINE_STRONG = "#2D3D5E"
LINE_THRESHOLD = "#3E5078"

TEXT = "#EEF2F7"
TEXT_SECONDARY = "#B5C0D4"
TEXT_MUTED = "#7F8EA8"

# Restrained electric blue primary action accent (white text >= 5.1:1 contrast)
ACCENT = "#2563EB"
ACCENT_HOVER = "#3B82F6"
ACCENT_PRESSED = "#1D4ED8"
ACCENT_SOFT = "#172554"
ON_ACCENT = "#FFFFFF"

# Secondary measurement / data visualization colors
CYAN = "#0EA5E9"       # Download traffic / primary RF curve
PURPLE = "#C084FC"     # Upload traffic / secondary diagnostics (>= 6.5:1 contrast on dark surfaces)

# Semantic status colors (ONLY used to convey real measured/verified state)
STATUS_OK = "#22C55E"
STATUS_WARN = "#F59E0B"
STATUS_BAD = "#EF4444"
STATUS_INFO = "#38BDF8"
STATUS_PURPLE = "#C084FC"

# Soft chip / pill backgrounds & borders
BAD_SOFT_BG = "#2A1215"
BAD_SOFT_BORDER = "#692329"
BAD_SOFT_TEXT = "#FCA5A5"

OK_SOFT_BG = "#0E291B"
OK_SOFT_BORDER = "#1E5E3A"
OK_SOFT_TEXT = "#4ADE80"

WARN_SOFT_BG = "#291E0B"
WARN_BORDER = "#6B4E16"
WARN_SOFT_TEXT = "#FCD34D"

INFO_SOFT_BG = "#0F223A"
INFO_SOFT_BORDER = "#1E4B7A"
INFO_SOFT_TEXT = "#7DD3FC"

PURPLE_SOFT_BG = "#231438"
PURPLE_SOFT_BORDER = "#582D8C"
PURPLE_SOFT_TEXT = "#D8B4FE"

# Empty / future progress bar & semantic token aliases
BAR_FUTURE = "#1E293B"
BG_ELEVATED = SURFACE_ELEVATED
ACCENT_BRIGHT = "#60A5FA"
SECONDARY_CYAN = CYAN
SECONDARY_PURPLE = PURPLE
INFO_BORDER = INFO_SOFT_BORDER
PURPLE_BORDER = PURPLE_SOFT_BORDER

# Focus ring
FOCUS_RING = "#60A5FA"

# -----------------------------------------------------------------------------
# Global Standardized Status System
# -----------------------------------------------------------------------------
class SystemStatus(str, Enum):
    HEALTHY = "healthy"
    ACTIVE = "active"
    RUNNING = "running"
    WARNING = "warning"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    NOT_CONNECTED = "not_connected"
    WAITING = "waiting"
    VERIFYING = "verifying"


# (foreground, background, border)
STATUS_COLOR_MAP: Dict[str, Tuple[str, str, str]] = {
    SystemStatus.HEALTHY.value: (STATUS_OK, OK_SOFT_BG, OK_SOFT_BORDER),
    SystemStatus.ACTIVE.value: (STATUS_OK, OK_SOFT_BG, OK_SOFT_BORDER),
    SystemStatus.RUNNING.value: (STATUS_INFO, INFO_SOFT_BG, INFO_SOFT_BORDER),
    SystemStatus.WARNING.value: (STATUS_WARN, WARN_SOFT_BG, WARN_BORDER),
    SystemStatus.FAILED.value: (STATUS_BAD, BAD_SOFT_BG, BAD_SOFT_BORDER),
    SystemStatus.UNAVAILABLE.value: (TEXT_MUTED, SURFACE_INSET, LINE),
    SystemStatus.UNSUPPORTED.value: (TEXT_MUTED, SURFACE_INSET, LINE),
    SystemStatus.NOT_CONNECTED.value: (STATUS_BAD, BAD_SOFT_BG, BAD_SOFT_BORDER),
    SystemStatus.WAITING.value: (TEXT_SECONDARY, SURFACE_INSET, LINE_STRONG),
    SystemStatus.VERIFYING.value: (STATUS_PURPLE, PURPLE_SOFT_BG, PURPLE_SOFT_BORDER),
}

# -----------------------------------------------------------------------------
# Layer 3: Spacing & Radii (4px grid)
# -----------------------------------------------------------------------------
SPACING_SCALE = [4, 8, 12, 16, 20, 24, 28, 32, 40]
PAGE_PADDING_DESKTOP = 28
PAGE_PADDING_NARROW = 16
MAX_CONTENT_WIDTH = 1360
SECTION_GAP = 20
PANEL_GAP = 16

RADIUS_PANEL = 12
RADIUS_BUTTON = 8
RADIUS_INNER = 10
RADIUS_CHIP = 999
RADIUS_BAR = 3

BORDER_WIDTH = 1

# Global animation switch and master clock parameters
# Energy-efficient 20 FPS (50ms) unified clock
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


_LATIN_TECH_RUN_RE = re.compile(
    r"\(\s*[A-Za-z0-9][A-Za-z0-9_.\-/:+=% ]*[A-Za-z0-9%]\s*\)"
    r"|(?:[+\-]?(?:[A-Za-z0-9][A-Za-z0-9_.\-/:+=% ]*[A-Za-z0-9%]))"
    r"|(?:[+\-]?\d+(?:\.\d+)?%)"
    r"|(?:[A-Za-z])"
)


def bidi_isolate(text: Any) -> str:
    """Wrap Latin tokens or numeric specs in Unicode LTR isolate so RTL punctuation never scrambles."""
    return f"\u2066{text}\u2069"


def bidi_isolate_mixed(text: Any) -> str:
    """Keep Arabic RTL paragraphs in RTL direction while isolating embedded Latin/numeric tokens as LTR."""
    if text is None:
        return ""
    s = str(text)
    if not s:
        return s
    has_arabic = any("\u0600" <= ch <= "\u06FF" or "\u0750" <= ch <= "\u077F" or "\u08A0" <= ch <= "\u08FF" for ch in s)
    if not has_arabic:
        if s.startswith("\u2066") and s.endswith("\u2069"):
            return s
        if any(ch.isascii() and (ch.isalnum() or ch in "<>-+.") for ch in s):
            return bidi_isolate(s)
        return s
    parts = re.split(r"(\u2066[^\u2069]*\u2069)", s)
    out = []
    for part in parts:
        if part.startswith("\u2066") and part.endswith("\u2069"):
            out.append(part)
        else:
            out.append(_LATIN_TECH_RUN_RE.sub(lambda m: f"\u2066{m.group(0)}\u2069\u200f", part))
    return "".join(out)


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
