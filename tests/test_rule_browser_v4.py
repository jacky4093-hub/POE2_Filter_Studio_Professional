"""P18.3 Rule Browser V4 tests.

Sections:
  A. Visual structure — V4 header elements, badge system
  B. Performance guards — verify P17.7/P17.8 architecture is preserved
     (no extra widget creation on refresh/filter/single-card-update)
  C. Rule status display — Show/Hide/disabled states
  D. Active filter chip — header shows/hides based on filter state
"""

import pytest

from PySide6.QtWidgets import QApplication

from core.models import FilterRule
from core.categorizer import Category


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


# ── Helpers ────────────────────────────────────────────────────────────

def _rule(action: str = "Show", **conds) -> FilterRule:
    return FilterRule(action=action, conditions=[[k, v] for k, v in conds.items()])

def _currency() -> FilterRule:
    return _rule(Class='"Currency"')

def _gem() -> FilterRule:
    return _rule(Class='"Skill Gem"')

def _disabled() -> FilterRule:
    r = _currency()
    r.enabled = False
    return r

def _tail() -> FilterRule:
    return FilterRule(action="__TAIL__")

def _load(browser, rules):
    browser.load_rules(rules, None)


# ──────────────────────────────────────────────────────────────────────
# A. Visual structure
# ──────────────────────────────────────────────────────────────────────

class TestV4VisualStructure:
    @pytest.fixture
    def browser(self, qapp):
        from ui.rule_card_browser import RuleCardBrowser
        return RuleCardBrowser()

    def test_v4_header_widget_exists(self, browser):
        assert hasattr(browser, "_header")
        assert browser._header.objectName() == "RuleBrowserHeaderV4"

    def test_count_label_exists(self, browser):
        assert hasattr(browser, "_count_lbl")
        assert browser._count_lbl.objectName() == "RuleBrowserCount"

    def test_active_filter_chip_exists(self, browser):
        assert hasattr(browser, "_active_filter_lbl")
        assert browser._active_filter_lbl.objectName() == "RuleBrowserActiveFilterChip"

    def test_active_filter_hidden_on_init(self, browser):
        assert browser._active_filter_lbl.isHidden()

    def test_count_shows_after_load(self, browser):
        _load(browser, [_currency(), _gem()])
        text = browser._count_lbl.text()
        assert "2" in text

    def test_active_filter_shows_on_category_filter(self, browser):
        _load(browser, [_currency(), _gem()])
        browser.set_category_filter(Category.CURRENCY)
        assert not browser._active_filter_lbl.isHidden()
        assert "通貨" in browser._active_filter_lbl.text()

    def test_active_filter_hides_on_clear_filter(self, browser):
        _load(browser, [_currency(), _gem()])
        browser.set_category_filter(Category.CURRENCY)
        browser.set_category_filter(Category.ALL)
        assert browser._active_filter_lbl.isHidden()

    def test_active_filter_shows_on_search(self, browser):
        _load(browser, [_currency(), _gem()])
        browser.set_search_filter("Currency")
        assert not browser._active_filter_lbl.isHidden()
        assert "Currency" in browser._active_filter_lbl.text()

    def test_active_filter_hides_on_clear_search(self, browser):
        _load(browser, [_currency(), _gem()])
        browser.set_search_filter("Currency")
        browser.clear_search_filter()
        assert browser._active_filter_lbl.isHidden()

    def test_count_shows_filtered_fraction(self, browser):
        _load(browser, [_currency(), _currency(), _gem()])
        browser.set_category_filter(Category.CURRENCY)
        text = browser._count_lbl.text()
        # Should show "2 / 3" or similar
        assert "2" in text and "3" in text

    def test_count_no_fraction_when_all_visible(self, browser):
        _load(browser, [_currency(), _gem()])
        text = browser._count_lbl.text()
        # "2" but NOT "2 / 2"
        assert "2" in text
        # When unfiltered, no fraction separator
        assert "/" not in text


# ──────────────────────────────────────────────────────────────────────
# B. Performance guards — P17.7 / P17.8 architecture preserved
# ──────────────────────────────────────────────────────────────────────

class TestPerformanceGuards:
    @pytest.fixture
    def browser(self, qapp):
        from ui.rule_card_browser import RuleCardBrowser
        return RuleCardBrowser()

    def test_load_rules_builds_card_pool(self, browser):
        """load_rules() must create exactly N non-tail cards in _cards."""
        rules = [_currency(), _gem(), _tail()]
        _load(browser, rules)
        assert len(browser._cards) == 2   # tail excluded

    def test_refresh_does_not_create_new_cards(self, browser):
        """refresh() must NOT add or remove cards — only change visibility."""
        rules = [_currency(), _gem()]
        _load(browser, rules)
        card_ids_before = {id(c) for c in browser._cards.values()}

        browser.refresh()

        card_ids_after = {id(c) for c in browser._cards.values()}
        assert card_ids_before == card_ids_after, \
            "refresh() must reuse existing card objects, not create new ones"

    def test_category_filter_does_not_create_new_cards(self, browser):
        """set_category_filter() calls refresh() — must not allocate new widgets."""
        rules = [_currency(), _gem()]
        _load(browser, rules)
        card_ids_before = {id(c) for c in browser._cards.values()}

        browser.set_category_filter(Category.CURRENCY)
        browser.set_category_filter(Category.ALL)

        card_ids_after = {id(c) for c in browser._cards.values()}
        assert card_ids_before == card_ids_after, \
            "Category filter must reuse card objects, not create new ones"

    def test_update_single_card_is_inplace(self, browser):
        """update_single_card() must update the SAME widget, not replace it."""
        import copy
        rules = [_currency()]
        _load(browser, rules)
        original_card = browser._cards[0]

        updated_rule = copy.deepcopy(rules[0])
        updated_rule.inline_comment = "# updated"
        browser.update_single_card(0, updated_rule)

        assert browser._cards[0] is original_card, \
            "update_single_card() must update in-place, not replace the widget"

    def test_pool_insert_increments_card_count(self, browser):
        """pool_insert_card() must add exactly 1 card."""
        rules = [_currency(), _gem()]
        _load(browser, rules)
        count_before = len(browser._cards)

        new_rule = _rule(Class='"Map"')
        browser.pool_insert_card(1, new_rule, [_currency(), new_rule, _gem()])

        assert len(browser._cards) == count_before + 1

    def test_pool_insert_does_not_rebuild_existing_cards(self, browser):
        """pool_insert_card() must not replace existing card objects."""
        rules = [_currency(), _gem()]
        _load(browser, rules)
        existing_card_0 = browser._cards[0]  # first card before insert

        new_rule = _rule()
        # Insert at position 1; card 0 should be the same object
        browser.pool_insert_card(1, new_rule, [_currency(), new_rule, _gem()])

        assert browser._cards[0] is existing_card_0, \
            "pool_insert_card() must not destroy existing card widgets"

    def test_pool_remove_decrements_card_count(self, browser):
        """pool_remove_card() must remove exactly 1 card."""
        rules = [_currency(), _gem()]
        _load(browser, rules)
        count_before = len(browser._cards)

        browser.pool_remove_card(0, [_gem()])

        assert len(browser._cards) == count_before - 1

    def test_pool_swap_does_not_change_card_count(self, browser):
        """pool_swap_cards() must not add or remove cards."""
        rules = [_currency(), _gem()]
        _load(browser, rules)
        count_before = len(browser._cards)

        browser.pool_swap_cards(0, 1, [_gem(), _currency()])

        assert len(browser._cards) == count_before

    def test_load_rules_twice_replaces_pool_cleanly(self, browser):
        """Second load_rules() call must produce a fresh pool of the right size."""
        _load(browser, [_currency(), _gem()])
        _load(browser, [_gem(), _currency(), _currency()])
        assert len(browser._cards) == 3

    def test_refresh_does_not_call_load_rules(self, browser, monkeypatch):
        """Calling refresh() must NOT trigger load_rules()."""
        calls = []
        original_load = browser.load_rules
        monkeypatch.setattr(browser, "load_rules",
                            lambda *a, **kw: calls.append(True) or original_load(*a, **kw))

        _load(browser, [_currency()])
        calls.clear()          # ignore the initial load
        browser.refresh()

        assert not calls, "refresh() must not call load_rules()"


# ──────────────────────────────────────────────────────────────────────
# C. Rule status display
# ──────────────────────────────────────────────────────────────────────

class TestRuleStatusDisplay:
    @pytest.fixture
    def browser(self, qapp):
        from ui.rule_card_browser import RuleCardBrowser
        return RuleCardBrowser()

    def test_show_rule_card_has_correct_action(self, browser):
        _load(browser, [_rule("Show", Class='"Currency"')])
        card = browser._cards[0]
        assert card._action_badge_lbl.text() == "Show"

    def test_hide_rule_card_has_correct_action(self, browser):
        _load(browser, [_rule("Hide", Class='"Currency"')])
        card = browser._cards[0]
        assert card._action_badge_lbl.text() == "Hide"

    def test_disabled_rule_card_property(self, browser):
        _load(browser, [_disabled()])
        card = browser._cards[0]
        assert card.property("cardDisabled") is True

    def test_enabled_rule_card_property(self, browser):
        _load(browser, [_currency()])
        card = browser._cards[0]
        assert card.property("cardDisabled") is False

    def test_disabled_tag_visible_for_disabled_rule(self, browser):
        _load(browser, [_disabled()])
        card = browser._cards[0]
        assert not card._disabled_tag_lbl.isHidden()

    def test_disabled_tag_hidden_for_enabled_rule(self, browser):
        _load(browser, [_currency()])
        card = browser._cards[0]
        assert card._disabled_tag_lbl.isHidden()

    def test_number_label_format(self, browser):
        """V4 number format is '#N', not '[N]'."""
        _load(browser, [_currency(), _gem()])
        card_0 = browser._cards[0]
        card_1 = browser._cards[1]
        assert card_0._num_lbl.text() == "#1"
        assert card_1._num_lbl.text() == "#2"

    def test_category_badge_text(self, browser):
        """Category badge shows category label text."""
        _load(browser, [_currency()])
        card = browser._cards[0]
        assert "通貨" in card._cat_badge_lbl.text()


# ──────────────────────────────────────────────────────────────────────
# D. Badge system
# ──────────────────────────────────────────────────────────────────────

class TestBadgeSystem:
    @pytest.fixture
    def browser(self, qapp):
        from ui.rule_card_browser import RuleCardBrowser
        return RuleCardBrowser()

    def test_font_badge_visible_when_font_action_set(self, browser):
        r = FilterRule(action="Show", conditions=[["Class", '"Currency"']],
                       actions=[["SetFontSize", "36"]])
        _load(browser, [r])
        card = browser._cards[0]
        assert not card._fs_badge_lbl.isHidden()
        assert "36" in card._fs_badge_lbl.text()

    def test_font_badge_hidden_when_no_font_action(self, browser):
        _load(browser, [_currency()])
        card = browser._cards[0]
        assert card._fs_badge_lbl.isHidden()

    def test_sound_badge_visible_when_play_alert_set(self, browser):
        r = FilterRule(action="Show", conditions=[["Class", '"Currency"']],
                       actions=[["PlayAlertSound", "1 200"]])
        _load(browser, [r])
        card = browser._cards[0]
        assert not card._sound_badge_lbl.isHidden()

    def test_sound_badge_hidden_when_no_sound(self, browser):
        _load(browser, [_currency()])
        card = browser._cards[0]
        assert card._sound_badge_lbl.isHidden()

    def test_minimap_badge_visible_when_minimap_icon_set(self, browser):
        r = FilterRule(action="Show", conditions=[["Class", '"Currency"']],
                       actions=[["MinimapIcon", "0 Blue Circle"]])
        _load(browser, [r])
        card = browser._cards[0]
        assert not card._minimap_badge_lbl.isHidden()

    def test_minimap_badge_hidden_when_no_minimap(self, browser):
        _load(browser, [_currency()])
        card = browser._cards[0]
        assert card._minimap_badge_lbl.isHidden()

    def test_update_rule_updates_badges_inplace(self, browser):
        """update_rule() must refresh badge visibility without replacing the widget."""
        import copy
        r = _currency()
        _load(browser, [r])
        card = browser._cards[0]
        assert card._fs_badge_lbl.isHidden()

        updated = copy.deepcopy(r)
        updated.actions.append(["SetFontSize", "42"])
        card.update_rule(updated)

        assert not card._fs_badge_lbl.isHidden()
        assert "42" in card._fs_badge_lbl.text()
