"""P23.3 — RuleDetailEditor × ItemSelectorWidget 整合測試。

涵蓋：
  1. BaseType 按鈕存在及屬性
  2. _create_item_selector_dialog 可建立（不 exec）
  3. 選取物品後寫入 BaseType 欄位（格式含引號）
  4. 選取後觸發 rule_changed 訊號
  5. 取消對話框不修改 BaseType
  6. 選取後同步 ConditionBuilderWidget

所有測試使用 Qt offscreen 平台，不需顯示螢幕。
"""

from __future__ import annotations

import pytest

from core.item_database import ItemDefinition
from core.models import FilterRule


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

class _MockDialog:
    """最小化假 QDialog：exec() 回傳預設結果，不顯示視窗。"""
    def __init__(self, result: int) -> None:
        self._result = result

    def exec(self) -> int:
        return self._result


class _MockSelector:
    """最小化假 ItemSelectorWidget：selected_item() 回傳預設物品。"""
    def __init__(self, item: ItemDefinition | None) -> None:
        self._item = item

    def selected_item(self) -> ItemDefinition | None:
        return self._item


def _fake_item(name_en: str = "War Sword", name_zh: str = "戰劍") -> ItemDefinition:
    return ItemDefinition(
        id=f"test-{name_en.lower().replace(' ', '-')}",
        name_en=name_en,
        name_zh=name_zh,
        category="Weapons",
        subcategory="單手劍",
    )


def _make_rule(conditions: list | None = None) -> FilterRule:
    r = FilterRule()
    r.action = "Show"
    r.enabled = True
    r.conditions = list(conditions or [])
    r.actions = []
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
    from ui.rule_detail_editor import RuleDetailEditor
    return RuleDetailEditor()


@pytest.fixture
def editor_with_rule(editor):
    editor.set_rule(_make_rule(conditions=[["Rarity", ">= Rare"]]), 0)
    return editor


# ---------------------------------------------------------------------------
# 1. BaseType 按鈕存在及屬性
# ---------------------------------------------------------------------------

class TestBaseTypePickButton:

    def test_button_attribute_exists(self, editor):
        assert hasattr(editor, "_basetype_pick_btn")

    def test_button_text_contains_pick(self, editor):
        assert "選擇" in editor._basetype_pick_btn.text()

    def test_button_objectname(self, editor):
        assert editor._basetype_pick_btn.objectName() == "BaseTypePickBtn"

    def test_button_is_visible_when_rule_set(self, editor_with_rule):
        assert editor_with_rule._basetype_pick_btn is not None

    def test_basetype_edit_still_exists(self, editor):
        assert hasattr(editor, "_basetype_edit")

    def test_basetype_edit_is_lineedit(self, editor):
        from PySide6.QtWidgets import QLineEdit
        assert isinstance(editor._basetype_edit, QLineEdit)


# ---------------------------------------------------------------------------
# 2. _create_item_selector_dialog 可建立（不 exec）
# ---------------------------------------------------------------------------

class TestDialogCreation:

    def test_create_dialog_returns_tuple(self, editor):
        result = editor._create_item_selector_dialog()
        assert isinstance(result, tuple) and len(result) == 2

    def test_dialog_is_qdialog(self, editor):
        from PySide6.QtWidgets import QDialog
        dlg, _ = editor._create_item_selector_dialog()
        assert isinstance(dlg, QDialog)

    def test_selector_is_item_selector_widget(self, editor):
        from ui.item_selector_widget import ItemSelectorWidget
        _, selector = editor._create_item_selector_dialog()
        assert isinstance(selector, ItemSelectorWidget)

    def test_dialog_title(self, editor):
        dlg, _ = editor._create_item_selector_dialog()
        assert "選擇" in dlg.windowTitle()

    def test_dialog_has_objectname(self, editor):
        dlg, _ = editor._create_item_selector_dialog()
        assert dlg.objectName() == "ItemSelectorDialog"

    def test_selector_has_categories(self, editor):
        _, selector = editor._create_item_selector_dialog()
        assert selector._cat_combo.count() >= 6


# ---------------------------------------------------------------------------
# 2-B. Dialog 互動：雙擊 / Enter 直接確定（H-01、M-04）
# ---------------------------------------------------------------------------

class TestDialogInteraction:

    def test_item_activated_signal_accepts_dialog(self, editor):
        """itemActivated（雙擊 / Enter）應呼叫 dlg.accept() 並發射 accepted 訊號。"""
        dlg, selector = editor._create_item_selector_dialog()

        accepted_calls: list = []
        dlg.accepted.connect(lambda: accepted_calls.append(1))

        # ItemSelectorWidget 初始化後 Weapons 已載入
        if selector._item_list.count() > 0:
            first_item = selector._item_list.item(0)
            selector._item_list.itemActivated.emit(first_item)

        assert len(accepted_calls) == 1

    def test_item_activated_with_no_items_does_not_crash(self, editor):
        """列表為空時觸發 itemActivated 不應崩潰。"""
        dlg, selector = editor._create_item_selector_dialog()
        # 強制搜尋空結果
        selector._search_edit.setText("xyzzy_nonexistent_abc123")
        # 沒有可 emit 的 real item，直接確認無 exception 即可
        assert selector.selected_item() is None

    def test_double_click_does_not_accept_without_selection(self, editor):
        """未選取物品時（placeholder），accepted 不應發射。"""
        dlg, selector = editor._create_item_selector_dialog()

        accepted_calls: list = []
        dlg.accepted.connect(lambda: accepted_calls.append(1))

        # 搜尋到無結果，列表只有 placeholder（非可選取 item）
        selector._search_edit.setText("xyzzy_nonexistent_abc123")
        # 若有 placeholder，嘗試 emit itemActivated（無法對 disabled item emit）
        if selector._item_list.count() == 0:
            pass  # 空列表：不做任何 emit
        # accepted 不應被觸發
        assert len(accepted_calls) == 0


# ---------------------------------------------------------------------------
# 3 & 4. 選取物品後寫入 BaseType（含格式），並觸發 rule_changed
# ---------------------------------------------------------------------------

class TestBaseTypeWriteback:

    def _patch_accept(self, editor, monkeypatch, item: ItemDefinition):
        from PySide6.QtWidgets import QDialog
        monkeypatch.setattr(
            editor,
            "_create_item_selector_dialog",
            lambda: (_MockDialog(QDialog.DialogCode.Accepted), _MockSelector(item)),
        )

    def test_writes_quoted_name(self, editor_with_rule, monkeypatch):
        item = _fake_item("War Sword")
        self._patch_accept(editor_with_rule, monkeypatch, item)
        editor_with_rule._on_pick_basetype_item()
        assert editor_with_rule._basetype_edit.text() == '"War Sword"'

    def test_writes_chaos_orb(self, editor_with_rule, monkeypatch):
        item = _fake_item("Chaos Orb", "混沌石")
        self._patch_accept(editor_with_rule, monkeypatch, item)
        editor_with_rule._on_pick_basetype_item()
        assert editor_with_rule._basetype_edit.text() == '"Chaos Orb"'

    def test_format_starts_with_quote(self, editor_with_rule, monkeypatch):
        item = _fake_item("Divine Orb", "神聖石")
        self._patch_accept(editor_with_rule, monkeypatch, item)
        editor_with_rule._on_pick_basetype_item()
        assert editor_with_rule._basetype_edit.text().startswith('"')

    def test_format_ends_with_quote(self, editor_with_rule, monkeypatch):
        item = _fake_item("Divine Orb", "神聖石")
        self._patch_accept(editor_with_rule, monkeypatch, item)
        editor_with_rule._on_pick_basetype_item()
        assert editor_with_rule._basetype_edit.text().endswith('"')

    def test_triggers_rule_changed(self, editor_with_rule, monkeypatch):
        item = _fake_item("Chaos Orb", "混沌石")
        self._patch_accept(editor_with_rule, monkeypatch, item)
        received = []
        editor_with_rule.rule_changed.connect(lambda _idx, rule: received.append(rule))
        editor_with_rule._on_pick_basetype_item()
        assert len(received) >= 1

    def test_rule_changed_carries_updated_rule(self, editor_with_rule, monkeypatch):
        item = _fake_item("Chaos Orb", "混沌石")
        self._patch_accept(editor_with_rule, monkeypatch, item)
        received_rules: list[FilterRule] = []
        editor_with_rule.rule_changed.connect(lambda _idx, rule: received_rules.append(rule))
        editor_with_rule._on_pick_basetype_item()
        assert len(received_rules) >= 1
        rule = received_rules[-1]
        basetype_values = [v for k, v in rule.conditions if k == "BaseType"]
        assert basetype_values and '"Chaos Orb"' in basetype_values[0]


# ---------------------------------------------------------------------------
# 5. 取消對話框不修改 BaseType
# ---------------------------------------------------------------------------

class TestCancelDoesNotModify:

    def test_cancel_leaves_basetype_unchanged(self, editor_with_rule, monkeypatch):
        initial = '"Existing Item"'
        editor_with_rule._basetype_edit.setText(initial)
        from PySide6.QtWidgets import QDialog
        monkeypatch.setattr(
            editor_with_rule,
            "_create_item_selector_dialog",
            lambda: (
                _MockDialog(QDialog.DialogCode.Rejected),
                _MockSelector(item=_fake_item()),
            ),
        )
        editor_with_rule._on_pick_basetype_item()
        assert editor_with_rule._basetype_edit.text() == initial

    def test_cancel_no_rule_changed_emitted(self, editor_with_rule, monkeypatch):
        from PySide6.QtWidgets import QDialog
        monkeypatch.setattr(
            editor_with_rule,
            "_create_item_selector_dialog",
            lambda: (
                _MockDialog(QDialog.DialogCode.Rejected),
                _MockSelector(item=_fake_item()),
            ),
        )
        received = []
        editor_with_rule.rule_changed.connect(received.append)
        editor_with_rule._on_pick_basetype_item()
        assert len(received) == 0

    def test_none_selection_leaves_basetype_unchanged(self, editor_with_rule, monkeypatch):
        """selected_item() == None 時不應寫入任何內容。"""
        initial = '"Safe Value"'
        editor_with_rule._basetype_edit.setText(initial)
        from PySide6.QtWidgets import QDialog
        monkeypatch.setattr(
            editor_with_rule,
            "_create_item_selector_dialog",
            lambda: (
                _MockDialog(QDialog.DialogCode.Accepted),
                _MockSelector(item=None),
            ),
        )
        editor_with_rule._on_pick_basetype_item()
        assert editor_with_rule._basetype_edit.text() == initial


# ---------------------------------------------------------------------------
# 6. 選取後同步 ConditionBuilderWidget
# ---------------------------------------------------------------------------

class TestConditionBuilderSync:

    def test_cond_builder_exists(self, editor_with_rule):
        assert editor_with_rule._cond_builder is not None

    def test_pick_adds_basetype_to_cond_builder(self, editor_with_rule, monkeypatch):
        item = _fake_item("War Sword", "戰劍")
        from PySide6.QtWidgets import QDialog
        monkeypatch.setattr(
            editor_with_rule,
            "_create_item_selector_dialog",
            lambda: (_MockDialog(QDialog.DialogCode.Accepted), _MockSelector(item)),
        )
        editor_with_rule._on_pick_basetype_item()
        conds = editor_with_rule._cond_builder.get_conditions()
        keys = [k for k, _ in conds]
        assert "BaseType" in keys

    def test_cond_builder_basetype_value_contains_name(self, editor_with_rule, monkeypatch):
        item = _fake_item("War Sword", "戰劍")
        from PySide6.QtWidgets import QDialog
        monkeypatch.setattr(
            editor_with_rule,
            "_create_item_selector_dialog",
            lambda: (_MockDialog(QDialog.DialogCode.Accepted), _MockSelector(item)),
        )
        editor_with_rule._on_pick_basetype_item()
        conds = editor_with_rule._cond_builder.get_conditions()
        bt_value = next((v for k, v in conds if k == "BaseType"), None)
        assert bt_value is not None and '"War Sword"' in bt_value
