"""P21.5 — RuleEditorAliasService 整合測試。

純 Python 測試（無 Qt 依賴）。

覆蓋範圍：
  1. 中文 BaseType 解析
  2. 英文 BaseType 保留
  3. 中文 Class 解析
  4. 英文 Class 保留
  5. 補全整合（completer 輸出格式）
  6. 無效輸入容錯
  7. 反向顯示 Tooltip
"""

import pytest

from core.alias_resolver import AliasResolver
from core.rule_editor_alias import RuleEditorAliasService


@pytest.fixture(scope="module")
def svc() -> RuleEditorAliasService:
    return RuleEditorAliasService()


# ---------------------------------------------------------------------------
# 1. 中文 BaseType 解析
# ---------------------------------------------------------------------------

class TestBaseTypeResolution:
    def test_zh_single_divine_orb(self, svc):
        """單一中文名稱：神聖石 → "Divine Orb"。"""
        result = svc.resolve_filter_value("神聖石", "BaseType")
        assert result == '"Divine Orb"'

    def test_zh_single_chaos_orb(self, svc):
        """單一中文名稱：混沌石 → "Chaos Orb"。"""
        result = svc.resolve_filter_value("混沌石", "BaseType")
        assert result == '"Chaos Orb"'

    def test_zh_alias_match(self, svc):
        """中文別名：混沌 → Chaos Orb。"""
        result = svc.resolve_filter_value("混沌", "BaseType")
        assert result == '"Chaos Orb"'

    def test_zh_two_items(self, svc):
        """兩個中文名稱空格分隔。"""
        result = svc.resolve_filter_value("神聖石 混沌石", "BaseType")
        assert result == '"Divine Orb" "Chaos Orb"'

    def test_zh_alias_div(self, svc):
        """英文縮寫 div → Divine Orb。"""
        result = svc.resolve_filter_value("div", "BaseType")
        assert result == '"Divine Orb"'

    def test_zh_vaal_orb(self, svc):
        """瓦爾石（Vaal Orb 的中文名）→ "Vaal Orb"。"""
        result = svc.resolve_filter_value("瓦爾石", "BaseType")
        assert result == '"Vaal Orb"'

    def test_result_has_quotes(self, svc):
        """解析結果必須帶引號。"""
        result = svc.resolve_filter_value("神聖石", "BaseType")
        assert result.startswith('"') and result.endswith('"')

    def test_resolve_returns_string(self, svc):
        assert isinstance(svc.resolve_filter_value("混沌石", "BaseType"), str)


# ---------------------------------------------------------------------------
# 2. 英文 BaseType 保留
# ---------------------------------------------------------------------------

class TestBaseTypeEnglish:
    def test_quoted_english_preserved(self, svc):
        """已帶引號的英文值應保留。"""
        result = svc.resolve_filter_value('"Divine Orb"', "BaseType")
        assert result == '"Divine Orb"'

    def test_quoted_two_items_preserved(self, svc):
        """雙項英文值應保留格式。"""
        result = svc.resolve_filter_value('"Divine Orb" "Chaos Orb"', "BaseType")
        assert result == '"Divine Orb" "Chaos Orb"'

    def test_unquoted_english_untouched(self, svc):
        """無引號英文（如來自補全器）：不含中文時原樣回傳。"""
        result = svc.resolve_filter_value("Chaos Orb", "BaseType")
        assert result == "Chaos Orb"

    def test_empty_string_preserved(self, svc):
        assert svc.resolve_filter_value("", "BaseType") == ""

    def test_whitespace_preserved(self, svc):
        assert svc.resolve_filter_value("   ", "BaseType") == "   "


# ---------------------------------------------------------------------------
# 3. 中文 Class 解析
# ---------------------------------------------------------------------------

class TestClassResolution:
    def test_zh_currency_class(self, svc):
        """通貨 → "Stackable Currency" "Currency"。"""
        result = svc.resolve_filter_value("通貨", "Class")
        assert '"Stackable Currency"' in result
        assert '"Currency"' in result

    def test_zh_rune_class(self, svc):
        """符文 → "Rune"。"""
        result = svc.resolve_filter_value("符文", "Class")
        assert result == '"Rune"'

    def test_zh_helmet_class(self, svc):
        """頭盔 → "Helmet"。"""
        result = svc.resolve_filter_value("頭盔", "Class")
        assert result == '"Helmet"'

    def test_zh_waystone_class(self, svc):
        """傳送石 → "Waystone"。"""
        result = svc.resolve_filter_value("傳送石", "Class")
        assert result == '"Waystone"'

    def test_zh_flask_class(self, svc):
        """藥劑 → 包含 Flask class。"""
        result = svc.resolve_filter_value("藥劑", "Class")
        assert "Flask" in result

    def test_zh_gem_class(self, svc):
        """技能寶石 → 包含 Skill Gem。"""
        result = svc.resolve_filter_value("技能寶石", "Class")
        assert '"Skill Gem"' in result

    def test_zh_short_rune(self, svc):
        """zh_short '符文' 與 zh 相同，仍應解析。"""
        result = svc.resolve_filter_value("符文", "Class")
        assert result == '"Rune"'

    def test_class_result_has_quotes(self, svc):
        """Class 解析結果必須帶引號。"""
        result = svc.resolve_filter_value("符文", "Class")
        assert '"' in result


# ---------------------------------------------------------------------------
# 4. 英文 Class 保留
# ---------------------------------------------------------------------------

class TestClassEnglish:
    def test_quoted_english_class_preserved(self, svc):
        result = svc.resolve_filter_value('"Rune"', "Class")
        assert result == '"Rune"'

    def test_quoted_two_classes_preserved(self, svc):
        result = svc.resolve_filter_value('"Stackable Currency" "Currency"', "Class")
        assert result == '"Stackable Currency" "Currency"'

    def test_unquoted_english_class_untouched(self, svc):
        """無引號英文 Class：無中文時原樣回傳。"""
        result = svc.resolve_filter_value("Rune", "Class")
        assert result == "Rune"


# ---------------------------------------------------------------------------
# 5. 補全整合（completer 輸出格式化）
# ---------------------------------------------------------------------------

class TestCompleterIntegration:
    def test_basetype_token_divine_orb(self, svc):
        """resolve_basetype_token 回傳英文名稱。"""
        result = svc.resolve_basetype_token("神聖石")
        assert result == "Divine Orb"

    def test_basetype_token_english_passthrough(self, svc):
        """已知英文名稱，token 原樣回傳。"""
        result = svc.resolve_basetype_token("Divine Orb")
        assert result == "Divine Orb"

    def test_class_token_rune(self, svc):
        """resolve_class_token 回傳 en_class 清單。"""
        result = svc.resolve_class_token("符文")
        assert result == ["Rune"]

    def test_class_token_currency_multi(self, svc):
        """通貨 resolve 回傳多個 class。"""
        result = svc.resolve_class_token("通貨")
        assert "Stackable Currency" in result
        assert "Currency" in result

    def test_class_token_unknown_passthrough(self, svc):
        """未知 token 原樣回傳。"""
        result = svc.resolve_class_token("UnknownClass")
        assert result == ["UnknownClass"]

    def test_basetype_token_unknown_passthrough(self, svc):
        """未知 token 原樣回傳。"""
        result = svc.resolve_basetype_token("完全未知物品")
        assert result == "完全未知物品"


# ---------------------------------------------------------------------------
# 6. 無效輸入容錯
# ---------------------------------------------------------------------------

class TestInvalidInput:
    def test_empty_basetype(self, svc):
        assert svc.resolve_filter_value("", "BaseType") == ""

    def test_empty_class(self, svc):
        assert svc.resolve_filter_value("", "Class") == ""

    def test_whitespace_basetype(self, svc):
        result = svc.resolve_filter_value("   ", "BaseType")
        assert result == "   "

    def test_unknown_field_type(self, svc):
        """未知 field_type 應原樣回傳，不拋例外。"""
        result = svc.resolve_filter_value("神聖石", "UnknownField")
        assert result == "神聖石"

    def test_unmatched_quote_no_exception(self, svc):
        """引號不匹配的輸入不拋例外。"""
        try:
            result = svc.resolve_filter_value('"Divine Orb', "BaseType")
        except Exception as e:
            pytest.fail(f"應不拋例外，但收到：{e}")

    def test_no_exception_on_none_like_input(self, svc):
        """各種邊界輸入不拋例外。"""
        for val in ("", " ", "\t", "\n", "???", "🔥"):
            try:
                svc.resolve_filter_value(val, "BaseType")
                svc.resolve_filter_value(val, "Class")
            except Exception as e:
                pytest.fail(f"輸入 {val!r} 不應拋例外，但收到：{e}")

    def test_none_tooltip_on_empty(self, svc):
        """空白輸入 tooltip 應回傳 None。"""
        assert svc.tooltip_basetype("") is None
        assert svc.tooltip_class("") is None


# ---------------------------------------------------------------------------
# 7. 反向顯示 Tooltip
# ---------------------------------------------------------------------------

class TestReverseDisplay:
    def test_basetype_tooltip_divine_orb(self, svc):
        """tooltip_basetype 含英文名與中文名。"""
        tt = svc.tooltip_basetype('"Divine Orb"')
        assert tt is not None
        assert "Divine Orb" in tt
        assert "神聖石" in tt

    def test_basetype_tooltip_format(self, svc):
        """tooltip 格式：英文名\\n(中文名)。"""
        tt = svc.tooltip_basetype('"Chaos Orb"')
        assert tt is not None
        assert "Chaos Orb" in tt
        assert "(混沌石)" in tt

    def test_basetype_tooltip_two_items(self, svc):
        """兩個物品 tooltip 應包含兩者。"""
        tt = svc.tooltip_basetype('"Divine Orb" "Chaos Orb"')
        assert tt is not None
        assert "Divine Orb" in tt
        assert "Chaos Orb" in tt
        assert "神聖石" in tt
        assert "混沌石" in tt

    def test_class_tooltip_rune(self, svc):
        """tooltip_class 含英文分類名與中文名。"""
        tt = svc.tooltip_class('"Rune"')
        assert tt is not None
        assert "Rune" in tt
        assert "符文" in tt

    def test_class_tooltip_stackable_currency(self, svc):
        """tooltip_class 通貨 class。"""
        tt = svc.tooltip_class('"Stackable Currency"')
        assert tt is not None
        assert "Stackable Currency" in tt
        assert "通貨" in tt

    def test_basetype_tooltip_unknown_no_exception(self, svc):
        """未知英文名：tooltip 仍回傳字串（可能只有英文名），不拋例外。"""
        try:
            result = svc.tooltip_basetype('"UnknownItem"')
        except Exception as e:
            pytest.fail(f"不應拋例外：{e}")
        assert result is None or isinstance(result, str)

    def test_tooltip_returns_none_for_blank(self, svc):
        assert svc.tooltip_basetype("   ") is None
        assert svc.tooltip_class("   ") is None
