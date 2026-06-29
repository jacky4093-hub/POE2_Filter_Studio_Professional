"""P21.3 — Alias Database Completeness tests.

Validates structural integrity and minimum coverage of
src/data/bundled_aliases_zh_tw.json after P21.3 expansion.
"""

import json
import pathlib
import pytest

_DATA_FILE = pathlib.Path(__file__).parent.parent / "src" / "data" / "bundled_aliases_zh_tw.json"


@pytest.fixture(scope="session")
def db() -> dict:
    assert _DATA_FILE.exists(), f"找不到 alias 資料檔：{_DATA_FILE}"
    with _DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def items(db) -> list:
    return db["items"]


@pytest.fixture(scope="session")
def categories(db) -> dict:
    return db["categories"]


# ---------------------------------------------------------------------------
# TestIdField — id 欄位
# ---------------------------------------------------------------------------

class TestIdField:
    def test_every_item_has_id(self, items):
        for i, item in enumerate(items):
            assert "id" in item, f"items[{i}]({item.get('zh','?')}) 缺少 id"

    def test_every_id_is_nonempty_string(self, items):
        for i, item in enumerate(items):
            assert isinstance(item.get("id"), str) and item["id"].strip(), \
                f"items[{i}]({item.get('zh','?')}).id 必須是非空字串"

    def test_id_unique(self, items):
        ids = [item["id"] for item in items]
        seen, dupes = set(), set()
        for id_ in ids:
            if id_ in seen:
                dupes.add(id_)
            seen.add(id_)
        assert not dupes, f"items 中有重複的 id：{dupes}"


# ---------------------------------------------------------------------------
# TestZhUniqueness — zh 唯一性
# ---------------------------------------------------------------------------

class TestZhUniqueness:
    def test_zh_unique(self, items):
        zhs = [item["zh"] for item in items]
        seen, dupes = set(), set()
        for zh in zhs:
            if zh in seen:
                dupes.add(zh)
            seen.add(zh)
        assert not dupes, f"items 中有重複的 zh 名稱：{dupes}"


# ---------------------------------------------------------------------------
# TestEnUniqueness — en 唯一性
# ---------------------------------------------------------------------------

class TestEnUniqueness:
    def test_en_unique(self, items):
        ens = [item["en"] for item in items]
        seen, dupes = set(), set()
        for en in ens:
            if en in seen:
                dupes.add(en)
            seen.add(en)
        assert not dupes, f"items 中有重複的 en 名稱：{dupes}"


# ---------------------------------------------------------------------------
# TestAliasesNoDuplicate — aliases_zh 各項目內不重複
# ---------------------------------------------------------------------------

class TestAliasesNoDuplicate:
    def test_aliases_zh_no_duplicate_within_item(self, items):
        for i, item in enumerate(items):
            aliases = item.get("aliases_zh", [])
            seen, dupes = set(), set()
            for a in aliases:
                if a in seen:
                    dupes.add(a)
                seen.add(a)
            assert not dupes, \
                f"items[{i}]({item.get('zh','?')}).aliases_zh 有重複值：{dupes}"


# ---------------------------------------------------------------------------
# TestCategoryValid — category 合法性
# ---------------------------------------------------------------------------

class TestCategoryValid:
    def test_all_categories_exist_in_categories_dict(self, items, categories):
        known = set(categories.keys())
        for i, item in enumerate(items):
            cat = item.get("category", "")
            assert cat in known, \
                f"items[{i}]({item.get('zh','?')}).category='{cat}' 不在 categories 中"

    def test_new_categories_exist(self, categories):
        required = {"unique", "base_type", "tablet", "essence", "rune", "catalyst"}
        missing = required - set(categories.keys())
        assert not missing, f"缺少必要的新分類：{missing}"


# ---------------------------------------------------------------------------
# TestMinimumCounts — 各分類最低數量
# ---------------------------------------------------------------------------

class TestMinimumCounts:
    def _count(self, items, category):
        return sum(1 for item in items if item["category"] == category)

    def test_unique_minimum_100(self, items):
        count = self._count(items, "unique")
        assert count >= 100, f"unique 物品數不足：現有 {count}，需要 ≥ 100"

    def test_base_type_minimum_50(self, items):
        count = self._count(items, "base_type")
        assert count >= 50, f"base_type 物品數不足：現有 {count}，需要 ≥ 50"

    def test_essence_minimum_20(self, items):
        count = self._count(items, "essence")
        assert count >= 20, f"essence 物品數不足：現有 {count}，需要 ≥ 20"

    def test_rune_minimum_20(self, items):
        count = self._count(items, "rune")
        assert count >= 20, f"rune 物品數不足：現有 {count}，需要 ≥ 20"

    def test_waystone_tablet_combined_minimum_20(self, items):
        count = self._count(items, "waystone") + self._count(items, "tablet")
        assert count >= 20, \
            f"waystone + tablet 物品數不足：現有 {count}，需要 ≥ 20"

    def test_total_items_minimum_200(self, items):
        assert len(items) >= 200, \
            f"總物品數不足：現有 {len(items)}，需要 ≥ 200"

    def test_currency_still_has_minimum(self, items):
        count = self._count(items, "currency")
        assert count >= 20, f"currency 物品數退化：現有 {count}"
