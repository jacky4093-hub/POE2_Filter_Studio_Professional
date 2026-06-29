"""SearchBar Widget — v0.9.0

A compact horizontal search bar with text input, match counter, and
previous / next navigation buttons.

Signals:
    search_changed(str)  — emitted on every keystroke (including clear)
    next_requested()     — user clicked ＞ or triggered Next shortcut
    prev_requested()     — user clicked ＜ or triggered Prev shortcut

Public API:
    set_count(total, current)  — update match counter and button states
    clear_count()              — reset counter, disable nav buttons
    current_text() -> str      — raw text in the input box
    clear()                    — clear input WITHOUT emitting search_changed
    focus_input()              — give keyboard focus to the input field

Keyboard shortcuts (handled inside this widget):
    Escape  — clear input and emit search_changed("") to reset highlights
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QLabel, QPushButton,
)
from PySide6.QtCore import Signal, Qt, QKeyCombination
from PySide6.QtGui import QKeySequence, QShortcut


class SearchBar(QWidget):
    search_changed = Signal(str)
    next_requested = Signal()
    prev_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        self._input = QLineEdit()
        self._input.setPlaceholderText("搜尋規則（Ctrl+F）…")
        self._input.setClearButtonEnabled(True)
        self._input.setFixedHeight(26)
        layout.addWidget(self._input, stretch=1)

        self._count_label = QLabel("")
        self._count_label.setMinimumWidth(64)
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._count_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._count_label)

        self._prev_btn = QPushButton("＜")
        self._prev_btn.setFixedSize(28, 26)
        self._prev_btn.setEnabled(False)
        self._prev_btn.setToolTip("上一個 (Shift+F3)")
        layout.addWidget(self._prev_btn)

        self._next_btn = QPushButton("＞")
        self._next_btn.setFixedSize(28, 26)
        self._next_btn.setEnabled(False)
        self._next_btn.setToolTip("下一個 (F3)")
        layout.addWidget(self._next_btn)

        self._input.textChanged.connect(self.search_changed)
        self._prev_btn.clicked.connect(self.prev_requested)
        self._next_btn.clicked.connect(self.next_requested)

        # Escape clears the input and fires search_changed("") via textChanged
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self._input)
        esc.setContext(Qt.ShortcutContext.WidgetShortcut)
        esc.activated.connect(self._on_escape)

        # P21.4 — 中文別名自動補全（可選，失敗不影響搜尋功能）
        self._alias_completer = None
        try:
            from widgets.alias_completer import AliasCompleter
            self._alias_completer = AliasCompleter(self._input, parent=self)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_count(self, total: int, current: int) -> None:
        """Update the match counter label and enable/disable nav buttons."""
        if total == 0:
            self._count_label.setText("0 結果")
            self._count_label.setStyleSheet("color: #666; font-size: 11px;")
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)
        else:
            self._count_label.setText(f"{current} / {total}")
            self._count_label.setStyleSheet("color: #aaa; font-size: 11px;")
            nav_ok = total >= 1
            self._prev_btn.setEnabled(nav_ok)
            self._next_btn.setEnabled(nav_ok)

    def clear_count(self) -> None:
        """Reset counter display and disable nav buttons (input text unchanged)."""
        self._count_label.setText("")
        self._count_label.setStyleSheet("color: #888; font-size: 11px;")
        self._prev_btn.setEnabled(False)
        self._next_btn.setEnabled(False)

    def current_text(self) -> str:
        """Return the raw text currently in the input field."""
        return self._input.text()

    def clear(self) -> None:
        """Clear the input field WITHOUT emitting search_changed."""
        self._input.blockSignals(True)
        self._input.clear()
        self._input.blockSignals(False)
        self.clear_count()

    def focus_input(self) -> None:
        """Give keyboard focus to the input field and select all text."""
        self._input.setFocus()
        self._input.selectAll()

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_escape(self) -> None:
        """Clear input without blockSignals — lets search_changed("") fire naturally."""
        self._input.clear()
