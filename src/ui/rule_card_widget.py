"""RuleCardWidget — v4.0.0  (P17.6 In-Place Update)

Single rule card for the Rule Card Browser.

P13.3 visual improvements (all public API from v2.2.0 preserved):
  - 3-row layout: main row / detail row / badge row
  - Action badge with accent background colour
  - BaseType shown in detail row when it isn't the first condition
  - FontSize / PlayAlertSound / MinimapIcon compact badges in badge row
  - "+N" extra-condition count for non-Class/non-BaseType conditions
  - Disabled rule: CSS property grey (unchanged) + "已停用" tag

P17.6 performance: in-place update
  - All mutable labels stored as instance attributes
  - update_rule(rule) refreshes content without destroying the widget
  - RuleCardBrowser.update_single_card() calls update_rule() instead of
    destroy-and-recreate, eliminating Qt widget allocation on every edit

Preserved public API:
  - clicked = Signal(int)
  - set_selected(selected: bool)
  - set_highlight(level: str)   — 'none' | 'match' | 'current'
  - real_index property
  - cardSelected / cardHighlight / cardDisabled  Qt dynamic properties
"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QMouseEvent

from core.models import FilterRule
from core.categorizer import CATEGORY_LABELS, CATEGORY_COLORS, classify_rule
from assets.icon_registry import IconRegistry


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
    """Visual card for one FilterRule.  Emits clicked(real_index) on mouse press.

    All mutable labels are stored as instance attributes so that update_rule()
    can refresh content in-place without destroying and recreating the widget.
    """

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
        self._display_num = display_num

        self.setObjectName("RuleCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(56)
        self.setMaximumHeight(92)

        self.setProperty("cardSelected", False)
        self.setProperty("cardHighlight", "none")
        self.setProperty("cardDisabled", False)

        self._build_ui(display_num)
        self._refresh_display()   # apply initial rule data

    # ------------------------------------------------------------------
    # UI construction — builds skeleton; _refresh_display() fills data
    # ------------------------------------------------------------------

    def _build_ui(self, display_num: int) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Left colour bar ────────────────────────────────────────────
        self._bar_lbl = QLabel()
        self._bar_lbl.setObjectName("RuleCardBar")
        self._bar_lbl.setFixedWidth(4)
        outer.addWidget(self._bar_lbl)

        # ── Body ───────────────────────────────────────────────────────
        body = QVBoxLayout()
        body.setContentsMargins(8, 4, 8, 4)
        body.setSpacing(2)

        self._build_main_row(body, display_num)
        self._build_detail_row(body)
        self._build_badge_row(body)

        outer.addLayout(body)

    def _build_main_row(self, body: QVBoxLayout, display_num: int) -> None:
        row = QHBoxLayout()
        row.setSpacing(5)

        self._num_lbl = QLabel(f"[{display_num}]")
        self._num_lbl.setObjectName("RuleCardNum")
        row.addWidget(self._num_lbl)

        self._action_icon_lbl = QLabel()
        self._action_icon_lbl.setObjectName("RuleCardActionIcon")
        self._action_icon_lbl.setFixedSize(12, 12)
        row.addWidget(self._action_icon_lbl)

        self._action_badge_lbl = QLabel()
        self._action_badge_lbl.setObjectName("RuleCardAction")
        row.addWidget(self._action_badge_lbl)

        self._main_lbl = QLabel()
        self._main_lbl.setObjectName("RuleCardLabel")
        self._main_lbl.setWordWrap(False)
        row.addWidget(self._main_lbl, stretch=1)

        body.addLayout(row)

    def _build_detail_row(self, body: QVBoxLayout) -> None:
        """Always build the row; show/hide individual labels in _refresh_display."""
        self._detail_container = QWidget()
        self._detail_container.setObjectName("RuleCardDetailRow")
        detail_layout = QHBoxLayout(self._detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(4)

        self._basetype_detail_lbl = QLabel()
        self._basetype_detail_lbl.setObjectName("RuleCardDetail")
        detail_layout.addWidget(self._basetype_detail_lbl)

        self._extra_count_lbl = QLabel()
        self._extra_count_lbl.setObjectName("RuleCardExtraCount")
        detail_layout.addWidget(self._extra_count_lbl)

        detail_layout.addStretch()
        body.addWidget(self._detail_container)

    def _build_badge_row(self, body: QVBoxLayout) -> None:
        """Always build all badge labels; show/hide in _refresh_display."""
        row = QHBoxLayout()
        row.setSpacing(4)

        self._cat_badge_lbl = QLabel()
        self._cat_badge_lbl.setObjectName("RuleCardCategory")
        row.addWidget(self._cat_badge_lbl)

        self._fs_badge_lbl = QLabel()
        self._fs_badge_lbl.setObjectName("RuleCardFontBadge")
        row.addWidget(self._fs_badge_lbl)

        self._sound_badge_lbl = QLabel("♪")
        self._sound_badge_lbl.setObjectName("RuleCardSoundBadge")
        row.addWidget(self._sound_badge_lbl)

        self._minimap_badge_lbl = QLabel("🗺")
        self._minimap_badge_lbl.setObjectName("RuleCardMinimapBadge")
        row.addWidget(self._minimap_badge_lbl)

        self._disabled_tag_lbl = QLabel("已停用")
        self._disabled_tag_lbl.setObjectName("RuleCardDisabledTag")
        row.addWidget(self._disabled_tag_lbl)

        row.addStretch()
        body.addLayout(row)

    # ------------------------------------------------------------------
    # Display refresh — pure data-to-labels mapping, called on init
    # and from update_rule()
    # ------------------------------------------------------------------

    def _refresh_display(self) -> None:
        """Apply all rule data to UI labels.  Called on construction and by update_rule()."""
        rule = self._rule

        # ── Colour bar ─────────────────────────────────────────────────
        bar_color = _ACTION_COLORS.get(rule.action, _BAR_DEFAULT)
        self._bar_lbl.setStyleSheet(f"background: {bar_color}; border: none;")

        # ── Action icon ────────────────────────────────────────────────
        action_icon = IconRegistry.get_rule_action_icon(rule.action)
        if not action_icon.isNull():
            self._action_icon_lbl.setPixmap(action_icon.pixmap(12, 12))
            self._action_icon_lbl.show()
        else:
            self._action_icon_lbl.hide()

        # ── Action badge ───────────────────────────────────────────────
        action_text = rule.action if rule.action != "__TAIL__" else "—"
        action_color = _ACTION_COLORS.get(rule.action, _BAR_DEFAULT)
        self._action_badge_lbl.setText(action_text)
        self._action_badge_lbl.setStyleSheet(
            f"color: {action_color}; font-weight: 600; font-size: 10px;"
            f"background: {action_color}1a;"
            "border-radius: 2px; padding: 1px 5px;"
        )

        # ── Main label ─────────────────────────────────────────────────
        self._main_lbl.setText(_make_label(rule))

        # ── Detail row ─────────────────────────────────────────────────
        first_key = rule.conditions[0][0] if rule.conditions else ""
        basetype_val = ""
        if first_key != "BaseType":
            for k, v in rule.conditions:
                if k == "BaseType":
                    raw = v.strip('"').strip("'").strip()
                    basetype_val = (raw[:30] + "…") if len(raw) > 33 else raw
                    break

        if basetype_val:
            self._basetype_detail_lbl.setText(f"BaseType: {basetype_val}")
            self._basetype_detail_lbl.show()
        else:
            self._basetype_detail_lbl.hide()

        extra_count = sum(1 for k, _ in rule.conditions if k not in _MANAGED_COND_KEYS)
        if extra_count > 0:
            self._extra_count_lbl.setText(f"+{extra_count}")
            self._extra_count_lbl.show()
        else:
            self._extra_count_lbl.hide()

        has_detail = bool(basetype_val) or extra_count > 0
        self._detail_container.setVisible(has_detail)

        # ── Category badge ─────────────────────────────────────────────
        cat = classify_rule(rule)
        cat_label = CATEGORY_LABELS.get(cat, "")
        cat_color = CATEGORY_COLORS.get(cat, "#64748b")
        if cat_label:
            self._cat_badge_lbl.setText(f"● {cat_label}")
            self._cat_badge_lbl.setStyleSheet(f"color: {cat_color};")
            self._cat_badge_lbl.show()
        else:
            self._cat_badge_lbl.hide()

        # ── FontSize badge ─────────────────────────────────────────────
        fontsize = _get_action_val(rule, "SetFontSize")
        if fontsize:
            self._fs_badge_lbl.setText(f"Fs:{fontsize}")
            self._fs_badge_lbl.show()
        else:
            self._fs_badge_lbl.hide()

        # ── Sound / Minimap badges ─────────────────────────────────────
        self._sound_badge_lbl.setVisible(bool(_get_first_sound(rule)))
        self._minimap_badge_lbl.setVisible(bool(_get_action_val(rule, "MinimapIcon")))

        # ── Disabled tag ───────────────────────────────────────────────
        self._disabled_tag_lbl.setVisible(not rule.enabled)

        # ── cardDisabled Qt property ───────────────────────────────────
        self.setProperty("cardDisabled", not rule.enabled)

    # ------------------------------------------------------------------
    # In-place update — the key P17.6 performance method
    # ------------------------------------------------------------------

    def update_display_num(self, num: int) -> None:
        """Update the display number label in-place (used by pool renumbering)."""
        self._display_num = num
        self._num_lbl.setText(f"[{num}]")

    def update_rule(self, rule: FilterRule) -> None:
        """Update card content in-place without destroying the widget.

        Avoids Qt widget allocation/deallocation on every field edit.
        Only repolishes the stylesheet when the enabled state changes
        (which affects the cardDisabled Qt property used by QSS selectors).
        """
        was_enabled = self._rule.enabled
        self._rule = rule
        self._refresh_display()
        if rule.enabled != was_enabled:
            self._repolish()
        else:
            self.update()

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
