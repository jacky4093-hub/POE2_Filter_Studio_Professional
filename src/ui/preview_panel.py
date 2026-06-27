"""Live Preview Panel — v2.0.0  (P13.2 Visual Rule Editor)

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

P13.2 additions:
    • Title bar shows "即時預覽" with styled separator
    • _disabled_banner  — shows when rule.enabled is False
    • _condition_lbl    — summarises Class / BaseType conditions
    • _unknown_lbl      — shows unrecognised actions + unknown_lines
    • Action badge uses colored backgrounds (Show=green, Hide=red, Continue=blue)
    • Disabled rules render item with dimmed palette + ban banner
    • Invalid colour strings are silently caught (no crash)
"""

from __future__ import annotations

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
    """Produce a sample item name from the rule's conditions.

    Priority: Class > BaseType > first condition key > "Item Name".
    """
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


# Known action keys that parse_rule_style handles
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
    Missing or unparseable actions silently fall back to PreviewStyle defaults.
    """
    try:
        style = PreviewStyle()
        style.item_action = (
            rule.action if rule.action in ("Show", "Hide", "Continue", "Minimal")
            else "Show"
        )
        style.item_name = _derive_item_name(rule)

        # Build last-wins lookup: later entries in rule.actions override earlier
        action_map: dict[str, str] = {}
        for key, value in rule.actions:
            action_map[key] = value

        if "SetTextColor" in action_map:
            style.text_color = _parse_rgba(
                action_map["SetTextColor"], style.text_color)

        if "SetBackgroundColor" in action_map:
            style.background_color = _parse_rgba(
                action_map["SetBackgroundColor"], style.background_color)

        if "SetBorderColor" in action_map:
            style.border_color = _parse_rgba(
                action_map["SetBorderColor"], style.border_color)

        if "SetFontSize" in action_map:
            style.font_size = _parse_int(
                action_map["SetFontSize"], style.font_size, lo=1, hi=45)

        if "MinimapIcon" in action_map:
            style.minimap_icon = action_map["MinimapIcon"].strip()

        if "PlayEffect" in action_map:
            style.play_effect = action_map["PlayEffect"].strip()

        # Sound: first match wins (PlayAlertSound > Positional > Custom)
        for sound_key in ("PlayAlertSound", "PlayAlertSoundPositional",
                          "CustomAlertSound", "CustomAlertSoundOptional"):
            if sound_key in action_map:
                style.alert_sound = f"{sound_key}: {action_map[sound_key].strip()}"
                break

        return style

    except Exception:
        return PreviewStyle()   # last-resort fallback


# ---------------------------------------------------------------------------
# PreviewPanel — QWidget (read-only)
# ---------------------------------------------------------------------------

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt


class PreviewPanel(QWidget):
    """Read-only visual preview of a FilterRule.

    Public API (unchanged from v0.7.0):
        show_rule(rule)  — render the rule
        show_empty()     — show no-selection placeholder

    P13.2 additions (internal, preserved for tests):
        _disabled_banner — shown when rule.enabled is False
        _condition_lbl   — summarises Class / BaseType conditions
        _unknown_lbl     — shows unrecognised actions and unknown_lines
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
        root.setSpacing(6)

        # ── Header ──────────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("PreviewHeader")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(0, 0, 0, 4)
        hdr_layout.setSpacing(0)

        title_lbl = QLabel("即時預覽")
        title_lbl.setObjectName("PreviewTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr_layout.addWidget(title_lbl, stretch=1)
        root.addWidget(header)

        # ── Action badge ─────────────────────────────────────────────────
        self._action_label = QLabel()
        self._action_label.setObjectName("PreviewActionBadge")
        self._action_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._action_label)

        # ── Disabled banner ───────────────────────────────────────────────
        self._disabled_banner = QLabel("◆  此規則已停用（Disabled）")
        self._disabled_banner.setObjectName("PreviewDisabledBanner")
        self._disabled_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._disabled_banner)

        # ── Item drop label (centered) ────────────────────────────────────
        item_outer = QHBoxLayout()
        item_outer.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._item_label = QLabel()
        self._item_label.setObjectName("PreviewItemLabel")
        self._item_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._item_label.setWordWrap(False)
        self._item_label.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )
        item_outer.addWidget(self._item_label)
        root.addLayout(item_outer)

        # ── Condition summary ─────────────────────────────────────────────
        self._condition_lbl = QLabel()
        self._condition_lbl.setObjectName("PreviewConditionLabel")
        self._condition_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._condition_lbl.setWordWrap(True)
        root.addWidget(self._condition_lbl)

        # ── Info badges (MinimapIcon / PlayEffect / Sound) ────────────────
        badge_frame = QFrame()
        badge_frame.setObjectName("PreviewBadgeFrame")
        badge_frame.setFrameShape(QFrame.Shape.NoFrame)
        badge_layout = QVBoxLayout(badge_frame)
        badge_layout.setContentsMargins(2, 4, 2, 0)
        badge_layout.setSpacing(3)

        self._minimap_badge = self._make_badge()
        self._effect_badge  = self._make_badge()
        self._sound_badge   = self._make_badge()
        for badge in (self._minimap_badge, self._effect_badge, self._sound_badge):
            badge_layout.addWidget(badge)
        root.addWidget(badge_frame)

        # ── Unknown actions / lines ───────────────────────────────────────
        self._unknown_lbl = QLabel()
        self._unknown_lbl.setObjectName("PreviewUnknownLabel")
        self._unknown_lbl.setWordWrap(True)
        self._unknown_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        root.addWidget(self._unknown_lbl)

        root.addStretch()

        # ── Empty-state placeholder ───────────────────────────────────────
        self._empty_label = QLabel("（未選取規則）")
        self._empty_label.setObjectName("PreviewEmptyLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._empty_label)

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

        # ── Item drop label ────────────────────────────────────────────
        tc = style.text_color
        bc = style.background_color
        br = style.border_color
        fs = max(9, min(36, style.font_size))   # clamp for Qt display

        is_hidden = (style.item_action == "Hide")

        # Dim hidden items; further dim disabled rules
        if is_disabled:
            alpha_factor = 0.45
        elif is_hidden:
            alpha_factor = 0.35
        else:
            alpha_factor = 1.0

        def _dim(ch: int) -> int:
            return int(ch * alpha_factor)

        tc_css = f"rgba({_dim(tc[0])},{_dim(tc[1])},{_dim(tc[2])},{_dim(tc[3])})"
        bc_css = f"rgba({_dim(bc[0])},{_dim(bc[1])},{_dim(bc[2])},{_dim(bc[3])})"

        if br[3] > 0:
            br_css = f"rgba({br[0]},{br[1]},{br[2]},{br[3]})"
            border_line = f"border: 2px solid {br_css};"
        else:
            border_line = "border: 1px solid #333;"

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
                    parts.append(f"Class {v}")
                    cls_found = True
                elif k == "BaseType" and not base_found:
                    parts.append(f"BaseType {v}")
                    base_found = True
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
                header_txt = "其他指令："
                self._unknown_lbl.setText(header_txt + "\n" + "\n".join(all_unknown))
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
