"""MinimapIconGrid — P19.6 MinimapIcon visual grid picker (P19.3C: 2×8 layout).

Provides a self-contained widget with:
  - 3 size toggle buttons (大/中/小 → 0/1/2)
  - 11 colour swatches matching POE2 MinimapIcon colours
  - 2×8 shape grid with Unicode symbols, tinted to the selected colour (was 3×4)

API:
    value()                          → (size: int, color: str, shape: str)
    set_value(size, color, shape)    → sets selection; unknown → defaults
    icon_changed = Signal(int, str, str)
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget,
)

# ── Size ──────────────────────────────────────────────────────────────

_GRID_SIZES: list[tuple[str, int]] = [
    ("大", 0),
    ("中", 1),
    ("小", 2),
]

# ── Colour ───────────────────────────────────────────────────────────

_GRID_COLORS: list[str] = [
    "Red", "Green", "Blue", "Brown", "White", "Yellow",
    "Cyan", "Grey", "Orange", "Pink", "Purple",
]

_COLOR_TONES: dict[str, str] = {
    "Red":    "#DC3C3C",
    "Green":  "#3CC83C",
    "Blue":   "#3C78DC",
    "Brown":  "#966428",
    "White":  "#E0E0E0",
    "Yellow": "#DCC828",
    "Cyan":   "#28C8C8",
    "Grey":   "#8C8C8C",
    "Orange": "#DC8C28",
    "Pink":   "#DC78AA",
    "Purple": "#9628C8",
}

# ── Shape ─────────────────────────────────────────────────────────────

_GRID_SHAPES: list[str] = [
    "Circle", "Diamond", "Hexagon", "Square", "Star",
    "Triangle", "Cross", "Moon", "Raindrop", "Kite",
    "Pentagon", "UpsideDownHouse",
]

# Visual order in the 3×4 grid
_SHAPE_GRID_ORDER: list[str] = [
    "Circle",   "Diamond",         "Star",     "Triangle",
    "Square",   "Cross",           "Hexagon",  "Kite",
    "Pentagon", "UpsideDownHouse", "Moon",     "Raindrop",
]

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

# ── Defaults ─────────────────────────────────────────────────────────

_DEFAULT_SIZE:  int = 0
_DEFAULT_COLOR: str = "Red"
_DEFAULT_SHAPE: str = "Star"


class MinimapIconGrid(QWidget):
    """Visual 3-part picker: size buttons + colour swatches + shape grid."""

    icon_changed = Signal(int, str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MinimapIconGrid")

        self._size:  int = _DEFAULT_SIZE
        self._color: str = _DEFAULT_COLOR
        self._shape: str = _DEFAULT_SHAPE

        self._size_buttons:  dict[int, QPushButton] = {}
        self._color_buttons: dict[str, QPushButton] = {}
        self._shape_buttons: dict[str, QPushButton] = {}

        self._size_group  = QButtonGroup(self)
        self._color_group = QButtonGroup(self)
        self._shape_group = QButtonGroup(self)
        self._size_group.setExclusive(True)
        self._color_group.setExclusive(True)
        self._shape_group.setExclusive(True)

        self._updating = False
        self._build()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)
        self._build_size_row(root)
        self._build_color_grid(root)
        self._build_shape_grid(root)
        self._init_selection()

    def _build_size_row(self, parent: QVBoxLayout) -> None:
        row_w = QWidget()
        row = QHBoxLayout(row_w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        lbl = QLabel("大小")
        lbl.setStyleSheet("color: #4d6080; font-size: 11px;")
        row.addWidget(lbl)

        for label, size_val in _GRID_SIZES:
            btn = QPushButton(label)
            btn.setObjectName(f"MinimapSizeBtn_{size_val}")
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setMinimumWidth(42)
            btn.setStyleSheet(
                "QPushButton {"
                "  background: #141a2e;"
                "  border: 1px solid #1e2a48;"
                "  border-radius: 5px;"
                "  color: #5a6a8a;"
                "  font-size: 12px;"
                "  padding: 0 8px;"
                "}"
                "QPushButton:hover {"
                "  border: 1.5px solid rgba(124,58,237,0.55);"
                "  color: #c0d0e8;"
                "}"
                "QPushButton:checked {"
                "  background: rgba(124,58,237,0.22);"
                "  border: 1.5px solid rgba(124,58,237,0.85);"
                "  color: #e8f0ff;"
                "  font-weight: 700;"
                "}"
            )
            self._size_buttons[size_val] = btn
            self._size_group.addButton(btn)
            row.addWidget(btn)
            btn.toggled.connect(
                lambda checked, sv=size_val: self._on_size_toggled(sv, checked)
            )
        row.addStretch()
        parent.addWidget(row_w)

    def _build_color_grid(self, parent: QVBoxLayout) -> None:
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)

        for idx, color in enumerate(_GRID_COLORS):
            row, col = divmod(idx, 6)
            tone = _COLOR_TONES.get(color, "#888888")
            btn = QPushButton()
            btn.setObjectName(f"MinimapColorBtn_{color}")
            btn.setCheckable(True)
            btn.setFixedSize(28, 22)
            btn.setToolTip(color)
            btn.setStyleSheet(
                "QPushButton {"
                f"  background: {tone};"
                "  border: 1.5px solid #0a0f20;"
                "  border-radius: 3px;"
                "}"
                "QPushButton:hover {"
                "  border: 2px solid #c0d0e8;"
                "}"
                "QPushButton:checked {"
                "  border: 2.5px solid rgba(255,255,255,0.9);"
                "}"
            )
            self._color_buttons[color] = btn
            self._color_group.addButton(btn)
            grid.addWidget(btn, row, col)
            btn.toggled.connect(
                lambda checked, c=color: self._on_color_toggled(c, checked)
            )
        parent.addWidget(grid_w)

    def _build_shape_grid(self, parent: QVBoxLayout) -> None:
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(5)

        for idx, shape in enumerate(_SHAPE_GRID_ORDER):
            row, col = divmod(idx, 8)   # 2×8 layout (P19.3C, was 3×4)
            sym = _SHAPE_SYMBOLS.get(shape, "?")
            btn = QPushButton(sym)
            btn.setObjectName(f"MinimapShapeBtn_{shape}")
            btn.setCheckable(True)
            btn.setFixedSize(40, 34)
            btn.setToolTip(shape)
            self._shape_buttons[shape] = btn
            self._shape_group.addButton(btn)
            grid.addWidget(btn, row, col)
            btn.toggled.connect(
                lambda checked, sh=shape: self._on_shape_toggled(sh, checked)
            )
        parent.addWidget(grid_w)
        self._refresh_shape_styles()

    def _init_selection(self) -> None:
        """Set initial button states without emitting icon_changed."""
        for btn in (*self._size_buttons.values(),
                    *self._color_buttons.values(),
                    *self._shape_buttons.values()):
            btn.blockSignals(True)

        self._size_buttons[_DEFAULT_SIZE].setChecked(True)
        self._color_buttons[_DEFAULT_COLOR].setChecked(True)
        self._shape_buttons[_DEFAULT_SHAPE].setChecked(True)

        for btn in (*self._size_buttons.values(),
                    *self._color_buttons.values(),
                    *self._shape_buttons.values()):
            btn.blockSignals(False)

    # ------------------------------------------------------------------
    # Style refresh
    # ------------------------------------------------------------------

    def _refresh_shape_styles(self) -> None:
        """Re-apply shape button styles using the current selected colour tone."""
        tone = _COLOR_TONES.get(self._color, "#8888cc")
        style = (
            "QPushButton {"
            "  background: #141a2e;"
            "  border: 1px solid #1e2a48;"
            "  border-radius: 6px;"
            "  color: #5a6a8a;"
            "  font-size: 15px;"
            "}"
            "QPushButton:hover {"
            f"  border: 1.5px solid {tone};"
            "  color: #c0d0e8;"
            "}"
            "QPushButton:checked {"
            "  background: rgba(124,58,237,0.22);"
            "  border: 1.5px solid rgba(124,58,237,0.85);"
            f"  color: {tone};"
            "  font-weight: 700;"
            "}"
        )
        for btn in self._shape_buttons.values():
            btn.setStyleSheet(style)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_size_toggled(self, size: int, checked: bool) -> None:
        if checked and not self._updating:
            self._size = size
            self.icon_changed.emit(self._size, self._color, self._shape)

    def _on_color_toggled(self, color: str, checked: bool) -> None:
        if checked and not self._updating:
            self._color = color
            self._refresh_shape_styles()
            self.icon_changed.emit(self._size, self._color, self._shape)

    def _on_shape_toggled(self, shape: str, checked: bool) -> None:
        if checked and not self._updating:
            self._shape = shape
            self.icon_changed.emit(self._size, self._color, self._shape)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def value(self) -> tuple[int, str, str]:
        """Return (size: int, color: str, shape: str)."""
        return (self._size, self._color, self._shape)

    def set_value(self, size: int, color: str, shape: str) -> None:
        """Select size/color/shape; unknown values fall back to defaults."""
        if size not in (0, 1, 2):
            size = _DEFAULT_SIZE
        if color not in _GRID_COLORS:
            color = _DEFAULT_COLOR
        if shape not in _GRID_SHAPES:
            shape = _DEFAULT_SHAPE

        if (size, color, shape) == (self._size, self._color, self._shape):
            return

        self._updating = True
        try:
            self._size  = size
            self._color = color
            self._shape = shape
            self._size_buttons[size].setChecked(True)
            self._color_buttons[color].setChecked(True)
            self._shape_buttons[shape].setChecked(True)
            self._refresh_shape_styles()
        finally:
            self._updating = False

        self.icon_changed.emit(size, color, shape)
