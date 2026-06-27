"""Tests for MainWindow — P14.1 Wizard Integration

Covers:
- Template rules from the wizard are inserted into the document
- Conditions are preserved exactly as specified in the template
- Selection moves to the newly inserted rule
- _on_add_rule() (toolbar / old path) still inserts an empty rule
- Inserting at a specific selection places the rule after the selected one
"""

import pytest
from PySide6.QtWidgets import QApplication

from core.document import FilterDocument
from core.models import FilterRule
from ui.main_window import MainWindow


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
# Helpers
# ---------------------------------------------------------------------------

def _make_window(qapp) -> MainWindow:
    """Return a MainWindow wired to a fresh, empty FilterDocument."""
    window = MainWindow()
    window._doc = FilterDocument()
    window._section_map = None
    window._selected_index = -1
    window._editing_snapshot = None
    window.rule_card_browser.load_rules([], None)
    return window


def _non_tail_rules(window: MainWindow) -> list[FilterRule]:
    return [r for r in window._doc.rules if r.action != "__TAIL__"]


# ---------------------------------------------------------------------------
# TestWizardTemplateInsertion
# ---------------------------------------------------------------------------

class TestWizardTemplateInsertion:
    """add_rule_from_wizard signal → _on_add_rule_from_template → doc updated."""

    def test_currency_template_inserted(self, qapp):
        window = _make_window(qapp)
        rule = FilterRule(action="Show", conditions=[["Class", "Currency"]])
        window.rule_card_browser.add_rule_from_wizard.emit(rule)

        rules = _non_tail_rules(window)
        assert len(rules) == 1
        assert any(k == "Class" and v == "Currency" for k, v in rules[0].conditions)

    def test_gem_template_inserted(self, qapp):
        window = _make_window(qapp)
        rule = FilterRule(action="Show", conditions=[["Class", "Gems"]])
        window.rule_card_browser.add_rule_from_wizard.emit(rule)

        rules = _non_tail_rules(window)
        assert len(rules) == 1
        assert any(k == "Class" and v == "Gems" for k, v in rules[0].conditions)

    def test_unique_template_inserted(self, qapp):
        window = _make_window(qapp)
        rule = FilterRule(action="Show", conditions=[["Rarity", "Unique"]])
        window.rule_card_browser.add_rule_from_wizard.emit(rule)

        rules = _non_tail_rules(window)
        assert any(k == "Rarity" and v == "Unique" for k, v in rules[0].conditions)

    def test_empty_template_inserted(self, qapp):
        window = _make_window(qapp)
        rule = FilterRule(action="Show")
        window.rule_card_browser.add_rule_from_wizard.emit(rule)

        rules = _non_tail_rules(window)
        assert len(rules) == 1
        assert rules[0].conditions == []

    def test_waystone_template_inserted(self, qapp):
        window = _make_window(qapp)
        rule = FilterRule(action="Show", conditions=[["Class", "Waystones"]])
        window.rule_card_browser.add_rule_from_wizard.emit(rule)

        rules = _non_tail_rules(window)
        assert any(k == "Class" and v == "Waystones" for k, v in rules[0].conditions)

    def test_template_action_preserved(self, qapp):
        window = _make_window(qapp)
        rule = FilterRule(action="Hide", conditions=[["Class", "Currency"]])
        window.rule_card_browser.add_rule_from_wizard.emit(rule)

        rules = _non_tail_rules(window)
        assert rules[0].action == "Hide"

    def test_template_conditions_preserved_exactly(self, qapp):
        window = _make_window(qapp)
        rule = FilterRule(action="Show", conditions=[["Rarity", "Magic"], ["Class", "Gems"]])
        window.rule_card_browser.add_rule_from_wizard.emit(rule)

        rules = _non_tail_rules(window)
        assert rules[0].conditions == [["Rarity", "Magic"], ["Class", "Gems"]]


# ---------------------------------------------------------------------------
# TestWizardDocState
# ---------------------------------------------------------------------------

class TestWizardDocState:
    """Document and UI state after wizard insertion."""

    def test_doc_marked_dirty_after_wizard_insert(self, qapp):
        window = _make_window(qapp)
        rule = FilterRule(action="Show", conditions=[["Class", "Currency"]])
        window.rule_card_browser.add_rule_from_wizard.emit(rule)
        assert window._doc.dirty is True

    def test_selection_moves_to_new_wizard_rule(self, qapp):
        window = _make_window(qapp)
        rule = FilterRule(action="Show", conditions=[["Class", "Currency"]])
        window.rule_card_browser.add_rule_from_wizard.emit(rule)
        assert window._selected_index == 0

    def test_wizard_insert_inserts_after_selection(self, qapp):
        window = _make_window(qapp)
        # Pre-load two rules and select the first
        r0 = FilterRule(action="Show", conditions=[["Rarity", "Normal"]])
        r1 = FilterRule(action="Show", conditions=[["Rarity", "Rare"]])
        window._doc._rules.extend([r0, r1])
        window._selected_index = 0
        window.rule_card_browser.load_rules(window._doc.rules, None)

        template = FilterRule(action="Show", conditions=[["Class", "Currency"]])
        window.rule_card_browser.add_rule_from_wizard.emit(template)

        # Template should be at index 1 (after the selected r0)
        assert window._doc.rules[1].conditions == [["Class", "Currency"]]

    def test_visible_count_increments(self, qapp):
        window = _make_window(qapp)
        assert window._doc.visible_count == 0
        rule = FilterRule(action="Show", conditions=[["Class", "Currency"]])
        window.rule_card_browser.add_rule_from_wizard.emit(rule)
        assert window._doc.visible_count == 1


# ---------------------------------------------------------------------------
# TestOldAddRuleBackwardCompat
# ---------------------------------------------------------------------------

class TestOldAddRuleBackwardCompat:
    """_on_add_rule() (toolbar path) still works as before."""

    def test_on_add_rule_inserts_empty_rule(self, qapp):
        window = _make_window(qapp)
        window._on_add_rule()

        rules = _non_tail_rules(window)
        assert len(rules) == 1
        assert rules[0].action == "Show"
        assert rules[0].conditions == []

    def test_on_add_rule_marks_dirty(self, qapp):
        window = _make_window(qapp)
        window._on_add_rule()
        assert window._doc.dirty is True

    def test_on_add_rule_moves_selection(self, qapp):
        window = _make_window(qapp)
        window._on_add_rule()
        assert window._selected_index == 0

    def test_multiple_on_add_rule_calls(self, qapp):
        window = _make_window(qapp)
        window._on_add_rule()
        window._on_add_rule()
        assert window._doc.visible_count == 2

    def test_wizard_and_toolbar_add_independently(self, qapp):
        window = _make_window(qapp)
        window._on_add_rule()  # toolbar: inserts empty
        currency_rule = FilterRule(action="Show", conditions=[["Class", "Currency"]])
        window.rule_card_browser.add_rule_from_wizard.emit(currency_rule)  # wizard

        rules = _non_tail_rules(window)
        assert len(rules) == 2
        # First rule: empty (from toolbar)
        assert rules[0].conditions == []
        # Second rule: currency (from wizard, inserted after first)
        assert any(k == "Class" and v == "Currency" for k, v in rules[1].conditions)


# ---------------------------------------------------------------------------
# TestWizardSignalConnected
# ---------------------------------------------------------------------------

class TestWizardSignalConnected:
    """Verify MainWindow connects the new signal."""

    def test_add_rule_from_wizard_signal_connected(self, qapp):
        """Firing add_rule_from_wizard should change doc state (proves connection)."""
        window = _make_window(qapp)
        initial_count = window._doc.visible_count
        rule = FilterRule(action="Show")
        window.rule_card_browser.add_rule_from_wizard.emit(rule)
        assert window._doc.visible_count == initial_count + 1

    def test_on_add_rule_from_template_method_exists(self, qapp):
        window = _make_window(qapp)
        assert hasattr(window, "_on_add_rule_from_template")
        assert callable(window._on_add_rule_from_template)
