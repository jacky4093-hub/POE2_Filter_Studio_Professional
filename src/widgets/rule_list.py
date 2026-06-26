from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from core.models import FilterRule


class RuleListWidget(QWidget):
    rule_selected = Signal(int)          # real index into rules list
    add_rule_requested = Signal()
    delete_rule_requested = Signal(int)  # real index
    copy_rule_requested = Signal(int)    # real index

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules: list[FilterRule] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("＋ 新增")
        self.btn_del = QPushButton("－ 刪除")
        self.btn_copy = QPushButton("複製")
        for b in (self.btn_add, self.btn_del, self.btn_copy):
            b.setFixedHeight(26)
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        layout.addWidget(self.list_widget)

        self.btn_add.clicked.connect(self._on_add)
        self.btn_del.clicked.connect(self._on_delete)
        self.btn_copy.clicked.connect(self._on_copy)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_rules(self, rules: list[FilterRule]):
        self._rules = rules
        self.refresh()

    def refresh(self):
        current_row = self.list_widget.currentRow()
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        display_num = 1
        for real_idx, rule in enumerate(self._rules):
            if rule.action == "__TAIL__":
                continue
            label = self._make_label(display_num, rule)
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, real_idx)
            item.setForeground(
                QColor("#90ee90") if rule.action == "Show" else QColor("#aaaaaa")
            )
            self.list_widget.addItem(item)
            display_num += 1

        self.list_widget.blockSignals(False)

        # Restore selection (clamp to valid range)
        count = self.list_widget.count()
        if count > 0:
            target = max(0, min(current_row, count - 1))
            self.list_widget.setCurrentRow(target)

    def select_real_index(self, real_index: int):
        """Highlight the list row that corresponds to rules[real_index]."""
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item and item.data(Qt.ItemDataRole.UserRole) == real_index:
                self.list_widget.blockSignals(True)
                self.list_widget.setCurrentRow(row)
                self.list_widget.blockSignals(False)
                return

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_label(display_num: int, rule: FilterRule) -> str:
        first = ""
        if rule.conditions:
            k, v = rule.conditions[0]
            first = f"  {k} {v}".rstrip()
        elif rule.actions:
            k, v = rule.actions[0]
            first = f"  {k}".rstrip()
        label = f"{rule.action}{first}"
        if len(label) > 48:
            label = label[:45] + "…"
        return f"[{display_num}] {label}"

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_row_changed(self, row: int):
        if row < 0:
            return
        item = self.list_widget.item(row)
        if item is None:
            return
        self.rule_selected.emit(item.data(Qt.ItemDataRole.UserRole))

    def _on_add(self):
        self.add_rule_requested.emit()

    def _on_delete(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        self.delete_rule_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    def _on_copy(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        self.copy_rule_requested.emit(item.data(Qt.ItemDataRole.UserRole))
