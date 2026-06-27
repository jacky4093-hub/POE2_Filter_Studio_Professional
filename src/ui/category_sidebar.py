"""CategorySidebarWidget — v2.1.0

Left sidebar for filtering rules by item category.
Emits category_selected when the user picks a category.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from core.models import FilterRule
from core.categorizer import (
    Category,
    CATEGORY_SIDEBAR_ORDER,
    CATEGORY_LABELS,
    CATEGORY_COLORS,
    count_by_category,
    total_visible_rules,
)
from assets.icon_registry import IconRegistry

_CATEGORY_ROLE = Qt.ItemDataRole.UserRole + 10


class CategorySidebarWidget(QWidget):
    category_selected = Signal(object)   # Category

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("CategorySidebar")
        self._active: Category = Category.ALL

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title = QLabel("分類")
        title.setObjectName("CategorySidebarTitle")
        layout.addWidget(title)

        self._list = QListWidget()
        self._list.setObjectName("CategorySidebarList")
        self._list.setFrameShape(QListWidget.Shape.NoFrame)
        self._list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        layout.addWidget(self._list, stretch=1)

        self._build_items()
        self._list.currentItemChanged.connect(self._on_item_changed)

    def _build_items(self) -> None:
        self._list.clear()

        all_item = self._make_item(Category.ALL, 0)
        self._list.addItem(all_item)

        for cat in CATEGORY_SIDEBAR_ORDER:
            self._list.addItem(self._make_item(cat, 0))

        self._select_category(self._active, emit_signal=False)

    def _make_item(self, category: Category, count: int) -> QListWidgetItem:
        label = CATEGORY_LABELS[category]
        dot = CATEGORY_COLORS[category]
        text = label if category != Category.ALL else label
        if count > 0 or category == Category.ALL:
            text = f"{text}   {count}"

        item = QListWidgetItem(text)
        item.setIcon(IconRegistry.get_category_icon(category))
        item.setData(_CATEGORY_ROLE, category)
        item.setForeground(QColor(dot if category != Category.ALL else "#e2e8f0"))
        return item

    def update_counts(self, rules: list[FilterRule]) -> None:
        """Refresh count badges from the current document rules."""
        counts = count_by_category(rules)
        total = total_visible_rules(rules)

        for row in range(self._list.count()):
            item = self._list.item(row)
            cat = item.data(_CATEGORY_ROLE)
            if cat == Category.ALL:
                item.setText(f"{CATEGORY_LABELS[Category.ALL]}   {total}")
            else:
                n = counts.get(cat, 0)
                item.setText(f"{CATEGORY_LABELS[cat]}   {n}")

    def set_active_category(self, category: Category, *, emit_signal: bool = False) -> None:
        self._active = category
        self._select_category(category, emit_signal=emit_signal)

    def active_category(self) -> Category:
        return self._active

    def _select_category(self, category: Category, *, emit_signal: bool) -> None:
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item.data(_CATEGORY_ROLE) == category:
                self._list.blockSignals(True)
                self._list.setCurrentRow(row)
                self._list.blockSignals(False)
                if emit_signal:
                    self.category_selected.emit(category)
                return

    def _on_item_changed(self, current: QListWidgetItem | None, _previous) -> None:
        if current is None:
            return
        cat = current.data(_CATEGORY_ROLE)
        if cat is None or cat == self._active:
            return
        self._active = cat
        self.category_selected.emit(cat)
