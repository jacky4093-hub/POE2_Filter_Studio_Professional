"""P21.1 — Chinese Alias Schema validation tests.

Validates the structure and integrity of
src/data/bundled_aliases_zh_tw.json without loading any UI.
"""

import json
import pathlib

import pytest

# ---------------------------------------------------------------------------
# Path resolution — works regardless of CWD
# ---------------------------------------------------------------------------

_TESTS_DIR   = pathlib.Path(__file__).parent
_PROJECT_ROOT = _TESTS_DIR.parent
_DATA_FILE   = _PROJECT_ROOT / "src" / "data" / "bundled_aliases_zh_tw.json"

# ---------------------------------------------------------------------------
# Fixture: load JSON once per session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def alias_db() -> dict:
    assert _DATA_FILE.exists(), f"找不到 alias 資料檔：{_DATA_FILE}"
    with _DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# TestSchemaFile — 檔案層級基礎檢查
# ---------------------------------------------------------------------------

class TestSchemaFile:
    def test_file_exists(self):
        assert _DATA_FILE.exists(), f"缺少檔案：{_DATA_FILE}"

    def test_file_is_valid_json(self):
        with _DATA_FILE.open(encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_meta_schema_version_exists(self, alias_db):
        assert "_meta" in alias_db
        assert "schema_version" in alias_db["_meta"]

    def test_meta_schema_version_is_string(self, alias_db):
        assert isinstance(alias_db["_meta"]["schema_version"], str)

    def test_meta_game_is_poe2(self, alias_db):
        assert alias_db["_meta"].get("game") == "POE2"

    def test_meta_language_is_zh_tw(self, alias_db):
        assert alias_db["_meta"].get("language") == "zh-TW"


# ---------------------------------------------------------------------------
# TestTopLevelKeys — 頂層欄位存在
# ---------------------------------------------------------------------------

class TestTopLevelKeys:
    def test_categories_exists(self, alias_db):
        assert "categories" in alias_db

    def test_categories_is_dict(self, alias_db):
        assert isinstance(alias_db["categories"], dict)

    def test_conditions_exists(self, alias_db):
        assert "conditions" in alias_db

    def test_conditions_is_dict(self, alias_db):
        assert isinstance(alias_db["conditions"], dict)

    def test_items_exists(self, alias_db):
        assert "items" in alias_db

    def test_items_is_list(self, alias_db):
        assert isinstance(alias_db["items"], list)

    def test_items_not_empty(self, alias_db):
        assert len(alias_db["items"]) > 0


# ---------------------------------------------------------------------------
# TestCategories — categories 結構
# ---------------------------------------------------------------------------

class TestCategories:
    def test_each_category_has_zh(self, alias_db):
        for key, cat in alias_db["categories"].items():
            assert "zh" in cat, f"categories[{key}] 缺少 zh"

    def test_each_category_has_en_class(self, alias_db):
        for key, cat in alias_db["categories"].items():
            assert "en_class" in cat, f"categories[{key}] 缺少 en_class"

    def test_each_category_en_class_is_list(self, alias_db):
        for key, cat in alias_db["categories"].items():
            assert isinstance(cat["en_class"], list), \
                f"categories[{key}].en_class 必須是 list"

    def test_each_category_has_priority(self, alias_db):
        for key, cat in alias_db["categories"].items():
            assert "priority" in cat, f"categories[{key}] 缺少 priority"

    def test_each_category_priority_is_int(self, alias_db):
        for key, cat in alias_db["categories"].items():
            assert isinstance(cat["priority"], int), \
                f"categories[{key}].priority 必須是 int"


# ---------------------------------------------------------------------------
# TestConditions — conditions 結構
# ---------------------------------------------------------------------------

class TestConditions:
    def test_each_condition_has_zh(self, alias_db):
        for key, cond in alias_db["conditions"].items():
            assert "zh" in cond, f"conditions[{key}] 缺少 zh"

    def test_each_condition_has_type(self, alias_db):
        for key, cond in alias_db["conditions"].items():
            assert "type" in cond, f"conditions[{key}] 缺少 type"

    def test_each_condition_type_is_valid(self, alias_db):
        valid_types = {"string", "numeric", "bool", "enum"}
        for key, cond in alias_db["conditions"].items():
            assert cond["type"] in valid_types, \
                f"conditions[{key}].type='{cond['type']}' 不是有效類型"

    def test_no_scourged_condition(self, alias_db):
        assert "Scourged" not in alias_db["conditions"], \
            "conditions 不得包含 Scourged（POE1 殘留條件）"

    def test_class_condition_exists(self, alias_db):
        assert "Class" in alias_db["conditions"]

    def test_basetype_condition_exists(self, alias_db):
        assert "BaseType" in alias_db["conditions"]

    def test_rarity_condition_exists(self, alias_db):
        assert "Rarity" in alias_db["conditions"]

    def test_rarity_is_enum_type(self, alias_db):
        assert alias_db["conditions"]["Rarity"]["type"] == "enum"

    def test_rarity_has_enum_values(self, alias_db):
        assert "enum_values" in alias_db["conditions"]["Rarity"]

    def test_rarity_contains_normal(self, alias_db):
        evs = alias_db["conditions"]["Rarity"]["enum_values"]
        assert "普通" in evs, "Rarity enum_values 缺少 '普通'"

    def test_rarity_contains_magic(self, alias_db):
        evs = alias_db["conditions"]["Rarity"]["enum_values"]
        assert "魔法" in evs, "Rarity enum_values 缺少 '魔法'"

    def test_rarity_contains_rare(self, alias_db):
        evs = alias_db["conditions"]["Rarity"]["enum_values"]
        assert "稀有" in evs, "Rarity enum_values 缺少 '稀有'"

    def test_rarity_contains_unique_traditional(self, alias_db):
        evs = alias_db["conditions"]["Rarity"]["enum_values"]
        assert "傳說" in evs, "Rarity enum_values 缺少 '傳說'"

    def test_rarity_contains_unique_alternative(self, alias_db):
        evs = alias_db["conditions"]["Rarity"]["enum_values"]
        assert "獨特" in evs, "Rarity enum_values 缺少 '獨特'"

    def test_rarity_enum_values_map_to_english(self, alias_db):
        evs = alias_db["conditions"]["Rarity"]["enum_values"]
        for zh_key, en_val in evs.items():
            assert isinstance(en_val, str) and len(en_val) > 0, \
                f"Rarity enum_values[{zh_key}] 英文值無效"


# ---------------------------------------------------------------------------
# TestItems — items 每筆記錄
# ---------------------------------------------------------------------------

class TestItems:
    def test_each_item_has_zh(self, alias_db):
        for i, item in enumerate(alias_db["items"]):
            assert "zh" in item, f"items[{i}] 缺少 zh"

    def test_each_item_zh_is_nonempty_string(self, alias_db):
        for i, item in enumerate(alias_db["items"]):
            assert isinstance(item["zh"], str) and item["zh"].strip(), \
                f"items[{i}].zh 必須是非空字串"

    def test_each_item_has_en(self, alias_db):
        for i, item in enumerate(alias_db["items"]):
            assert "en" in item, f"items[{i}]({item.get('zh','?')}) 缺少 en"

    def test_each_item_en_is_nonempty_string(self, alias_db):
        for i, item in enumerate(alias_db["items"]):
            assert isinstance(item["en"], str) and item["en"].strip(), \
                f"items[{i}]({item.get('zh','?')}).en 必須是非空字串"

    def test_each_item_has_aliases_zh(self, alias_db):
        for i, item in enumerate(alias_db["items"]):
            assert "aliases_zh" in item, \
                f"items[{i}]({item.get('zh','?')}) 缺少 aliases_zh"

    def test_each_item_aliases_zh_is_list(self, alias_db):
        for i, item in enumerate(alias_db["items"]):
            assert isinstance(item["aliases_zh"], list), \
                f"items[{i}]({item.get('zh','?')}).aliases_zh 必須是 list"

    def test_each_item_has_category(self, alias_db):
        for i, item in enumerate(alias_db["items"]):
            assert "category" in item, \
                f"items[{i}]({item.get('zh','?')}) 缺少 category"

    def test_each_item_category_exists_in_categories(self, alias_db):
        known = set(alias_db["categories"].keys())
        for i, item in enumerate(alias_db["items"]):
            cat = item.get("category", "")
            assert cat in known, \
                f"items[{i}]({item.get('zh','?')}).category='{cat}' 不在 categories 中"

    def test_each_item_has_priority(self, alias_db):
        for i, item in enumerate(alias_db["items"]):
            assert "priority" in item, \
                f"items[{i}]({item.get('zh','?')}) 缺少 priority"

    def test_each_item_priority_is_int(self, alias_db):
        for i, item in enumerate(alias_db["items"]):
            assert isinstance(item["priority"], int), \
                f"items[{i}]({item.get('zh','?')}).priority 必須是 int，得到 {type(item['priority'])}"


# ---------------------------------------------------------------------------
# TestItemIntegrity — items 資料完整性
# ---------------------------------------------------------------------------

class TestItemIntegrity:
    def test_no_scourged_in_items(self, alias_db):
        for item in alias_db["items"]:
            assert "Scourged" not in item.get("en", ""), \
                f"items 不得包含 Scourged 相關物品"

    def test_no_duplicate_en_names(self, alias_db):
        en_names = [item["en"] for item in alias_db["items"]]
        seen, dupes = set(), set()
        for name in en_names:
            if name in seen:
                dupes.add(name)
            seen.add(name)
        assert not dupes, f"items 中有重複的英文名稱：{dupes}"

    def test_chaos_orb_exists(self, alias_db):
        en_names = {item["en"] for item in alias_db["items"]}
        assert "Chaos Orb" in en_names, "items 缺少 Chaos Orb"

    def test_divine_orb_exists(self, alias_db):
        en_names = {item["en"] for item in alias_db["items"]}
        assert "Divine Orb" in en_names, "items 缺少 Divine Orb"

    def test_minimum_item_count(self, alias_db):
        assert len(alias_db["items"]) >= 20, \
            f"items 數量不足（現有 {len(alias_db['items'])}，最少需要 20）"

    def test_all_currency_items_in_currency_category(self, alias_db):
        currency_items = [i for i in alias_db["items"] if i["category"] == "currency"]
        assert len(currency_items) >= 10, \
            f"currency 類別物品數不足（現有 {len(currency_items)}）"
