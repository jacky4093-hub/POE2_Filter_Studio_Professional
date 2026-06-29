"""P22.3 — ConditionPresetService 與 ConditionBuilderWidget Preset UI 測試。

純 Python 部分（TestPresetDefinition、TestPresetService、TestPresetToConditions、
TestPresetToConditionValues）不需要 Qt。

Qt 部分（TestPresetUI）使用 offscreen 平台。
"""

from __future__ import annotations

import pytest

from core.condition_presets import ConditionPresetService, PresetDefinition
from core.condition_builder import ConditionBuilderService, ConditionValue


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def svc() -> ConditionPresetService:
    return ConditionPresetService()


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(["-platform", "offscreen"])


@pytest.fixture
def widget(qapp):
    from ui.condition_builder_widget import ConditionBuilderWidget
    return ConditionBuilderWidget()


# ---------------------------------------------------------------------------
# 1. PresetDefinition 靜態定義
# ---------------------------------------------------------------------------

class TestPresetDefinition:

    def test_is_frozen(self, svc):
        pdef = svc.get_preset("high_value_currency")
        with pytest.raises((AttributeError, TypeError)):
            pdef.key = "modified"   # type: ignore[misc]

    def test_has_key(self, svc):
        pdef = svc.get_preset("high_value_currency")
        assert pdef.key == "high_value_currency"

    def test_has_label(self, svc):
        pdef = svc.get_preset("high_value_currency")
        assert pdef.label == "高價值通貨"

    def test_has_conditions_tuple(self, svc):
        pdef = svc.get_preset("high_value_currency")
        assert isinstance(pdef.conditions, tuple)

    def test_empty_preset_has_no_conditions(self, svc):
        pdef = svc.get_preset("empty")
        assert pdef.conditions == ()

    def test_six_presets_defined(self, svc):
        assert len(svc.PRESETS) == 6


# ---------------------------------------------------------------------------
# 2. ConditionPresetService 查詢
# ---------------------------------------------------------------------------

class TestPresetService:
    EXPECTED_KEYS = {
        "high_value_currency",
        "high_quality_gem",
        "six_link",
        "endgame_rare",
        "high_tier_waystone",
        "empty",
    }

    def test_available_presets_returns_all(self, svc):
        presets = svc.available_presets()
        keys = {p.key for p in presets}
        assert keys == self.EXPECTED_KEYS

    def test_available_presets_returns_list(self, svc):
        assert isinstance(svc.available_presets(), list)

    def test_get_preset_high_value_currency(self, svc):
        pdef = svc.get_preset("high_value_currency")
        assert pdef is not None
        assert pdef.label == "高價值通貨"

    def test_get_preset_high_quality_gem(self, svc):
        assert svc.get_preset("high_quality_gem") is not None

    def test_get_preset_six_link(self, svc):
        assert svc.get_preset("six_link") is not None

    def test_get_preset_endgame_rare(self, svc):
        assert svc.get_preset("endgame_rare") is not None

    def test_get_preset_high_tier_waystone(self, svc):
        assert svc.get_preset("high_tier_waystone") is not None

    def test_get_preset_empty(self, svc):
        assert svc.get_preset("empty") is not None

    def test_get_preset_unknown_returns_none(self, svc):
        assert svc.get_preset("nonexistent_preset") is None

    def test_get_preset_empty_string_returns_none(self, svc):
        assert svc.get_preset("") is None


# ---------------------------------------------------------------------------
# 3. preset_to_conditions — 正確條件內容
# ---------------------------------------------------------------------------

class TestPresetToConditions:

    def test_high_value_currency_has_class(self, svc):
        conds = svc.preset_to_conditions("high_value_currency")
        keys = [item[0] for item in conds]
        assert "Class" in keys

    def test_high_value_currency_class_value(self, svc):
        conds = svc.preset_to_conditions("high_value_currency")
        class_item = next(item for item in conds if item[0] == "Class")
        assert '"Currency"' in class_item[1]

    def test_high_quality_gem_has_class_and_quality(self, svc):
        conds = svc.preset_to_conditions("high_quality_gem")
        keys = [item[0] for item in conds]
        assert "Class" in keys and "Quality" in keys

    def test_high_quality_gem_class_value(self, svc):
        conds = svc.preset_to_conditions("high_quality_gem")
        class_item = next(item for item in conds if item[0] == "Class")
        assert '"Skill Gem"' in class_item[1]

    def test_high_quality_gem_quality_value(self, svc):
        conds = svc.preset_to_conditions("high_quality_gem")
        q = next(item for item in conds if item[0] == "Quality")
        assert "20" in q[1]

    def test_six_link_has_linked_sockets(self, svc):
        conds = svc.preset_to_conditions("six_link")
        keys = [item[0] for item in conds]
        assert "LinkedSockets" in keys

    def test_six_link_value_gte_6(self, svc):
        conds = svc.preset_to_conditions("six_link")
        ls = next(item for item in conds if item[0] == "LinkedSockets")
        assert "6" in ls[1]

    def test_endgame_rare_has_rarity_and_item_level(self, svc):
        conds = svc.preset_to_conditions("endgame_rare")
        keys = [item[0] for item in conds]
        assert "Rarity" in keys and "ItemLevel" in keys

    def test_endgame_rare_rarity_value(self, svc):
        conds = svc.preset_to_conditions("endgame_rare")
        r = next(item for item in conds if item[0] == "Rarity")
        assert "Rare" in r[1]

    def test_endgame_rare_item_level_value(self, svc):
        conds = svc.preset_to_conditions("endgame_rare")
        il = next(item for item in conds if item[0] == "ItemLevel")
        assert "82" in il[1]

    def test_high_tier_waystone_has_class_and_area_level(self, svc):
        conds = svc.preset_to_conditions("high_tier_waystone")
        keys = [item[0] for item in conds]
        assert "Class" in keys and "AreaLevel" in keys

    def test_high_tier_waystone_class_value(self, svc):
        conds = svc.preset_to_conditions("high_tier_waystone")
        class_item = next(item for item in conds if item[0] == "Class")
        assert '"Waystone"' in class_item[1]

    def test_high_tier_waystone_area_level_value(self, svc):
        conds = svc.preset_to_conditions("high_tier_waystone")
        al = next(item for item in conds if item[0] == "AreaLevel")
        assert "79" in al[1]

    def test_empty_preset_returns_empty_list(self, svc):
        assert svc.preset_to_conditions("empty") == []

    def test_unknown_preset_returns_empty_list(self, svc):
        assert svc.preset_to_conditions("nonexistent") == []

    def test_conditions_format_compatible_with_rule(self, svc):
        """回傳格式必須是 [[key, value], ...] 清單。"""
        conds = svc.preset_to_conditions("endgame_rare")
        for item in conds:
            assert isinstance(item, list)
            assert len(item) == 2
            assert isinstance(item[0], str)
            assert isinstance(item[1], str)


# ---------------------------------------------------------------------------
# 4. preset_to_condition_values — ConditionValue 清單
# ---------------------------------------------------------------------------

class TestPresetToConditionValues:

    def test_high_value_currency_returns_cv_list(self, svc):
        cvs = svc.preset_to_condition_values("high_value_currency")
        assert isinstance(cvs, list)
        assert len(cvs) >= 1

    def test_high_quality_gem_two_values(self, svc):
        cvs = svc.preset_to_condition_values("high_quality_gem")
        assert len(cvs) == 2

    def test_six_link_linked_sockets_cv(self, svc):
        cvs = svc.preset_to_condition_values("six_link")
        assert len(cvs) == 1
        assert cvs[0].key == "LinkedSockets"
        assert cvs[0].value == "6"

    def test_endgame_rare_rarity_cv(self, svc):
        cvs = svc.preset_to_condition_values("endgame_rare")
        rarity_cv = next((cv for cv in cvs if cv.key == "Rarity"), None)
        assert rarity_cv is not None
        assert rarity_cv.value == "Rare"

    def test_endgame_rare_item_level_cv(self, svc):
        cvs = svc.preset_to_condition_values("endgame_rare")
        il_cv = next((cv for cv in cvs if cv.key == "ItemLevel"), None)
        assert il_cv is not None
        assert il_cv.value == "82"

    def test_empty_preset_returns_empty(self, svc):
        cvs = svc.preset_to_condition_values("empty")
        assert cvs == []

    def test_unknown_preset_returns_empty(self, svc):
        cvs = svc.preset_to_condition_values("totally_unknown")
        assert cvs == []

    def test_cv_is_condition_value(self, svc):
        cvs = svc.preset_to_condition_values("endgame_rare")
        for cv in cvs:
            assert isinstance(cv, ConditionValue)

    def test_compatible_with_condition_builder_service(self, svc):
        """preset_to_condition_values 回傳的 cv 應能通過 ConditionBuilderService.validate。"""
        cb_svc = ConditionBuilderService()
        for key in ("endgame_rare", "six_link", "high_quality_gem"):
            for cv in svc.preset_to_condition_values(key):
                assert cb_svc.validate(cv), f"{key}/{cv.key} 應通過 validate"


# ---------------------------------------------------------------------------
# 5. Widget Preset UI（Qt）
# ---------------------------------------------------------------------------

class TestPresetUI:

    def test_preset_combo_exists(self, widget):
        assert hasattr(widget, "_preset_combo")

    def test_preset_combo_has_items(self, widget):
        """combo 應有佔位符 + 6 個 preset = 7 項。"""
        assert widget._preset_combo.count() == 7

    def test_preset_combo_placeholder_first(self, widget):
        """第一項應是佔位符，userData 為 None。"""
        assert widget._preset_combo.itemData(0) is None

    def test_preset_combo_labels_are_chinese(self, widget):
        """Preset 項目標籤應包含中文字。"""
        labels = [
            widget._preset_combo.itemText(i)
            for i in range(1, widget._preset_combo.count())
        ]
        for label in labels:
            assert any("一" <= c <= "鿿" for c in label), f"{label!r} 應含中文"

    def test_apply_preset_high_value_currency(self, widget):
        widget.apply_preset("high_value_currency", skip_confirm=True)
        keys = [row._cdef.key for row in widget._rows]
        assert "Class" in keys

    def test_apply_preset_high_quality_gem_two_rows(self, widget):
        widget.apply_preset("high_quality_gem", skip_confirm=True)
        assert widget.row_count() == 2

    def test_apply_preset_high_quality_gem_class(self, widget):
        widget.apply_preset("high_quality_gem", skip_confirm=True)
        class_row = next(r for r in widget._rows if r._cdef.key == "Class")
        assert '"Skill Gem"' in class_row.get_value().value

    def test_apply_preset_six_link_one_row(self, widget):
        widget.apply_preset("six_link", skip_confirm=True)
        assert widget.row_count() == 1
        assert widget._rows[0]._cdef.key == "LinkedSockets"

    def test_apply_preset_endgame_rare_two_rows(self, widget):
        widget.apply_preset("endgame_rare", skip_confirm=True)
        assert widget.row_count() == 2

    def test_apply_preset_endgame_rare_item_level_value(self, widget):
        widget.apply_preset("endgame_rare", skip_confirm=True)
        il_row = next(r for r in widget._rows if r._cdef.key == "ItemLevel")
        assert il_row.get_value().value == "82"

    def test_apply_preset_high_tier_waystone(self, widget):
        widget.apply_preset("high_tier_waystone", skip_confirm=True)
        keys = [row._cdef.key for row in widget._rows]
        assert "Class" in keys and "AreaLevel" in keys

    def test_apply_preset_empty_clears_rows(self, widget):
        """先套用有條件的 preset，再套用 empty → 0 列。"""
        widget.apply_preset("endgame_rare",  skip_confirm=True)
        widget.apply_preset("empty",         skip_confirm=True)
        assert widget.row_count() == 0

    def test_apply_unknown_preset_no_crash(self, widget):
        """不存在的 preset key 不應拋例外，也不應改變 widget 狀態。"""
        widget.apply_preset("endgame_rare", skip_confirm=True)
        before = widget.row_count()
        try:
            widget.apply_preset("nonexistent_preset", skip_confirm=True)
        except Exception as e:
            pytest.fail(f"不應拋例外：{e}")
        assert widget.row_count() == before   # 狀態未改變

    def test_apply_preset_replaces_previous(self, widget):
        """套用新 preset 應完全取代現有條件。"""
        widget.apply_preset("endgame_rare",        skip_confirm=True)
        widget.apply_preset("high_value_currency", skip_confirm=True)
        keys = [row._cdef.key for row in widget._rows]
        assert "Rarity"    not in keys   # endgame_rare 的條件應被清除
        assert "ItemLevel" not in keys
        assert "Class"     in keys       # high_value_currency 的條件

    def test_apply_preset_emits_conditions_changed(self, widget):
        """apply_preset 後應發射 conditions_changed。"""
        received = []
        widget.conditions_changed.connect(received.append)
        widget.apply_preset("endgame_rare", skip_confirm=True)
        assert len(received) >= 1

    def test_conditions_changed_content_correct(self, widget):
        """conditions_changed 發射的清單應包含正確條件。"""
        received = []
        widget.conditions_changed.connect(received.append)
        widget.apply_preset("six_link", skip_confirm=True)
        assert len(received) >= 1
        last = received[-1]
        keys = [item[0] for item in last]
        assert "LinkedSockets" in keys

    def test_get_conditions_after_preset(self, widget):
        """apply_preset 後 get_conditions() 應回傳正確格式。"""
        widget.apply_preset("endgame_rare", skip_confirm=True)
        conds = widget.get_conditions()
        keys = [item[0] for item in conds]
        assert "Rarity" in keys and "ItemLevel" in keys

    def test_placeholder_selected_no_action(self, widget):
        """選中佔位符時 _on_apply_preset 不應做任何事。"""
        widget.apply_preset("endgame_rare", skip_confirm=True)
        before = widget.row_count()
        widget._preset_combo.setCurrentIndex(0)  # 佔位符
        widget._on_apply_preset()
        assert widget.row_count() == before       # 狀態未改變
