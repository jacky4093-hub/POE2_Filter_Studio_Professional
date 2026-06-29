"""VisualEffectPicker — P19.3C PlayEffect 1×8 visual grid widget (was 2×4)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QGridLayout, QPushButton, QWidget

_EFFECT_COLORS: list[str] = [
    "", "White", "Red", "Orange", "Yellow", "Green", "Blue", "Purple",
]

_EFFECT_LABELS: dict[str, str] = {
    "":       "無",
    "White":  "白",
    "Red":    "紅",
    "Orange": "橘",
    "Yellow": "黃",
    "Green":  "綠",
    "Blue":   "藍",
    "Purple": "紫",
}

_EFFECT_TONES: dict[str, str] = {
    "":       "#555577",
    "White":  "#E0E0F0",
    "Red":    "#DC3C3C",
    "Orange": "#DC8C28",
    "Yellow": "#DCC828",
    "Green":  "#3CC83C",
    "Blue":   "#3C78DC",
    "Purple": "#9628C8",
}


class VisualEffectPicker(QWidget):
    """1×8 grid of toggle buttons for PlayEffect colour selection.

    API:
        value()               → current colour string, or "" for no effect
        set_value(v: str)     → select by name; unknown names fall back to ""
        effect_changed(str)   → emitted when the selected colour changes
    """

    effect_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("VisualEffectPicker")
        self._current: str = ""
        self._buttons: dict[str, QPushButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._build()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build(self) -> None:
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)

        for idx, color in enumerate(_EFFECT_COLORS):
            row, col = divmod(idx, 8)   # 1×8 layout (P19.3C, was 2×4)
            tone  = _EFFECT_TONES.get(color, "#888888")
            label = _EFFECT_LABELS[color]

            btn = QPushButton(label)
            btn.setObjectName(f"EffectBtn_{color or 'None'}")
            btn.setCheckable(True)
            btn.setFixedSize(48, 44)
            btn.setToolTip(color if color else "無效果")
            btn.setStyleSheet(
                "QPushButton {"
                "  background: #141a2e;"
                "  border: 1px solid #1e2a48;"
                "  border-radius: 7px;"
                "  color: #6a7a9a;"
                "  font-size: 12px;"
                "}"
                "QPushButton:hover {"
                f"  border: 1.5px solid {tone};"
                "  color: #c0d0e8;"
                "  background: rgba(124,58,237,0.07);"
                "}"
                "QPushButton:checked {"
                "  background: rgba(124,58,237,0.22);"
                "  border: 1.5px solid rgba(124,58,237,0.85);"
                "  color: #e8f0ff;"
                "  font-weight: 700;"
                "}"
            )
            self._buttons[color] = btn
            self._group.addButton(btn)
            grid.addWidget(btn, row, col)
            btn.toggled.connect(
                lambda checked, c=color: self._on_toggled(c, checked)
            )

        # Set initial selection to "no effect" without emitting effect_changed
        none_btn = self._buttons[""]
        none_btn.blockSignals(True)
        none_btn.setChecked(True)
        none_btn.blockSignals(False)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_toggled(self, color: str, checked: bool) -> None:
        if checked:
            self._current = color
            self.effect_changed.emit(color)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def value(self) -> str:
        """Return the currently selected colour string, or "" for no effect."""
        return self._current

    def set_value(self, v: str) -> None:
        """Select the given colour. Unknown values silently fall back to ""."""
        v = v.strip()
        if v not in _EFFECT_COLORS:
            v = ""
        if v == self._current:
            return
        # setChecked fires toggled → _on_toggled → updates _current + emits
        self._buttons[v].setChecked(True)
