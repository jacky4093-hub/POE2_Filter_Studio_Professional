"""SearchBarWidget — P10 Quick Filter search bar

Left-column filter widget distinct from the nav-bar SearchBar.
Filters Rule Card Browser cards by text.

Signals:
    search_changed(str, dict)  — emitted on every keystroke / option change
                                 args: (query, options)
    clear_requested()          — emitted when Clear button is pressed

Public API:
    set_result_count(visible_count, total_count)
    clear()              — clear without emitting search_changed
    get_query() -> str
    get_options() -> dict
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit,
    QPushButton, QLabel, QCheckBox,
)
from PySide6.QtCore import Signal, Qt


class SearchBarWidget(QWidget):
    search_changed  = Signal(str, dict)
    clear_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SearchBarWidget")
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 2)
        root.setSpacing(2)

        # --- Input row ---
        input_row = QHBoxLayout()
        input_row.setSpacing(4)

        self._input = QLineEdit()
        self._input.setObjectName("SearchInput")
        self._input.setPlaceholderText("搜尋規則…")
        self._input.setFixedHeight(24)
        input_row.addWidget(self._input, stretch=1)

        self._clear_btn = QPushButton("✕")
        self._clear_btn.setObjectName("SearchClearButton")
        self._clear_btn.setFixedSize(24, 24)
        self._clear_btn.setToolTip("清除搜尋")
        input_row.addWidget(self._clear_btn)

        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("SearchCountLabel")
        self._count_lbl.setFixedWidth(68)
        self._count_lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        input_row.addWidget(self._count_lbl)

        root.addLayout(input_row)

        # --- Options row ---
        opt_row = QHBoxLayout()
        opt_row.setSpacing(4)
        opt_row.setContentsMargins(0, 0, 0, 0)

        self._cb_case  = QCheckBox("Aa")
        self._cb_case.setObjectName("SearchOptionCheckbox")
        self._cb_case.setToolTip("區分大小寫")

        self._cb_raw   = QCheckBox("Raw")
        self._cb_raw.setObjectName("SearchOptionCheckbox")
        self._cb_raw.setToolTip("原始文字")

        self._cb_act   = QCheckBox("動作")
        self._cb_act.setObjectName("SearchOptionCheckbox")
        self._cb_act.setToolTip("搜尋 Show/Hide 動作")

        self._cb_cls   = QCheckBox("Class")
        self._cb_cls.setObjectName("SearchOptionCheckbox")
        self._cb_cls.setToolTip("搜尋 Class 條件")

        self._cb_base  = QCheckBox("Base")
        self._cb_base.setObjectName("SearchOptionCheckbox")
        self._cb_base.setToolTip("搜尋 BaseType 條件")

        for cb in (self._cb_case, self._cb_raw, self._cb_act, self._cb_cls, self._cb_base):
            opt_row.addWidget(cb)

        opt_row.addStretch()
        root.addLayout(opt_row)

        # --- Connections ---
        self._input.textChanged.connect(self._on_text_changed)
        self._clear_btn.clicked.connect(self._on_clear)
        for cb in (self._cb_case, self._cb_raw, self._cb_act, self._cb_cls, self._cb_base):
            cb.stateChanged.connect(self._on_option_changed)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_text_changed(self, text: str) -> None:
        self.search_changed.emit(text, self.get_options())

    def _on_option_changed(self) -> None:
        self.search_changed.emit(self.get_query(), self.get_options())

    def _on_clear(self) -> None:
        self._input.blockSignals(True)
        self._input.clear()
        self._input.blockSignals(False)
        self._count_lbl.setText("")
        self.clear_requested.emit()
        self.search_changed.emit("", self.get_options())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_result_count(self, visible_count: int, total_count: int) -> None:
        if total_count == 0 and visible_count == 0 and not self.get_query():
            self._count_lbl.setText("")
        else:
            self._count_lbl.setText(f"{visible_count}/{total_count}")

    def clear(self) -> None:
        """Clear input and count WITHOUT emitting search_changed."""
        self._input.blockSignals(True)
        self._input.clear()
        self._input.blockSignals(False)
        self._count_lbl.setText("")

    def get_query(self) -> str:
        return self._input.text()

    def get_options(self) -> dict:
        return {
            "match_case": self._cb_case.isChecked(),
            "raw_text":   self._cb_raw.isChecked(),
            "action":     self._cb_act.isChecked(),
            "class":      self._cb_cls.isChecked(),
            "basetype":   self._cb_base.isChecked(),
        }
