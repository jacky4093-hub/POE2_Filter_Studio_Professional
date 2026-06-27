"""Tests for RuleCreationDialog — v1.0.0  (P14.0 Rule Creation Wizard)

Covers:
- Dialog can be instantiated (headless)
- Template list contains all expected entries
- get_rule() returns the correct FilterRule for each template
- get_rule() returns None on cancel
- Returned rule is a deep copy of the prototype
- Double-click on item confirms dialog
- Browser integration: add button opens wizard, emits signals correctly
"""

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from core.models import FilterRule
from ui.rule_creation_dialog import RuleCreationDialog


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
# TestDialogConstruction
# ---------------------------------------------------------------------------

class TestDialogConstruction:

    def test_dialog_can_be_instantiated(self, qapp):
        dlg = RuleCreationDialog()
        assert dlg is not None

    def test_dialog_has_list_widget(self, qapp):
        from PySide6.QtWidgets import QListWidget
        dlg = RuleCreationDialog()
        assert hasattr(dlg, "_list")
        assert isinstance(dlg._list, QListWidget)

    def test_dialog_has_create_button(self, qapp):
        from PySide6.QtWidgets import QPushButton
        dlg = RuleCreationDialog()
        assert hasattr(dlg, "_btn_create")
        assert isinstance(dlg._btn_create, QPushButton)

    def test_dialog_has_cancel_button(self, qapp):
        from PySide6.QtWidgets import QPushButton
        dlg = RuleCreationDialog()
        assert hasattr(dlg, "_btn_cancel")
        assert isinstance(dlg._btn_cancel, QPushButton)


# ---------------------------------------------------------------------------
# TestTemplateList
# ---------------------------------------------------------------------------

class TestTemplateList:

    def test_template_count_is_7(self, qapp):
        dlg = RuleCreationDialog()
        assert dlg._list.count() == 7

    def test_template_names_returns_7_entries(self, qapp):
        dlg = RuleCreationDialog()
        assert len(dlg.template_names()) == 7

    def test_templates_include_currency(self, qapp):
        dlg = RuleCreationDialog()
        assert "Currency" in dlg.template_names()

    def test_templates_include_unique(self, qapp):
        dlg = RuleCreationDialog()
        names = dlg.template_names()
        assert any("Unique" in n for n in names)

    def test_templates_include_rare(self, qapp):
        dlg = RuleCreationDialog()
        names = dlg.template_names()
        assert any("Rare" in n for n in names)

    def test_templates_include_magic(self, qapp):
        dlg = RuleCreationDialog()
        names = dlg.template_names()
        assert any("Magic" in n for n in names)

    def test_templates_include_gem(self, qapp):
        dlg = RuleCreationDialog()
        assert "Gem" in dlg.template_names()

    def test_templates_include_waystone(self, qapp):
        dlg = RuleCreationDialog()
        assert "Waystone" in dlg.template_names()

    def test_templates_include_empty_rule(self, qapp):
        dlg = RuleCreationDialog()
        assert "空規則" in dlg.template_names()

    def test_default_selection_is_row_0(self, qapp):
        dlg = RuleCreationDialog()
        assert dlg._list.currentRow() == 0


# ---------------------------------------------------------------------------
# TestCreateRule — get_rule() with monkeypatched exec
# ---------------------------------------------------------------------------

class TestCreateRule:

    def test_get_rule_returns_filterrule_on_accept(self, qapp, monkeypatch):
        monkeypatch.setattr(RuleCreationDialog, "exec",
                            lambda self: QDialog.DialogCode.Accepted)
        result = RuleCreationDialog.get_rule()
        assert isinstance(result, FilterRule)

    def test_cancel_returns_none(self, qapp, monkeypatch):
        monkeypatch.setattr(RuleCreationDialog, "exec",
                            lambda self: QDialog.DialogCode.Rejected)
        result = RuleCreationDialog.get_rule()
        assert result is None

    def test_create_currency_rule(self, qapp, monkeypatch):
        monkeypatch.setattr(RuleCreationDialog, "exec",
                            lambda self: QDialog.DialogCode.Accepted)
        result = RuleCreationDialog.get_rule()  # row 0 = Currency
        assert result is not None
        assert any(k == "Class" and v == "Currency" for k, v in result.conditions)

    def test_create_unique_rule(self, qapp, monkeypatch):
        def mock_exec(self):
            self._list.setCurrentRow(1)  # Unique 物品
            return QDialog.DialogCode.Accepted
        monkeypatch.setattr(RuleCreationDialog, "exec", mock_exec)
        result = RuleCreationDialog.get_rule()
        assert result is not None
        assert any(k == "Rarity" and v == "Unique" for k, v in result.conditions)

    def test_create_rare_rule(self, qapp, monkeypatch):
        def mock_exec(self):
            self._list.setCurrentRow(2)  # Rare 物品
            return QDialog.DialogCode.Accepted
        monkeypatch.setattr(RuleCreationDialog, "exec", mock_exec)
        result = RuleCreationDialog.get_rule()
        assert result is not None
        assert any(k == "Rarity" and v == "Rare" for k, v in result.conditions)

    def test_create_magic_rule(self, qapp, monkeypatch):
        def mock_exec(self):
            self._list.setCurrentRow(3)  # Magic 物品
            return QDialog.DialogCode.Accepted
        monkeypatch.setattr(RuleCreationDialog, "exec", mock_exec)
        result = RuleCreationDialog.get_rule()
        assert result is not None
        assert any(k == "Rarity" and v == "Magic" for k, v in result.conditions)

    def test_create_gem_rule(self, qapp, monkeypatch):
        def mock_exec(self):
            self._list.setCurrentRow(4)  # Gem
            return QDialog.DialogCode.Accepted
        monkeypatch.setattr(RuleCreationDialog, "exec", mock_exec)
        result = RuleCreationDialog.get_rule()
        assert result is not None
        assert any(k == "Class" and v == "Gems" for k, v in result.conditions)

    def test_create_waystone_rule(self, qapp, monkeypatch):
        def mock_exec(self):
            self._list.setCurrentRow(5)  # Waystone
            return QDialog.DialogCode.Accepted
        monkeypatch.setattr(RuleCreationDialog, "exec", mock_exec)
        result = RuleCreationDialog.get_rule()
        assert result is not None
        assert any(k == "Class" and v == "Waystones" for k, v in result.conditions)

    def test_create_empty_rule(self, qapp, monkeypatch):
        def mock_exec(self):
            self._list.setCurrentRow(6)  # 空規則
            return QDialog.DialogCode.Accepted
        monkeypatch.setattr(RuleCreationDialog, "exec", mock_exec)
        result = RuleCreationDialog.get_rule()
        assert result is not None
        assert result.conditions == []

    def test_returned_rule_is_deep_copy(self, qapp, monkeypatch):
        monkeypatch.setattr(RuleCreationDialog, "exec",
                            lambda self: QDialog.DialogCode.Accepted)
        r1 = RuleCreationDialog.get_rule()
        r2 = RuleCreationDialog.get_rule()
        assert r1 is not r2
        # Mutating one should not affect the other or the template
        r1.conditions.append(["Extra", "val"])
        r2 = RuleCreationDialog.get_rule()
        assert ["Extra", "val"] not in r2.conditions

    def test_returned_rule_action_is_show(self, qapp, monkeypatch):
        monkeypatch.setattr(RuleCreationDialog, "exec",
                            lambda self: QDialog.DialogCode.Accepted)
        result = RuleCreationDialog.get_rule()
        assert result.action == "Show"

    def test_returned_rule_is_enabled(self, qapp, monkeypatch):
        monkeypatch.setattr(RuleCreationDialog, "exec",
                            lambda self: QDialog.DialogCode.Accepted)
        result = RuleCreationDialog.get_rule()
        assert result.enabled is True


# ---------------------------------------------------------------------------
# TestDialogInteraction
# ---------------------------------------------------------------------------

class TestDialogInteraction:

    def test_confirm_button_accepts(self, qapp):
        dlg = RuleCreationDialog()
        accepted_count = []
        dlg.accepted.connect(lambda: accepted_count.append(1))
        dlg._btn_create.click()
        assert len(accepted_count) == 1

    def test_cancel_button_rejects(self, qapp):
        dlg = RuleCreationDialog()
        rejected_count = []
        dlg.rejected.connect(lambda: rejected_count.append(1))
        dlg._btn_cancel.click()
        assert len(rejected_count) == 1

    def test_double_click_confirms(self, qapp):
        dlg = RuleCreationDialog()
        accepted_count = []
        dlg.accepted.connect(lambda: accepted_count.append(1))
        item = dlg._list.item(0)
        dlg._list.itemDoubleClicked.emit(item)
        assert len(accepted_count) == 1


# ---------------------------------------------------------------------------
# TestBrowserIntegration
# ---------------------------------------------------------------------------

class TestBrowserIntegration:

    def test_browser_has_add_from_wizard_signal(self, qapp):
        from ui.rule_card_browser import RuleCardBrowser
        browser = RuleCardBrowser()
        assert hasattr(browser, "add_rule_from_wizard")

    def test_add_button_opens_wizard(self, qapp, monkeypatch):
        from ui.rule_card_browser import RuleCardBrowser
        browser = RuleCardBrowser()
        wizard_calls: list = []
        currency_rule = FilterRule(action="Show", conditions=[["Class", "Currency"]])

        monkeypatch.setattr(
            RuleCreationDialog, "get_rule",
            lambda parent=None: (wizard_calls.append(True), currency_rule)[1],
        )

        browser._btn_add.click()
        assert len(wizard_calls) == 1

    def test_wizard_confirm_emits_add_from_wizard(self, qapp, monkeypatch):
        from ui.rule_card_browser import RuleCardBrowser
        browser = RuleCardBrowser()
        currency_rule = FilterRule(action="Show", conditions=[["Class", "Currency"]])

        monkeypatch.setattr(RuleCreationDialog, "get_rule", lambda parent=None: currency_rule)

        from_wizard: list[FilterRule] = []
        browser.add_rule_from_wizard.connect(lambda r: from_wizard.append(r))

        browser._btn_add.click()

        assert len(from_wizard) == 1
        assert from_wizard[0] is currency_rule

    def test_wizard_confirm_also_emits_add_requested(self, qapp, monkeypatch):
        from ui.rule_card_browser import RuleCardBrowser
        browser = RuleCardBrowser()
        currency_rule = FilterRule(action="Show", conditions=[["Class", "Currency"]])

        monkeypatch.setattr(RuleCreationDialog, "get_rule", lambda parent=None: currency_rule)

        add_requested: list = []
        browser.add_rule_requested.connect(lambda: add_requested.append(True))

        browser._btn_add.click()
        assert len(add_requested) == 1

    def test_wizard_cancel_does_not_emit_from_wizard(self, qapp, monkeypatch):
        from ui.rule_card_browser import RuleCardBrowser
        browser = RuleCardBrowser()

        monkeypatch.setattr(RuleCreationDialog, "get_rule", lambda parent=None: None)

        from_wizard: list = []
        browser.add_rule_from_wizard.connect(lambda r: from_wizard.append(r))

        browser._btn_add.click()
        assert from_wizard == []

    def test_wizard_cancel_does_not_emit_add_requested(self, qapp, monkeypatch):
        from ui.rule_card_browser import RuleCardBrowser
        browser = RuleCardBrowser()

        monkeypatch.setattr(RuleCreationDialog, "get_rule", lambda parent=None: None)

        add_requested: list = []
        browser.add_rule_requested.connect(lambda: add_requested.append(True))

        browser._btn_add.click()
        assert add_requested == []

    def test_wizard_emits_correct_template(self, qapp, monkeypatch):
        from ui.rule_card_browser import RuleCardBrowser
        browser = RuleCardBrowser()
        gem_rule = FilterRule(action="Show", conditions=[["Class", "Gems"]])

        monkeypatch.setattr(RuleCreationDialog, "get_rule", lambda parent=None: gem_rule)

        from_wizard: list[FilterRule] = []
        browser.add_rule_from_wizard.connect(lambda r: from_wizard.append(r))

        browser._btn_add.click()

        assert len(from_wizard) == 1
        assert any(k == "Class" and v == "Gems" for k, v in from_wizard[0].conditions)
