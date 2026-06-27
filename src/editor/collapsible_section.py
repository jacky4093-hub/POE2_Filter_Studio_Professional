"""CollapsibleSection — generic collapsible panel widget.

A reusable QWidget with a clickable header and a scrollable content area.
The header shows the section title plus an optional item count badge.

Public API
----------
  add_widget(w)          — add a widget to the content area
  remove_widget(w)       — remove a widget from the content area
  clear_widgets()        — remove and delete all content widgets

  expand()               — show content area
  collapse()             — hide content area
  toggle()               — flip expand / collapse
  is_expanded() -> bool

  set_title(str)         — update the title text
  set_count(n)           — show "(n)" badge in the title

  set_max_content_height(h)  — cap scroll area height

  save_state()    -> dict    — {"expanded": bool}
  restore_state(dict)        — restore from saved state
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QToolButton, QSizePolicy,
)
from PySide6.QtCore import Qt


class CollapsibleSection(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._title_base: str = title
        self._count: int = 0
        self._expanded: bool = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header button ───────────────────────────────────────────────
        self._header = QToolButton()
        self._header.setCheckable(True)
        self._header.setChecked(True)
        self._header.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._header.setObjectName("CollapsibleSectionHeader")
        self._header.toggled.connect(self._on_toggle)
        self._update_header()
        outer.addWidget(self._header)

        # ── Scroll + content ────────────────────────────────────────────
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._content_layout.setSpacing(2)
        self._content_layout.setContentsMargins(4, 2, 4, 4)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setMaximumHeight(220)
        self._scroll.setWidget(self._content_widget)

        outer.addWidget(self._scroll)

    # ------------------------------------------------------------------
    # Content management
    # ------------------------------------------------------------------

    def add_widget(self, w: QWidget) -> None:
        self._content_layout.addWidget(w)

    def remove_widget(self, w: QWidget) -> None:
        self._content_layout.removeWidget(w)

    def clear_widgets(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    # ------------------------------------------------------------------
    # Title / count
    # ------------------------------------------------------------------

    def set_title(self, title: str) -> None:
        self._title_base = title
        self._update_header()

    def set_count(self, n: int) -> None:
        self._count = n
        self._update_header()

    # ------------------------------------------------------------------
    # Expand / collapse
    # ------------------------------------------------------------------

    def expand(self) -> None:
        self._expanded = True
        self._header.blockSignals(True)
        self._header.setChecked(True)
        self._header.blockSignals(False)
        self._scroll.setVisible(True)
        self._update_header()

    def collapse(self) -> None:
        self._expanded = False
        self._header.blockSignals(True)
        self._header.setChecked(False)
        self._header.blockSignals(False)
        self._scroll.setVisible(False)
        self._update_header()

    def toggle(self) -> None:
        if self._expanded:
            self.collapse()
        else:
            self.expand()

    def is_expanded(self) -> bool:
        return self._expanded

    # ------------------------------------------------------------------
    # Sizing
    # ------------------------------------------------------------------

    def set_max_content_height(self, h: int) -> None:
        self._scroll.setMaximumHeight(h)

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def save_state(self) -> dict:
        """Return a plain dict that can be stored (e.g. in QSettings)."""
        return {"expanded": self._expanded}

    def restore_state(self, state: dict) -> None:
        """Restore from a dict previously returned by save_state()."""
        if state.get("expanded", True):
            self.expand()
        else:
            self.collapse()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_toggle(self, checked: bool) -> None:
        self._expanded = checked
        self._scroll.setVisible(checked)
        self._update_header()

    def _update_header(self) -> None:
        arrow = "▼" if self._expanded else "▶"
        badge = f"  ({self._count})" if self._count > 0 else ""
        self._header.setText(f" {arrow}  {self._title_base}{badge}")
