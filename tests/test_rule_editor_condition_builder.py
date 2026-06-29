"""P22.2 — RuleDetailEditor × ConditionBuilderWidget 整合測試。

測試範圍：
  1. Rule → Widget  (set_rule 後 widget 顯示正確條件列)
  2. Widget → Rule  (_build_rule_from_fields 使用 widget 條件)
  3. 新增條件       (widget._add_row → rule 包含新條件)
  4. 修改條件       (row.set_value → rule 反映變更)
  5. 刪除條件       (_on_remove_row → rule 不含已刪條件)
  6. Alias 整合     (中文輸入同步至 widget)
  7. 未支援條件保留  (HasExplicitMod 等不被遺失)
  8. 空條件         (rule.conditions=[] → 0 列)

所有測試使用 Qt offscreen 平台，不需顯示螢幕。
"""

from __future__ import annotations

import copy
import pytest

from core.models import FilterRule


# ---------------------------------------------------------------------------
# 工具函式
# ---------------------------------------------------------------------------

def _make_rule(conditions: list | None = None, actions: list | None = None) -> FilterRule:
    r = FilterRule()
    r.action     = "Show"
    r.enabled    = True
    r.conditions = list(conditions or [])
    r.actions    = list(actions    or [])
    return r


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(["-platform", "offscreen"])


@pytest.fixture
def editor(qapp):
    """每個測試取得全新的 RuleDetailEditor。"""
    from ui.rule_detail_editor import RuleDetailEditor
    e = RuleDetailEditor()
    return e


# ---------------------------------------------------------------------------
# 1. Rule → Widget
# ---------------------------------------------------------------------------

class TestRuleToWidget:

    def test_cond_builder_created(self, editor):
        """RuleDetailEditor 應成功建立 _cond_builder。"""
        assert editor._cond_builder is not None

    def test_empty_conditions_zero_rows(self, editor):
        editor.set_rule(_make_rule(conditions=[]), 0)
        assert editor._cond_builder.row_count() == 0

    def test_rarity_condition_shows_one_row(self, editor):
        editor.set_rule(_make_rule(conditions=[["Rarity", ">= Rare"]]), 0)
        assert editor._cond_builder.row_count() == 1

    def test_rarity_row_has_correct_key(self, editor):
        editor.set_rule(_make_rule(conditions=[["Rarity", ">= Rare"]]), 0)
        row = editor._cond_builder._rows[0]
        assert row._cdef.key == "Rarity"

    def test_rarity_row_value(self, editor):
        editor.set_rule(_make_rule(conditions=[["Rarity", ">= Rare"]]), 0)
        cv = editor._cond_builder._rows[0].get_value()
        assert cv.value == "Rare" and cv.op == ">="

    def test_item_level_condition(self, editor):
        editor.set_rule(_make_rule(conditions=[["ItemLevel", ">= 70"]]), 0)
        assert editor._cond_builder.row_count() == 1
        cv = editor._cond_builder._rows[0].get_value()
        assert cv.key == "ItemLevel" and cv.value == "70"

    def test_multiple_conditions(self, editor):
        conds = [["Rarity", ">= Rare"], ["ItemLevel", ">= 70"], ["Quality", ">= 15"]]
        editor.set_rule(_make_rule(conditions=conds), 0)
        assert editor._cond_builder.row_count() == 3

    def test_class_condition_shows_row(self, editor):
        editor.set_rule(_make_rule(conditions=[["Class", '"Currency"']]), 0)
        keys = [r._cdef.key for r in editor._cond_builder._rows]
        assert "Class" in keys

    def test_basetype_condition_shows_row(self, editor):
        editor.set_rule(_make_rule(conditions=[["BaseType", '"Divine Orb"']]), 0)
        keys = [r._cdef.key for r in editor._cond_builder._rows]
        assert "BaseType" in keys

    def test_class_syncs_to_text_field(self, editor):
        """Widget 載入後，Class 文字欄位也應同步顯示。"""
        editor.set_rule(_make_rule(conditions=[["Class", '"Rune"']]), 0)
        assert editor._class_edit.text() == '"Rune"'

    def test_basetype_syncs_to_text_field(self, editor):
        editor.set_rule(_make_rule(conditions=[["BaseType", '"Chaos Orb"']]), 0)
        assert editor._basetype_edit.text() == '"Chaos Orb"'

    def test_unsupported_condition_no_row(self, editor):
        """HasExplicitMod 不在 CONDITION_DEFS → widget 不顯示對應列。"""
        conds = [["HasExplicitMod", '"of the Fox"'], ["Rarity", ">= Rare"]]
        editor.set_rule(_make_rule(conditions=conds), 0)
        keys = [r._cdef.key for r in editor._cond_builder._rows]
        assert "HasExplicitMod" not in keys

    def test_set_rule_twice_resets_rows(self, editor):
        """第二次 set_rule 應清除舊列，重新載入。"""
        editor.set_rule(_make_rule(conditions=[["Rarity", ">= Rare"], ["ItemLevel", ">= 70"]]), 0)
        assert editor._cond_builder.row_count() == 2
        editor.set_rule(_make_rule(conditions=[["Quality", ">= 15"]]), 0)
        assert editor._cond_builder.row_count() == 1


# ---------------------------------------------------------------------------
# 2. Widget → Rule
# ---------------------------------------------------------------------------

class TestWidgetToRule:

    def test_rarity_in_output(self, editor):
        editor.set_rule(_make_rule(conditions=[["Rarity", ">= Rare"]]), 0)
        result = editor._build_rule_from_fields()
        keys = [item[0] for item in result.conditions]
        assert "Rarity" in keys

    def test_rarity_value_correct(self, editor):
        editor.set_rule(_make_rule(conditions=[["Rarity", ">= Rare"]]), 0)
        result = editor._build_rule_from_fields()
        rarity = next(item for item in result.conditions if item[0] == "Rarity")
        assert "Rare" in rarity[1]

    def test_item_level_in_output(self, editor):
        editor.set_rule(_make_rule(conditions=[["ItemLevel", ">= 70"]]), 0)
        result = editor._build_rule_from_fields()
        keys = [item[0] for item in result.conditions]
        assert "ItemLevel" in keys

    def test_class_in_output(self, editor):
        editor.set_rule(_make_rule(conditions=[["Class", '"Currency"']]), 0)
        result = editor._build_rule_from_fields()
        class_item = next((item for item in result.conditions if item[0] == "Class"), None)
        assert class_item is not None and '"Currency"' in class_item[1]

    def test_basetype_in_output(self, editor):
        editor.set_rule(_make_rule(conditions=[["BaseType", '"Divine Orb"']]), 0)
        result = editor._build_rule_from_fields()
        bt = next((item for item in result.conditions if item[0] == "BaseType"), None)
        assert bt is not None and '"Divine Orb"' in bt[1]

    def test_unsupported_condition_preserved(self, editor):
        """HasExplicitMod 不在 CONDITION_DEFS → save_to_rule 原樣保留。"""
        conds = [["HasExplicitMod", '"of the Fox"'], ["Rarity", ">= Rare"]]
        editor.set_rule(_make_rule(conditions=conds), 0)
        result = editor._build_rule_from_fields()
        keys = [item[0] for item in result.conditions]
        assert "HasExplicitMod" in keys

    def test_corrupted_preserved(self, editor):
        conds = [["Corrupted", "True"], ["ItemLevel", ">= 70"]]
        editor.set_rule(_make_rule(conditions=conds), 0)
        result = editor._build_rule_from_fields()
        keys = [item[0] for item in result.conditions]
        assert "Corrupted" in keys

    def test_identified_preserved(self, editor):
        conds = [["Identified", "False"], ["Rarity", ">= Rare"]]
        editor.set_rule(_make_rule(conditions=conds), 0)
        result = editor._build_rule_from_fields()
        keys = [item[0] for item in result.conditions]
        assert "Identified" in keys

    def test_empty_conditions_empty_output(self, editor):
        editor.set_rule(_make_rule(conditions=[]), 0)
        result = editor._build_rule_from_fields()
        assert result.conditions == []

    def test_actions_preserved(self, editor):
        """_build_rule_from_fields 不應影響 actions。"""
        editor.set_rule(
            _make_rule(conditions=[["Rarity", ">= Rare"]],
                       actions=[["SetFontSize", "30"]]),
            0,
        )
        result = editor._build_rule_from_fields()
        fs = next((item for item in result.actions if item[0] == "SetFontSize"), None)
        assert fs is not None


# ---------------------------------------------------------------------------
# 3. 新增條件
# ---------------------------------------------------------------------------

class TestAddCondition:

    def test_add_row_increases_count(self, editor):
        editor.set_rule(_make_rule(conditions=[]), 0)
        from core.condition_builder import ConditionValue
        editor._cond_builder._add_row(ConditionValue("ItemLevel", ">=", "70"))
        assert editor._cond_builder.row_count() == 1

    def test_added_condition_in_rule(self, editor):
        editor.set_rule(_make_rule(conditions=[]), 0)
        from core.condition_builder import ConditionValue
        editor._cond_builder._add_row(ConditionValue("ItemLevel", ">=", "70"))
        result = editor._build_rule_from_fields()
        keys = [item[0] for item in result.conditions]
        assert "ItemLevel" in keys

    def test_add_rarity_condition(self, editor):
        editor.set_rule(_make_rule(conditions=[]), 0)
        from core.condition_builder import ConditionValue
        editor._cond_builder._add_row(ConditionValue("Rarity", ">=", "Rare"))
        result = editor._build_rule_from_fields()
        rarity = next((item for item in result.conditions if item[0] == "Rarity"), None)
        assert rarity is not None and "Rare" in rarity[1]

    def test_add_multiple_conditions(self, editor):
        editor.set_rule(_make_rule(conditions=[]), 0)
        from core.condition_builder import ConditionValue
        editor._cond_builder._add_row(ConditionValue("Rarity", ">=", "Rare"))
        editor._cond_builder._add_row(ConditionValue("ItemLevel", ">=", "70"))
        result = editor._build_rule_from_fields()
        keys = [item[0] for item in result.conditions]
        assert "Rarity" in keys and "ItemLevel" in keys

    def test_add_condition_preserves_existing_unknown(self, editor):
        """新增條件後，現有的未知條件仍應保留。"""
        conds = [["HasExplicitMod", '"of the Fox"']]
        editor.set_rule(_make_rule(conditions=conds), 0)
        from core.condition_builder import ConditionValue
        editor._cond_builder._add_row(ConditionValue("Rarity", ">=", "Rare"))
        result = editor._build_rule_from_fields()
        keys = [item[0] for item in result.conditions]
        assert "HasExplicitMod" in keys
        assert "Rarity" in keys

    def test_add_condition_signal_emits(self, editor):
        """_on_condition_changed 應觸發 conditions_changed。"""
        editor.set_rule(_make_rule(conditions=[]), 0)
        received = []
        editor._cond_builder.conditions_changed.connect(received.append)
        from core.condition_builder import ConditionValue
        editor._cond_builder._add_row(ConditionValue("Rarity", ">=", "Rare"))
        editor._cond_builder._on_condition_changed()
        assert len(received) >= 1


# ---------------------------------------------------------------------------
# 4. 修改條件
# ---------------------------------------------------------------------------

class TestEditCondition:

    def test_modify_rarity_value(self, editor):
        editor.set_rule(_make_rule(conditions=[["Rarity", ">= Rare"]]), 0)
        from core.condition_builder import ConditionValue
        rarity_row = next(r for r in editor._cond_builder._rows if r._cdef.key == "Rarity")
        rarity_row.set_value(ConditionValue("Rarity", ">=", "Magic"))
        result = editor._build_rule_from_fields()
        rarity = next(item for item in result.conditions if item[0] == "Rarity")
        assert "Magic" in rarity[1]

    def test_modify_item_level(self, editor):
        editor.set_rule(_make_rule(conditions=[["ItemLevel", ">= 60"]]), 0)
        from core.condition_builder import ConditionValue
        il_row = next(r for r in editor._cond_builder._rows if r._cdef.key == "ItemLevel")
        il_row.set_value(ConditionValue("ItemLevel", ">=", "86"))
        result = editor._build_rule_from_fields()
        il = next(item for item in result.conditions if item[0] == "ItemLevel")
        assert "86" in il[1]

    def test_modify_class(self, editor):
        editor.set_rule(_make_rule(conditions=[["Class", '"Currency"']]), 0)
        from core.condition_builder import ConditionValue
        class_row = next(r for r in editor._cond_builder._rows if r._cdef.key == "Class")
        class_row.set_value(ConditionValue("Class", "", '"Rune"'))
        result = editor._build_rule_from_fields()
        class_item = next(item for item in result.conditions if item[0] == "Class")
        assert '"Rune"' in class_item[1]

    def test_modify_does_not_affect_other_conditions(self, editor):
        conds = [["Rarity", ">= Rare"], ["ItemLevel", ">= 70"]]
        editor.set_rule(_make_rule(conditions=conds), 0)
        from core.condition_builder import ConditionValue
        rarity_row = next(r for r in editor._cond_builder._rows if r._cdef.key == "Rarity")
        rarity_row.set_value(ConditionValue("Rarity", ">=", "Magic"))
        result = editor._build_rule_from_fields()
        il = next((item for item in result.conditions if item[0] == "ItemLevel"), None)
        assert il is not None and "70" in il[1]

    def test_update_condition_syncs_basetype_text_field(self, editor):
        """update_condition 更新 BaseType 後，後續 get_conditions 應反映。"""
        editor.set_rule(_make_rule(conditions=[["BaseType", '"Divine Orb"']]), 0)
        from core.condition_builder import ConditionValue
        editor._cond_builder.update_condition(
            ConditionValue("BaseType", "", '"Chaos Orb"')
        )
        result = editor._build_rule_from_fields()
        bt = next((item for item in result.conditions if item[0] == "BaseType"), None)
        assert bt is not None and '"Chaos Orb"' in bt[1]


# ---------------------------------------------------------------------------
# 5. 刪除條件
# ---------------------------------------------------------------------------

class TestDeleteCondition:

    def test_remove_rarity_row(self, editor):
        editor.set_rule(_make_rule(conditions=[["Rarity", ">= Rare"]]), 0)
        rarity_row = next(r for r in editor._cond_builder._rows if r._cdef.key == "Rarity")
        editor._cond_builder._on_remove_row(rarity_row)
        assert editor._cond_builder.row_count() == 0

    def test_remove_rarity_not_in_rule(self, editor):
        editor.set_rule(_make_rule(conditions=[["Rarity", ">= Rare"]]), 0)
        rarity_row = next(r for r in editor._cond_builder._rows if r._cdef.key == "Rarity")
        editor._cond_builder._on_remove_row(rarity_row)
        result = editor._build_rule_from_fields()
        keys = [item[0] for item in result.conditions]
        assert "Rarity" not in keys

    def test_remove_one_leaves_others(self, editor):
        conds = [["Rarity", ">= Rare"], ["ItemLevel", ">= 70"]]
        editor.set_rule(_make_rule(conditions=conds), 0)
        rarity_row = next(r for r in editor._cond_builder._rows if r._cdef.key == "Rarity")
        editor._cond_builder._on_remove_row(rarity_row)
        result = editor._build_rule_from_fields()
        keys = [item[0] for item in result.conditions]
        assert "Rarity" not in keys
        assert "ItemLevel" in keys

    def test_remove_preserves_unknown(self, editor):
        """刪除已知條件後，未知條件仍應保留。"""
        conds = [["HasExplicitMod", '"of the Fox"'], ["Rarity", ">= Rare"]]
        editor.set_rule(_make_rule(conditions=conds), 0)
        rarity_row = next(r for r in editor._cond_builder._rows if r._cdef.key == "Rarity")
        editor._cond_builder._on_remove_row(rarity_row)
        result = editor._build_rule_from_fields()
        keys = [item[0] for item in result.conditions]
        assert "HasExplicitMod" in keys
        assert "Rarity" not in keys

    def test_row_count_after_remove(self, editor):
        conds = [["Rarity", ">= Rare"], ["ItemLevel", ">= 70"], ["Quality", ">= 15"]]
        editor.set_rule(_make_rule(conditions=conds), 0)
        assert editor._cond_builder.row_count() == 3
        row = editor._cond_builder._rows[0]
        editor._cond_builder._on_remove_row(row)
        assert editor._cond_builder.row_count() == 2


# ---------------------------------------------------------------------------
# 6. Alias 整合
# ---------------------------------------------------------------------------

class TestAliasIntegration:

    def test_alias_svc_available(self, editor):
        assert editor._alias_svc is not None

    def test_resolve_basetype_syncs_to_widget(self, editor):
        """_resolve_basetype_alias 解析中文後應同步至 ConditionBuilderWidget。"""
        editor.set_rule(_make_rule(conditions=[]), 0)
        editor._basetype_edit.setText("神聖石")
        editor._resolve_basetype_alias()
        # 文字欄位應已解析
        assert editor._basetype_edit.text() == '"Divine Orb"'
        # widget 應有 BaseType 列
        result = editor._build_rule_from_fields()
        bt = next((item for item in result.conditions if item[0] == "BaseType"), None)
        assert bt is not None and '"Divine Orb"' in bt[1]

    def test_resolve_class_syncs_to_widget(self, editor):
        """_resolve_class_alias 解析中文後應同步至 ConditionBuilderWidget。"""
        editor.set_rule(_make_rule(conditions=[]), 0)
        editor._class_edit.setText("符文")
        editor._resolve_class_alias()
        assert editor._class_edit.text() == '"Rune"'
        result = editor._build_rule_from_fields()
        class_item = next((item for item in result.conditions if item[0] == "Class"), None)
        assert class_item is not None and '"Rune"' in class_item[1]

    def test_update_condition_adds_basetype_row(self, editor):
        """update_condition 對不存在的 key → 新增列。"""
        editor.set_rule(_make_rule(conditions=[]), 0)
        from core.condition_builder import ConditionValue
        editor._cond_builder.update_condition(
            ConditionValue("BaseType", "", '"Chaos Orb"')
        )
        keys = [r._cdef.key for r in editor._cond_builder._rows]
        assert "BaseType" in keys

    def test_update_condition_updates_existing_row(self, editor):
        """update_condition 對已存在的 key → 更新值。"""
        editor.set_rule(_make_rule(conditions=[["BaseType", '"Divine Orb"']]), 0)
        from core.condition_builder import ConditionValue
        editor._cond_builder.update_condition(
            ConditionValue("BaseType", "", '"Chaos Orb"')
        )
        bt_row = next(r for r in editor._cond_builder._rows if r._cdef.key == "BaseType")
        assert '"Chaos Orb"' in bt_row.get_value().value

    def test_widget_to_text_field_sync_class(self, editor):
        """Widget 條件改變 → _on_cond_builder_changed → Class 文字欄位同步。"""
        editor.set_rule(_make_rule(conditions=[["Class", '"Currency"']]), 0)
        editor._on_cond_builder_changed([["Class", '"Rune"']])
        assert editor._class_edit.text() == '"Rune"'

    def test_widget_to_text_field_sync_basetype(self, editor):
        editor.set_rule(_make_rule(conditions=[["BaseType", '"Divine Orb"']]), 0)
        editor._on_cond_builder_changed([["BaseType", '"Chaos Orb"']])
        assert editor._basetype_edit.text() == '"Chaos Orb"'


# ---------------------------------------------------------------------------
# 7. 未支援條件保留
# ---------------------------------------------------------------------------

class TestUnsupportedConditionPreservation:

    UNKNOWN_CONDS = [
        ["HasExplicitMod",  '"of the Fox"'],
        ["HasImplicitMod",  '"of Regrowth"'],
        ["Corrupted",       "True"],
        ["Identified",      "False"],
        ["HasInfluence",    "Shaper Elder"],
        ["GemLevel",        ">= 20"],
    ]

    @pytest.mark.parametrize("cond", UNKNOWN_CONDS)
    def test_unknown_condition_preserved(self, editor, cond):
        """任何未知條件應在 _build_rule_from_fields 後保留。"""
        editor.set_rule(_make_rule(conditions=[cond]), 0)
        result = editor._build_rule_from_fields()
        keys = [item[0] for item in result.conditions]
        assert cond[0] in keys, f"{cond[0]} 應被保留但遺失了"

    def test_multiple_unknown_all_preserved(self, editor):
        """多個未知條件全部應被保留。"""
        conds = [["HasExplicitMod", '"of the Fox"'], ["Corrupted", "True"],
                 ["Rarity", ">= Rare"]]
        editor.set_rule(_make_rule(conditions=conds), 0)
        result = editor._build_rule_from_fields()
        keys = [item[0] for item in result.conditions]
        assert "HasExplicitMod" in keys
        assert "Corrupted" in keys

    def test_unknown_value_unchanged(self, editor):
        """未知條件的值應原樣保留。"""
        editor.set_rule(
            _make_rule(conditions=[["HasExplicitMod", '"of the Fox"']]), 0
        )
        result = editor._build_rule_from_fields()
        mod = next(item for item in result.conditions if item[0] == "HasExplicitMod")
        assert mod[1] == '"of the Fox"'


# ---------------------------------------------------------------------------
# 8. 空條件 / 邊界
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_rule_no_crash(self, editor):
        editor.set_rule(_make_rule(conditions=[]), 0)
        result = editor._build_rule_from_fields()
        assert result.conditions == []

    def test_no_conditions_emitted_on_load(self, editor):
        """set_rule 期間不得觸發 rule_changed。"""
        received = []
        editor.rule_changed.connect(lambda idx, r: received.append(r))
        editor.set_rule(_make_rule(conditions=[["Rarity", ">= Rare"]]), 0)
        assert len(received) == 0

    def test_on_cond_builder_changed_before_set_rule(self, editor):
        """未載入 rule 時，_on_cond_builder_changed 不應拋例外。"""
        try:
            editor._on_cond_builder_changed([["Rarity", ">= Rare"]])
        except Exception as e:
            pytest.fail(f"未載入 rule 時不應拋例外：{e}")

    def test_invalid_condition_value_no_crash(self, editor):
        """不合法的條件值在 set_rule / build 時不應造成閃退。"""
        try:
            editor.set_rule(
                _make_rule(conditions=[["ItemLevel", "abc"], ["Rarity", ""]]), 0
            )
            editor._build_rule_from_fields()
        except Exception as e:
            pytest.fail(f"不合法條件值不應拋例外：{e}")

    def test_update_condition_empty_no_add(self, editor):
        """update_condition(空值, 不存在的 key) → 不應新增列。"""
        editor.set_rule(_make_rule(conditions=[]), 0)
        from core.condition_builder import ConditionValue
        before = editor._cond_builder.row_count()
        editor._cond_builder.update_condition(ConditionValue("ItemLevel", ">=", ""))
        assert editor._cond_builder.row_count() == before

    def test_rule_action_preserved_through_condition_edit(self, editor):
        """條件編輯不應影響 rule.action。"""
        editor.set_rule(_make_rule(conditions=[["Rarity", ">= Rare"]]), 0)
        result = editor._build_rule_from_fields()
        assert result.action == "Show"
