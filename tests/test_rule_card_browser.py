"""Tests for RuleCardBrowser and RuleCardWidget — v2.3.0

Covers:
- load_rules / set_rules
- category filter
- selection state
- highlight partial-update
- real_index mapping preserved after filter
- signal emission
- get_section_states / apply_section_states stubs
- P10: search filter, visible/total counts, highlight, selection behaviour
"""

import pytest
from PySide6.QtWidgets import QApplication

from core.models import FilterRule
from core.categorizer import Category
from core.sections import build_section_map
from ui.rule_card_browser import RuleCardBrowser
from ui.rule_card_widget import RuleCardWidget


# ---------------------------------------------------------------------------
# Session-scoped QApplication (offscreen, no display needed)
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
# TestLoadRules
# ---------------------------------------------------------------------------

class TestLoadRules:
    def test_empty_rules_no_cards(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([])
        assert len(b._cards) == 0

    def test_load_creates_cards(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _tail()]
        b.load_rules(rules)
        assert len(b._cards) == 2          # tail excluded

    def test_tail_excluded(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _tail()])
        assert 1 not in b._cards           # real_index 1 is __TAIL__

    def test_reload_replaces_cards(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_currency(), _tail()])
        first_card = b._cards.get(0)
        b.load_rules([_map_rule(), _tail()])
        # Previous card object is gone; new one is different
        assert b._cards.get(0) is not first_card

    def test_real_index_keys_match_doc_order(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _gem(), _tail()]
        b.load_rules(rules)
        assert set(b._cards.keys()) == {0, 1, 2}


# ---------------------------------------------------------------------------
# TestCategoryFilter
# ---------------------------------------------------------------------------

class TestRuleVisibility:
    def test_is_rule_visible_true_for_loaded_rule_and_false_for_missing(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _tail()]
        b.load_rules(rules)

        assert b.is_rule_visible(0) is True
        assert b.is_rule_visible(1) is True
        assert b.is_rule_visible(99) is False

    def test_is_rule_visible_false_after_category_filter(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _tail()]
        b.load_rules(rules)
        b.set_category_filter(Category.CURRENCY)

        assert b.is_rule_visible(0) is True
        assert b.is_rule_visible(1) is False

    def test_is_rule_visible_false_after_search_filter(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _tail()]
        b.load_rules(rules)
        b.set_search_filter("Waystones")

        assert b.is_rule_visible(0) is False
        assert b.is_rule_visible(1) is True


class TestCategoryFilter:
    def test_all_shows_everything(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _tail()]
        b.load_rules(rules)
        b.set_category_filter(Category.ALL)
        assert len(b._cards) == 2

    def test_none_shows_everything(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _tail()]
        b.load_rules(rules)
        b.set_category_filter(None)
        assert len(b._cards) == 2

    def test_currency_filter(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _currency(), _tail()]
        b.load_rules(rules)
        b.set_category_filter(Category.CURRENCY)
        assert 0 in b._cards
        assert 1 not in b._cards           # map excluded
        assert 2 in b._cards

    def test_maps_filter(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _gem(), _tail()]
        b.load_rules(rules)
        b.set_category_filter(Category.MAPS)
        assert 0 not in b._cards
        assert 1 in b._cards
        assert 2 not in b._cards

    def test_filter_with_no_match_shows_no_cards(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _tail()]
        b.load_rules(rules)
        b.set_category_filter(Category.GEMS)
        assert len(b._cards) == 0

    def test_same_filter_twice_is_noop(self, qapp):
        """Calling set_category_filter with same value must not rebuild."""
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _tail()]
        b.load_rules(rules)
        b.set_category_filter(Category.CURRENCY)
        first_card = b._cards.get(0)
        b.set_category_filter(Category.CURRENCY)   # should be no-op
        assert b._cards.get(0) is first_card


# ---------------------------------------------------------------------------
# TestRealIndexMapping
# ---------------------------------------------------------------------------

class TestRealIndexMapping:
    def test_real_index_preserved_after_filter(self, qapp):
        """real_index must reflect position in the document, not display order."""
        b = RuleCardBrowser()
        # doc: 0=currency, 1=map, 2=currency, 3=tail
        rules = [_currency(), _map_rule(), _currency(), _tail()]
        b.load_rules(rules)
        b.set_category_filter(Category.CURRENCY)
        # Only doc indices 0 and 2 should be present
        assert 0 in b._cards
        assert 2 in b._cards
        assert 1 not in b._cards

    def test_card_real_index_property(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _tail()]
        b.load_rules(rules)
        assert b._cards[0].real_index == 0
        assert b._cards[1].real_index == 1


# ---------------------------------------------------------------------------
# TestSelection
# ---------------------------------------------------------------------------

class TestSelection:
    def test_select_real_index_marks_selected(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _tail()]
        b.load_rules(rules)
        b.select_real_index(0)
        assert b._cards[0].property("cardSelected") is True

    def test_select_deselects_previous(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _tail()]
        b.load_rules(rules)
        b.select_real_index(0)
        b.select_real_index(1)
        assert b._cards[0].property("cardSelected") is False
        assert b._cards[1].property("cardSelected") is True

    def test_selected_real_updated(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _tail()]
        b.load_rules(rules)
        b.select_real_index(1)
        assert b._selected_real == 1

    def test_card_click_emits_signal(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _tail()]
        b.load_rules(rules)

        received: list[int] = []
        b.selected_rule_changed.connect(received.append)
        b._cards[0].clicked.emit(0)
        assert received == [0]

    def test_card_click_selects_card(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _tail()]
        b.load_rules(rules)
        b._cards[1].clicked.emit(1)
        assert b._cards[1].property("cardSelected") is True

    def test_selection_restored_on_refresh(self, qapp):
        b = RuleCardBrowser()
        rules = [_currency(), _map_rule(), _tail()]
        b.load_rules(rules)
        b.select_real_index(1)
        b.refresh()   # full rebuild
        assert b._cards[1].property("cardSelected") is True


# ---------------------------------------------------------------------------
# TestHighlights
# ---------------------------------------------------------------------------

class TestHighlights:
    def test_set_highlights_current(self, qapp):
        b = RuleCardBrowser()
        rules = [_rule() for _ in range(4)] + [_tail()]
        b.load_rules(rules)
        b.set_highlights({0, 1, 2}, current=1)
        assert b._cards[1].property("cardHighlight") == "current"

    def test_set_highlights_other_matches(self, qapp):
        b = RuleCardBrowser()
        rules = [_rule() for _ in range(4)] + [_tail()]
        b.load_rules(rules)
        b.set_highlights({0, 1, 2}, current=1)
        assert b._cards[0].property("cardHighlight") == "match"
        assert b._cards[2].property("cardHighlight") == "match"

    def test_set_highlights_non_match_untouched(self, qapp):
        b = RuleCardBrowser()
        rules = [_rule() for _ in range(4)] + [_tail()]
        b.load_rules(rules)
        b.set_highlights({0, 1}, current=0)
        hl = b._cards[3].property("cardHighlight")
        assert hl in ("none", None)

    def test_clear_highlights(self, qapp):
        b = RuleCardBrowser()
        rules = [_rule() for _ in range(3)] + [_tail()]
        b.load_rules(rules)
        b.set_highlights({0, 1, 2}, current=0)
        b.clear_highlights()
        for idx in (0, 1, 2):
            hl = b._cards[idx].property("cardHighlight")
            assert hl in ("none", None)

    def test_clear_resets_internal_state(self, qapp):
        b = RuleCardBrowser()
        rules = [_rule() for _ in range(3)] + [_tail()]
        b.load_rules(rules)
        b.set_highlights({0, 1, 2}, current=1)
        b.clear_highlights()
        assert b._highlight_matches == set()
        assert b._highlight_current == -1

    def test_highlights_restored_on_refresh(self, qapp):
        b = RuleCardBrowser()
        rules = [_rule() for _ in range(3)] + [_tail()]
        b.load_rules(rules)
        b.set_highlights({0, 1}, current=0)
        b.refresh()   # full rebuild must restore highlight
        assert b._cards[0].property("cardHighlight") == "current"
        assert b._cards[1].property("cardHighlight") == "match"

    def test_cursor_move_within_match_set(self, qapp):
        """Moving cursor from 0 → 1 inside {0,1,2}: 0 demoted, 1 promoted."""
        b = RuleCardBrowser()
        rules = [_rule() for _ in range(3)] + [_tail()]
        b.load_rules(rules)
        b.set_highlights({0, 1, 2}, current=0)
        b.set_highlights({0, 1, 2}, current=1)
        assert b._cards[1].property("cardHighlight") == "current"
        assert b._cards[0].property("cardHighlight") == "match"


# ---------------------------------------------------------------------------
# TestSectionStubs
# ---------------------------------------------------------------------------

class TestSectionStubs:
    def test_get_section_states_returns_empty(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _tail()])
        assert b.get_section_states() == {}

    def test_apply_section_states_noop(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _tail()])
        b.apply_section_states({0: False, 1: True})   # must not raise


# ---------------------------------------------------------------------------
# TestWithSections
# ---------------------------------------------------------------------------

SEP = "#================================================"


class TestWithSections:
    def _make_sectioned_rules(self):
        r0 = FilterRule(action="Show", pre_lines=[SEP, "# Currency", SEP],
                        conditions=[["Class", '"Currency"']])
        r1 = FilterRule(action="Hide", conditions=[["Class", '"Currency"']])
        r2 = FilterRule(action="Show", pre_lines=[SEP, "# Gems", SEP],
                        conditions=[["Class", '"Skill Gem"']])
        r3 = FilterRule(action="Show", conditions=[["Class", '"Skill Gem"']])
        tail = FilterRule(action="__TAIL__")
        return [r0, r1, r2, r3, tail]

    def test_sectioned_load_all_cards(self, qapp):
        rules = self._make_sectioned_rules()
        smap = build_section_map(rules)
        b = RuleCardBrowser()
        b.load_rules(rules, smap)
        assert len(b._cards) == 4   # 4 visible rules

    def test_sectioned_filter_gems_only(self, qapp):
        rules = self._make_sectioned_rules()
        smap = build_section_map(rules)
        b = RuleCardBrowser()
        b.load_rules(rules, smap)
        b.set_category_filter(Category.GEMS)
        assert 2 in b._cards
        assert 3 in b._cards
        assert 0 not in b._cards
        assert 1 not in b._cards


# ---------------------------------------------------------------------------
# TestRuleCardWidget (unit)
# ---------------------------------------------------------------------------

class TestRuleCardWidget:
    def test_initial_selected_false(self, qapp):
        rule = _currency()
        card = RuleCardWidget(0, rule, 1)
        assert card.property("cardSelected") is False

    def test_set_selected_true(self, qapp):
        rule = _currency()
        card = RuleCardWidget(0, rule, 1)
        card.set_selected(True)
        assert card.property("cardSelected") is True

    def test_set_selected_toggle(self, qapp):
        rule = _currency()
        card = RuleCardWidget(0, rule, 1)
        card.set_selected(True)
        card.set_selected(False)
        assert card.property("cardSelected") is False

    def test_initial_highlight_none(self, qapp):
        rule = _currency()
        card = RuleCardWidget(0, rule, 1)
        assert card.property("cardHighlight") == "none"

    def test_set_highlight_current(self, qapp):
        rule = _currency()
        card = RuleCardWidget(0, rule, 1)
        card.set_highlight("current")
        assert card.property("cardHighlight") == "current"

    def test_set_highlight_match(self, qapp):
        rule = _currency()
        card = RuleCardWidget(0, rule, 1)
        card.set_highlight("match")
        assert card.property("cardHighlight") == "match"

    def test_real_index_property(self, qapp):
        rule = _currency()
        card = RuleCardWidget(42, rule, 1)
        assert card.real_index == 42

    def test_disabled_rule_has_property(self, qapp):
        rule = FilterRule(action="Show", enabled=False)
        card = RuleCardWidget(0, rule, 1)
        assert card.property("cardDisabled") is True

    def test_enabled_rule_no_disabled_property(self, qapp):
        rule = FilterRule(action="Show", enabled=True)
        card = RuleCardWidget(0, rule, 1)
        assert not card.property("cardDisabled")


# ---------------------------------------------------------------------------
# TestSearchFilter — P10 search filter functionality
# ---------------------------------------------------------------------------

class TestSearchFilter:
    def test_set_search_filter_basic(self, qapp):
        """Basic search filter should show matching rules."""
        b = RuleCardBrowser()
        rules = [
            _rule(Class='"Currency"'),
            _rule(Class='"Skill Gem"'),
            _tail(),
        ]
        b.load_rules(rules)
        b.set_search_filter("Currency")
        # Only rule with 'Currency' visible
        assert 0 in b._cards
        assert 1 not in b._cards

    def test_clear_search_filter(self, qapp):
        """clear_search_filter should restore all cards."""
        b = RuleCardBrowser()
        rules = [
            _rule(Class='"Currency"'),
            _rule(Class='"Skill Gem"'),
            _tail(),
        ]
        b.load_rules(rules)
        b.set_search_filter("Currency")
        assert len(b._cards) == 1
        b.clear_search_filter()
        assert len(b._cards) == 2
        assert 0 in b._cards
        assert 1 in b._cards

    def test_get_visible_count(self, qapp):
        """get_visible_count should return number of visible cards."""
        b = RuleCardBrowser()
        rules = [
            _rule(Class='"Currency"'),
            _rule(Class='"Skill Gem"'),
            _rule(Class='"Currency"'),
            _tail(),
        ]
        b.load_rules(rules)
        assert b.get_visible_count() == 3
        b.set_search_filter("Currency")
        assert b.get_visible_count() == 2

    def test_get_total_count(self, qapp):
        """get_total_count should return count of all non-tail rules."""
        b = RuleCardBrowser()
        rules = [
            _rule(Class='"Currency"'),
            _rule(Class='"Skill Gem"'),
            _tail(),
        ]
        b.load_rules(rules)
        # Total is always 2 (non-tail rules), regardless of filters
        assert b.get_total_count() == 2
        b.set_search_filter("Currency")
        assert b.get_total_count() == 2

    def test_search_filter_with_options(self, qapp):
        """Search filter should respect options dict."""
        b = RuleCardBrowser()
        rules = [
            _rule(Class='"Currency"'),
            _rule(Class='"currency"'),  # lowercase
            _tail(),
        ]
        b.load_rules(rules)
        # Case-insensitive (default)
        b.set_search_filter("currency")
        assert b.get_visible_count() == 2
        # Case-sensitive
        b.set_search_filter("currency", {"match_case": True})
        assert b.get_visible_count() == 1

    def test_search_filter_empty_query(self, qapp):
        """Empty search query should show all cards."""
        b = RuleCardBrowser()
        rules = [_rule(), _rule(), _tail()]
        b.load_rules(rules)
        b.set_search_filter("")
        assert len(b._cards) == 2

    def test_search_filter_no_matches(self, qapp):
        """Search with no matches should show empty message."""
        b = RuleCardBrowser()
        rules = [
            _rule(Class='"Currency"'),
            _tail(),
        ]
        b.load_rules(rules)
        b.set_search_filter("Nonexistent")
        assert len(b._cards) == 0

    def test_search_filter_combined_with_category(self, qapp):
        """Both search and category filter should apply with AND logic."""
        b = RuleCardBrowser()
        rules = [
            _currency(),
            _currency(),
            _map_rule(),
            _gem(),
            _tail(),
        ]
        b.load_rules(rules)
        # Filter by category only
        b.set_category_filter(Category.CURRENCY)
        assert b.get_visible_count() == 2
        # Filter by category + search
        b.set_search_filter("Currency")
        # Search text "Currency" only in CURRENCY category rules
        assert 0 in b._cards
        assert 1 in b._cards
        assert 2 not in b._cards  # MAPS not in CURRENCY
        assert 3 not in b._cards  # GEMS not in CURRENCY

    def test_search_highlight_applied_to_matches(self, qapp):
        """Matching cards should get 'match' highlight when search active."""
        b = RuleCardBrowser()
        rules = [
            _rule(Class='"Currency"'),
            _rule(Class='"Skill Gem"'),
            _tail(),
        ]
        b.load_rules(rules)
        b.set_search_filter("Currency")
        assert b._cards[0].property("cardHighlight") == "match"
        assert 1 not in b._cards  # not visible

    def test_search_highlight_cleared_on_empty_query(self, qapp):
        """Highlight should clear when search is cleared."""
        b = RuleCardBrowser()
        rules = [_rule(), _rule(), _tail()]
        b.load_rules(rules)
        b.set_search_filter("Show")
        # Both visible and highlighted
        for idx in (0, 1):
            assert b._cards[idx].property("cardHighlight") == "match"
        b.clear_search_filter()
        # Highlight should be cleared
        for idx in (0, 1):
            hl = b._cards[idx].property("cardHighlight")
            assert hl in ("none", None)

    def test_search_preserves_selection_if_visible(self, qapp):
        """Selected rule should remain selected if still visible after search."""
        b = RuleCardBrowser()
        rules = [
            _rule(Class='"Currency"'),
            _rule(Class='"Currency"'),
            _rule(Class='"Skill Gem"'),
            _tail(),
        ]
        b.load_rules(rules)
        # Select first rule
        b.select_real_index(0)
        assert b._cards[0].property("cardSelected") is True
        # Search that includes the selected rule
        b.set_search_filter("Currency")
        # Selection should be preserved
        assert 0 in b._cards
        assert b._cards[0].property("cardSelected") is True

    def test_search_clears_selection_if_not_visible(self, qapp):
        """Selected rule should be deselected if filtered out by search."""
        b = RuleCardBrowser()
        rules = [
            _rule(Class='"Currency"'),
            _rule(Class='"Skill Gem"'),
            _tail(),
        ]
        b.load_rules(rules)
        # Select first rule (Currency)
        b.select_real_index(0)
        assert b._selected_real == 0
        # Search that excludes the selected rule
        b.set_search_filter("Gem")
        # Selection should be cleared
        assert 0 not in b._cards
        assert b._selected_real == -1

    def test_search_after_category_filter(self, qapp):
        """Applying search after category filter should apply both."""
        b = RuleCardBrowser()
        rules = [
            _currency(),
            _currency(),
            _map_rule(),
            _gem(),
            _tail(),
        ]
        b.load_rules(rules)
        # First set category filter
        b.set_category_filter(Category.CURRENCY)
        visible_after_cat = b.get_visible_count()
        assert visible_after_cat == 2
        # Then apply search
        b.set_search_filter("Currency")
        assert b.get_visible_count() == 2  # Both currencies match
        # Search text that wouldn't match
        b.set_search_filter("Gem")
        assert b.get_visible_count() == 0  # No gems in currency category

    def test_search_filter_refresh_restores_state(self, qapp):
        """Manual refresh should preserve search filter state."""
        b = RuleCardBrowser()
        rules = [_rule(), _rule(), _tail()]
        b.load_rules(rules)
        b.set_search_filter("Show")
        first_count = b.get_visible_count()
        b.refresh()
        assert b.get_visible_count() == first_count

    def test_empty_rules_with_search_shows_no_cards(self, qapp):
        """Searching with empty rules list should be safe."""
        b = RuleCardBrowser()
        b.load_rules([])
        b.set_search_filter("anything")
        assert len(b._cards) == 0

    def test_search_filter_status_query_property(self, qapp):
        """_search_query should track the current search query."""
        b = RuleCardBrowser()
        b.load_rules([_rule(), _tail()])
        assert b._search_query == ""
        b.set_search_filter("test")
        assert b._search_query == "test"
        b.clear_search_filter()
        assert b._search_query == ""

    def test_search_filter_status_options_property(self, qapp):
        """_search_options should track options."""
        b = RuleCardBrowser()
        b.load_rules([_rule(), _tail()])
        assert b._search_options == {}
        opts = {"match_case": True, "class": True}
        b.set_search_filter("test", opts)
        assert b._search_options == opts
        b.clear_search_filter()
        assert b._search_options == {}


# ---------------------------------------------------------------------------
# TestP135ButtonStates  (P13.5 新增)
# ---------------------------------------------------------------------------

class TestP135ButtonStates:
    """Action buttons are enabled / disabled based on selection and position."""

    # ── No selection ─────────────────────────────────────────────

    def test_no_selection_add_always_enabled(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        assert b._btn_add.isEnabled()

    def test_no_selection_del_disabled(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        assert not b._btn_del.isEnabled()

    def test_no_selection_copy_disabled(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        assert not b._btn_copy.isEnabled()

    def test_no_selection_up_disabled(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        assert not b._btn_up.isEnabled()

    def test_no_selection_down_disabled(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        assert not b._btn_dn.isEnabled()

    def test_empty_browser_all_move_disabled(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([])
        assert not b._btn_del.isEnabled()
        assert not b._btn_copy.isEnabled()
        assert not b._btn_up.isEnabled()
        assert not b._btn_dn.isEnabled()

    # ── Selection enables del / copy ─────────────────────────────

    def test_selection_enables_del(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        b.select_real_index(0)
        assert b._btn_del.isEnabled()

    def test_selection_enables_copy(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        b.select_real_index(0)
        assert b._btn_copy.isEnabled()

    # ── First item ───────────────────────────────────────────────

    def test_first_item_up_disabled(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        b.select_real_index(0)
        assert not b._btn_up.isEnabled()

    def test_first_item_down_enabled(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        b.select_real_index(0)
        assert b._btn_dn.isEnabled()

    # ── Last item ────────────────────────────────────────────────

    def test_last_item_down_disabled(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        b.select_real_index(1)   # real_index 1 is the last non-tail
        assert not b._btn_dn.isEnabled()

    def test_last_item_up_enabled(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        b.select_real_index(1)
        assert b._btn_up.isEnabled()

    # ── Single rule ──────────────────────────────────────────────

    def test_single_item_up_disabled(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _tail()])
        b.select_real_index(0)
        assert not b._btn_up.isEnabled()

    def test_single_item_down_disabled(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _tail()])
        b.select_real_index(0)
        assert not b._btn_dn.isEnabled()

    # ── Middle item ──────────────────────────────────────────────

    def test_middle_item_both_move_enabled(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _rule(), _tail()])
        b.select_real_index(1)   # middle
        assert b._btn_up.isEnabled()
        assert b._btn_dn.isEnabled()

    # ── Update via _on_card_clicked ───────────────────────────────

    def test_card_click_updates_button_states(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        # Click first card
        b._on_card_clicked(0)
        assert not b._btn_up.isEnabled()
        # Click second card
        b._on_card_clicked(1)
        assert b._btn_up.isEnabled()
        assert not b._btn_dn.isEnabled()

    # ── Manual _update_button_states ──────────────────────────────

    def test_manual_deselect_disables_all(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        b.select_real_index(0)
        b._selected_real = -1
        b._update_button_states()
        assert not b._btn_del.isEnabled()
        assert not b._btn_copy.isEnabled()
        assert not b._btn_up.isEnabled()
        assert not b._btn_dn.isEnabled()


# ---------------------------------------------------------------------------
# TestP135Tooltips  (P13.5 新增)
# ---------------------------------------------------------------------------

class TestP135Tooltips:
    """Every action button has a non-empty Chinese tooltip."""

    def test_add_button_has_tooltip(self, qapp):
        b = RuleCardBrowser()
        assert b._btn_add.toolTip() != ""

    def test_del_button_has_tooltip(self, qapp):
        b = RuleCardBrowser()
        assert b._btn_del.toolTip() != ""

    def test_copy_button_has_tooltip(self, qapp):
        b = RuleCardBrowser()
        assert b._btn_copy.toolTip() != ""

    def test_up_button_has_tooltip(self, qapp):
        b = RuleCardBrowser()
        assert b._btn_up.toolTip() != ""

    def test_down_button_has_tooltip(self, qapp):
        b = RuleCardBrowser()
        assert b._btn_dn.toolTip() != ""

    def test_del_tooltip_mentions_delete(self, qapp):
        b = RuleCardBrowser()
        assert "刪除" in b._btn_del.toolTip()

    def test_up_tooltip_mentions_move(self, qapp):
        b = RuleCardBrowser()
        assert "上移" in b._btn_up.toolTip() or "移" in b._btn_up.toolTip()

    def test_down_tooltip_mentions_move(self, qapp):
        b = RuleCardBrowser()
        assert "下移" in b._btn_dn.toolTip() or "移" in b._btn_dn.toolTip()


# ---------------------------------------------------------------------------
# TestP135DangerMarker  (P13.5 新增)
# ---------------------------------------------------------------------------

class TestP135DangerMarker:
    """Delete button is marked as danger; other buttons are not."""

    def test_del_button_object_name_is_BtnDanger(self, qapp):
        b = RuleCardBrowser()
        assert b._btn_del.objectName() == "BtnDanger"

    def test_add_button_not_danger(self, qapp):
        b = RuleCardBrowser()
        assert b._btn_add.objectName() != "BtnDanger"

    def test_copy_button_not_danger(self, qapp):
        b = RuleCardBrowser()
        assert b._btn_copy.objectName() != "BtnDanger"

    def test_up_button_not_danger(self, qapp):
        b = RuleCardBrowser()
        assert b._btn_up.objectName() != "BtnDanger"

    def test_down_button_not_danger(self, qapp):
        b = RuleCardBrowser()
        assert b._btn_dn.objectName() != "BtnDanger"


# ---------------------------------------------------------------------------
# TestP135MoveSignal  (P13.5 新增)
# ---------------------------------------------------------------------------

class TestP135MoveSignal:
    """Move buttons emit move_rule_requested with correct (from, to) indices."""

    def test_up_emits_move_rule_requested(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        received: list[tuple] = []
        b.move_rule_requested.connect(lambda fr, to: received.append((fr, to)))
        b.select_real_index(1)
        b._on_move_up()
        assert received == [(1, 0)]

    def test_down_emits_move_rule_requested(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        received: list[tuple] = []
        b.move_rule_requested.connect(lambda fr, to: received.append((fr, to)))
        b.select_real_index(0)
        b._on_move_down()
        assert received == [(0, 1)]

    def test_up_at_first_does_not_emit(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        received: list[tuple] = []
        b.move_rule_requested.connect(lambda fr, to: received.append((fr, to)))
        b.select_real_index(0)
        b._on_move_up()   # already at first — should not emit
        assert received == []

    def test_down_at_last_does_not_emit(self, qapp):
        b = RuleCardBrowser()
        b.load_rules([_rule(), _rule(), _tail()])
        received: list[tuple] = []
        b.move_rule_requested.connect(lambda fr, to: received.append((fr, to)))
        b.select_real_index(1)
        b._on_move_down()  # already at last — should not emit
        assert received == []

    def test_move_buttons_exist(self, qapp):
        b = RuleCardBrowser()
        assert hasattr(b, "_btn_up")
        assert hasattr(b, "_btn_dn")
