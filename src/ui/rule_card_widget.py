"""RuleCardWidget — v2.2.0

Single rule card for the P3 Rule Card Browser.
Displays action colour bar, rule label, category badge, and disabled state.
Uses Qt dynamic properties so browser.qss can style selected / highlight states.
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


def _make_label(rule: FilterRule) -> str:
    if rule.conditions:
        k, v = rule.conditions[0]
        v_clean = v.strip('"').strip("'").strip()
        detail = f"{k}: {v_clean}"
    elif rule.actions:
        k, _v = rule.actions[0]
        detail = k
    else:
        detail = "空規則"
    if len(detail) > 50:
        detail = detail[:47] + "…"
    return detail


class RuleCardWidget(QFrame):
    """Visual card for one FilterRule. Emits clicked(real_index) on mouse press."""

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
        self.setMinimumHeight(52)
        self.setMaximumHeight(70)

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

        # Left colour bar — reflects rule action
        bar = QLabel()
        bar.setObjectName("RuleCardBar")
        bar.setFixedWidth(4)
        bar_color = _ACTION_COLORS.get(self._rule.action, _BAR_DEFAULT)
        bar.setStyleSheet(f"background: {bar_color}; border: none;")
        outer.addWidget(bar)

        # Content body
        body = QVBoxLayout()
        body.setContentsMargins(8, 5, 8, 5)
        body.setSpacing(2)

        # Top row: [num]  Action  label
        top = QHBoxLayout()
        top.setSpacing(6)

        num_lbl = QLabel(f"[{display_num}]")
        num_lbl.setObjectName("RuleCardNum")
        top.addWidget(num_lbl)

        action_text = self._rule.action if self._rule.action != "__TAIL__" else "—"
        action_lbl = QLabel(action_text)
        action_lbl.setObjectName("RuleCardAction")
        action_color = _ACTION_COLORS.get(self._rule.action, _BAR_DEFAULT)
        action_lbl.setStyleSheet(f"color: {action_color}; font-weight: 600;")
        top.addWidget(action_lbl)

        label_lbl = QLabel(_make_label(self._rule))
        label_lbl.setObjectName("RuleCardLabel")
        label_lbl.setWordWrap(False)
        top.addWidget(label_lbl, stretch=1)
        body.addLayout(top)

        # Bottom row: category dot  [已停用]
        bot = QHBoxLayout()
        bot.setSpacing(4)

        cat = classify_rule(self._rule)
        cat_label = CATEGORY_LABELS.get(cat, "")
        cat_color = CATEGORY_COLORS.get(cat, "#64748b")
        if cat_label:
            cat_lbl = QLabel(f"● {cat_label}")
            cat_lbl.setObjectName("RuleCardCategory")
            cat_lbl.setStyleSheet(f"color: {cat_color};")
            bot.addWidget(cat_lbl)

        if not self._rule.enabled:
            dis_lbl = QLabel("已停用")
            dis_lbl.setObjectName("RuleCardDisabledTag")
            bot.addWidget(dis_lbl)

        bot.addStretch()
        body.addLayout(bot)

        outer.addLayout(body)

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
