"""P23.1 — ItemDatabase 測試。

涵蓋：分類取得、子分類取得、物品取得、英文搜尋、中文搜尋、空結果、
      AliasResolver 整合搜尋、資料完整性。

純 Python，不依賴 Qt。
"""

from __future__ import annotations

import pytest

from core.item_database import ItemDatabase, ItemDefinition


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db() -> ItemDatabase:
    return ItemDatabase()


# ---------------------------------------------------------------------------
# 1. ItemDefinition 資料模型
# ---------------------------------------------------------------------------

class TestItemDefinition:

    def test_has_id(self):
        item = ItemDefinition(id="test", name_en="A", name_zh="甲", category="C", subcategory="S")
        assert item.id == "test"

    def test_has_name_en(self):
        item = ItemDefinition(id="x", name_en="Chaos Orb", name_zh="混沌石", category="C", subcategory="S")
        assert item.name_en == "Chaos Orb"

    def test_has_name_zh(self):
        item = ItemDefinition(id="x", name_en="A", name_zh="混沌石", category="C", subcategory="S")
        assert item.name_zh == "混沌石"

    def test_has_category(self):
        item = ItemDefinition(id="x", name_en="A", name_zh="甲", category="Currency", subcategory="S")
        assert item.category == "Currency"

    def test_has_subcategory(self):
        item = ItemDefinition(id="x", name_en="A", name_zh="甲", category="C", subcategory="基本通貨")
        assert item.subcategory == "基本通貨"

    def test_tags_default_empty(self):
        item = ItemDefinition(id="x", name_en="A", name_zh="甲", category="C", subcategory="S")
        assert item.tags == []

    def test_tags_can_be_set(self):
        item = ItemDefinition(id="x", name_en="A", name_zh="甲", category="C", subcategory="S", tags=["foo", "bar"])
        assert "foo" in item.tags


# ---------------------------------------------------------------------------
# 2. get_categories()
# ---------------------------------------------------------------------------

class TestGetCategories:

    def test_returns_list(self, db):
        assert isinstance(db.get_categories(), list)

    def test_includes_weapons(self, db):
        assert "Weapons" in db.get_categories()

    def test_includes_armour(self, db):
        assert "Armour" in db.get_categories()

    def test_includes_jewellery(self, db):
        assert "Jewellery" in db.get_categories()

    def test_includes_currency(self, db):
        assert "Currency" in db.get_categories()

    def test_includes_waystones(self, db):
        assert "Waystones" in db.get_categories()

    def test_includes_tablets(self, db):
        assert "Tablets" in db.get_categories()

    def test_weapons_before_currency(self, db):
        cats = db.get_categories()
        assert cats.index("Weapons") < cats.index("Currency")

    def test_armour_before_currency(self, db):
        cats = db.get_categories()
        assert cats.index("Armour") < cats.index("Currency")

    def test_jewellery_before_currency(self, db):
        cats = db.get_categories()
        assert cats.index("Jewellery") < cats.index("Currency")


# ---------------------------------------------------------------------------
# 3. get_subcategories()
# ---------------------------------------------------------------------------

class TestGetSubcategories:

    def test_weapons_has_sword(self, db):
        subs = db.get_subcategories("Weapons")
        assert "單手劍" in subs

    def test_weapons_has_bow(self, db):
        assert "弓" in db.get_subcategories("Weapons")

    def test_weapons_has_two_hand_sword(self, db):
        assert "雙手劍" in db.get_subcategories("Weapons")

    def test_armour_has_body(self, db):
        assert "胸甲" in db.get_subcategories("Armour")

    def test_armour_has_helmet(self, db):
        assert "頭盔" in db.get_subcategories("Armour")

    def test_armour_has_gloves(self, db):
        assert "手套" in db.get_subcategories("Armour")

    def test_armour_has_boots(self, db):
        assert "鞋子" in db.get_subcategories("Armour")

    def test_armour_has_shield(self, db):
        assert "盾牌" in db.get_subcategories("Armour")

    def test_jewellery_has_amulet(self, db):
        assert "項鍊" in db.get_subcategories("Jewellery")

    def test_jewellery_has_ring(self, db):
        assert "戒指" in db.get_subcategories("Jewellery")

    def test_jewellery_has_belt(self, db):
        assert "腰帶" in db.get_subcategories("Jewellery")

    def test_currency_has_basic(self, db):
        assert "基本通貨" in db.get_subcategories("Currency")

    def test_currency_has_essence(self, db):
        assert "精華" in db.get_subcategories("Currency")

    def test_currency_has_rune(self, db):
        assert "符文" in db.get_subcategories("Currency")

    def test_currency_has_catalyst(self, db):
        assert "催化劑" in db.get_subcategories("Currency")

    def test_waystones_subcategory(self, db):
        assert "傳送石" in db.get_subcategories("Waystones")

    def test_tablets_subcategory(self, db):
        assert "石板" in db.get_subcategories("Tablets")

    def test_unknown_category_returns_empty(self, db):
        assert db.get_subcategories("DoesNotExist") == []


# ---------------------------------------------------------------------------
# 4. get_items()
# ---------------------------------------------------------------------------

class TestGetItems:

    def test_one_hand_sword_has_items(self, db):
        items = db.get_items("Weapons", "單手劍")
        assert len(items) >= 1

    def test_bow_has_items(self, db):
        assert len(db.get_items("Weapons", "弓")) >= 1

    def test_body_armour_has_items(self, db):
        assert len(db.get_items("Armour", "胸甲")) >= 1

    def test_amulet_has_items(self, db):
        assert len(db.get_items("Jewellery", "項鍊")) >= 1

    def test_ring_has_items(self, db):
        assert len(db.get_items("Jewellery", "戒指")) >= 1

    def test_belt_has_items(self, db):
        assert len(db.get_items("Jewellery", "腰帶")) >= 1

    def test_basic_currency_has_items(self, db):
        assert len(db.get_items("Currency", "基本通貨")) >= 1

    def test_waystones_has_items(self, db):
        assert len(db.get_items("Waystones", "傳送石")) >= 1

    def test_tablets_has_items(self, db):
        assert len(db.get_items("Tablets", "石板")) >= 1

    def test_items_are_item_definitions(self, db):
        for item in db.get_items("Weapons", "單手劍"):
            assert isinstance(item, ItemDefinition)

    def test_items_in_correct_category(self, db):
        for item in db.get_items("Armour", "胸甲"):
            assert item.category == "Armour"
            assert item.subcategory == "胸甲"

    def test_unknown_category_returns_empty(self, db):
        assert db.get_items("NoSuch", "NoSub") == []

    def test_unknown_subcategory_returns_empty(self, db):
        assert db.get_items("Weapons", "不存在子分類") == []


# ---------------------------------------------------------------------------
# 5. 資料完整性
# ---------------------------------------------------------------------------

class TestDataIntegrity:

    def test_total_items_over_100(self, db):
        assert len(db.all_items()) >= 100

    def test_all_ids_unique(self, db):
        ids = [item.id for item in db.all_items()]
        assert len(ids) == len(set(ids))

    def test_all_items_have_non_empty_id(self, db):
        for item in db.all_items():
            assert item.id, f"空白 id: {item}"

    def test_all_items_have_name_en(self, db):
        for item in db.all_items():
            assert item.name_en, f"空 name_en: {item.id}"

    def test_all_items_have_name_zh(self, db):
        for item in db.all_items():
            assert item.name_zh, f"空 name_zh: {item.id}"

    def test_all_items_have_category(self, db):
        for item in db.all_items():
            assert item.category, f"空 category: {item.id}"

    def test_all_items_have_subcategory(self, db):
        for item in db.all_items():
            assert item.subcategory, f"空 subcategory: {item.id}"

    def test_tags_is_list(self, db):
        for item in db.all_items():
            assert isinstance(item.tags, list), f"{item.id} tags 非 list"

    def test_weapons_count(self, db):
        weapons = [i for i in db.all_items() if i.category == "Weapons"]
        assert len(weapons) >= 20

    def test_armour_count(self, db):
        armour = [i for i in db.all_items() if i.category == "Armour"]
        assert len(armour) >= 15

    def test_jewellery_count(self, db):
        jewellery = [i for i in db.all_items() if i.category == "Jewellery"]
        assert len(jewellery) >= 10

    def test_currency_count(self, db):
        currency = [i for i in db.all_items() if i.category == "Currency"]
        assert len(currency) >= 20

    def test_waystones_count(self, db):
        waystones = [i for i in db.all_items() if i.category == "Waystones"]
        assert len(waystones) >= 10

    def test_tablets_count(self, db):
        tablets = [i for i in db.all_items() if i.category == "Tablets"]
        assert len(tablets) >= 5


# ---------------------------------------------------------------------------
# 6. 英文搜尋
# ---------------------------------------------------------------------------

class TestSearchEnglish:

    def test_search_empty_returns_empty(self, db):
        assert db.search("") == []

    def test_search_whitespace_returns_empty(self, db):
        assert db.search("   ") == []

    def test_search_chaos_orb(self, db):
        results = db.search("Chaos Orb")
        names = [r.name_en for r in results]
        assert "Chaos Orb" in names

    def test_search_partial_chaos(self, db):
        results = db.search("Chaos")
        assert len(results) >= 1

    def test_search_divine(self, db):
        results = db.search("Divine Orb")
        names = [r.name_en for r in results]
        assert "Divine Orb" in names

    def test_search_case_insensitive(self, db):
        lower = db.search("chaos orb")
        upper = db.search("CHAOS ORB")
        mixed = db.search("Chaos Orb")
        assert len(lower) == len(upper) == len(mixed)

    def test_search_war_sword(self, db):
        results = db.search("War Sword")
        names = [r.name_en for r in results]
        assert "War Sword" in names

    def test_search_bow_returns_multiple(self, db):
        results = db.search("Bow")
        assert len(results) >= 3

    def test_search_waystone_returns_multiple(self, db):
        results = db.search("Waystone")
        assert len(results) >= 5

    def test_search_tablet_returns_multiple(self, db):
        results = db.search("Tablet")
        assert len(results) >= 3

    def test_search_no_match_returns_empty(self, db):
        assert db.search("xyzzy_nonexistent_item_abc123") == []

    def test_search_results_are_item_definitions(self, db):
        for item in db.search("Orb"):
            assert isinstance(item, ItemDefinition)

    def test_search_results_no_duplicates(self, db):
        results = db.search("Bow")
        ids = [r.id for r in results]
        assert len(ids) == len(set(ids))

    def test_search_plate_helm(self, db):
        results = db.search("Plate Helm")
        names = [r.name_en for r in results]
        assert "Plate Helm" in names

    def test_search_coral_amulet(self, db):
        results = db.search("Coral Amulet")
        names = [r.name_en for r in results]
        assert "Coral Amulet" in names


# ---------------------------------------------------------------------------
# 7. 中文搜尋
# ---------------------------------------------------------------------------

class TestSearchChinese:

    def test_search_chaos_orb_zh(self, db):
        results = db.search("混沌石")
        names = [r.name_zh for r in results]
        assert "混沌石" in names

    def test_search_divine_orb_zh(self, db):
        results = db.search("神聖石")
        names = [r.name_zh for r in results]
        assert "神聖石" in names

    def test_search_zh_partial_waystone(self, db):
        results = db.search("傳送石")
        assert len(results) >= 5

    def test_search_zh_war_sword(self, db):
        results = db.search("戰劍")
        names = [r.name_zh for r in results]
        assert "戰劍" in names

    def test_search_zh_bow(self, db):
        results = db.search("弓")
        assert len(results) >= 3

    def test_search_zh_coral_amulet(self, db):
        results = db.search("珊瑚護符")
        names = [r.name_zh for r in results]
        assert "珊瑚護符" in names

    def test_search_zh_iron_ring(self, db):
        results = db.search("鐵戒")
        names = [r.name_zh for r in results]
        assert "鐵戒" in names

    def test_search_zh_rune(self, db):
        results = db.search("符文")
        assert len(results) >= 5

    def test_search_zh_essence(self, db):
        results = db.search("精華")
        assert len(results) >= 5

    def test_search_zh_tablet(self, db):
        results = db.search("石板")
        assert len(results) >= 3

    def test_search_zh_no_match(self, db):
        results = db.search("完全不存在的物品名稱xyz")
        assert results == []


# ---------------------------------------------------------------------------
# 8. 中文別名搜尋（P21 AliasResolver 整合）
# ---------------------------------------------------------------------------

class TestSearchAlias:

    def test_alias_chaos(self, db):
        """'混沌' 別名 → Chaos Orb。"""
        results = db.search("混沌")
        names = [r.name_en for r in results]
        assert "Chaos Orb" in names

    def test_alias_div(self, db):
        """'div' 英文別名 → Divine Orb。"""
        results = db.search("div")
        names = [r.name_en for r in results]
        assert "Divine Orb" in names

    def test_alias_gcp(self, db):
        """'GCP' 別名 → Gemcutter's Prism。"""
        results = db.search("gcp")
        names_lower = [r.name_en.lower() for r in results]
        assert "gemcutter's prism" in names_lower

    def test_alias_vaal(self, db):
        """'瓦爾' 別名 → Vaal Orb。"""
        results = db.search("瓦爾")
        names = [r.name_en for r in results]
        assert "Vaal Orb" in names

    def test_alias_cemetery_waystone(self, db):
        """'墓地' 別名 → Cemetery Waystone。"""
        results = db.search("墓地")
        names = [r.name_en for r in results]
        assert any("Cemetery" in n for n in names)

    def test_alias_returns_item_definitions(self, db):
        results = db.search("混沌")
        for item in results:
            assert isinstance(item, ItemDefinition)

    def test_alias_no_duplicates(self, db):
        results = db.search("混沌")
        ids = [r.id for r in results]
        assert len(ids) == len(set(ids))
