"""P23.2 — ItemSelectorWidget 測試。

涵蓋：Category 瀏覽、Subcategory 聯動、Item List 顯示、
      即時搜尋（英文 / 中文 / 別名）、Selection 回傳、Signal 發射。

Qt6 offscreen 平台，不顯示視窗。
"""

from __future__ import annotations

import pytest

from core.item_database import ItemDatabase, ItemDefinition


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(["-platform", "offscreen"])


@pytest.fixture
def db():
    return ItemDatabase()


@pytest.fixture
def widget(qapp, db):
    from ui.item_selector_widget import ItemSelectorWidget
    return ItemSelectorWidget(db=db)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _set_category(widget, name: str) -> bool:
    for i in range(widget._cat_combo.count()):
        if widget._cat_combo.itemText(i) == name:
            widget._cat_combo.setCurrentIndex(i)
            return True
    return False


def _set_subcategory(widget, name: str) -> bool:
    for i in range(widget._sub_combo.count()):
        if widget._sub_combo.itemText(i) == name:
            widget._sub_combo.setCurrentIndex(i)
            return True
    return False


def _list_texts(widget) -> list[str]:
    return [widget._item_list.item(i).text() for i in range(widget._item_list.count())]


# ---------------------------------------------------------------------------
# 1. Category Combo
# ---------------------------------------------------------------------------

class TestCategoryCombo:

    def test_exists(self, widget):
        assert hasattr(widget, "_cat_combo")

    def test_has_at_least_6_items(self, widget):
        assert widget._cat_combo.count() >= 6

    def test_includes_weapons(self, widget):
        texts = [widget._cat_combo.itemText(i) for i in range(widget._cat_combo.count())]
        assert "Weapons" in texts

    def test_includes_armour(self, widget):
        texts = [widget._cat_combo.itemText(i) for i in range(widget._cat_combo.count())]
        assert "Armour" in texts

    def test_includes_jewellery(self, widget):
        texts = [widget._cat_combo.itemText(i) for i in range(widget._cat_combo.count())]
        assert "Jewellery" in texts

    def test_includes_currency(self, widget):
        texts = [widget._cat_combo.itemText(i) for i in range(widget._cat_combo.count())]
        assert "Currency" in texts

    def test_includes_waystones(self, widget):
        texts = [widget._cat_combo.itemText(i) for i in range(widget._cat_combo.count())]
        assert "Waystones" in texts

    def test_includes_tablets(self, widget):
        texts = [widget._cat_combo.itemText(i) for i in range(widget._cat_combo.count())]
        assert "Tablets" in texts

    def test_weapons_is_first(self, widget):
        assert widget._cat_combo.itemText(0) == "Weapons"

    def test_objectname(self, widget):
        assert widget._cat_combo.objectName() == "ItemSelectorCatCombo"


# ---------------------------------------------------------------------------
# 2. Subcategory Combo
# ---------------------------------------------------------------------------

class TestSubcategoryCombo:

    def test_exists(self, widget):
        assert hasattr(widget, "_sub_combo")

    def test_populated_after_init(self, widget):
        assert widget._sub_combo.count() >= 1

    def test_weapons_has_single_sword(self, widget):
        _set_category(widget, "Weapons")
        subs = {widget._sub_combo.itemText(i) for i in range(widget._sub_combo.count())}
        assert "單手劍" in subs

    def test_weapons_has_bow(self, widget):
        _set_category(widget, "Weapons")
        subs = {widget._sub_combo.itemText(i) for i in range(widget._sub_combo.count())}
        assert "弓" in subs

    def test_armour_has_body(self, widget):
        _set_category(widget, "Armour")
        subs = {widget._sub_combo.itemText(i) for i in range(widget._sub_combo.count())}
        assert "胸甲" in subs

    def test_armour_has_helmet(self, widget):
        _set_category(widget, "Armour")
        subs = {widget._sub_combo.itemText(i) for i in range(widget._sub_combo.count())}
        assert "頭盔" in subs

    def test_armour_has_shield(self, widget):
        _set_category(widget, "Armour")
        subs = {widget._sub_combo.itemText(i) for i in range(widget._sub_combo.count())}
        assert "盾牌" in subs

    def test_jewellery_has_ring(self, widget):
        _set_category(widget, "Jewellery")
        subs = {widget._sub_combo.itemText(i) for i in range(widget._sub_combo.count())}
        assert "戒指" in subs

    def test_jewellery_has_amulet(self, widget):
        _set_category(widget, "Jewellery")
        subs = {widget._sub_combo.itemText(i) for i in range(widget._sub_combo.count())}
        assert "項鍊" in subs

    def test_jewellery_has_belt(self, widget):
        _set_category(widget, "Jewellery")
        subs = {widget._sub_combo.itemText(i) for i in range(widget._sub_combo.count())}
        assert "腰帶" in subs

    def test_currency_has_basic(self, widget):
        _set_category(widget, "Currency")
        subs = {widget._sub_combo.itemText(i) for i in range(widget._sub_combo.count())}
        assert "基本通貨" in subs

    def test_subcategory_changes_when_category_changes(self, widget):
        _set_category(widget, "Weapons")
        weapons_count = widget._sub_combo.count()
        _set_category(widget, "Jewellery")
        jewellery_count = widget._sub_combo.count()
        # 首飾 3 個子分類；武器多於 3
        assert weapons_count > jewellery_count

    def test_objectname(self, widget):
        assert widget._sub_combo.objectName() == "ItemSelectorSubCombo"


# ---------------------------------------------------------------------------
# 3. Item List
# ---------------------------------------------------------------------------

class TestItemList:

    def test_exists(self, widget):
        assert hasattr(widget, "_item_list")

    def test_populated_after_init(self, widget):
        _set_category(widget, "Weapons")
        assert widget._item_list.count() >= 1

    def test_item_shows_chinese_name(self, widget):
        _set_category(widget, "Weapons")
        assert widget._item_list.count() >= 1
        text = widget._item_list.item(0).text()
        assert any("一" <= c <= "鿿" for c in text)

    def test_item_shows_english_name(self, widget):
        _set_category(widget, "Weapons")
        text = widget._item_list.item(0).text()
        assert any(c.isalpha() and c.isascii() for c in text)

    def test_item_zh_before_en(self, widget):
        """中文名稱應在第一行，英文在第二行。"""
        _set_category(widget, "Weapons")
        _set_subcategory(widget, "單手劍")
        text = widget._item_list.item(0).text()
        lines = text.split("\n")
        assert len(lines) == 2
        assert any("一" <= c <= "鿿" for c in lines[0]), "第一行應含中文"
        assert any(c.isalpha() and c.isascii() for c in lines[1]), "第二行應含英文"

    def test_currency_items_listed(self, widget):
        _set_category(widget, "Currency")
        assert widget._item_list.count() >= 1

    def test_waystones_items_listed(self, widget):
        _set_category(widget, "Waystones")
        assert widget._item_list.count() >= 5

    def test_tablets_items_listed(self, widget):
        _set_category(widget, "Tablets")
        assert widget._item_list.count() >= 3

    def test_subcategory_single_sword_items(self, widget):
        _set_category(widget, "Weapons")
        _set_subcategory(widget, "單手劍")
        assert widget._item_list.count() >= 1

    def test_subcategory_change_updates_list(self, widget):
        _set_category(widget, "Armour")
        _set_subcategory(widget, "胸甲")
        count_body = widget._item_list.count()
        _set_subcategory(widget, "頭盔")
        count_helm = widget._item_list.count()
        assert count_body >= 1 and count_helm >= 1

    def test_current_items_matches_list_count(self, widget):
        _set_category(widget, "Currency")
        assert len(widget._current_items) == widget._item_list.count()

    def test_objectname(self, widget):
        assert widget._item_list.objectName() == "ItemSelectorItemList"


# ---------------------------------------------------------------------------
# 4. Search
# ---------------------------------------------------------------------------

class TestSearch:

    def test_search_edit_exists(self, widget):
        assert hasattr(widget, "_search_edit")

    def test_objectname(self, widget):
        assert widget._search_edit.objectName() == "ItemSelectorSearchEdit"

    def test_search_english_chaos_orb(self, widget):
        widget._search_edit.setText("Chaos Orb")
        texts = _list_texts(widget)
        assert any("Chaos Orb" in t for t in texts)

    def test_search_english_partial_orb(self, widget):
        widget._search_edit.setText("Orb")
        assert widget._item_list.count() >= 3

    def test_search_english_bow(self, widget):
        widget._search_edit.setText("Bow")
        texts = _list_texts(widget)
        assert any("Bow" in t for t in texts)

    def test_search_english_case_insensitive(self, widget):
        widget._search_edit.setText("chaos orb")
        c_lower = widget._item_list.count()
        widget._search_edit.setText("CHAOS ORB")
        c_upper = widget._item_list.count()
        assert c_lower == c_upper

    def test_search_chinese_shen_sheng_shi(self, widget):
        widget._search_edit.setText("神聖石")
        texts = _list_texts(widget)
        assert any("Divine Orb" in t for t in texts)

    def test_search_chinese_war_sword(self, widget):
        widget._search_edit.setText("戰劍")
        texts = _list_texts(widget)
        assert any("War Sword" in t for t in texts)

    def test_search_chinese_waystone(self, widget):
        widget._search_edit.setText("傳送石")
        assert widget._item_list.count() >= 5

    def test_search_alias_div(self, widget):
        """英文別名 'div' → Divine Orb。"""
        widget._search_edit.setText("div")
        texts = _list_texts(widget)
        assert any("Divine Orb" in t for t in texts)

    def test_search_alias_chaos_zh(self, widget):
        """中文別名 '混沌' → Chaos Orb。"""
        widget._search_edit.setText("混沌")
        texts = _list_texts(widget)
        assert any("Chaos Orb" in t for t in texts)

    def test_search_alias_vaal(self, widget):
        """中文別名 '瓦爾' → Vaal Orb。"""
        widget._search_edit.setText("瓦爾")
        texts = _list_texts(widget)
        assert any("Vaal Orb" in t for t in texts)

    def test_search_no_match_shows_placeholder(self, widget):
        widget._search_edit.setText("xyzzy_nonexistent_abc123")
        assert widget._item_list.count() == 1  # H-02: placeholder 取代空列表

    def test_search_clear_restores_category_view(self, widget):
        _set_category(widget, "Weapons")
        count_before = widget._item_list.count()
        widget._search_edit.setText("Chaos Orb")
        # Now clear search — should restore Weapons items
        widget._search_edit.setText("")
        assert widget._item_list.count() == count_before

    def test_search_current_items_updates(self, widget):
        widget._search_edit.setText("Chaos Orb")
        assert len(widget._current_items) >= 1
        assert all(isinstance(i, ItemDefinition) for i in widget._current_items)
        widget._search_edit.setText("")  # cleanup

    def test_search_placeholder_text(self, widget):
        assert "搜尋" in widget._search_edit.placeholderText()

    def test_search_no_match_placeholder_not_selectable(self, widget):
        """H-02: placeholder item 必須不可選取。"""
        from PySide6.QtCore import Qt
        widget._search_edit.setText("xyzzy_nonexistent_abc123")
        assert widget._item_list.count() == 1
        flag = widget._item_list.item(0).flags()
        assert not bool(flag & Qt.ItemFlag.ItemIsSelectable)

    def test_search_no_match_selected_item_is_none(self, widget):
        """H-02: placeholder 被程式選取時 selected_item() 仍回傳 None。"""
        widget._search_edit.setText("xyzzy_nonexistent_abc123")
        widget._item_list.setCurrentRow(0)
        assert widget.selected_item() is None

    def test_search_clear_after_no_match_restores_list(self, widget):
        """清空搜尋（在無結果後）應恢復正常分類列表，不保留 placeholder。"""
        _set_category(widget, "Weapons")
        count_before = widget._item_list.count()
        widget._search_edit.setText("xyzzy_nonexistent_abc123")
        widget._search_edit.setText("")
        assert widget._item_list.count() == count_before


# ---------------------------------------------------------------------------
# 5. Selection
# ---------------------------------------------------------------------------

class TestSelection:

    def test_selected_item_none_when_no_row(self, widget):
        _set_category(widget, "Weapons")
        widget._item_list.setCurrentRow(-1)
        assert widget.selected_item() is None

    def test_selected_item_returns_item_definition(self, widget):
        _set_category(widget, "Weapons")
        if widget._item_list.count() > 0:
            widget._item_list.setCurrentRow(0)
            result = widget.selected_item()
            assert isinstance(result, ItemDefinition)

    def test_selected_item_matches_row(self, widget):
        _set_category(widget, "Weapons")
        if widget._item_list.count() >= 2:
            widget._item_list.setCurrentRow(1)
            item = widget.selected_item()
            assert item is widget._current_items[1]

    def test_selected_item_has_name_en(self, widget):
        _set_category(widget, "Currency")
        if widget._item_list.count() > 0:
            widget._item_list.setCurrentRow(0)
            item = widget.selected_item()
            assert item is not None and item.name_en

    def test_selected_item_has_name_zh(self, widget):
        _set_category(widget, "Currency")
        if widget._item_list.count() > 0:
            widget._item_list.setCurrentRow(0)
            item = widget.selected_item()
            assert item is not None and item.name_zh

    def test_selected_item_has_category(self, widget):
        _set_category(widget, "Armour")
        if widget._item_list.count() > 0:
            widget._item_list.setCurrentRow(0)
            item = widget.selected_item()
            assert item is not None and item.category

    def test_selected_item_correct_after_search(self, widget):
        widget._search_edit.setText("Chaos Orb")
        if widget._item_list.count() > 0:
            widget._item_list.setCurrentRow(0)
            item = widget.selected_item()
            assert item is not None
            assert "Chaos Orb" in item.name_en
        widget._search_edit.setText("")  # cleanup


# ---------------------------------------------------------------------------
# 6. Signal
# ---------------------------------------------------------------------------

class TestSignal:

    def test_signal_emits_on_row_selection(self, widget):
        received = []
        widget.item_selected.connect(received.append)
        _set_category(widget, "Weapons")
        if widget._item_list.count() > 0:
            widget._item_list.setCurrentRow(0)
        assert len(received) >= 1

    def test_signal_carries_item_definition(self, widget):
        received = []
        widget.item_selected.connect(received.append)
        _set_category(widget, "Currency")
        if widget._item_list.count() > 0:
            widget._item_list.setCurrentRow(0)
        if received:
            assert isinstance(received[-1], ItemDefinition)

    def test_signal_item_has_valid_name_en(self, widget):
        received = []
        widget.item_selected.connect(received.append)
        _set_category(widget, "Waystones")
        if widget._item_list.count() > 0:
            widget._item_list.setCurrentRow(0)
        if received:
            assert received[-1].name_en

    def test_signal_item_has_valid_name_zh(self, widget):
        received = []
        widget.item_selected.connect(received.append)
        _set_category(widget, "Waystones")
        if widget._item_list.count() > 0:
            widget._item_list.setCurrentRow(0)
        if received:
            assert received[-1].name_zh

    def test_no_signal_on_empty_list(self, widget):
        received = []
        widget.item_selected.connect(received.append)
        widget._search_edit.setText("xyzzy_nonexistent_abc123")
        prev = len(received)
        widget._item_list.setCurrentRow(0)  # no items → no-op
        assert len(received) == prev
        widget._search_edit.setText("")  # cleanup

    def test_signal_updates_on_different_row(self, widget):
        received = []
        widget.item_selected.connect(received.append)
        _set_category(widget, "Weapons")
        if widget._item_list.count() >= 2:
            widget._item_list.setCurrentRow(0)
            widget._item_list.setCurrentRow(1)
        assert len(received) >= 1
