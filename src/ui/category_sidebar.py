"""CategorySidebarWidget — v4.0.0  P18.2

V4 Sidebar with Category Search, Active Filter Chip, and Quick Search placeholder.

Layout (top → bottom):
  CategorySidebarHeader   — section title "分類"
  CategorySearchRow       — search input + clear button
  CategorySidebarList     — category list (preserved, all public API kept)
  CategoryActiveFilterChip — current-category indicator with clear button
  CategoryQuickSearchSection — placeholder for P18.3+ rule search

Preserved public API (unchanged from v2.1.0):
  - category_selected = Signal(object)  # Category
  - self._list  (QListWidget, objectName "CategorySidebarList")
  - update_counts(rules)
  - set_active_category(category, *, emit_signal=False)
  - active_category()
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton,
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
    """V4 category sidebar widget."""

    category_selected = Signal(object)   # Category

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("CategorySidebar")
        self._active: Category = Category.ALL

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_search_row())

        # ── Category List (preserved attribute) ───────────────────────
        self._list = QListWidget()
        self._list.setObjectName("CategorySidebarList")
        self._list.setFrameShape(QListWidget.Shape.NoFrame)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(self._list, stretch=1)

        root.addWidget(self._build_active_chip())
        root.addWidget(self._build_quick_search_section())

        self._build_items()
        self._list.currentItemChanged.connect(self._on_item_changed)
        self._update_chip()

    # ------------------------------------------------------------------
    # Sub-widget construction
    # ------------------------------------------------------------------

    def _build_header(self) -> QWidget:
        hdr = QWidget()
        hdr.setObjectName("CategorySidebarHeader")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(10, 10, 10, 4)
        hl.setSpacing(0)
        title = QLabel("分類")
        title.setObjectName("CategorySidebarTitle")
        hl.addWidget(title)
        hl.addStretch()
        return hdr

    def _build_search_row(self) -> QWidget:
        row = QWidget()
        row.setObjectName("CategorySearchRow")
        hl = QHBoxLayout(row)
        hl.setContentsMargins(8, 4, 8, 4)
        hl.setSpacing(4)

        self._search_input = QLineEdit()
        self._search_input.setObjectName("CategorySearchInput")
        self._search_input.setPlaceholderText("搜尋分類...")
        self._search_input.textChanged.connect(self._on_category_search_changed)
        hl.addWidget(self._search_input, stretch=1)

        self._search_clear_btn = QPushButton("✕")
        self._search_clear_btn.setObjectName("CategorySearchClearButton")
        self._search_clear_btn.setFixedSize(22, 22)
        self._search_clear_btn.setEnabled(False)
        self._search_clear_btn.clicked.connect(self._clear_search)
        hl.addWidget(self._search_clear_btn)

        return row

    def _build_active_chip(self) -> QWidget:
        self._chip_container = QWidget()
        self._chip_container.setObjectName("CategoryActiveFilterChip")
        hl = QHBoxLayout(self._chip_container)
        hl.setContentsMargins(8, 4, 8, 4)
        hl.setSpacing(4)

        self._chip_label = QLabel()
        self._chip_label.setObjectName("CategoryActiveFilterLabel")
        hl.addWidget(self._chip_label, stretch=1)

        self._chip_clear_btn = QPushButton("✕")
        self._chip_clear_btn.setObjectName("CategoryActiveFilterClearButton")
        self._chip_clear_btn.setFixedSize(18, 18)
        self._chip_clear_btn.clicked.connect(self._on_chip_clear)
        hl.addWidget(self._chip_clear_btn)

        return self._chip_container

    def _build_quick_search_section(self) -> QWidget:
        """P18.3+ placeholder — UI only, not wired to any search logic."""
        section = QWidget()
        section.setObjectName("CategoryQuickSearchSection")
        vl = QVBoxLayout(section)
        vl.setContentsMargins(8, 8, 8, 8)
        vl.setSpacing(4)

        section_label = QLabel("快捷搜尋")
        section_label.setObjectName("CategoryQuickSearchTitle")
        vl.addWidget(section_label)

        self._quick_search_input = QLineEdit()
        self._quick_search_input.setObjectName("CategoryQuickSearchInput")
        self._quick_search_input.setPlaceholderText("搜尋物品... （P18.3 規劃）")
        self._quick_search_input.setEnabled(False)
        vl.addWidget(self._quick_search_input)

        return section

    # ------------------------------------------------------------------
    # Category list construction
    # ------------------------------------------------------------------

    def _build_items(self) -> None:
        self._list.clear()
        self._list.addItem(self._make_item(Category.ALL, 0))
        for cat in CATEGORY_SIDEBAR_ORDER:
            self._list.addItem(self._make_item(cat, 0))
        self._select_category(self._active, emit_signal=False)

    def _make_item(self, category: Category, count: int) -> QListWidgetItem:
        label = CATEGORY_LABELS[category]
        text = f"{label}   {count}" if (count > 0 or category == Category.ALL) else label
        item = QListWidgetItem(text)
        item.setIcon(IconRegistry.get_category_icon(category))
        item.setData(_CATEGORY_ROLE, category)
        dot = CATEGORY_COLORS[category]
        item.setForeground(QColor(dot if category != Category.ALL else "#e2e8f0"))
        return item

    # ------------------------------------------------------------------
    # Public API (preserved — identical semantics to v2.1.0)
    # ------------------------------------------------------------------

    def update_counts(self, rules: list[FilterRule]) -> None:
        """Refresh count badges from the current document rules."""
        counts = count_by_category(rules)
        total  = total_visible_rules(rules)

        for row in range(self._list.count()):
            item = self._list.item(row)
            cat  = item.data(_CATEGORY_ROLE)
            if cat == Category.ALL:
                item.setText(f"{CATEGORY_LABELS[Category.ALL]}   {total}")
            else:
                n = counts.get(cat, 0)
                item.setText(f"{CATEGORY_LABELS[cat]}   {n}")

    def set_active_category(self, category: Category, *, emit_signal: bool = False) -> None:
        self._active = category
        self._select_category(category, emit_signal=emit_signal)
        self._update_chip()

    def active_category(self) -> Category:
        return self._active

    # ------------------------------------------------------------------
    # Category search — only filters the sidebar list rows
    # Does NOT call rule_card_browser, QuickFilterController, or validator.
    # ------------------------------------------------------------------

    def _on_category_search_changed(self, text: str) -> None:
        self._search_clear_btn.setEnabled(bool(text))
        self._apply_category_search(text)

    def _apply_category_search(self, query: str) -> None:
        """Show/hide list rows by matching query against category labels only."""
        q = query.strip().lower()
        for row in range(self._list.count()):
            item = self._list.item(row)
            cat  = item.data(_CATEGORY_ROLE)
            hidden = bool(q) and q not in CATEGORY_LABELS[cat].lower()
            self._list.setRowHidden(row, hidden)

    def _clear_search(self) -> None:
        self._search_input.clear()   # textChanged("") re-shows all rows

    # ------------------------------------------------------------------
    # Active filter chip
    # ------------------------------------------------------------------

    def _update_chip(self) -> None:
        if self._active == Category.ALL:
            self._chip_container.setVisible(False)
        else:
            self._chip_label.setText(f"分類：{CATEGORY_LABELS[self._active]}")
            self._chip_container.setVisible(True)

    def _on_chip_clear(self) -> None:
        """Reset active category to ALL and clear the search input."""
        was_filtered = self._active != Category.ALL
        self._clear_search()
        self.set_active_category(Category.ALL, emit_signal=False)
        if was_filtered:
            self.category_selected.emit(Category.ALL)

    # ------------------------------------------------------------------
    # Internal selection helper
    # ------------------------------------------------------------------

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
        self._update_chip()
        self.category_selected.emit(cat)
