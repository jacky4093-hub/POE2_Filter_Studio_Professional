"""Live Preview Panel — v3.0.0  (P19.4A Preview Modernization)

Architecture (unchanged from v0.7.0)
--------------------------------------
PreviewStyle          — pure Python dataclass, zero Qt dependency
parse_rule_style()    — pure function: FilterRule → PreviewStyle, never raises
PreviewPanel          — QWidget that renders PreviewStyle, read-only

Public API of PreviewPanel (unchanged):
    show_rule(rule: FilterRule)  — update display for the given rule
    show_empty()                 — show "no selection" placeholder

Design contract (unchanged):
    • PreviewPanel never modifies FilterRule or FilterDocument
    • PreviewPanel never calls any Command
    • parse_rule_style() is a side-effect-free pure function
    • Every parse error falls back to PreviewStyle defaults silently

P19.4A additions (all use QPainter, no external assets):
    • GroundPreviewWidget  — dark stone ground + PlayEffect beam + item label overlay
    • MinimapPreviewWidget — circular minimap with concentric rings + icon marker
    • FilterSyntaxHighlighter — minimal keyword/value highlighting for filter syntax
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models import FilterRule


# ---------------------------------------------------------------------------
# PreviewStyle — pure data, no Qt
# ---------------------------------------------------------------------------

@dataclass
class PreviewStyle:
    item_action:      str   = "Show"
    text_color:       tuple = (200, 200, 200, 255)   # RGBA — POE2 default white-grey
    background_color: tuple = (0,   0,   0,   210)   # RGBA — POE2 default dark
    border_color:     tuple = (0,   0,   0,     0)   # RGBA — transparent = no border
    font_size:        int   = 32                      # POE2 default
    minimap_icon:     str   = ""                      # raw value from filter or ""
    play_effect:      str   = ""                      # raw value or ""
    alert_sound:      str   = ""                      # formatted or ""
    item_name:        str   = "Item Name"             # derived from conditions


# ---------------------------------------------------------------------------
# Internal parse helpers — all pure, never raise
# ---------------------------------------------------------------------------

def _parse_rgba(s: str, default: tuple) -> tuple:
    """Parse "R G B [A]" → clamped (R, G, B, A) tuple.  Fallback on any error."""
    try:
        parts = s.strip().split()
        vals  = [max(0, min(255, int(p))) for p in parts[:4]]
        while len(vals) < 4:
            vals.append(255)
        return tuple(vals[:4])
    except Exception:
        return default


def _parse_int(s: str, default: int, lo: int = 0, hi: int = 10000) -> int:
    """Parse first token as int, clamped to [lo, hi].  Fallback on any error."""
    try:
        return max(lo, min(hi, int(s.strip().split()[0])))
    except Exception:
        return default


def _derive_item_name(rule: "FilterRule") -> str:
    """Produce a sample item name from the rule's conditions."""
    for key in ("Class", "BaseType"):
        for k, v in rule.conditions:
            if k == key:
                cleaned    = v.strip().strip('"').strip("'").strip()
                first_word = cleaned.split()[0] if cleaned else ""
                if first_word:
                    return first_word
    if rule.conditions:
        return rule.conditions[0][0]
    return "Item Name"


_KNOWN_ACTIONS = frozenset({
    "SetTextColor", "SetBackgroundColor", "SetBorderColor", "SetFontSize",
    "MinimapIcon", "PlayEffect",
    "PlayAlertSound", "PlayAlertSoundPositional",
    "CustomAlertSound", "CustomAlertSoundOptional",
})


# ---------------------------------------------------------------------------
# parse_rule_style — pure function (unchanged behaviour from v0.7.0)
# ---------------------------------------------------------------------------

def parse_rule_style(rule: "FilterRule") -> PreviewStyle:
    """Convert a FilterRule to a PreviewStyle.

    Guaranteed pure: never raises, never modifies rule, no Qt dependency.
    """
    try:
        style = PreviewStyle()
        style.item_action = (
            rule.action if rule.action in ("Show", "Hide", "Continue", "Minimal")
            else "Show"
        )
        style.item_name = _derive_item_name(rule)

        action_map: dict[str, str] = {}
        for key, value in rule.actions:
            action_map[key] = value

        if "SetTextColor"       in action_map:
            style.text_color       = _parse_rgba(action_map["SetTextColor"],       style.text_color)
        if "SetBackgroundColor" in action_map:
            style.background_color = _parse_rgba(action_map["SetBackgroundColor"], style.background_color)
        if "SetBorderColor"     in action_map:
            style.border_color     = _parse_rgba(action_map["SetBorderColor"],     style.border_color)
        if "SetFontSize"        in action_map:
            style.font_size        = _parse_int( action_map["SetFontSize"],        style.font_size, lo=1, hi=45)
        if "MinimapIcon"        in action_map:
            style.minimap_icon = action_map["MinimapIcon"].strip()
        if "PlayEffect"         in action_map:
            style.play_effect  = action_map["PlayEffect"].strip()

        for sound_key in ("PlayAlertSound", "PlayAlertSoundPositional",
                          "CustomAlertSound", "CustomAlertSoundOptional"):
            if sound_key in action_map:
                style.alert_sound = f"{sound_key}: {action_map[sound_key].strip()}"
                break

        return style

    except Exception:
        return PreviewStyle()


# ---------------------------------------------------------------------------
# Effect / colour lookup tables  (shared by GroundPreviewWidget + Minimap)
# ---------------------------------------------------------------------------

_EFFECT_RGB: dict[str, tuple[int, int, int]] = {
    "White":  (230, 230, 230),
    "Red":    (220,  60,  60),
    "Green":  ( 60, 200,  60),
    "Blue":   ( 60, 120, 220),
    "Brown":  (150, 100,  40),
    "Yellow": (220, 200,  40),
    "Orange": (220, 140,  40),
    "Pink":   (220, 120, 170),
    "Purple": (150,  40, 200),
    "Cyan":   ( 40, 200, 200),
    "Grey":   (140, 140, 140),
}

_MINIMAP_RGB: dict[str, tuple[int, int, int]] = {
    "Red":    (220,  60,  60),
    "Green":  ( 60, 200,  60),
    "Blue":   ( 60, 120, 220),
    "Brown":  (150, 100,  40),
    "White":  (230, 230, 230),
    "Yellow": (220, 200,  40),
    "Cyan":   ( 40, 200, 200),
    "Grey":   (140, 140, 140),
    "Orange": (220, 140,  40),
    "Pink":   (220, 120, 170),
    "Purple": (150,  40, 200),
}

_SHAPE_SYMBOLS: dict[str, str] = {
    "Circle":          "●",
    "Diamond":         "◆",
    "Star":            "★",
    "Triangle":        "▲",
    "Square":          "■",
    "Cross":           "✚",
    "Hexagon":         "⬡",
    "Kite":            "◇",
    "Pentagon":        "⬟",
    "UpsideDownHouse": "⌂",
    "Moon":            "◐",
    "Raindrop":        "♦",
}


# ---------------------------------------------------------------------------
# GroundPreviewWidget — QPainter ground scene
# ---------------------------------------------------------------------------

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSizePolicy, QTextEdit,
)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient,
    QBrush, QPen, QFont, QSyntaxHighlighter, QTextCharFormat,
)


def _gen_noise(seed: int = 42, count: int = 280) -> list:
    """Pre-generate deterministic noise for ground texture (percent coords)."""
    rng = random.Random(seed)
    return [
        (rng.randint(0, 100),   # x %
         rng.randint(0, 100),   # y %
         rng.randint(1, 5),     # size px
         rng.randint(12, 50),   # alpha
         rng.randint(0, 4))     # colour variant index
        for _ in range(count)
    ]


_NOISE_CACHE = _gen_noise()   # computed once at import time


class GroundPreviewWidget(QWidget):
    """Paints a dark stone/ground background with optional PlayEffect beam."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("GroundPreviewWidget")
        self.setMinimumHeight(170)
        self.setMaximumHeight(210)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._style: PreviewStyle | None = None
        self._label: QLabel | None = None   # set by PreviewPanel after construction

    def set_style(self, style: PreviewStyle | None) -> None:
        self._style = style
        self._reposition_label()
        self.update()

    def _reposition_label(self) -> None:
        if self._label and self.width() > 0 and self.height() > 0:
            w, h = self.width(), self.height()
            lw = min(w - 24, 300)
            lh = 52
            # Horizontally centred (beam_x = w//2 = label centre_x)
            lx = (w - lw) // 2
            # Vertically: centre-lower (60 % from top)
            ly = max(0, h * 60 // 100 - lh // 2)
            self._label.setGeometry(lx, ly, lw, lh)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_label()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        w, h = self.width(), self.height()

        # ── Base: very dark brownish-gray stone ───────────────────────
        p.fillRect(0, 0, w, h, QColor(22, 16, 11))

        # ── Noise texture: scattered dark earth-tone pixels ───────────
        _NOISE_COLS = [
            QColor(48, 36, 24),   # brown
            QColor(36, 36, 32),   # dark grey
            QColor(28, 26, 18),   # olive-dark
            QColor(55, 40, 26),   # lighter brown
            QColor(18, 22, 28),   # dark blue-grey
        ]
        for pct_x, pct_y, psize, palpha, cidx in _NOISE_CACHE:
            nx = pct_x * w // 100
            ny = pct_y * h // 100
            col = _NOISE_COLS[cidx]
            col.setAlpha(palpha)
            p.fillRect(nx, ny, psize, psize, col)

        # ── Subtle vertical gradient overlay ─────────────────────────
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0,  QColor(10,  8,  5, 140))
        grad.setColorAt(0.35, QColor(32, 24, 16,  50))
        grad.setColorAt(1.0,  QColor( 6,  4,  2, 180))
        p.fillRect(0, 0, w, h, QBrush(grad))

        # ── PlayEffect beam ───────────────────────────────────────────
        if self._style and self._style.play_effect:
            color_key = self._style.play_effect.strip().split()[0]
            rgb = _EFFECT_RGB.get(color_key)
            if rgb:
                r, g, b = rgb
                bx = w // 2  # beam centre = label centre (both horizontally centred)
                # wide outer glow
                for gw, ga in ((44, 12), (24, 28), (10, 55), (4, 140)):
                    glow = QColor(r, g, b, ga)
                    p.fillRect(bx - gw // 2, 0, gw, h, glow)
                # bright core line
                beam_pen = QPen(QColor(r, g, b, 200), 2)
                p.setPen(beam_pen)
                p.drawLine(bx, 0, bx, h)

        # ── Vignette: darken the four edges ──────────────────────────
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        vig_w = min(70, w // 4)
        vig_h = min(50, h // 4)

        gl = QLinearGradient(0, 0, vig_w, 0)
        gl.setColorAt(0.0, QColor(0, 0, 0, 170));  gl.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(0, 0, vig_w, h, QBrush(gl))

        gr = QLinearGradient(w - vig_w, 0, w, 0)
        gr.setColorAt(0.0, QColor(0, 0, 0, 0));  gr.setColorAt(1.0, QColor(0, 0, 0, 170))
        p.fillRect(w - vig_w, 0, vig_w, h, QBrush(gr))

        gb = QLinearGradient(0, h - vig_h, 0, h)
        gb.setColorAt(0.0, QColor(0, 0, 0, 0));  gb.setColorAt(1.0, QColor(0, 0, 0, 200))
        p.fillRect(0, h - vig_h, w, vig_h, QBrush(gb))

        gt = QLinearGradient(0, 0, 0, vig_h)
        gt.setColorAt(0.0, QColor(0, 0, 0, 120));  gt.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(0, 0, w, vig_h, QBrush(gt))

        p.end()


# ---------------------------------------------------------------------------
# MinimapPreviewWidget — QPainter circular minimap
# ---------------------------------------------------------------------------

class MinimapPreviewWidget(QWidget):
    """Draws a circular POE2-style minimap with a coloured shape marker."""

    _SIZE = 150

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MinimapPreviewWidget")
        self.setFixedSize(self._SIZE, self._SIZE)
        self._color: str = ""
        self._shape: str = ""

    def set_icon(self, icon_str: str) -> None:
        """Parse 'size color shape' minimap icon string and repaint."""
        parts = icon_str.strip().split() if icon_str else []
        if len(parts) >= 3:
            self._color = parts[1]
            self._shape = parts[2]
        else:
            self._color = ""
            self._shape = ""
        self.update()

    def clear(self) -> None:
        self._color = ""
        self._shape = ""
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        s = self._SIZE
        cx, cy = s // 2, s // 2
        r = s // 2 - 4

        # ── Circular dark background ──────────────────────────────────
        bg_grad = QRadialGradient(cx, cy, r)
        bg_grad.setColorAt(0.0, QColor(30, 46, 80))
        bg_grad.setColorAt(0.65, QColor(18, 28, 55))
        bg_grad.setColorAt(1.0,  QColor( 8, 12, 28))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(bg_grad))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # ── Concentric rings (map grid lines) ─────────────────────────
        p.setBrush(Qt.BrushStyle.NoBrush)
        for frac in (0.30, 0.55, 0.80):
            rr = int(r * frac)
            p.setPen(QPen(QColor(50, 80, 130, 70), 1))
            p.drawEllipse(cx - rr, cy - rr, rr * 2, rr * 2)

        # ── Crosshair lines ───────────────────────────────────────────
        p.setPen(QPen(QColor(40, 65, 105, 55), 1))
        p.drawLine(cx - r, cy, cx + r, cy)
        p.drawLine(cx, cy - r, cx, cy + r)

        # ── Outer border ring ─────────────────────────────────────────
        p.setPen(QPen(QColor(65, 105, 175, 200), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # ── Inner decorative rim (subtle glow) ────────────────────────
        p.setPen(QPen(QColor(80, 130, 220, 60), 1))
        p.drawEllipse(cx - r + 3, cy - r + 3, (r - 3) * 2, (r - 3) * 2)

        # ── Marker ────────────────────────────────────────────────────
        if self._color and self._shape:
            rgb = _MINIMAP_RGB.get(self._color, (200, 200, 200))
            mc = QColor(*rgb)
            sym = _SHAPE_SYMBOLS.get(self._shape, "★")

            # marker position: slightly right of and above centre
            mx = cx + int(r * 0.28)
            my = cy - int(r * 0.10)
            marker_size = 16

            # glow halo
            glow = QColor(rgb[0], rgb[1], rgb[2], 70)
            font_glow = QFont("Arial Unicode MS, Segoe UI Symbol, Arial", marker_size + 4)
            p.setFont(font_glow)
            p.setPen(QPen(glow))
            rect_glow = QRect(mx - marker_size, my - marker_size,
                               marker_size * 2, marker_size * 2)
            p.drawText(rect_glow, Qt.AlignmentFlag.AlignCenter, sym)

            # main symbol
            font_main = QFont("Arial Unicode MS, Segoe UI Symbol, Arial", marker_size)
            font_main.setBold(True)
            p.setFont(font_main)
            p.setPen(QPen(mc))
            rect_main = QRect(mx - marker_size, my - marker_size,
                               marker_size * 2, marker_size * 2)
            p.drawText(rect_main, Qt.AlignmentFlag.AlignCenter, sym)

        p.end()


# ---------------------------------------------------------------------------
# FilterSyntaxHighlighter — minimal colour coding for filter text
# ---------------------------------------------------------------------------

class FilterSyntaxHighlighter(QSyntaxHighlighter):
    """Highlights POE2 filter keywords, directives, strings, and numbers."""

    def __init__(self, document) -> None:
        super().__init__(document)

        def _fmt(hex_color: str, bold: bool = False) -> QTextCharFormat:
            f = QTextCharFormat()
            f.setForeground(QColor(hex_color))
            if bold:
                f.setFontWeight(QFont.Weight.Bold)
            return f

        # Rules applied in order; later rules override earlier on overlap.
        # Each entry: (compiled regex, QTextCharFormat, group_index)
        # group_index=0 means highlight the whole match; group_index=N means group N.
        self._rules: list[tuple[re.Pattern, QTextCharFormat, int]] = [

            # Show / Hide / Continue / Minimal  (line-start keyword)
            (re.compile(r"^(Show|Hide|Continue|Minimal)\b"),
             _fmt("#55efc4", bold=True), 0),

            # Commented-out rule (# Show / # Hide …)
            (re.compile(r"^#\s*(Show|Hide|Continue|Minimal)\b"),
             _fmt("#636e72"), 0),

            # Full comment line
            (re.compile(r"^\s*#.*$"),
             _fmt("#4a5568"), 0),

            # Condition directive names
            (re.compile(
                r"(?m)^\s+(Class|BaseType|ItemLevel|ItemRarity|AreaLevel|Rarity|"
                r"GemLevel|Quality|HasExplicitMod|SocketGroup|Sockets|"
                r"LinkedSockets|Height|Width|MapTier|DropLevel|Corrupted|"
                r"Identified|HasInfluence|BlightedMap|FracturedItem|"
                r"SynthesisedItem|Replica|Mirrored|Scourged|StackSize|"
                r"AlternateQuality|WaystoneTier)\b"),
             _fmt("#a29bfe"), 0),

            # Action directive names
            (re.compile(
                r"(?m)^\s+(SetTextColor|SetBackgroundColor|SetBorderColor|"
                r"SetFontSize|MinimapIcon|PlayEffect|PlayAlertSound|"
                r"PlayAlertSoundPositional|CustomAlertSound|"
                r"CustomAlertSoundOptional)\b"),
             _fmt("#74b9ff"), 0),

            # Quoted strings
            (re.compile(r'"[^"]*"'),
             _fmt("#fdcb6e"), 0),

            # Bare numbers (not inside strings)
            (re.compile(r"\b\d+\b"),
             _fmt("#81ecec"), 0),

            # Comparison operators
            (re.compile(r"(?<!\w)(>=|<=|>|<|=|!)(?!\w)"),
             _fmt("#fd79a8"), 0),
        ]

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt, _grp in self._rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


# ---------------------------------------------------------------------------
# PreviewPanel — QWidget (read-only)
# ---------------------------------------------------------------------------

class PreviewPanel(QWidget):
    """Read-only visual preview of a FilterRule.

    Public API (unchanged from v0.7.0):
        show_rule(rule)  — render the rule
        show_empty()     — show no-selection placeholder

    All P13.2 widget attributes preserved for backward compatibility:
        _disabled_banner, _condition_lbl, _unknown_lbl
        _action_label, _item_label
        _minimap_badge, _effect_badge, _sound_badge
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("PreviewPanel")
        self.setMinimumWidth(180)
        self._setup_ui()
        self.show_empty()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(4)

        # ── Action badge (compact, at top) ────────────────────────────
        self._action_label = QLabel()
        self._action_label.setObjectName("PreviewActionBadge")
        self._action_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._action_label)

        # ── Disabled banner ───────────────────────────────────────────
        self._disabled_banner = QLabel("◆  此規則已停用（Disabled）")
        self._disabled_banner.setObjectName("PreviewDisabledBanner")
        self._disabled_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._disabled_banner)

        # ── Ground Preview section ────────────────────────────────────
        ground_hdr = QLabel("地面預覽")
        ground_hdr.setObjectName("PreviewSectionHeader")
        root.addWidget(ground_hdr)

        self._ground_widget = GroundPreviewWidget(self)
        root.addWidget(self._ground_widget)

        # _item_label is an overlay child of _ground_widget
        self._item_label = QLabel(self._ground_widget)
        self._item_label.setObjectName("PreviewItemLabel")
        self._item_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._item_label.setWordWrap(False)
        self._item_label.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )
        self._ground_widget._label = self._item_label

        # ── Condition summary ─────────────────────────────────────────
        self._condition_lbl = QLabel()
        self._condition_lbl.setObjectName("PreviewConditionLabel")
        self._condition_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._condition_lbl.setWordWrap(True)
        root.addWidget(self._condition_lbl)

        # ── Minimap Preview section ───────────────────────────────────
        mm_hdr = QLabel("小地圖預覽")
        mm_hdr.setObjectName("PreviewSectionHeader")
        root.addWidget(mm_hdr)

        mm_row = QHBoxLayout()
        mm_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._minimap_widget = MinimapPreviewWidget(self)
        mm_row.addWidget(self._minimap_widget)
        root.addLayout(mm_row)

        # ── Info badges (kept for backward compat / test assertions) ──
        badge_frame = QFrame()
        badge_frame.setObjectName("PreviewBadgeFrame")
        badge_frame.setFrameShape(QFrame.Shape.NoFrame)
        badge_layout = QVBoxLayout(badge_frame)
        badge_layout.setContentsMargins(2, 2, 2, 0)
        badge_layout.setSpacing(2)

        self._minimap_badge = self._make_badge()
        self._effect_badge  = self._make_badge()
        self._sound_badge   = self._make_badge()
        for badge in (self._minimap_badge, self._effect_badge, self._sound_badge):
            badge_layout.addWidget(badge)
        root.addWidget(badge_frame)

        # ── Unknown actions / lines ───────────────────────────────────
        self._unknown_lbl = QLabel()
        self._unknown_lbl.setObjectName("PreviewUnknownLabel")
        self._unknown_lbl.setWordWrap(True)
        self._unknown_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        root.addWidget(self._unknown_lbl)

        root.addStretch()

        # ── Syntax Preview section ────────────────────────────────────
        self._syntax_header = QLabel("語法預覽")
        self._syntax_header.setObjectName("PreviewSyntaxHeader")
        root.addWidget(self._syntax_header)

        self._syntax_text = QTextEdit()
        self._syntax_text.setObjectName("PreviewSyntaxText")
        self._syntax_text.setReadOnly(True)
        self._syntax_text.setMaximumHeight(200)
        self._syntax_text.setFont(QFont(
            "Consolas, Cascadia Code, Courier New, monospace", 11
        ))
        self._syntax_highlighter = FilterSyntaxHighlighter(
            self._syntax_text.document()
        )
        root.addWidget(self._syntax_text)

        # ── Empty-state placeholder ───────────────────────────────────
        self._empty_label = QLabel("（未選取規則）")
        self._empty_label.setObjectName("PreviewEmptyLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._empty_label)

    @staticmethod
    def _render_filter_text(rule: "FilterRule") -> str:
        """Generate raw filter text from a rule."""
        try:
            prefix = "" if rule.enabled else "# "
            lines = [f"{prefix}{rule.action}"]
            for key, value in rule.conditions:
                lines.append(f"    {key} {value}")
            for key, value in rule.actions:
                lines.append(f"    {key} {value}")
            for ul in rule.unknown_lines:
                lines.append(f"    {ul}")
            return "\n".join(lines)
        except Exception:
            return ""

    @staticmethod
    def _make_badge() -> QLabel:
        lbl = QLabel()
        lbl.setObjectName("PreviewBadge")
        lbl.setWordWrap(True)
        lbl.hide()
        return lbl

    # ------------------------------------------------------------------
    # Public API (unchanged signatures)
    # ------------------------------------------------------------------

    def show_rule(self, rule: "FilterRule") -> None:
        """Render the visual appearance of *rule*."""
        if rule is None or rule.action == "__TAIL__":
            self.show_empty()
            return
        try:
            style = parse_rule_style(rule)
            self._render(style, rule)
            self._syntax_text.setPlainText(self._render_filter_text(rule))
        except Exception:
            self.show_empty()

    def show_empty(self) -> None:
        """Display the no-selection placeholder."""
        self._action_label.hide()
        self._item_label.hide()
        self._minimap_badge.hide()
        self._effect_badge.hide()
        self._sound_badge.hide()
        self._disabled_banner.hide()
        self._condition_lbl.hide()
        self._unknown_lbl.hide()
        self._syntax_text.setPlainText("")
        self._ground_widget.set_style(None)
        self._minimap_widget.clear()
        self._empty_label.show()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render(self, style: PreviewStyle, rule: "FilterRule | None" = None) -> None:
        self._empty_label.hide()

        # ── Disabled banner ────────────────────────────────────────────
        is_disabled = rule is not None and not rule.enabled
        if is_disabled:
            self._disabled_banner.show()
        else:
            self._disabled_banner.hide()

        # ── Action badge ───────────────────────────────────────────────
        if style.item_action == "Hide":
            self._action_label.setText("▪ Hide（隱藏）")
            self._action_label.setStyleSheet(
                "font-size: 11px; color: #ff6b6b;"
                "background: #2a1515; border-radius: 3px; padding: 2px 8px;"
            )
        elif style.item_action == "Minimal":
            self._action_label.setText("▷ Minimal（最小化）")
            self._action_label.setStyleSheet(
                "font-size: 11px; color: #aaa;"
                "background: #1e1e1e; border-radius: 3px; padding: 2px 8px;"
            )
        elif style.item_action == "Continue":
            self._action_label.setText("▶ Continue（穿透）")
            self._action_label.setStyleSheet(
                "font-size: 11px; color: #74b9ff;"
                "background: #0d1a2e; border-radius: 3px; padding: 2px 8px;"
            )
        else:
            self._action_label.setText("▶ Show（顯示）")
            self._action_label.setStyleSheet(
                "font-size: 11px; color: #55efc4;"
                "background: #0d2a1f; border-radius: 3px; padding: 2px 8px;"
            )
        self._action_label.show()

        # ── Ground widget ──────────────────────────────────────────────
        self._ground_widget.set_style(style)

        # ── Minimap widget ─────────────────────────────────────────────
        self._minimap_widget.set_icon(style.minimap_icon)

        # ── Item label (overlay inside _ground_widget) ─────────────────
        tc = style.text_color
        bc = style.background_color
        br = style.border_color
        fs = max(9, min(36, style.font_size))

        is_hidden   = (style.item_action == "Hide")
        alpha_factor = 0.45 if is_disabled else (0.35 if is_hidden else 1.0)

        def _dim(ch: int) -> int:
            return int(ch * alpha_factor)

        tc_css = f"rgba({_dim(tc[0])},{_dim(tc[1])},{_dim(tc[2])},{_dim(tc[3])})"
        bc_css = f"rgba({_dim(bc[0])},{_dim(bc[1])},{_dim(bc[2])},{_dim(bc[3])})"
        border_line = (
            f"border: 2px solid rgba({br[0]},{br[1]},{br[2]},{br[3]});"
            if br[3] > 0 else "border: 1px solid #333;"
        )

        self._item_label.setText(style.item_name)
        self._item_label.setStyleSheet(
            f"background-color: {bc_css};"
            f"color: {tc_css};"
            f"{border_line}"
            f"font-size: {fs}px;"
            f"padding: 4px 14px;"
        )
        self._item_label.show()

        # ── Condition summary ──────────────────────────────────────────
        if rule is not None:
            parts: list[str] = []
            cls_found = base_found = False
            for k, v in rule.conditions:
                if k == "Class" and not cls_found:
                    parts.append(f"Class {v}");  cls_found = True
                elif k == "BaseType" and not base_found:
                    parts.append(f"BaseType {v}");  base_found = True
            if parts:
                self._condition_lbl.setText("  ·  ".join(parts))
                self._condition_lbl.show()
            else:
                self._condition_lbl.hide()
        else:
            self._condition_lbl.hide()

        # ── Info badges ────────────────────────────────────────────────
        self._set_badge(self._minimap_badge, style.minimap_icon, "🗺 小地圖：")
        self._set_badge(self._effect_badge,  style.play_effect,  "✦ 光柱：")
        self._set_badge(self._sound_badge,   style.alert_sound,  "🔔 ")

        # ── Unknown actions + unknown_lines ────────────────────────────
        if rule is not None:
            unknown_actions = [
                f"  {k} {v}"
                for k, v in rule.actions
                if k not in _KNOWN_ACTIONS
            ]
            unknown_lines = list(rule.unknown_lines or [])
            all_unknown = unknown_actions + [f"  {l}" for l in unknown_lines]
            if all_unknown:
                self._unknown_lbl.setText("其他指令：\n" + "\n".join(all_unknown))
                self._unknown_lbl.show()
            else:
                self._unknown_lbl.hide()
        else:
            self._unknown_lbl.hide()

    @staticmethod
    def _set_badge(lbl: QLabel, value: str, prefix: str) -> None:
        if value:
            lbl.setText(f"{prefix}{value}")
            lbl.show()
        else:
            lbl.hide()
