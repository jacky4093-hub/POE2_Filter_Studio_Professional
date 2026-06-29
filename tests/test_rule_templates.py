"""P24.1 — RuleTemplate 系統測試。

涵蓋：
  1. get_templates()           — 清單、副本隔離、資料完整性
  2. get_template()            — 有效 / 無效 id、副本隔離
  3. 各內建模板內容             — currency / unique / rare / waystone / gem / empty
  4. create_rule_from_template  — FilterRule 格式、條件 / 動作串接、獨立副本

純 Python，不依賴 Qt。
"""

from __future__ import annotations

import pytest

from core.models import FilterRule
from core.rule_templates import (
    RuleTemplate,
    create_rule_from_template,
    get_template,
    get_templates,
)


# ---------------------------------------------------------------------------
# 1. get_templates()
# ---------------------------------------------------------------------------

class TestGetTemplates:

    def test_returns_list(self):
        assert isinstance(get_templates(), list)

    def test_minimum_count(self):
        assert len(get_templates()) >= 6

    def test_contains_all_required_ids(self):
        ids = {t.id for t in get_templates()}
        required = {
            "high_value_currency", "unique_item", "rare_equipment",
            "high_tier_waystone", "high_quality_gem", "empty_rule",
        }
        assert required <= ids

    def test_returns_new_list_each_call(self):
        assert get_templates() is not get_templates()

    def test_mutation_does_not_affect_next_call(self):
        a = get_templates()
        original_len = len(get_templates())
        a.append(None)  # 修改回傳的清單
        assert len(get_templates()) == original_len

    def test_template_conditions_mutation_isolated(self):
        """修改回傳模板的 conditions 不影響下次呼叫。"""
        tmpl = next(t for t in get_templates() if t.id == "high_tier_waystone")
        tmpl.conditions.append(["ExtraKey", "999"])
        fresh = get_template("high_tier_waystone")
        assert not any(c[0] == "ExtraKey" for c in fresh.conditions)

    def test_all_have_id(self):
        for tmpl in get_templates():
            assert tmpl.id

    def test_all_have_name(self):
        for tmpl in get_templates():
            assert tmpl.name

    def test_all_have_description(self):
        for tmpl in get_templates():
            assert tmpl.description

    def test_ids_unique(self):
        ids = [t.id for t in get_templates()]
        assert len(ids) == len(set(ids))

    def test_items_are_rule_template(self):
        for tmpl in get_templates():
            assert isinstance(tmpl, RuleTemplate)


# ---------------------------------------------------------------------------
# 2. get_template()
# ---------------------------------------------------------------------------

class TestGetTemplate:

    def test_valid_id_returns_template(self):
        tmpl = get_template("empty_rule")
        assert tmpl is not None
        assert isinstance(tmpl, RuleTemplate)

    def test_invalid_id_returns_none(self):
        assert get_template("nonexistent_id_xyz_abc") is None

    def test_empty_string_returns_none(self):
        assert get_template("") is None

    def test_returns_independent_copy(self):
        a = get_template("high_value_currency")
        b = get_template("high_value_currency")
        assert a is not b

    def test_all_template_ids_accessible(self):
        for tmpl in get_templates():
            result = get_template(tmpl.id)
            assert result is not None
            assert result.id == tmpl.id


# ---------------------------------------------------------------------------
# 3-A. high_value_currency
# ---------------------------------------------------------------------------

class TestCurrencyTemplate:

    def test_exists(self):
        assert get_template("high_value_currency") is not None

    def test_name_contains_currency(self):
        assert "貨幣" in get_template("high_value_currency").name

    def test_rule_class_is_currency(self):
        assert get_template("high_value_currency").rule_class == "Currency"

    def test_font_size_is_45(self):
        assert get_template("high_value_currency").font_size == 45

    def test_has_border_color(self):
        assert get_template("high_value_currency").border_color is not None

    def test_border_color_is_string(self):
        color = get_template("high_value_currency").border_color
        assert isinstance(color, str) and len(color) > 0


# ---------------------------------------------------------------------------
# 3-B. unique_item
# ---------------------------------------------------------------------------

class TestUniqueTemplate:

    def test_exists(self):
        assert get_template("unique_item") is not None

    def test_name_contains_unique_keyword(self):
        assert "傳奇" in get_template("unique_item").name

    def test_has_rarity_condition(self):
        conds = get_template("unique_item").conditions
        assert any(c[0] == "Rarity" for c in conds)

    def test_rarity_value_contains_unique(self):
        conds = get_template("unique_item").conditions
        rarity_val = next((c[1] for c in conds if c[0] == "Rarity"), None)
        assert rarity_val is not None and "Unique" in rarity_val

    def test_font_size_is_42(self):
        assert get_template("unique_item").font_size == 42

    def test_no_rule_class(self):
        assert get_template("unique_item").rule_class is None


# ---------------------------------------------------------------------------
# 3-C. rare_equipment
# ---------------------------------------------------------------------------

class TestRareTemplate:

    def test_exists(self):
        assert get_template("rare_equipment") is not None

    def test_name_contains_rare_keyword(self):
        assert "稀有" in get_template("rare_equipment").name

    def test_has_rarity_condition(self):
        conds = get_template("rare_equipment").conditions
        assert any(c[0] == "Rarity" for c in conds)

    def test_rarity_value_contains_rare(self):
        conds = get_template("rare_equipment").conditions
        rarity_val = next((c[1] for c in conds if c[0] == "Rarity"), None)
        assert rarity_val is not None and "Rare" in rarity_val

    def test_no_rule_class(self):
        assert get_template("rare_equipment").rule_class is None


# ---------------------------------------------------------------------------
# 3-D. high_tier_waystone
# ---------------------------------------------------------------------------

class TestWaystoneTemplate:

    def test_exists(self):
        assert get_template("high_tier_waystone") is not None

    def test_name_contains_map_keyword(self):
        name = get_template("high_tier_waystone").name
        assert "地圖" in name or "Waystone" in name

    def test_rule_class_is_waystones(self):
        assert get_template("high_tier_waystone").rule_class == "Waystones"

    def test_has_arealevel_condition(self):
        conds = get_template("high_tier_waystone").conditions
        assert any(c[0] == "AreaLevel" for c in conds)

    def test_arealevel_value_contains_75(self):
        conds = get_template("high_tier_waystone").conditions
        al_val = next((c[1] for c in conds if c[0] == "AreaLevel"), None)
        assert al_val is not None and "75" in al_val


# ---------------------------------------------------------------------------
# 3-E. high_quality_gem
# ---------------------------------------------------------------------------

class TestGemTemplate:

    def test_exists(self):
        assert get_template("high_quality_gem") is not None

    def test_name_contains_gem_keyword(self):
        name = get_template("high_quality_gem").name
        assert "品質" in name or "技能石" in name

    def test_has_quality_condition(self):
        conds = get_template("high_quality_gem").conditions
        assert any(c[0] == "Quality" for c in conds)

    def test_quality_value_contains_20(self):
        conds = get_template("high_quality_gem").conditions
        q_val = next((c[1] for c in conds if c[0] == "Quality"), None)
        assert q_val is not None and "20" in q_val

    def test_no_rule_class(self):
        assert get_template("high_quality_gem").rule_class is None


# ---------------------------------------------------------------------------
# 3-F. empty_rule
# ---------------------------------------------------------------------------

class TestEmptyTemplate:

    def test_exists(self):
        assert get_template("empty_rule") is not None

    def test_name_indicates_empty(self):
        name = get_template("empty_rule").name
        assert "空" in name or "empty" in name.lower()

    def test_no_conditions(self):
        assert get_template("empty_rule").conditions == []

    def test_no_rule_class(self):
        assert get_template("empty_rule").rule_class is None

    def test_no_text_color(self):
        assert get_template("empty_rule").text_color is None

    def test_no_background_color(self):
        assert get_template("empty_rule").background_color is None

    def test_no_border_color(self):
        assert get_template("empty_rule").border_color is None

    def test_no_font_size(self):
        assert get_template("empty_rule").font_size is None

    def test_no_play_alert_sound(self):
        assert not get_template("empty_rule").play_alert_sound


# ---------------------------------------------------------------------------
# 4. create_rule_from_template()
# ---------------------------------------------------------------------------

class TestCreateRuleFromTemplate:

    # 基本結構

    def test_returns_filter_rule(self):
        rule = create_rule_from_template("empty_rule")
        assert isinstance(rule, FilterRule)

    def test_invalid_id_returns_none(self):
        assert create_rule_from_template("nonexistent_xyz_abc") is None

    def test_action_is_show(self):
        assert create_rule_from_template("empty_rule").action == "Show"

    def test_enabled_is_true(self):
        assert create_rule_from_template("empty_rule").enabled is True

    def test_empty_template_no_conditions(self):
        assert create_rule_from_template("empty_rule").conditions == []

    def test_empty_template_no_actions(self):
        assert create_rule_from_template("empty_rule").actions == []

    # high_value_currency

    def test_currency_has_class_condition(self):
        keys = [c[0] for c in create_rule_from_template("high_value_currency").conditions]
        assert "Class" in keys

    def test_currency_class_value_contains_currency(self):
        conds = create_rule_from_template("high_value_currency").conditions
        cls_val = next((c[1] for c in conds if c[0] == "Class"), None)
        assert cls_val is not None and "Currency" in cls_val

    def test_currency_class_value_is_quoted(self):
        conds = create_rule_from_template("high_value_currency").conditions
        cls_val = next((c[1] for c in conds if c[0] == "Class"), None)
        assert cls_val is not None and cls_val.startswith('"') and cls_val.endswith('"')

    def test_currency_has_setfontsize_action(self):
        keys = [a[0] for a in create_rule_from_template("high_value_currency").actions]
        assert "SetFontSize" in keys

    def test_currency_font_size_value(self):
        acts = create_rule_from_template("high_value_currency").actions
        fs = next((a[1] for a in acts if a[0] == "SetFontSize"), None)
        assert fs == "45"

    def test_currency_has_setbordercolor_action(self):
        keys = [a[0] for a in create_rule_from_template("high_value_currency").actions]
        assert "SetBorderColor" in keys

    # unique_item

    def test_unique_has_rarity_condition(self):
        keys = [c[0] for c in create_rule_from_template("unique_item").conditions]
        assert "Rarity" in keys

    def test_unique_rarity_value(self):
        conds = create_rule_from_template("unique_item").conditions
        rarity = next((c[1] for c in conds if c[0] == "Rarity"), None)
        assert rarity is not None and "Unique" in rarity

    def test_unique_has_font_size_action(self):
        keys = [a[0] for a in create_rule_from_template("unique_item").actions]
        assert "SetFontSize" in keys

    # high_tier_waystone

    def test_waystone_has_class_and_arealevel(self):
        conds = create_rule_from_template("high_tier_waystone").conditions
        cond_keys = [c[0] for c in conds]
        assert "Class" in cond_keys
        assert "AreaLevel" in cond_keys

    def test_waystone_class_is_first(self):
        conds = create_rule_from_template("high_tier_waystone").conditions
        assert conds[0][0] == "Class"

    def test_waystone_class_value_contains_waystones(self):
        conds = create_rule_from_template("high_tier_waystone").conditions
        cls_val = next((c[1] for c in conds if c[0] == "Class"), None)
        assert cls_val is not None and "Waystones" in cls_val

    # 獨立副本

    def test_multiple_calls_return_independent_rules(self):
        rule1 = create_rule_from_template("high_value_currency")
        rule2 = create_rule_from_template("high_value_currency")
        rule1.conditions.append(["ExtraKey", "999"])
        assert not any(c[0] == "ExtraKey" for c in rule2.conditions)

    def test_condition_mutation_does_not_affect_template(self):
        rule = create_rule_from_template("high_tier_waystone")
        rule.conditions[0][1] = "MUTATED"
        fresh = create_rule_from_template("high_tier_waystone")
        assert fresh.conditions[0][1] != "MUTATED"
