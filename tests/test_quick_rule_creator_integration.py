"""P24.3 — QuickRuleCreatorDialog 整合測試。

涵蓋：
  1. 快速建立規則按鈕存在及屬性
  2. _on_quick_add 開啟 QuickRuleCreatorDialog（monkeypatch）
  3. dialog.exec() Accepted → add_rule_from_wizard 訊號攜帶 FilterRule
  4. dialog.exec() Rejected → 不發訊號、不插入 rule
  5. 插入後 rule list 數量增加（MainWindow 完整流程）
  6. 插入後新 rule 被選中
  7. 插入後 dirty 狀態為 True
  8. 有選中 rule 時插入到其下方
  9. 無選中 rule 時沿用既有邏輯（tail_insert_pos）
 10. 不破壞既有「＋ 新增」功能

所有測試使用 Qt offscreen 平台。
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from core.document import FilterDocument
from core.models import FilterRule


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


# ---------------------------------------------------------------------------
# Helpers（仿照 test_main_window.py 既有模式）
# ---------------------------------------------------------------------------

def _make_window(qapp):
    """建立帶有空文件的 MainWindow（不顯示）。"""
    from ui.main_window import MainWindow
    window = MainWindow()
    window._doc = FilterDocument()
    window._section_map = None
    window._selected_index = -1
    window._editing_snapshot = None
    window.rule_card_browser.load_rules([], None)
    return window


def _non_tail_rules(window) -> list[FilterRule]:
    return [r for r in window._doc.rules if r.action != "__TAIL__"]


def _add_rule_to_window(window, rule: FilterRule) -> None:
    """直接插入規則到文件並更新 browser（測試 setup 用）。"""
    from core.commands import AddRuleCommand
    from core.sections import build_section_map
    cmd = AddRuleCommand(window._doc, 0, rule)
    window._doc.execute(cmd)
    window._section_map = build_section_map(window._doc.rules)
    window.rule_card_browser.load_rules(window._doc.rules, window._section_map)


def _make_mock_dialog_class(result_code: int, rule: FilterRule | None = None):
    """回傳一個模擬 QuickRuleCreatorDialog 的假 class。"""
    class _MockQRC:
        def __init__(self, parent=None):
            self._created_rule = rule

        def exec(self) -> int:
            return result_code

    return _MockQRC


# ---------------------------------------------------------------------------
# 1. 快速建立規則按鈕存在及屬性
# ---------------------------------------------------------------------------

class TestQuickAddButtonExists:

    @pytest.fixture
    def browser(self, qapp):
        from ui.rule_card_browser import RuleCardBrowser
        b = RuleCardBrowser()
        b.load_rules([], None)
        return b

    def test_button_attribute_exists(self, browser):
        assert hasattr(browser, "_btn_quick_add")

    def test_button_objectname(self, browser):
        assert browser._btn_quick_add.objectName() == "BtnQuickAdd"

    def test_button_text_contains_keyword(self, browser):
        text = browser._btn_quick_add.text()
        assert "快速" in text or "建立" in text

    def test_button_always_enabled(self, browser):
        """快速建立規則按鈕不依賴 rule 選取，隨時可用。"""
        assert browser._btn_quick_add.isEnabled()

    def test_existing_add_button_still_exists(self, browser):
        assert hasattr(browser, "_btn_add")
        assert browser._btn_add.objectName() == "BtnAdd"


# ---------------------------------------------------------------------------
# 2. _on_quick_add 開啟 QuickRuleCreatorDialog
# ---------------------------------------------------------------------------

class TestQuickAddDialogCreation:

    @pytest.fixture
    def browser(self, qapp):
        from ui.rule_card_browser import RuleCardBrowser
        b = RuleCardBrowser()
        b.load_rules([], None)
        return b

    def test_on_quick_add_creates_quick_rule_creator_dialog(self, browser, monkeypatch):
        """_on_quick_add 應建立 QuickRuleCreatorDialog 實例。"""
        import ui.quick_rule_creator_dialog as qrc_module
        created: list = []

        class _MockQRC:
            def __init__(self, parent=None):
                created.append(self)
            def exec(self) -> int:
                return QDialog.DialogCode.Rejected

        monkeypatch.setattr(qrc_module, "QuickRuleCreatorDialog", _MockQRC)
        browser._on_quick_add()
        assert len(created) == 1


# ---------------------------------------------------------------------------
# 3 & 4. 訊號行為：Accepted / Rejected
# ---------------------------------------------------------------------------

class TestQuickAddSignals:

    @pytest.fixture
    def browser(self, qapp):
        from ui.rule_card_browser import RuleCardBrowser
        b = RuleCardBrowser()
        b.load_rules([], None)
        return b

    def test_accepted_emits_add_rule_from_wizard(self, browser, monkeypatch):
        import ui.quick_rule_creator_dialog as qrc_module
        rule = FilterRule(action="Show", enabled=True)
        monkeypatch.setattr(qrc_module, "QuickRuleCreatorDialog",
                            _make_mock_dialog_class(QDialog.DialogCode.Accepted, rule))
        received: list[FilterRule] = []
        browser.add_rule_from_wizard.connect(received.append)
        browser._on_quick_add()
        assert len(received) == 1
        assert received[0] is rule

    def test_accepted_also_emits_add_rule_requested(self, browser, monkeypatch):
        import ui.quick_rule_creator_dialog as qrc_module
        rule = FilterRule(action="Show", enabled=True)
        monkeypatch.setattr(qrc_module, "QuickRuleCreatorDialog",
                            _make_mock_dialog_class(QDialog.DialogCode.Accepted, rule))
        fired: list = []
        browser.add_rule_requested.connect(lambda: fired.append(1))
        browser._on_quick_add()
        assert len(fired) == 1

    def test_rejected_does_not_emit_add_rule_from_wizard(self, browser, monkeypatch):
        import ui.quick_rule_creator_dialog as qrc_module
        rule = FilterRule(action="Show", enabled=True)
        monkeypatch.setattr(qrc_module, "QuickRuleCreatorDialog",
                            _make_mock_dialog_class(QDialog.DialogCode.Rejected, rule))
        received: list = []
        browser.add_rule_from_wizard.connect(received.append)
        browser._on_quick_add()
        assert len(received) == 0

    def test_accepted_with_none_rule_does_not_emit(self, browser, monkeypatch):
        """_created_rule が None の場合はシグナルを発しない。"""
        import ui.quick_rule_creator_dialog as qrc_module
        monkeypatch.setattr(qrc_module, "QuickRuleCreatorDialog",
                            _make_mock_dialog_class(QDialog.DialogCode.Accepted, None))
        received: list = []
        browser.add_rule_from_wizard.connect(received.append)
        browser._on_quick_add()
        assert len(received) == 0


# ---------------------------------------------------------------------------
# 5–9. MainWindow 完整整合測試
# ---------------------------------------------------------------------------

class TestQuickAddIntegration:

    def _trigger_quick_add(self, window, monkeypatch, rule: FilterRule) -> None:
        """透過 monkeypatch 模擬 QuickRuleCreatorDialog 接受並觸發插入。"""
        import ui.quick_rule_creator_dialog as qrc_module
        monkeypatch.setattr(qrc_module, "QuickRuleCreatorDialog",
                            _make_mock_dialog_class(QDialog.DialogCode.Accepted, rule))
        window.rule_card_browser._on_quick_add()

    def test_rule_inserted_on_accept(self, qapp, monkeypatch):
        window = _make_window(qapp)
        rule = FilterRule(action="Show", enabled=True,
                          conditions=[["Class", '"Currency"']])
        self._trigger_quick_add(window, monkeypatch, rule)
        rules = _non_tail_rules(window)
        assert len(rules) == 1

    def test_rule_count_increases_on_accept(self, qapp, monkeypatch):
        window = _make_window(qapp)
        existing = FilterRule(action="Show", enabled=True)
        _add_rule_to_window(window, existing)
        count_before = len(_non_tail_rules(window))

        new_rule = FilterRule(action="Show", enabled=True)
        self._trigger_quick_add(window, monkeypatch, new_rule)

        assert len(_non_tail_rules(window)) == count_before + 1

    def test_no_rule_inserted_on_cancel(self, qapp, monkeypatch):
        import ui.quick_rule_creator_dialog as qrc_module
        window = _make_window(qapp)
        monkeypatch.setattr(qrc_module, "QuickRuleCreatorDialog",
                            _make_mock_dialog_class(QDialog.DialogCode.Rejected,
                                                    FilterRule()))
        window.rule_card_browser._on_quick_add()
        assert len(_non_tail_rules(window)) == 0

    def test_dirty_state_set_after_insert(self, qapp, monkeypatch):
        window = _make_window(qapp)
        rule = FilterRule(action="Show", enabled=True)
        self._trigger_quick_add(window, monkeypatch, rule)
        assert window._doc.dirty is True

    def test_new_rule_selected_after_insert(self, qapp, monkeypatch):
        window = _make_window(qapp)
        rule = FilterRule(action="Show", enabled=True)
        self._trigger_quick_add(window, monkeypatch, rule)
        # After insert, selected_index should point to the newly added rule
        assert window._selected_index >= 0

    def test_rule_conditions_preserved(self, qapp, monkeypatch):
        """建立後，插入的規則應保留原始條件。"""
        window = _make_window(qapp)
        rule = FilterRule(action="Show", enabled=True,
                          conditions=[["Class", '"Currency"'],
                                      ["SetFontSize", "45"]])
        self._trigger_quick_add(window, monkeypatch, rule)
        inserted = _non_tail_rules(window)[0]
        assert any(k == "Class" for k, _ in inserted.conditions)


# ---------------------------------------------------------------------------
# 8. 插入位置
# ---------------------------------------------------------------------------

class TestInsertionPosition:

    def _trigger_quick_add(self, window, monkeypatch, rule: FilterRule) -> None:
        import ui.quick_rule_creator_dialog as qrc_module
        monkeypatch.setattr(qrc_module, "QuickRuleCreatorDialog",
                            _make_mock_dialog_class(QDialog.DialogCode.Accepted, rule))
        window.rule_card_browser._on_quick_add()

    def test_inserts_after_selected_rule(self, qapp, monkeypatch):
        """有選中 rule 時，新 rule 插入到其下方（selected_index + 1）。"""
        window = _make_window(qapp)
        # 先新增 2 條 rule 作為底層資料
        for _ in range(2):
            _add_rule_to_window(window, FilterRule(action="Show", enabled=True))

        # 發出 selected_rule_changed 訊號以更新 window._selected_index
        window.rule_card_browser.selected_rule_changed.emit(0)

        new_rule = FilterRule(action="Hide", enabled=True)
        self._trigger_quick_add(window, monkeypatch, new_rule)

        # 新 rule 應在 index 1（selected 0 的下方）
        rules = _non_tail_rules(window)
        assert rules[1].action == "Hide"

    def test_inserts_at_tail_when_no_selection(self, qapp, monkeypatch):
        """無選中 rule 時，沿用既有 tail_insert_pos 邏輯（加到最後）。"""
        window = _make_window(qapp)
        _add_rule_to_window(window, FilterRule(action="Show", enabled=True))
        window._selected_index = -1   # 明確設為無選取

        new_rule = FilterRule(action="Hide", enabled=True)
        self._trigger_quick_add(window, monkeypatch, new_rule)

        rules = _non_tail_rules(window)
        assert len(rules) == 2
        assert rules[-1].action == "Hide"


# ---------------------------------------------------------------------------
# 10. 不破壞既有「＋ 新增」功能
# ---------------------------------------------------------------------------

class TestExistingAddFunctionUnaffected:

    def test_existing_add_rule_via_signal_still_works(self, qapp):
        """emit add_rule_from_wizard（既有流程）依然正確插入 rule。"""
        window = _make_window(qapp)
        rule = FilterRule(action="Show", conditions=[["Class", '"Gems"']])
        window.rule_card_browser.add_rule_from_wizard.emit(rule)
        rules = _non_tail_rules(window)
        assert len(rules) == 1
        assert any(k == "Class" for k, _ in rules[0].conditions)

    def test_existing_on_add_rule_method_still_works(self, qapp):
        """_on_add_rule（toolbar 路徑）依然插入空白 rule。"""
        window = _make_window(qapp)
        window._on_add_rule()
        rules = _non_tail_rules(window)
        assert len(rules) == 1
        assert rules[0].action == "Show"
