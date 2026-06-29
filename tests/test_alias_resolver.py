"""P21.2 — AliasResolver 單元測試。

涵蓋：
  1. exact match (zh)
  2. alias match (aliases_zh)
  3. partial match (startswith / contains)
  4. reverse lookup
  5. unknown lookup
  6. priority ordering
"""

import pytest
from src.core.alias_resolver import AliasResolver


@pytest.fixture(scope="module")
def resolver() -> AliasResolver:
    return AliasResolver()


# ---------------------------------------------------------------------------
# 1. Exact match — zh 完全匹配
# ---------------------------------------------------------------------------

class TestExactMatchZh:
    def test_chaos_orb_exact_zh(self, resolver):
        result = resolver.resolve_zh("混沌石")
        assert "Chaos Orb" in result

    def test_divine_orb_exact_zh(self, resolver):
        result = resolver.resolve_zh("神聖石")
        assert "Divine Orb" in result

    def test_mirror_exact_zh(self, resolver):
        result = resolver.resolve_zh("卡蘭德的魔鏡")
        assert "Mirror of Kalandra" in result

    def test_exact_zh_returns_only_that_item(self, resolver):
        result = resolver.resolve_zh("崇高石")
        assert result[0] == "Exalted Orb"


# ---------------------------------------------------------------------------
# 2. Alias match — aliases_zh 完全匹配
# ---------------------------------------------------------------------------

class TestAliasMatch:
    def test_alias_shen_sheng(self, resolver):
        """'神聖' 是 Divine Orb 的別名"""
        result = resolver.resolve_zh("神聖")
        assert "Divine Orb" in result

    def test_alias_hun_dun(self, resolver):
        """'混沌' 是 Chaos Orb 的別名"""
        result = resolver.resolve_zh("混沌")
        assert "Chaos Orb" in result

    def test_alias_jing_zi(self, resolver):
        """'鏡子' 是 Mirror of Kalandra 的別名"""
        result = resolver.resolve_zh("鏡子")
        assert "Mirror of Kalandra" in result

    def test_alias_english_div(self, resolver):
        """'div' 是 Divine Orb 的英文簡寫別名"""
        result = resolver.resolve_zh("div")
        assert "Divine Orb" in result

    def test_alias_english_c(self, resolver):
        """'c' 是 Chaos Orb 的英文簡寫別名"""
        result = resolver.resolve_zh("c")
        assert "Chaos Orb" in result

    def test_alias_gcp(self, resolver):
        """'GCP' 是 Gemcutter's Prism 的別名"""
        result = resolver.resolve_zh("GCP")
        assert "Gemcutter's Prism" in result


# ---------------------------------------------------------------------------
# 3. Partial match — 開頭 / 包含
# ---------------------------------------------------------------------------

class TestPartialMatch:
    def test_startswith_zh_lian_jin(self, resolver):
        """'煉' 應命中 '煉金石' (Orb of Alchemy)"""
        result = resolver.resolve_zh("煉")
        assert "Orb of Alchemy" in result

    def test_startswith_alias_trans(self, resolver):
        """'tran' 應命中 '蛻變石' alias 'tran'（完全匹配），或 'trans'（開頭匹配）"""
        result = resolver.resolve_zh("tran")
        assert "Orb of Transmutation" in result

    def test_contains_zh_shu_bian(self, resolver):
        """'石' 應命中多個含 '石' 的物品"""
        result = resolver.resolve_zh("石")
        assert len(result) >= 3

    def test_startswith_alias_chaos(self, resolver):
        """'chaos' 是 Chaos Orb 完全匹配別名，開頭搜尋也應命中"""
        result = resolver.resolve_zh("chao")
        assert "Chaos Orb" in result

    def test_contains_alias_jewel(self, resolver):
        """'eweller' 包含在 'greater jeweller' 別名中"""
        result = resolver.resolve_zh("eweller")
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# 4. Reverse lookup
# ---------------------------------------------------------------------------

class TestReverseLookup:
    def test_reverse_divine_orb(self, resolver):
        assert resolver.reverse_resolve("Divine Orb") == "神聖石"

    def test_reverse_chaos_orb(self, resolver):
        assert resolver.reverse_resolve("Chaos Orb") == "混沌石"

    def test_reverse_mirror(self, resolver):
        assert resolver.reverse_resolve("Mirror of Kalandra") == "卡蘭德的魔鏡"

    def test_reverse_exalted_orb(self, resolver):
        assert resolver.reverse_resolve("Exalted Orb") == "崇高石"

    def test_reverse_vaal_orb(self, resolver):
        assert resolver.reverse_resolve("Vaal Orb") == "瓦爾石"


# ---------------------------------------------------------------------------
# 5. Unknown lookup
# ---------------------------------------------------------------------------

class TestUnknownLookup:
    def test_unknown_zh_returns_empty(self, resolver):
        assert resolver.resolve_zh("不存在的物品") == []

    def test_unknown_en_reverse_returns_none(self, resolver):
        assert resolver.reverse_resolve("Nonexistent Item") is None

    def test_empty_string_returns_empty(self, resolver):
        assert resolver.resolve_zh("") == []

    def test_unicode_noise_returns_empty(self, resolver):
        assert resolver.resolve_zh("zzzzz99999") == []


# ---------------------------------------------------------------------------
# 6. Priority ordering
# ---------------------------------------------------------------------------

class TestPriorityOrdering:
    def test_priority1_items_come_before_priority2(self, resolver):
        """搜尋 '石' 時，priority=1 的物品應排在 priority=2 之前"""
        result = resolver.resolve_zh("石")
        assert len(result) >= 2

        from src.core.alias_resolver import AliasResolver
        import pathlib, json
        data_file = pathlib.Path(__file__).parent.parent / "src" / "data" / "bundled_aliases_zh_tw.json"
        with data_file.open(encoding="utf-8") as f:
            db = json.load(f)
        priority_map = {item["en"]: item["priority"] for item in db["items"]}

        priorities = [priority_map[en] for en in result if en in priority_map]
        assert priorities == sorted(priorities), \
            f"結果未按 priority 排序：{list(zip(result, priorities))}"

    def test_exact_match_beats_partial(self, resolver):
        """'混沌' 完全匹配 alias → Chaos Orb 應排在第一"""
        result = resolver.resolve_zh("混沌")
        assert result[0] == "Chaos Orb"

    def test_resolve_returns_list(self, resolver):
        result = resolver.resolve_zh("神聖")
        assert isinstance(result, list)

    def test_no_duplicate_in_result(self, resolver):
        result = resolver.resolve_zh("石")
        assert len(result) == len(set(result)), "結果清單不得有重複英文名稱"
