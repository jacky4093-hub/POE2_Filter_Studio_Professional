"""RuleCardWidget — v3.0.0  (P13.3 Rule Card Browser V2)

Single rule card for the Rule Card Browser.

P13.3 visual improvements (all public API from v2.2.0 preserved):
  - 3-row layout: main row / detail row / badge row
  - Action badge with accent background colour
  - BaseType shown in detail row when it isn't the first condition
  - FontSize / PlayAlertSound / MinimapIcon compact badges in badge row
  - "+N" extra-condition count for non-Class/non-BaseType conditions
  - Disabled rule: CSS property grey (unchanged) + "已停用" tag

Preserved public API:
  - clicked = Signal(int)
  - set_selected(selected: bool)
  - set_highlight(level: str)   — 'none' | 'match' | 'current'
  - real_index property
  - cardSelected / cardHighlight / cardDisabled  Qt dynamic properties
"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QMouseEvent

from core.models import FilterRule
from core.categorizer import CATEGORY_LABELS, CATEGORY_COLORS, classify_rule


_ACTION_COLORS: dict[str, str] = {
    "Show":     "#4ade80",
    "Hide":     "#f87171",
    "Continue": "#fbbf24",
}
_BAR_DEFAULT = "#64748b"

# Condition keys treated as "managed" — excluded from the "+N" count
_MANAGED_COND_KEYS = frozenset({"Class", "BaseType"})

# Action keys that map to recognised badge fields
_SOUND_KEYS = ("PlayAlertSound", "PlayAlertSoundPositional",
               "CustomAlertSound", "CustomAlertSoundOptional")


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def _make_label(rule: FilterRule) -> str:
    """Row-1 main label: first condition or first action key, truncated."""
    if rule.conditions:
        k, v = rule.conditions[0]
        v_clean = v.strip('"').strip("'").strip()
        detail = f"{k}: {v_clean}"
    elif rule.actions:
        k, _v = rule.actions[0]
        detail = k
    else:
        detail = "空規則"
    return detail[:47] + "…" if len(detail) > 50 else detail


def _get_action_val(rule: FilterRule, key: str) -> str:
    """Return the first value for *key* in rule.actions, or ''."""
    for k, v in rule.actions:
        if k == key:
            return v.strip()
    return ""


def _get_first_sound(rule: FilterRule) -> str:
    """Return first matching sound action value (priority order), or ''."""
    action_map = {k: v for k, v in rule.actions}
    for key in _SOUND_KEYS:
        if key in action_map:
            return action_map[key].strip()
    return ""


# ---------------------------------------------------------------------------
# RuleCardWidget
# ---------------------------------------------------------------------------

class RuleCardWidget(QFrame):
    """Visual card for one FilterRule.  Emits clicked(real_index) on mouse press."""

    clicked = Signal(int)   # real_index

    def __init__(
        self,
        real_index: int,
        rule: FilterRule,
        display_num: int,
        parent: QFrame | None = None,
    ) -> None:
        super().__init__(parent)
        self._real_index = real_index
        self._rule = rule

        self.setObjectName("RuleCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(56)
        self.setMaximumHeight(92)

        # Dynamic properties used by browser.qss selectors
        self.setProperty("cardSelected", False)
        self.setProperty("cardHighlight", "none")   # "none" | "match" | "current"
        if not rule.enabled:
            self.setProperty("cardDisabled", True)

        self._build_ui(display_num)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, display_num: int) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Left colour bar ───────────────────────────────────────────
        bar = QLabel()
        bar.setObjectName("RuleCardBar")
        bar.setFixedWidth(4)
        bar_color = _ACTION_COLORS.get(self._rule.action, _BAR_DEFAULT)
        bar.setStyleSheet(f"background: {bar_color}; border: none;")
        outer.addWidget(bar)

        # ── Body ─────────────────────────────────────────────────────
        body = QVBoxLayout()
        body.setContentsMargins(8, 4, 8, 4)
        body.setSpacing(2)

        self._build_main_row(body, display_num)
        self._build_detail_row(body)
        self._build_badge_row(body)

        outer.addLayout(body)

    def _build_main_row(self, body: QVBoxLayout, display_num: int) -> None:
        """Row 1: [#N] ACTION_BADGE  main-label"""
        row = QHBoxLayout()
        row.setSpacing(5)

        # Number
        num_lbl = QLabel(f"[{display_num}]")
        num_lbl.setObjectName("RuleCardNum")
        row.addWidget(num_lbl)

        # Action badge (background accent)
        action_text = self._rule.action if self._rule.action != "__TAIL__" else "—"
        action_lbl = QLabel(action_text)
        action_lbl.setObjectName("RuleCardAction")
        action_color = _ACTION_COLORS.get(self._rule.action, _BAR_DEFAULT)
        action_lbl.setStyleSheet(
            f"color: {action_color}; font-weight: 600; font-size: 10px;"
            f"background: {action_color}1a;"
            "border-radius: 2px; padding: 1px 5px;"
        )
        row.addWidget(action_lbl)

        # Main label
        label_lbl = QLabel(_make_label(self._rule))
        label_lbl.setObjectName("RuleCardLabel")
        label_lbl.setWordWrap(False)
        row.addWidget(label_lbl, stretch=1)

        body.addLayout(row)

    def _build_detail_row(self, body: QVBoxLayout) -> None:
        """Row 2 (optional): BaseType value  |  +N extra conditions.

        Only added to the layout if there is at least one piece of info to show.
        """
        first_key = self._rule.conditions[0][0] if self._rule.conditions else ""

        # BaseType — only shown when it's NOT already the first-row condition
        basetype_val = ""
        if first_key != "BaseType":
            for k, v in self._rule.conditions:
                if k == "BaseType":
                    raw = v.strip('"').strip("'").strip()
                    basetype_val = (raw[:30] + "…") if len(raw) > 33 else raw
                    break

        # Extra conditions: not Class, not BaseType
        extra_count = sum(
            1 for k, _ in self._rule.conditions if k not in _MANAGED_COND_KEYS
        )

        if not basetype_val and extra_count == 0:
            return   # nothing to show — skip this row entirely

        row = QHBoxLayout()
        row.setSpacing(4)

        if basetype_val:
            detail_lbl = QLabel(f"BaseType: {basetype_val}")
            detail_lbl.setObjectName("RuleCardDetail")
            row.addWidget(detail_lbl)

        if extra_count > 0:
            extra_lbl = QLabel(f"+{extra_count}")
            extra_lbl.setObjectName("RuleCardExtraCount")
            row.addWidget(extra_lbl)

        row.addStretch()
        body.addLayout(row)

    def _build_badge_row(self, body: QVBoxLayout) -> None:
        """Row 3: Category dot  FontSize  Sound  Minimap  Disabled."""
        row = QHBoxLayout()
        row.setSpacing(4)

        # Category dot + label
        cat = classify_rule(self._rule)
        cat_label = CATEGORY_LABELS.get(cat, "")
        cat_color = CATEGORY_COLORS.get(cat, "#64748b")
        if cat_label:
            cat_lbl = QLabel(f"● {cat_label}")
            cat_lbl.setObjectName("RuleCardCategory")
            cat_lbl.setStyleSheet(f"color: {cat_color};")
            row.addWidget(cat_lbl)

        # FontSize badge
        fontsize = _get_action_val(self._rule, "SetFontSize")
        if fontsize:
            fs_lbl = QLabel(f"Fs:{fontsize}")
            fs_lbl.setObjectName("RuleCardFontBadge")
            row.addWidget(fs_lbl)

        # Sound badge
        sound = _get_first_sound(self._rule)
        if sound:
            sound_lbl = QLabel("♪")
            sound_lbl.setObjectName("RuleCardSoundBadge")
            row.addWidget(sound_lbl)

        # Minimap badge
        if _get_action_val(self._rule, "MinimapIcon"):
            map_lbl = QLabel("🗺")
            map_lbl.setObjectName("RuleCardMinimapBadge")
            row.addWidget(map_lbl)

        # Disabled tag
        if not self._rule.enabled:
            dis_lbl = QLabel("已停用")
            dis_lbl.setObjectName("RuleCardDisabledTag")
            row.addWidget(dis_lbl)

        row.addStretch()
        body.addLayout(row)

    # ------------------------------------------------------------------
    # Public state API
    # ------------------------------------------------------------------

    def set_selected(self, selected: bool) -> None:
        self.setProperty("cardSelected", selected)
        self._repolish()

    def set_highlight(self, level: str) -> None:
        """level: 'none' | 'match' | 'current'"""
        self.setProperty("cardHighlight", level)
        self._repolish()

    def _repolish(self) -> None:
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    # ------------------------------------------------------------------
    # Mouse event
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._real_index)
        super().mousePressEvent(event)

    # ------------------------------------------------------------------
    # Property
    # ------------------------------------------------------------------

    @property
    def real_index(self) -> int:
        return self._real_index
