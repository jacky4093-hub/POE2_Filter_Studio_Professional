"""P21.4 — AliasCompleterLogic unit tests.

Tests the pure-Python data layer (AliasCompleterLogic) without any Qt dependency.

Covers:
  1. 中文搜尋 (Chinese name search)
  2. 英文搜尋 (English alias search)
  3. Alias 搜尋 (alias-key search)
  4. 排序正確 (priority ordering)
  5. 空字串 (empty query)
  6. 無結果 (no matches)
"""

import pytest

from core.alias_resolver import AliasResolver
from widgets.alias_completer import AliasCompleterLogic


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def logic() -> AliasCompleterLogic:
    return AliasCompleterLogic(AliasResolver())


# ---------------------------------------------------------------------------
# 1. 中文搜尋
# ---------------------------------------------------------------------------

class TestChineseSearch:
    def test_exact_zh_name(self, logic):
        """完整中文名稱應直接匹配。"""
        results = logic.suggest("神聖石")
        en_names = [en for _, en in results]
        assert "Divine Orb" in en_names

    def test_exact_zh_name_chaos(self, logic):
        results = logic.suggest("混沌石")
        assert any(en == "Chaos Orb" for _, en in results)

    def test_zh_alias_match(self, logic):
        """中文別名完全匹配。"""
        results = logic.suggest("神聖")
        assert any(en == "Divine Orb" for _, en in results)

    def test_zh_alias_jing_zi(self, logic):
        results = logic.suggest("鏡子")
        assert any(en == "Mirror of Kalandra" for _, en in results)

    def test_partial_zh_returns_multiple(self, logic):
        """'石' 應命中多個含石的物品。"""
        results = logic.suggest("石")
        assert len(results) >= 3

    def test_zh_headhunter_alias(self, logic):
        """'獵頭' 應找到 Headhunter。"""
        results = logic.suggest("獵頭")
        assert any(en == "Headhunter" for _, en in results)

    def test_zh_kaom_alias(self, logic):
        """'考心' 是 Kaom's Heart 的中文別名。"""
        results = logic.suggest("考心")
        assert any(en == "Kaom's Heart" for _, en in results)

    def test_zh_mageblood_alias(self, logic):
        """'法師血' 是 Mageblood 的中文別名。"""
        results = logic.suggest("法師血")
        assert any(en == "Mageblood" for _, en in results)

    def test_results_contain_zh_and_en(self, logic):
        """每個建議都是 (zh, en) 二元組。"""
        results = logic.suggest("混沌")
        assert len(results) >= 1
        zh, en = results[0]
        assert isinstance(zh, str) and zh
        assert isinstance(en, str) and en


# ---------------------------------------------------------------------------
# 2. 英文搜尋
# ---------------------------------------------------------------------------

class TestEnglishSearch:
    def test_english_div_alias(self, logic):
        """'div' 英文別名對應 Divine Orb。"""
        results = logic.suggest("div")
        assert any(en == "Divine Orb" for _, en in results)

    def test_english_chaos_alias(self, logic):
        """'chaos' 對應 Chaos Orb。"""
        results = logic.suggest("chaos")
        assert any(en == "Chaos Orb" for _, en in results)

    def test_english_shav_alias(self, logic):
        """'shav' 對應 Shavronne's Wrappings。"""
        results = logic.suggest("shav")
        assert any(en == "Shavronne's Wrappings" for _, en in results)

    def test_english_kaom_alias(self, logic):
        """'kaom' 對應 Kaom's Heart。"""
        results = logic.suggest("kaom")
        assert any(en == "Kaom's Heart" for _, en in results)

    def test_english_mirror_alias(self, logic):
        """'mirror' 對應 Mirror of Kalandra。"""
        results = logic.suggest("mirror")
        assert any(en == "Mirror of Kalandra" for _, en in results)

    def test_english_partial_ex(self, logic):
        """'ex' 應命中 Exalted Orb。"""
        results = logic.suggest("ex")
        assert any(en == "Exalted Orb" for _, en in results)


# ---------------------------------------------------------------------------
# 3. Alias 搜尋
# ---------------------------------------------------------------------------

class TestAliasSearch:
    def test_gcp_upper(self, logic):
        """'GCP' 大寫縮寫對應 Gemcutter's Prism。"""
        results = logic.suggest("GCP")
        assert any(en == "Gemcutter's Prism" for _, en in results)

    def test_mb_upper(self, logic):
        """'MB' 縮寫對應 Mageblood。"""
        results = logic.suggest("MB")
        assert any(en == "Mageblood" for _, en in results)

    def test_hh_upper(self, logic):
        """'HH' 縮寫對應 Headhunter。"""
        results = logic.suggest("HH")
        assert any(en == "Headhunter" for _, en in results)

    def test_we_upper(self, logic):
        """'WE' 縮寫對應 Watcher's Eye。"""
        results = logic.suggest("WE")
        assert any(en == "Watcher's Eye" for _, en in results)

    def test_six_link_tabula(self, logic):
        """'六聯' 對應 Tabula Rasa。"""
        results = logic.suggest("六聯")
        assert any(en == "Tabula Rasa" for _, en in results)

    def test_vaal_alias(self, logic):
        """'vaal' 對應 Vaal Orb。"""
        results = logic.suggest("vaal")
        assert any(en == "Vaal Orb" for _, en in results)


# ---------------------------------------------------------------------------
# 4. 排序正確
# ---------------------------------------------------------------------------

class TestSortOrder:
    def test_result_is_list(self, logic):
        results = logic.suggest("混沌")
        assert isinstance(results, list)

    def test_capped_at_max_suggestions(self, logic):
        """結果數量不超過 MAX_SUGGESTIONS。"""
        results = logic.suggest("石")
        assert len(results) <= AliasCompleterLogic.MAX_SUGGESTIONS

    def test_exact_match_comes_first(self, logic):
        """完全匹配的項目排在最前面。"""
        results = logic.suggest("神聖石")
        assert len(results) >= 1
        assert results[0][1] == "Divine Orb"

    def test_chaos_exact_alias_first(self, logic):
        """'混沌' 完全匹配 alias → Chaos Orb 應排第一。"""
        results = logic.suggest("混沌")
        assert results[0][1] == "Chaos Orb"

    def test_priority_order(self, logic):
        """結果按 priority 升序排列（數字小 = 優先級高）。"""
        import json, pathlib
        data_file = pathlib.Path(__file__).parent.parent / "src" / "data" / "bundled_aliases_zh_tw.json"
        with data_file.open(encoding="utf-8") as f:
            db = json.load(f)
        priority_map = {item["en"]: item["priority"] for item in db["items"]}

        results = logic.suggest("石")
        priorities = [priority_map[en] for _, en in results if en in priority_map]
        assert priorities == sorted(priorities), \
            f"結果未按 priority 排序：{list(zip([en for _, en in results], priorities))}"


# ---------------------------------------------------------------------------
# 5. 空字串
# ---------------------------------------------------------------------------

class TestEmptyQuery:
    def test_empty_string(self, logic):
        assert logic.suggest("") == []

    def test_whitespace_only(self, logic):
        assert logic.suggest("   ") == []

    def test_tab_only(self, logic):
        assert logic.suggest("\t") == []

    def test_newline_only(self, logic):
        assert logic.suggest("\n") == []


# ---------------------------------------------------------------------------
# 6. 無結果
# ---------------------------------------------------------------------------

class TestNoResults:
    def test_unknown_zh(self, logic):
        assert logic.suggest("完全不存在的物品名稱") == []

    def test_unknown_english(self, logic):
        assert logic.suggest("zzz999notexist") == []

    def test_unicode_noise(self, logic):
        assert logic.suggest("☆★♦♣") == []

    def test_numbers_only(self, logic):
        assert logic.suggest("12345") == []


# ---------------------------------------------------------------------------
# format_display 靜態方法
# ---------------------------------------------------------------------------

class TestFormatDisplay:
    def test_divine_orb_format(self):
        display = AliasCompleterLogic.format_display("神聖石", "Divine Orb")
        assert display == "神聖石\n(Divine Orb)"

    def test_headhunter_format(self):
        display = AliasCompleterLogic.format_display("獵頭者", "Headhunter")
        assert display == "獵頭者\n(Headhunter)"

    def test_format_newline_separator(self):
        zh, en = "混沌石", "Chaos Orb"
        display = AliasCompleterLogic.format_display(zh, en)
        lines = display.split("\n")
        assert lines[0] == zh
        assert lines[1] == f"({en})"
