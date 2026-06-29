"""P22 — ConditionBuilderService 與 ConditionBuilderWidget 測試。

純 Python 部分（TestConditionDef、TestParseRaw、TestSerialize、TestValidate、
TestLoadFromRule、TestSaveToRule、TestClassBaseTypeAlias）不需要 Qt。

Qt Widget 部分（TestConditionBuilderWidget）使用 offscreen 平台。

涵蓋需求：
  * Rarity 條件
  * 數值條件 >= <= =
  * Class / BaseType 中文輸入解析（透過 P21 RuleEditorAliasService）
  * 新增條件
  * 移除條件
  * 修改條件
  * 無效值處理
  * 與既有 rule 資料結構相容
"""

from __future__ import annotations

import pytest

from core.condition_builder import (
    ConditionBuilderService, ConditionDef, ConditionValue, FieldType,
)


# ---------------------------------------------------------------------------
# 共用 Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def svc() -> ConditionBuilderService:
    return ConditionBuilderService()


@pytest.fixture(scope="module")
def alias_svc():
    from core.rule_editor_alias import RuleEditorAliasService
    return RuleEditorAliasService()


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(["-platform", "offscreen"])


# ---------------------------------------------------------------------------
# 1. ConditionDef — 靜態定義完整性
# ---------------------------------------------------------------------------

class TestConditionDef:
    def test_all_p22_conditions_defined(self, svc):
        required = {
            "Rarity", "ItemLevel", "AreaLevel", "Quality",
            "Sockets", "LinkedSockets", "StackSize", "Class", "BaseType",
        }
        assert required.issubset(set(svc.available_keys()))

    def test_rarity_is_enum(self, svc):
        assert svc.get_def("Rarity").field_type == FieldType.ENUM

    def test_item_level_is_numeric(self, svc):
        assert svc.get_def("ItemLevel").field_type == FieldType.NUMERIC

    def test_class_is_string(self, svc):
        assert svc.get_def("Class").field_type == FieldType.STRING

    def test_basetype_is_string(self, svc):
        assert svc.get_def("BaseType").field_type == FieldType.STRING

    def test_rarity_choices_correct(self, svc):
        cdef = svc.get_def("Rarity")
        assert set(cdef.choices) == {"Normal", "Magic", "Rare", "Unique"}

    def test_item_level_range(self, svc):
        cdef = svc.get_def("ItemLevel")
        assert cdef.min_val == 0 and cdef.max_val == 100

    def test_sockets_range(self, svc):
        cdef = svc.get_def("Sockets")
        assert cdef.max_val == 6

    def test_stack_size_range(self, svc):
        cdef = svc.get_def("StackSize")
        assert cdef.max_val == 5000

    def test_get_def_unknown_returns_none(self, svc):
        assert svc.get_def("HasExplicitMod") is None


# ---------------------------------------------------------------------------
# 2. parse_raw — 解析
# ---------------------------------------------------------------------------

class TestParseRaw:
    def test_rarity_gte_rare(self, svc):
        cv = svc.parse_raw("Rarity", ">= Rare")
        assert cv.op == ">=" and cv.value == "Rare"

    def test_rarity_no_op(self, svc):
        """無 op 前綴 → 使用 default_op。"""
        cv = svc.parse_raw("Rarity", "Rare")
        assert cv.value == "Rare"

    def test_rarity_lte(self, svc):
        cv = svc.parse_raw("Rarity", "<= Magic")
        assert cv.op == "<=" and cv.value == "Magic"

    def test_item_level_gte(self, svc):
        cv = svc.parse_raw("ItemLevel", ">= 70")
        assert cv.op == ">=" and cv.value == "70"

    def test_item_level_eq(self, svc):
        cv = svc.parse_raw("ItemLevel", "= 86")
        assert cv.op == "=" and cv.value == "86"

    def test_item_level_lte(self, svc):
        cv = svc.parse_raw("ItemLevel", "<= 60")
        assert cv.op == "<=" and cv.value == "60"

    def test_quality_gte(self, svc):
        cv = svc.parse_raw("Quality", ">= 15")
        assert cv.op == ">=" and cv.value == "15"

    def test_class_string(self, svc):
        cv = svc.parse_raw("Class", '"Currency" "Gems"')
        assert cv.value == '"Currency" "Gems"'
        assert cv.op == ""

    def test_basetype_string(self, svc):
        cv = svc.parse_raw("BaseType", '"Divine Orb"')
        assert cv.value == '"Divine Orb"' and cv.op == ""

    def test_empty_value(self, svc):
        cv = svc.parse_raw("ItemLevel", "")
        assert cv.is_empty()

    def test_key_not_in_defs(self, svc):
        cv = svc.parse_raw("HasExplicitMod", '"of the Fox"')
        assert cv.value == '"of the Fox"'

    def test_linked_sockets(self, svc):
        cv = svc.parse_raw("LinkedSockets", ">= 5")
        assert cv.op == ">=" and cv.value == "5"


# ---------------------------------------------------------------------------
# 3. serialize — 序列化
# ---------------------------------------------------------------------------

class TestSerialize:
    def test_rarity_gte(self, svc):
        cv = ConditionValue("Rarity", ">=", "Rare")
        assert svc.serialize(cv) == ">= Rare"

    def test_rarity_eq(self, svc):
        cv = ConditionValue("Rarity", "=", "Unique")
        assert svc.serialize(cv) == "= Unique"

    def test_item_level_gte(self, svc):
        cv = ConditionValue("ItemLevel", ">=", "70")
        assert svc.serialize(cv) == ">= 70"

    def test_item_level_lte(self, svc):
        cv = ConditionValue("ItemLevel", "<=", "60")
        assert svc.serialize(cv) == "<= 60"

    def test_quality_eq(self, svc):
        cv = ConditionValue("Quality", "=", "20")
        assert svc.serialize(cv) == "= 20"

    def test_class_string_no_op(self, svc):
        cv = ConditionValue("Class", "", '"Currency"')
        assert svc.serialize(cv) == '"Currency"'

    def test_basetype_string(self, svc):
        cv = ConditionValue("BaseType", "", '"Divine Orb"')
        assert svc.serialize(cv) == '"Divine Orb"'

    def test_empty_returns_empty(self, svc):
        cv = ConditionValue("ItemLevel", ">=", "")
        assert svc.serialize(cv) == ""

    def test_empty_whitespace_returns_empty(self, svc):
        cv = ConditionValue("Rarity", ">=", "   ")
        assert svc.serialize(cv) == ""

    def test_roundtrip_item_level(self, svc):
        raw = ">= 86"
        cv = svc.parse_raw("ItemLevel", raw)
        assert svc.serialize(cv) == raw

    def test_roundtrip_rarity(self, svc):
        raw = ">= Rare"
        cv = svc.parse_raw("Rarity", raw)
        assert svc.serialize(cv) == raw

    def test_roundtrip_class(self, svc):
        raw = '"Currency" "Gems"'
        cv = svc.parse_raw("Class", raw)
        assert svc.serialize(cv) == raw


# ---------------------------------------------------------------------------
# 4. validate — 驗證
# ---------------------------------------------------------------------------

class TestValidate:
    # Rarity
    def test_rarity_valid(self, svc):
        assert svc.validate(ConditionValue("Rarity", ">=", "Rare"))

    def test_rarity_all_choices_valid(self, svc):
        for v in ("Normal", "Magic", "Rare", "Unique"):
            assert svc.validate(ConditionValue("Rarity", ">=", v)), f"{v} 應合法"

    def test_rarity_invalid_value(self, svc):
        assert not svc.validate(ConditionValue("Rarity", ">=", "Epic"))

    def test_rarity_empty_invalid(self, svc):
        assert not svc.validate(ConditionValue("Rarity", ">=", ""))

    def test_rarity_invalid_op(self, svc):
        assert not svc.validate(ConditionValue("Rarity", ">", "Rare"))

    # Numeric
    def test_numeric_valid_gte(self, svc):
        assert svc.validate(ConditionValue("ItemLevel", ">=", "70"))

    def test_numeric_valid_lte(self, svc):
        assert svc.validate(ConditionValue("ItemLevel", "<=", "60"))

    def test_numeric_valid_eq(self, svc):
        assert svc.validate(ConditionValue("ItemLevel", "=", "86"))

    def test_numeric_valid_gt(self, svc):
        assert svc.validate(ConditionValue("ItemLevel", ">", "50"))

    def test_numeric_invalid_string_value(self, svc):
        assert not svc.validate(ConditionValue("ItemLevel", ">=", "abc"))

    def test_numeric_out_of_range_high(self, svc):
        assert not svc.validate(ConditionValue("ItemLevel", ">=", "999"))

    def test_numeric_out_of_range_low(self, svc):
        assert not svc.validate(ConditionValue("Quality", ">=", "-1"))

    def test_numeric_boundary_ok(self, svc):
        cdef = svc.get_def("Quality")
        assert svc.validate(ConditionValue("Quality", ">=", str(cdef.max_val)))

    # String (Class / BaseType)
    def test_string_valid_with_quotes(self, svc):
        assert svc.validate(ConditionValue("Class", "", '"Currency"'))

    def test_string_valid_without_quotes(self, svc):
        assert svc.validate(ConditionValue("BaseType", "", "Divine Orb"))

    def test_string_empty_invalid(self, svc):
        assert not svc.validate(ConditionValue("Class", "", ""))

    def test_string_whitespace_invalid(self, svc):
        assert not svc.validate(ConditionValue("BaseType", "", "   "))


# ---------------------------------------------------------------------------
# 5. load_from_rule — 從 rule.conditions 載入
# ---------------------------------------------------------------------------

class TestLoadFromRule:
    def test_load_rarity(self, svc):
        conds = [["Rarity", ">= Rare"]]
        cvs = svc.load_from_rule(conds)
        assert len(cvs) == 1
        assert cvs[0].key == "Rarity" and cvs[0].value == "Rare"

    def test_load_item_level_and_rarity(self, svc):
        conds = [["Rarity", ">= Rare"], ["ItemLevel", ">= 70"]]
        cvs = svc.load_from_rule(conds)
        keys = [cv.key for cv in cvs]
        assert "Rarity" in keys and "ItemLevel" in keys

    def test_load_preserves_order(self, svc):
        conds = [["ItemLevel", ">= 70"], ["Rarity", ">= Rare"]]
        cvs = svc.load_from_rule(conds)
        assert [cv.key for cv in cvs] == ["ItemLevel", "Rarity"]

    def test_load_ignores_unknown_keys(self, svc):
        conds = [["Rarity", "Rare"], ["HasExplicitMod", '"of the Fox"']]
        cvs = svc.load_from_rule(conds)
        keys = [cv.key for cv in cvs]
        assert "HasExplicitMod" not in keys
        assert "Rarity" in keys

    def test_load_class_and_basetype(self, svc):
        conds = [["Class", '"Currency"'], ["BaseType", '"Chaos Orb"']]
        cvs = svc.load_from_rule(conds)
        assert len(cvs) == 2

    def test_load_empty_conditions(self, svc):
        assert svc.load_from_rule([]) == []

    def test_load_skips_empty_value(self, svc):
        """空白值的條件不應被載入。"""
        conds = [["Rarity", ""], ["ItemLevel", ">= 70"]]
        cvs = svc.load_from_rule(conds)
        keys = [cv.key for cv in cvs]
        assert "Rarity" not in keys
        assert "ItemLevel" in keys


# ---------------------------------------------------------------------------
# 6. save_to_rule — 儲存回 rule.conditions
# ---------------------------------------------------------------------------

class TestSaveToRule:
    # 修改條件
    def test_update_existing_rarity(self, svc):
        existing = [["Rarity", "Rare"], ["ItemLevel", ">= 70"]]
        new_cvs  = [
            ConditionValue("Rarity",    ">=", "Magic"),
            ConditionValue("ItemLevel", ">=", "70"),
        ]
        result = svc.save_to_rule(new_cvs, existing)
        rarity = next(item for item in result if item[0] == "Rarity")
        assert rarity[1] == ">= Magic"

    def test_update_preserves_item_level(self, svc):
        existing = [["Rarity", "Rare"], ["ItemLevel", ">= 60"]]
        new_cvs  = [
            ConditionValue("Rarity",    ">=", "Rare"),
            ConditionValue("ItemLevel", ">=", "80"),
        ]
        result = svc.save_to_rule(new_cvs, existing)
        il = next(item for item in result if item[0] == "ItemLevel")
        assert il[1] == ">= 80"

    # 新增條件
    def test_add_new_condition(self, svc):
        existing = [["Rarity", ">= Rare"]]
        new_cvs  = [
            ConditionValue("Rarity",    ">=", "Rare"),
            ConditionValue("ItemLevel", ">=", "70"),   # new
        ]
        result = svc.save_to_rule(new_cvs, existing)
        keys = [item[0] for item in result]
        assert "ItemLevel" in keys

    def test_add_class_and_basetype(self, svc):
        existing = []
        new_cvs  = [
            ConditionValue("Class",    "", '"Currency"'),
            ConditionValue("BaseType", "", '"Chaos Orb"'),
        ]
        result = svc.save_to_rule(new_cvs, existing)
        keys = [item[0] for item in result]
        assert "Class" in keys and "BaseType" in keys

    # 移除條件
    def test_remove_condition_not_in_cvs(self, svc):
        """ItemLevel 不在 new_cvs → 應從輸出中移除。"""
        existing = [["Rarity", ">= Rare"], ["ItemLevel", ">= 70"]]
        new_cvs  = [ConditionValue("Rarity", ">=", "Rare")]
        result   = svc.save_to_rule(new_cvs, existing)
        keys     = [item[0] for item in result]
        assert "ItemLevel" not in keys
        assert "Rarity" in keys

    def test_remove_all_managed_conditions(self, svc):
        existing = [["Rarity", "Rare"], ["ItemLevel", ">= 70"]]
        result   = svc.save_to_rule([], existing)
        keys     = [item[0] for item in result]
        assert "Rarity" not in keys and "ItemLevel" not in keys

    # 保留未知條件
    def test_preserve_unknown_conditions(self, svc):
        existing = [["Rarity", "Rare"], ["HasExplicitMod", '"of the Fox"']]
        new_cvs  = [ConditionValue("Rarity", ">=", "Rare")]
        result   = svc.save_to_rule(new_cvs, existing)
        keys     = [item[0] for item in result]
        assert "HasExplicitMod" in keys

    def test_preserve_order_of_existing(self, svc):
        """已知條件的順序應保留。"""
        existing = [["ItemLevel", ">= 70"], ["Rarity", ">= Rare"]]
        new_cvs  = [
            ConditionValue("ItemLevel", ">=", "80"),
            ConditionValue("Rarity",    ">=", "Rare"),
        ]
        result = svc.save_to_rule(new_cvs, existing)
        keys   = [item[0] for item in result]
        assert keys.index("ItemLevel") < keys.index("Rarity")

    # 空值不輸出
    def test_empty_value_not_output(self, svc):
        existing = []
        new_cvs  = [ConditionValue("Class", "", "")]
        result   = svc.save_to_rule(new_cvs, existing)
        assert not any(item[0] == "Class" for item in result)


# ---------------------------------------------------------------------------
# 7. Class / BaseType 中文輸入解析（沿用 P21 RuleEditorAliasService）
# ---------------------------------------------------------------------------

class TestClassBaseTypeAlias:
    def test_zh_class_rune_resolves(self, svc, alias_svc):
        """中文分類 '符文' → '"Rune"'，可正確 parse 為 Class 條件。"""
        resolved = alias_svc.resolve_filter_value("符文", "Class")
        cv = svc.parse_raw("Class", resolved)
        assert '"Rune"' in cv.value

    def test_zh_class_currency_resolves(self, svc, alias_svc):
        """'通貨' → 包含 'Stackable Currency'。"""
        resolved = alias_svc.resolve_filter_value("通貨", "Class")
        cv = svc.parse_raw("Class", resolved)
        assert "Stackable Currency" in cv.value

    def test_zh_basetype_divine_orb(self, svc, alias_svc):
        """中文物品名 '神聖石' → '"Divine Orb"'。"""
        resolved = alias_svc.resolve_filter_value("神聖石", "BaseType")
        cv = svc.parse_raw("BaseType", resolved)
        assert cv.value == '"Divine Orb"'

    def test_zh_basetype_chaos_orb(self, svc, alias_svc):
        """'混沌石' → '"Chaos Orb"'。"""
        resolved = alias_svc.resolve_filter_value("混沌石", "BaseType")
        cv = svc.parse_raw("BaseType", resolved)
        assert cv.value == '"Chaos Orb"'

    def test_zh_basetype_serializes_correctly(self, svc, alias_svc):
        """解析後 serialize 應維持引號格式。"""
        resolved = alias_svc.resolve_filter_value("神聖石", "BaseType")
        cv       = svc.parse_raw("BaseType", resolved)
        assert svc.serialize(cv) == '"Divine Orb"'

    def test_zh_class_validate(self, svc, alias_svc):
        """中文解析後的 Class 值應通過 validate。"""
        resolved = alias_svc.resolve_filter_value("符文", "Class")
        cv = svc.parse_raw("Class", resolved)
        assert svc.validate(cv)

    def test_english_basetype_passthrough(self, svc, alias_svc):
        """已正確引號的英文值不被改變。"""
        raw = '"Divine Orb"'
        resolved = alias_svc.resolve_filter_value(raw, "BaseType")
        assert resolved == raw


# ---------------------------------------------------------------------------
# 8. ConditionBuilderWidget Qt 測試
# ---------------------------------------------------------------------------

class TestConditionBuilderWidget:

    def test_widget_creates_without_error(self, qapp):
        from ui.condition_builder_widget import ConditionBuilderWidget
        w = ConditionBuilderWidget()
        assert w is not None

    def test_set_conditions_loads_rows(self, qapp):
        from ui.condition_builder_widget import ConditionBuilderWidget
        w = ConditionBuilderWidget()
        w.set_conditions([["Rarity", ">= Rare"], ["ItemLevel", ">= 70"]])
        assert w.row_count() == 2

    def test_empty_conditions_zero_rows(self, qapp):
        from ui.condition_builder_widget import ConditionBuilderWidget
        w = ConditionBuilderWidget()
        w.set_conditions([])
        assert w.row_count() == 0

    def test_get_conditions_roundtrip(self, qapp):
        from ui.condition_builder_widget import ConditionBuilderWidget
        w = ConditionBuilderWidget()
        original = [["Rarity", ">= Rare"], ["ItemLevel", ">= 70"]]
        w.set_conditions(original)
        result = w.get_conditions()
        keys = [item[0] for item in result]
        assert "Rarity" in keys and "ItemLevel" in keys

    def test_get_conditions_preserves_unknown(self, qapp):
        from ui.condition_builder_widget import ConditionBuilderWidget
        w = ConditionBuilderWidget()
        original = [["Rarity", ">= Rare"], ["HasExplicitMod", '"of the Fox"']]
        w.set_conditions(original)
        result = w.get_conditions()
        keys = [item[0] for item in result]
        assert "HasExplicitMod" in keys

    def test_add_condition_increases_row_count(self, qapp):
        from ui.condition_builder_widget import ConditionBuilderWidget
        w = ConditionBuilderWidget()
        w.set_conditions([])
        initial = w.row_count()
        # Simulate clicking add with ItemLevel
        svc = ConditionBuilderService()
        from core.condition_builder import FieldType
        key = "ItemLevel"
        cdef = svc.get_def(key)
        cv = ConditionValue(key=key, op=">=", value="0")
        w._add_row(cv)
        assert w.row_count() == initial + 1

    def test_remove_row_decreases_row_count(self, qapp):
        from ui.condition_builder_widget import ConditionBuilderWidget
        w = ConditionBuilderWidget()
        w.set_conditions([["Rarity", ">= Rare"], ["ItemLevel", ">= 70"]])
        assert w.row_count() == 2
        row_to_remove = w._rows[0]
        w._on_remove_row(row_to_remove)
        assert w.row_count() == 1

    def test_conditions_changed_signal_emits(self, qapp):
        from ui.condition_builder_widget import ConditionBuilderWidget
        from PySide6.QtCore import QEventLoop, QTimer
        w = ConditionBuilderWidget()
        w.set_conditions([["Rarity", ">= Rare"]])

        received = []
        w.conditions_changed.connect(received.append)
        w._on_condition_changed()
        assert len(received) == 1

    def test_set_conditions_twice_resets_rows(self, qapp):
        from ui.condition_builder_widget import ConditionBuilderWidget
        w = ConditionBuilderWidget()
        w.set_conditions([["Rarity", ">= Rare"], ["ItemLevel", ">= 70"]])
        assert w.row_count() == 2
        w.set_conditions([["Quality", ">= 15"]])
        assert w.row_count() == 1

    def test_row_get_value_rarity(self, qapp):
        from ui.condition_builder_widget import ConditionBuilderWidget, ConditionRowWidget
        from core.condition_builder import FieldType
        w = ConditionBuilderWidget()
        w.set_conditions([["Rarity", ">= Rare"]])
        row = w._rows[0]
        cv = row.get_value()
        assert cv.key == "Rarity" and cv.value == "Rare"

    def test_row_get_value_item_level(self, qapp):
        from ui.condition_builder_widget import ConditionBuilderWidget
        w = ConditionBuilderWidget()
        w.set_conditions([["ItemLevel", ">= 86"]])
        row = w._rows[0]
        cv = row.get_value()
        assert cv.key == "ItemLevel" and cv.value == "86" and cv.op == ">="

    def test_invalid_conditions_no_crash(self, qapp):
        """不合法的條件值不得造成閃退。"""
        from ui.condition_builder_widget import ConditionBuilderWidget
        w = ConditionBuilderWidget()
        try:
            w.set_conditions([
                ["ItemLevel", ">= abc"],
                ["Rarity",    ""],
                ["Class",     ""],
            ])
        except Exception as e:
            pytest.fail(f"不合法條件不應拋例外：{e}")
