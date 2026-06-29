"""P24.2 — QuickRuleCreatorDialog 測試。

涵蓋：
  1. Dialog 結構與 UI 元件
  2. 模板載入（QComboBox 資料、API）
  3. 模板切換 → 說明更新、預覽更新
  4. 物品選取（monkeypatch _create_item_selector_dialog）
  5. create_rule() API
  6. 取消 / Reject 行為
  7. _create_item_selector_dialog helper

所有測試使用 Qt offscreen 平台，不需顯示螢幕。
"""

from __future__ import annotations

import pytest

from core.item_database import ItemDefinition
from core.models import FilterRule
from core.rule_templates import get_templates


# ---------------------------------------------------------------------------
# Mock helpers（沿用 P23.3 模式）
# ---------------------------------------------------------------------------

class _MockDialog:
    """假 QDialog：exec() 回傳預設結果，不顯示視窗。"""
    def __init__(self, result: int) -> None:
        self._result = result

    def exec(self) -> int:
        return self._result


class _MockSelector:
    """假 ItemSelectorWidget：selected_item() 回傳預設物品。"""
    def __init__(self, item: ItemDefinition | None) -> None:
        self._item = item

    def selected_item(self) -> ItemDefinition | None:
        return self._item


def _fake_item(
    name_en: str = "Chaos Orb",
    name_zh: str = "混沌石",
    category: str = "Currency",
) -> ItemDefinition:
    return ItemDefinition(
        id=f"test-{name_en.lower().replace(' ', '-')}",
        name_en=name_en,
        name_zh=name_zh,
        category=category,
        subcategory="基本通貨",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(["-platform", "offscreen"])


@pytest.fixture
def dlg(qapp):
    from ui.quick_rule_creator_dialog import QuickRuleCreatorDialog
    return QuickRuleCreatorDialog()


# ---------------------------------------------------------------------------
# 1. Dialog 結構
# ---------------------------------------------------------------------------

class TestDialogStructure:

    def test_dialog_creates_without_exception(self, dlg):
        assert dlg is not None

    def test_dialog_title(self, dlg):
        assert "建立" in dlg.windowTitle()

    def test_dialog_objectname(self, dlg):
        assert dlg.objectName() == "QuickRuleCreatorDialog"

    def test_template_combo_exists(self, dlg):
        from PySide6.QtWidgets import QComboBox
        assert hasattr(dlg, "_template_combo")
        assert isinstance(dlg._template_combo, QComboBox)

    def test_desc_label_exists(self, dlg):
        from PySide6.QtWidgets import QLabel
        assert hasattr(dlg, "_desc_label")
        assert isinstance(dlg._desc_label, QLabel)

    def test_item_btn_exists(self, dlg):
        from PySide6.QtWidgets import QPushButton
        assert hasattr(dlg, "_item_btn")
        assert isinstance(dlg._item_btn, QPushButton)

    def test_preview_widget_exists(self, dlg):
        from PySide6.QtWidgets import QTextEdit
        assert hasattr(dlg, "_preview")
        assert isinstance(dlg._preview, QTextEdit)

    def test_preview_is_readonly(self, dlg):
        assert dlg._preview.isReadOnly()

    def test_create_button_exists(self, dlg):
        from PySide6.QtWidgets import QPushButton
        assert hasattr(dlg, "_create_btn")
        assert isinstance(dlg._create_btn, QPushButton)

    def test_create_button_objectname(self, dlg):
        assert dlg._create_btn.objectName() == "QuickRuleCreateBtn"


# ---------------------------------------------------------------------------
# 2. 模板載入
# ---------------------------------------------------------------------------

class TestTemplateLoading:

    def test_combo_has_six_or_more_items(self, dlg):
        assert dlg._template_combo.count() >= 6

    def test_combo_count_matches_get_templates(self, dlg):
        assert dlg._template_combo.count() == len(get_templates())

    def test_selected_template_id_returns_string(self, dlg):
        tid = dlg.selected_template_id()
        assert isinstance(tid, str) and len(tid) > 0

    def test_selected_template_id_is_valid(self, dlg):
        from core.rule_templates import get_template
        tmpl = get_template(dlg.selected_template_id())
        assert tmpl is not None

    def test_template_names_visible_in_combo(self, dlg):
        expected_names = {t.name for t in get_templates()}
        combo_texts = {dlg._template_combo.itemText(i)
                       for i in range(dlg._template_combo.count())}
        assert expected_names == combo_texts

    def test_first_template_desc_not_empty(self, dlg):
        assert dlg._desc_label.text() not in ("", "—")


# ---------------------------------------------------------------------------
# 3. 模板切換
# ---------------------------------------------------------------------------

class TestTemplateSwitch:

    def _set_index(self, dlg, idx: int) -> None:
        dlg._template_combo.setCurrentIndex(idx)

    def test_desc_updates_on_switch(self, dlg):
        self._set_index(dlg, 0)
        desc_first = dlg._desc_label.text()
        self._set_index(dlg, 1)
        desc_second = dlg._desc_label.text()
        assert desc_first != desc_second

    def test_preview_not_empty_after_switch(self, dlg):
        self._set_index(dlg, 0)
        assert dlg._preview.toPlainText().strip() != ""

    def test_different_templates_different_preview(self, dlg):
        self._set_index(dlg, 0)
        preview_first = dlg._preview.toPlainText()
        self._set_index(dlg, 1)
        preview_second = dlg._preview.toPlainText()
        assert preview_first != preview_second

    def test_desc_label_matches_template_description(self, dlg):
        from core.rule_templates import get_template
        idx = dlg._template_combo.count() - 1  # empty_rule
        self._set_index(dlg, idx)
        tmpl = get_template(dlg.selected_template_id())
        assert dlg._desc_label.text() == tmpl.description

    def test_preview_contains_show_keyword(self, dlg):
        self._set_index(dlg, 0)
        assert "Show" in dlg._preview.toPlainText()


# ---------------------------------------------------------------------------
# 4. 物品選取
# ---------------------------------------------------------------------------

class TestSelectedItem:

    def test_selected_item_initially_none(self, dlg):
        assert dlg.selected_item() is None

    def test_item_stored_after_selection(self, dlg, monkeypatch):
        from PySide6.QtWidgets import QDialog
        fake_item = _fake_item()
        monkeypatch.setattr(
            dlg, "_create_item_selector_dialog",
            lambda: (_MockDialog(QDialog.DialogCode.Accepted), _MockSelector(fake_item)),
        )
        dlg._open_item_selector()
        assert dlg.selected_item() is not None
        assert dlg.selected_item().name_en == fake_item.name_en

    def test_preview_contains_item_name_when_selected(self, dlg):
        fake_item = _fake_item("Divine Orb", "神聖石")
        dlg._selected_item = fake_item
        dlg._update_preview()
        assert "Divine Orb" in dlg._preview.toPlainText()

    def test_item_btn_text_updates_after_selection(self, dlg, monkeypatch):
        from PySide6.QtWidgets import QDialog
        fake_item = _fake_item("Exalted Orb", "崇高石")
        monkeypatch.setattr(
            dlg, "_create_item_selector_dialog",
            lambda: (_MockDialog(QDialog.DialogCode.Accepted), _MockSelector(fake_item)),
        )
        dlg._open_item_selector()
        btn_text = dlg._item_btn.text()
        assert "Exalted Orb" in btn_text or "崇高石" in btn_text

    def test_cancel_does_not_store_item(self, dlg, monkeypatch):
        from PySide6.QtWidgets import QDialog
        dlg._selected_item = None
        monkeypatch.setattr(
            dlg, "_create_item_selector_dialog",
            lambda: (
                _MockDialog(QDialog.DialogCode.Rejected),
                _MockSelector(_fake_item()),
            ),
        )
        dlg._open_item_selector()
        assert dlg.selected_item() is None

    def test_none_selection_does_not_store(self, dlg, monkeypatch):
        from PySide6.QtWidgets import QDialog
        dlg._selected_item = None
        monkeypatch.setattr(
            dlg, "_create_item_selector_dialog",
            lambda: (
                _MockDialog(QDialog.DialogCode.Accepted),
                _MockSelector(None),
            ),
        )
        dlg._open_item_selector()
        assert dlg.selected_item() is None


# ---------------------------------------------------------------------------
# 5. create_rule()
# ---------------------------------------------------------------------------

class TestCreateRule:

    def test_create_rule_returns_filter_rule(self, dlg):
        rule = dlg.create_rule()
        assert isinstance(rule, FilterRule)

    def test_created_rule_action_is_show(self, dlg):
        rule = dlg.create_rule()
        assert rule.action == "Show"

    def test_create_rule_enabled_is_true(self, dlg):
        rule = dlg.create_rule()
        assert rule.enabled is True

    def test_create_rule_without_item_no_basetype(self, dlg):
        dlg._selected_item = None
        rule = dlg.create_rule()
        keys = [k for k, _ in rule.conditions]
        assert "BaseType" not in keys

    def test_create_rule_with_item_has_basetype(self, dlg):
        fake_item = _fake_item("Chaos Orb", "混沌石")
        dlg._selected_item = fake_item
        rule = dlg.create_rule()
        keys = [k for k, _ in rule.conditions]
        assert "BaseType" in keys

    def test_create_rule_basetype_value_is_quoted(self, dlg):
        fake_item = _fake_item("Chaos Orb", "混沌石")
        dlg._selected_item = fake_item
        rule = dlg.create_rule()
        bt_val = next((v for k, v in rule.conditions if k == "BaseType"), None)
        assert bt_val is not None
        assert bt_val.startswith('"') and bt_val.endswith('"')

    def test_create_rule_basetype_contains_item_name(self, dlg):
        fake_item = _fake_item("Divine Orb", "神聖石")
        dlg._selected_item = fake_item
        rule = dlg.create_rule()
        bt_val = next((v for k, v in rule.conditions if k == "BaseType"), None)
        assert bt_val is not None and "Divine Orb" in bt_val

    def test_create_rule_accepts_dialog(self, dlg):
        from PySide6.QtWidgets import QDialog
        dlg.create_rule()
        assert dlg.result() == QDialog.DialogCode.Accepted

    def test_created_rule_stored_in_instance(self, dlg):
        rule = dlg.create_rule()
        assert dlg._created_rule is not None
        assert dlg._created_rule is rule


# ---------------------------------------------------------------------------
# 6. 取消 / Reject
# ---------------------------------------------------------------------------

class TestCancelReject:

    def test_created_rule_initially_none(self, dlg):
        assert dlg._created_rule is None

    def test_reject_does_not_set_created_rule(self, qapp):
        from ui.quick_rule_creator_dialog import QuickRuleCreatorDialog
        fresh_dlg = QuickRuleCreatorDialog()
        fresh_dlg.reject()
        assert fresh_dlg._created_rule is None

    def test_reject_sets_rejected_result(self, qapp):
        from PySide6.QtWidgets import QDialog
        from ui.quick_rule_creator_dialog import QuickRuleCreatorDialog
        fresh_dlg = QuickRuleCreatorDialog()
        fresh_dlg.reject()
        assert fresh_dlg.result() == QDialog.DialogCode.Rejected


# ---------------------------------------------------------------------------
# 7. _create_item_selector_dialog helper
# ---------------------------------------------------------------------------

class TestItemSelectorDialogHelper:

    def test_returns_tuple(self, dlg):
        result = dlg._create_item_selector_dialog()
        assert isinstance(result, tuple) and len(result) == 2

    def test_dialog_is_qdialog(self, dlg):
        from PySide6.QtWidgets import QDialog
        sub_dlg, _ = dlg._create_item_selector_dialog()
        assert isinstance(sub_dlg, QDialog)

    def test_selector_is_item_selector_widget(self, dlg):
        from ui.item_selector_widget import ItemSelectorWidget
        _, selector = dlg._create_item_selector_dialog()
        assert isinstance(selector, ItemSelectorWidget)

    def test_sub_dialog_title(self, dlg):
        sub_dlg, _ = dlg._create_item_selector_dialog()
        assert "選擇" in sub_dlg.windowTitle()

    def test_sub_dialog_objectname(self, dlg):
        sub_dlg, _ = dlg._create_item_selector_dialog()
        assert sub_dlg.objectName() == "ItemSelectorDialog"
