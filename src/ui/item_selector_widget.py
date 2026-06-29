"""P23.2 — ItemSelectorWidget: 圖形化物品選擇器。

提供 Category → Subcategory → Item List 三層瀏覽，並支援即時中英文搜尋。
整合 P23.1 ItemDatabase，可獨立使用，不依賴 Rule Editor。

佈局：
    ┌─────────────┐
    │ Category    │  ← QComboBox
    ├─────────────┤
    │ Subcategory │  ← QComboBox（隨 Category 更新）
    ├─────────────┤
    │ Item List   │  ← QListWidget（中文名 + 英文名雙行顯示）
    ├─────────────┤
    │ Search      │  ← QLineEdit（即時搜尋，空白時恢復分類瀏覽）
    └─────────────┘
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.item_database import ItemDatabase, ItemDefinition


class ItemSelectorWidget(QWidget):
    """Category / Subcategory / 搜尋三合一物品選擇器。

    Signals
    -------
    item_selected(object)
        使用者點選物品清單時發射，攜帶選取的 ItemDefinition。
    """

    item_selected: Signal = Signal(object)  # carries ItemDefinition

    def __init__(
        self,
        db: Optional[ItemDatabase] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._db: ItemDatabase = db or ItemDatabase()
        self._current_items: list[ItemDefinition] = []
        self._setup_ui()
        self._populate_categories()

    # ── 公開 API ──────────────────────────────────────────────────────────

    def selected_item(self) -> Optional[ItemDefinition]:
        """回傳目前選取的 ItemDefinition；未選取時回傳 None。"""
        row = self._item_list.currentRow()
        if 0 <= row < len(self._current_items):
            return self._current_items[row]
        return None

    # ── UI 建構 ──────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setObjectName("ItemSelectorWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Category
        cat_lbl = QLabel("分類")
        cat_lbl.setObjectName("ItemSelectorLabel")
        self._cat_combo = QComboBox()
        self._cat_combo.setObjectName("ItemSelectorCatCombo")
        layout.addWidget(cat_lbl)
        layout.addWidget(self._cat_combo)

        # Subcategory
        sub_lbl = QLabel("子分類")
        sub_lbl.setObjectName("ItemSelectorLabel")
        self._sub_combo = QComboBox()
        self._sub_combo.setObjectName("ItemSelectorSubCombo")
        layout.addWidget(sub_lbl)
        layout.addWidget(self._sub_combo)

        # Item list（大部分空間給清單）
        item_lbl = QLabel("物品")
        item_lbl.setObjectName("ItemSelectorLabel")
        self._item_list = QListWidget()
        self._item_list.setObjectName("ItemSelectorItemList")
        self._item_list.setUniformItemSizes(False)
        layout.addWidget(item_lbl)
        layout.addWidget(self._item_list, stretch=1)

        # Search
        self._search_edit = QLineEdit()
        self._search_edit.setObjectName("ItemSelectorSearchEdit")
        self._search_edit.setPlaceholderText("搜尋物品（中文 / 英文 / 別名）…")
        self._search_edit.setClearButtonEnabled(True)
        layout.addWidget(self._search_edit)

        # Signals
        self._cat_combo.currentIndexChanged.connect(self._on_category_changed)
        self._sub_combo.currentIndexChanged.connect(self._on_subcategory_changed)
        self._item_list.currentItemChanged.connect(self._on_selection_changed)
        self._search_edit.textChanged.connect(self._on_search_changed)

    # ── 資料填充 ──────────────────────────────────────────────────────────

    def _populate_categories(self) -> None:
        self._cat_combo.blockSignals(True)
        self._cat_combo.clear()
        for cat in self._db.get_categories():
            self._cat_combo.addItem(cat, cat)
        self._cat_combo.blockSignals(False)
        # 觸發第一個分類的子分類 + 清單更新
        self._on_category_changed(0)

    def _populate_list(self, items: list[ItemDefinition]) -> None:
        """填充物品清單（blockSignals 防重複訊號，setUpdatesEnabled 批次重繪）。"""
        self._item_list.setUpdatesEnabled(False)
        self._item_list.blockSignals(True)
        self._item_list.clear()
        self._current_items = list(items)
        for item in items:
            lw = QListWidgetItem(f"{item.name_zh}\n{item.name_en}")
            lw.setSizeHint(QSize(-1, 42))
            self._item_list.addItem(lw)
        self._item_list.blockSignals(False)
        self._item_list.setUpdatesEnabled(True)

    def _refresh_item_list(self) -> None:
        """根據目前分類 / 子分類填充清單。"""
        cat = self._cat_combo.currentData()
        sub = self._sub_combo.currentData()
        if cat is None:
            self._populate_list([])
            return
        if sub is None:
            items: list[ItemDefinition] = []
            for s in self._db.get_subcategories(cat):
                items.extend(self._db.get_items(cat, s))
            self._populate_list(items)
        else:
            self._populate_list(self._db.get_items(cat, sub))

    # ── Slot ──────────────────────────────────────────────────────────────

    def _on_category_changed(self, idx: int) -> None:
        cat = self._cat_combo.currentData()
        self._sub_combo.blockSignals(True)
        self._sub_combo.clear()
        if cat is not None:
            for sub in self._db.get_subcategories(cat):
                self._sub_combo.addItem(sub, sub)
        self._sub_combo.blockSignals(False)
        # 分類變更一律刷新清單（覆蓋搜尋狀態）
        self._search_edit.blockSignals(True)
        self._search_edit.clear()
        self._search_edit.blockSignals(False)
        self._refresh_item_list()

    def _on_subcategory_changed(self, idx: int) -> None:
        if not self._search_edit.text().strip():
            self._refresh_item_list()

    def _on_search_changed(self, text: str) -> None:
        text = text.strip()
        if text:
            results = self._db.search(text)
            self._populate_list(results)
            if not results:
                hint = QListWidgetItem("沒有找到符合的物品")
                hint.setFlags(Qt.ItemFlag.NoItemFlags)
                self._item_list.addItem(hint)
        else:
            self._refresh_item_list()

    def _on_selection_changed(
        self,
        current: Optional[QListWidgetItem],
        _previous: Optional[QListWidgetItem],
    ) -> None:
        if current is None:
            return
        item = self.selected_item()
        if item is not None:
            self.item_selected.emit(item)
