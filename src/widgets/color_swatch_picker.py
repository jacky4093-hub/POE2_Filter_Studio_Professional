"""ColorSwatchPicker — P19.7 compound RGBA color input widget.

Layout: [color swatch QLabel] [RGBA QLineEdit] [選色 QPushButton]

Public attributes (used by RuleDetailEditor for backward compatibility):
    _swatch  : QLabel      — live color preview square
    _edit    : QLineEdit   — free-form "R G B A" text
    _btn     : QPushButton — opens QColorDialog (wired by the parent editor)

API:
    value()             → str    e.g. "255 128 0 200"
    set_value(rgba: str)         updates text field (triggers swatch refresh)
    color_changed = Signal(str)  emitted whenever the text field value changes
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget,
)


class ColorSwatchPicker(QWidget):
    """Compound RGBA color picker: swatch + text field + dialog button."""

    color_changed = Signal(str)

    def __init__(
        self,
        obj_name: str,
        placeholder: str,
        btn_obj_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ColorSwatchPicker")

        hlayout = QHBoxLayout(self)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setSpacing(4)

        # ── Colour swatch (visual preview, also clickable) ────────────
        self._swatch = QLabel()
        self._swatch.setObjectName("ColorSwatch")
        self._swatch.setFixedSize(26, 22)
        self._swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_swatch_style("")
        hlayout.addWidget(self._swatch)

        # ── RGBA text input ───────────────────────────────────────────
        self._edit = QLineEdit()
        self._edit.setObjectName(obj_name)
        self._edit.setPlaceholderText(placeholder)
        hlayout.addWidget(self._edit, stretch=1)

        # ── Dialog trigger button ─────────────────────────────────────
        self._btn = QPushButton("選色")
        self._btn.setObjectName(btn_obj_name)
        self._btn.setFixedWidth(48)
        self._btn.setFixedHeight(26)
        self._btn.setToolTip("開啟顏色選取器（支援 Alpha 透明度）")
        hlayout.addWidget(self._btn)

        # Internal wiring: keep swatch in sync and propagate value changes
        self._edit.textChanged.connect(self._on_text_changed)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_text_changed(self, text: str) -> None:
        self._apply_swatch_style(text)
        self.color_changed.emit(text)

    def _apply_swatch_style(self, text: str) -> None:
        """Parse 'R G B [A]' and paint the swatch; use error/empty style on failure."""
        if not text.strip():
            self._swatch.setStyleSheet(
                "background: transparent;"
                "border: 1.5px solid #1e2435;"
                "border-radius: 5px;"
            )
            return
        try:
            vals = [max(0, min(255, int(p))) for p in text.strip().split()[:4]]
            while len(vals) < 4:
                vals.append(255)
            r, g, b, a = vals
            self._swatch.setStyleSheet(
                f"background: rgba({r},{g},{b},{a});"
                "border: 1.5px solid #334155;"
                "border-radius: 5px;"
            )
        except (ValueError, TypeError):
            self._swatch.setStyleSheet(
                "background: transparent;"
                "border: 1.5px dashed #ef4444;"
                "border-radius: 5px;"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def value(self) -> str:
        """Return the current RGBA string, e.g. '255 128 0 200'."""
        return self._edit.text()

    def set_value(self, rgba: str) -> None:
        """Set the RGBA string; triggers swatch refresh and color_changed."""
        self._edit.setText(rgba)
