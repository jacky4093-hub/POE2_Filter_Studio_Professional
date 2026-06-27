"""RuleCreationDialog — v1.0.0  (P14.0 Rule Creation Wizard)

QDialog that lets the user pick a rule template before creation.
Call the static method get_rule() to show the dialog and obtain a
deep-copied FilterRule or None on cancel.
"""

import copy

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel,
)
from PySide6.QtCore import Qt

from core.models import FilterRule


# Template catalogue — (display_name, prototype FilterRule)
_TEMPLATES: list[tuple[str, FilterRule]] = [
    ("Currency",    FilterRule(action="Show", pre_lines=[""], conditions=[["Class",  "Currency"]])),
    ("Unique 物品", FilterRule(action="Show", pre_lines=[""], conditions=[["Rarity", "Unique"]])),
    ("Rare 物品",   FilterRule(action="Show", pre_lines=[""], conditions=[["Rarity", "Rare"]])),
    ("Magic 物品",  FilterRule(action="Show", pre_lines=[""], conditions=[["Rarity", "Magic"]])),
    ("Gem",         FilterRule(action="Show", pre_lines=[""], conditions=[["Class",  "Gems"]])),
    ("Waystone",    FilterRule(action="Show", pre_lines=[""], conditions=[["Class",  "Waystones"]])),
    ("空規則",      FilterRule(action="Show", pre_lines=[""])),
]


class RuleCreationDialog(QDialog):
    """Template-picker dialog.  Use get_rule() rather than instantiating directly."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新增規則")
        self.setObjectName("RuleCreationDialog")
        self.setMinimumWidth(280)
        self._build_ui()

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    @staticmethod
    def get_rule(parent=None) -> FilterRule | None:
        """Show dialog; return a deep copy of the selected template, or None on cancel."""
        dlg = RuleCreationDialog(parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg._selected_rule()
        return None

    def template_names(self) -> list[str]:
        """Return ordered list of template display names (useful for tests)."""
        return [name for name, _ in _TEMPLATES]

    # ----------------------------------------------------------------
    # Internals
    # ----------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        lbl = QLabel("選擇規則模板：")
        lbl.setObjectName("RuleCreationLabel")
        root.addWidget(lbl)

        self._list = QListWidget()
        self._list.setObjectName("RuleTemplateList")
        for name, _ in _TEMPLATES:
            self._list.addItem(QListWidgetItem(name))
        self._list.setCurrentRow(0)
        self._list.itemDoubleClicked.connect(self._on_confirm)
        root.addWidget(self._list)

        btn_row = QHBoxLayout()
        self._btn_cancel = QPushButton("取消")
        self._btn_cancel.setObjectName("BtnCancel")
        self._btn_create = QPushButton("建立")
        self._btn_create.setObjectName("BtnCreate")
        self._btn_create.setDefault(True)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_cancel)
        btn_row.addWidget(self._btn_create)
        root.addLayout(btn_row)

        self._btn_cancel.clicked.connect(self.reject)
        self._btn_create.clicked.connect(self._on_confirm)

    def _selected_rule(self) -> FilterRule:
        idx = self._list.currentRow()
        if 0 <= idx < len(_TEMPLATES):
            return copy.deepcopy(_TEMPLATES[idx][1])
        return copy.deepcopy(_TEMPLATES[-1][1])  # fallback: empty rule

    def _on_confirm(self) -> None:
        self.accept()
