"""Tests for MainWindow P10 integration — P10 search and quick filter

Covers:
- SearchBarWidget integration
- RuleCardBrowser search filter interaction
- result count display
- category + search combined behavior
- welcome screen doesn't crash with search features
"""

import pytest
from PySide6.QtWidgets import QApplication

from core.models import FilterRule
from core.categorizer import Category
from core.sections import build_section_map
from ui.main_window import MainWindow


# ---------------------------------------------------------------------------
# Session-scoped QApplication
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

def _rule(action: str = "Show", **conditions) -> FilterRule:
    conds = [[k, v] for k, v in conditions.items()]
    return FilterRule(action=action, conditions=conds)


def _currency(action: str = "Show") -> FilterRule:
    return _rule(action=action, Class='"Currency"')


def _map_rule(action: str = "Show") -> FilterRule:
    return _rule(action=action, Class='"Waystones"')


def _gem(action: str = "Show") -> FilterRule:
    return _rule(action=action, Class='"Skill Gem"')


def _tail() -> FilterRule:
    return FilterRule(action="__TAIL__")


# ---------------------------------------------------------------------------
# TestMainWindowP10Integration
# ---------------------------------------------------------------------------

class TestMainWindowP10Integration:
    def test_main_window_has_search_bar_widget(self, qapp):
        """MainWindow should have filter_search_bar (SearchBarWidget)."""
        w = MainWindow()
        assert w.filter_search_bar is not None
        assert hasattr(w.filter_search_bar, 'search_changed')
        assert hasattr(w.filter_search_bar, 'clear_requested')

    def test_main_window_has_rule_card_browser(self, qapp):
        """MainWindow should have rule_card_browser (RuleCardBrowser)."""
        w = MainWindow()
        assert w.rule_card_browser is not None
        assert hasattr(w.rule_card_browser, 'set_search_filter')
        assert hasattr(w.rule_card_browser, 'get_visible_count')

    def test_search_filter_updates_visible_count(self, qapp):
        """Applying search filter should update visible count in search bar."""
        w = MainWindow()
        rules = [
            _currency(),
            _currency(),
            _gem(),
            _tail(),
        ]
        w.rule_card_browser.load_rules(rules)
        w._update_filter_search_count()
        
        # Before search: 3 visible, 3 total
        assert w.rule_card_browser.get_visible_count() == 3
        assert w.rule_card_browser.get_total_count() == 3
        
        # Apply search
        w.rule_card_browser.set_search_filter("Currency")
        w._update_filter_search_count()
        
        # After search: 2 visible, 3 total
        assert w.rule_card_browser.get_visible_count() == 2
        assert w.rule_card_browser.get_total_count() == 3

    def test_search_bar_emits_search_changed_signal(self, qapp):
        """SearchBarWidget search_changed signal should connect to handler."""
        w = MainWindow()
        rules = [_currency(), _gem(), _tail()]
        w.rule_card_browser.load_rules(rules)
        
        # Emit search_changed signal manually
        w.filter_search_bar.search_changed.emit("Currency", {})
        
        # Should filter cards
        assert 0 in w.rule_card_browser._cards
        assert 1 not in w.rule_card_browser._cards

    def test_search_bar_clear_button_handler(self, qapp):
        """Clicking clear button should clear search filter."""
        w = MainWindow()
        rules = [_currency(), _gem(), _tail()]
        w.rule_card_browser.load_rules(rules)
        
        # Apply search
        w.rule_card_browser.set_search_filter("Currency")
        assert w.rule_card_browser.get_visible_count() == 1
        
        # Emit clear_requested signal
        w.filter_search_bar.clear_requested.emit()
        
        # Should restore all cards
        assert w.rule_card_browser.get_visible_count() == 2

    def test_category_filter_with_search_combined(self, qapp):
        """Category filter + search should apply with AND logic."""
        w = MainWindow()
        rules = [
            _currency(),
            _currency(),
            _gem(),
            _tail(),
        ]
        w.rule_card_browser.load_rules(rules)
        
        # Set category filter
        w.rule_card_browser.set_category_filter(Category.CURRENCY)
        assert w.rule_card_browser.get_visible_count() == 2
        
        # Add search filter
        w.filter_search_bar.search_changed.emit("Currency", {})
        assert w.rule_card_browser.get_visible_count() == 2
        
        # Search for gem (not in currency category)
        w.filter_search_bar.search_changed.emit("Gem", {})
        assert w.rule_card_browser.get_visible_count() == 0

    def test_search_preserves_selection_on_matching_rule(self, qapp):
        """Search should preserve selection if rule still matches."""
        w = MainWindow()
        rules = [
            _currency(),
            _gem(),
            _tail(),
        ]
        w.rule_card_browser.load_rules(rules)
        
        # Select currency rule
        w.rule_card_browser.select_real_index(0)
        assert w.rule_card_browser._selected_real == 0
        
        # Search that includes the selected rule
        w.filter_search_bar.search_changed.emit("Currency", {})
        assert 0 in w.rule_card_browser._cards
        assert w.rule_card_browser._selected_real == 0

    def test_search_clears_selection_on_filtered_rule(self, qapp):
        """Search should clear selection if rule is filtered out."""
        w = MainWindow()
        rules = [
            _currency(),
            _gem(),
            _tail(),
        ]
        w.rule_card_browser.load_rules(rules)
        
        # Select currency rule
        w.rule_card_browser.select_real_index(0)
        assert w.rule_card_browser._selected_real == 0
        
        # Search that excludes the selected rule
        w.filter_search_bar.search_changed.emit("Gem", {})
        assert 0 not in w.rule_card_browser._cards
        assert w.rule_card_browser._selected_real == -1
        # Should also clear the editor
        assert w._selected_index == -1

    def test_welcome_screen_with_search_features(self, qapp):
        """Welcome screen should not crash with search features present."""
        w = MainWindow()
        # Should start on welcome screen
        assert w._main_stack.currentIndex() == 0
        # Search bar should exist but not crash
        w.filter_search_bar.search_changed.emit("test", {})
        # Should still be on welcome screen
        assert w._main_stack.currentIndex() == 0

    def test_empty_load_with_search_no_crash(self, qapp):
        """Loading empty rules with search active should not crash."""
        w = MainWindow()
        rules = [_currency(), _tail()]
        w.rule_card_browser.load_rules(rules)
        
        # Apply search first
        w.filter_search_bar.search_changed.emit("Currency", {})
        assert w.rule_card_browser.get_visible_count() == 1
        
        # Then load empty rules
        w.rule_card_browser.load_rules([])
        assert w.rule_card_browser.get_visible_count() == 0
        assert w.rule_card_browser.get_total_count() == 0

    def test_section_display_with_search_filter(self, qapp):
        """Search filter should work with sectioned rules."""
        w = MainWindow()
        sep = "#================================================"
        
        r0 = FilterRule(action="Show", pre_lines=[sep, "# Currency", sep],
                       conditions=[["Class", '"Currency"']])
        r1 = FilterRule(action="Hide", conditions=[["Class", '"Currency"']])
        r2 = FilterRule(action="Show", pre_lines=[sep, "# Gems", sep],
                       conditions=[["Class", '"Skill Gem"']])
        r3 = FilterRule(action="Show", conditions=[["Class", '"Skill Gem"']])
        tail = FilterRule(action="__TAIL__")
        
        rules = [r0, r1, r2, r3, tail]
        smap = build_section_map(rules)
        w.rule_card_browser.load_rules(rules, smap)
        
        # Load all 4 rules (plus section headers)
        assert w.rule_card_browser.get_total_count() == 4
        assert w.rule_card_browser.get_visible_count() == 4
        
        # Search for currency only
        w.filter_search_bar.search_changed.emit("Currency", {})
        assert w.rule_card_browser.get_visible_count() == 2
        
        # Clear search
        w.filter_search_bar.clear_requested.emit()
        assert w.rule_card_browser.get_visible_count() == 4

    def test_result_count_display_updates(self, qapp):
        """Result count display in search bar should update."""
        w = MainWindow()
        rules = [_currency(), _gem(), _currency(), _tail()]
        w.rule_card_browser.load_rules(rules)
        
        # Initial count: 3 visible, 3 total
        w._update_filter_search_count()
        
        # Apply search
        w.rule_card_browser.set_search_filter("Currency")
        w._update_filter_search_count()
        
        # Search bar should show updated count
        visible = w.rule_card_browser.get_visible_count()
        total = w.rule_card_browser.get_total_count()
        assert visible == 2
        assert total == 3

    def test_rapid_search_changes(self, qapp):
        """Rapid search changes should be handled correctly."""
        w = MainWindow()
        rules = [_currency(), _gem(), _tail()]
        w.rule_card_browser.load_rules(rules)
        
        # Rapid search changes
        w.filter_search_bar.search_changed.emit("Currency", {})
        assert w.rule_card_browser.get_visible_count() == 1
        
        w.filter_search_bar.search_changed.emit("Gem", {})
        assert w.rule_card_browser.get_visible_count() == 1
        
        w.filter_search_bar.search_changed.emit("", {})
        assert w.rule_card_browser.get_visible_count() == 2

    def test_search_with_case_sensitivity_option(self, qapp):
        """Search should respect case sensitivity option."""
        w = MainWindow()
        rules = [
            _rule(Class='"Currency"'),
            _rule(Class='"currency"'),
            _tail(),
        ]
        w.rule_card_browser.load_rules(rules)
        
        # Case-insensitive search
        w.filter_search_bar.search_changed.emit("currency", {})
        assert w.rule_card_browser.get_visible_count() == 2
        
        # Case-sensitive search
        w.filter_search_bar.search_changed.emit("currency", {"match_case": True})
        assert w.rule_card_browser.get_visible_count() == 1

    def test_search_bar_result_count_setter(self, qapp):
        """SearchBarWidget set_result_count should work."""
        w = MainWindow()
        # Should not crash
        w.filter_search_bar.set_result_count(5, 10)
        w.filter_search_bar.set_result_count(0, 3)

    def test_no_cards_message_on_search_filter(self, qapp):
        """Should show appropriate message when search has no matches."""
        w = MainWindow()
        rules = [_currency(), _tail()]
        w.rule_card_browser.load_rules(rules)
        
        # Search with no matches
        w.filter_search_bar.search_changed.emit("Nonexistent", {})
        assert w.rule_card_browser.get_visible_count() == 0
        # Browser should display "no matching" message (verified by empty cards dict)

    def test_search_filter_clears_on_reload(self, qapp):
        """Loading new file should work correctly with search state."""
        w = MainWindow()
        
        # Load initial rules
        rules1 = [_currency(), _gem(), _tail()]
        w.rule_card_browser.load_rules(rules1)
        w.filter_search_bar.search_changed.emit("Currency", {})
        assert w.rule_card_browser.get_visible_count() == 1
        
        # Load new rules (simulates open_file)
        rules2 = [_gem(), _gem(), _tail()]
        w.rule_card_browser.load_rules(rules2)
        # After reload with same search, no matches
        assert w.rule_card_browser.get_visible_count() == 0
        
        # Clear and verify
        w.filter_search_bar.clear_requested.emit()
        assert w.rule_card_browser.get_visible_count() == 2
