"""P17.10B Category Classification Cache tests.

Verifies:
  - RuleCardBrowser._category_cache is built by load_rules() (P17.10B-1)
  - RuleCardWidget accepts a pre-classified category (P17.10B-2)
  - _passes_filter() uses the cache (P17.10B-3)
  - update_single_card() updates cache per-rule (P17.10B-4)
  - pool_insert/remove/swap rebuild the cache (P17.10B-5)
  - Fast paths (P17.7/P17.8/P17.9) are not regressed

No global cache, no Document cache, no background threads.
"""

from __future__ import annotations

import copy
import pytest

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from core.models import FilterRule
from core.categorizer import Category, classify_rule
from core.quick_fix import QuickFix


# ──────────────────────────────────────────────────────────────────────
# Helpers / fixtures
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.fixture
def browser(qapp):
    from ui.rule_card_browser import RuleCardBrowser
    return RuleCardBrowser()


@pytest.fixture
def window(qapp, tmp_path):
    from core.settings_manager import SettingsManager
    from ui.main_window import MainWindow
    mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
    return MainWindow(settings_mgr=mgr)


def _rule(action="Show", conditions=None, enabled=True) -> FilterRule:
    return FilterRule(
        action=action,
        enabled=enabled,
        conditions=conditions or [["Class", '"Currency"']],
        actions=[],
        pre_lines=[],
        inline_comment="",
        unknown_lines=[],
    )


def _currency_rule() -> FilterRule:
    return _rule(conditions=[["Class", '"Currency"']])


def _gem_rule() -> FilterRule:
    return _rule(conditions=[["Class", '"Skill Gems"']])


def _load(window, tmp_path, text: str) -> None:
    f = tmp_path / "t.filter"
    f.write_text(text, encoding="utf-8")
    window.load_file(str(f))


# ──────────────────────────────────────────────────────────────────────
# Cache Correctness
# ──────────────────────────────────────────────────────────────────────

class TestCacheCorrectness:

    def test_load_rules_builds_category_cache(self, browser):
        """After load_rules(), _category_cache must match classify_rule() for every rule."""
        rules = [_currency_rule(), _gem_rule(), _rule(action="Hide")]
        browser.load_rules(rules, None)

        assert browser._category_cache, "Cache must be non-empty after load_rules()"
        for i, rule in enumerate(rules):
            if rule.action == "__TAIL__":
                continue
            expected = classify_rule(rule)
            assert browser._category_cache.get(i) == expected, \
                f"Cache[{i}] must equal classify_rule() result; " \
                f"got {browser._category_cache.get(i)!r}, expected {expected!r}"

    def test_rule_card_widget_uses_cached_category(self, qapp, monkeypatch):
        """If category is pre-classified, RuleCardWidget._refresh_display()
        must NOT call classify_rule() for that card."""
        from ui.rule_card_widget import RuleCardWidget
        from core import categorizer

        classify_calls = []
        original = categorizer.classify_rule
        monkeypatch.setattr(categorizer, "classify_rule", lambda r: classify_calls.append(r) or original(r))

        rule = _currency_rule()
        pre_cat = classify_rule(rule)

        # Monkeypatch the module-level reference inside rule_card_widget too
        import ui.rule_card_widget as rcw_mod
        monkeypatch.setattr(rcw_mod, "classify_rule", categorizer.classify_rule)

        before = len(classify_calls)
        card = RuleCardWidget(0, rule, 1, category=pre_cat)
        after = len(classify_calls)

        assert after == before, \
            "RuleCardWidget must NOT call classify_rule() when category is pre-supplied"

    def test_category_filter_uses_cache(self, browser):
        """Filtering by category must produce the same visible cards as classify_rule()."""
        rules = [_currency_rule(), _gem_rule(), _rule(conditions=[["BaseType", '"Mirror"']])]
        browser.load_rules(rules, None)

        target = classify_rule(rules[0])
        browser.set_category_filter(target)
        browser.refresh()

        # is_rule_visible() uses `not card.isHidden()` — correct for offscreen widgets
        visible = [idx for idx in browser._cards if browser.is_rule_visible(idx)]
        expected = [i for i, r in enumerate(rules)
                    if classify_rule(r) == target and r.action != "__TAIL__"]
        assert sorted(visible) == sorted(expected), \
            "Category filter via cache must select same cards as classify_rule()"

    def test_category_cache_excludes_tail_rules(self, browser):
        """__TAIL__ rules must NOT appear in _category_cache."""
        tail = FilterRule(action="__TAIL__", enabled=True, conditions=[],
                          actions=[], pre_lines=[], inline_comment="", unknown_lines=[])
        rules = [_currency_rule(), tail]
        browser.load_rules(rules, None)
        for idx, cat in browser._category_cache.items():
            assert browser._rules[idx].action != "__TAIL__", \
                "__TAIL__ rule must not appear in category cache"


# ──────────────────────────────────────────────────────────────────────
# Cache Invalidation
# ──────────────────────────────────────────────────────────────────────

class TestCacheInvalidation:

    def test_update_single_card_updates_cache(self, browser):
        """update_single_card() must update _category_cache[index] for the changed rule."""
        currency = _currency_rule()
        gem = _gem_rule()
        browser.load_rules([currency, gem], None)

        old_cat = browser._category_cache[0]
        updated_gem = _gem_rule()          # completely different category
        browser.update_single_card(0, updated_gem)

        new_cat = browser._category_cache[0]
        expected = classify_rule(updated_gem)
        assert new_cat == expected, \
            "Cache[0] must be updated to new rule's category after update_single_card()"
        assert new_cat != old_cat or old_cat == expected, \
            "Cache[0] must reflect the updated rule's category"

    def test_quick_fix_updates_cache(self, window, tmp_path):
        """After a quick-fix via fast path, the browser cache for that rule must be correct."""
        _load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        window._on_quick_fix_requested(0, QuickFix("修正為 60", "SetFontSize", "60"))
        updated_rule = window._doc.rules[0]
        expected_cat = classify_rule(updated_rule)
        cached_cat = window.rule_card_browser._category_cache.get(0)
        assert cached_cat == expected_cat, \
            "Cache must be updated after quick fix"

    def test_load_rules_replaces_old_cache(self, browser):
        """A second load_rules() call must fully replace the old cache."""
        browser.load_rules([_currency_rule()], None)
        old_cache_id = id(browser._category_cache)

        browser.load_rules([_gem_rule(), _gem_rule()], None)
        new_cache_id = id(browser._category_cache)

        assert len(browser._category_cache) == 2
        # Old currency entry (index 0) should now map to gem category
        assert browser._category_cache.get(0) == classify_rule(_gem_rule()), \
            "Second load_rules() must overwrite all previous cache entries"
        # The cache dict itself is replaced (not just updated in-place)
        assert new_cache_id != old_cache_id

    def test_pool_insert_rebuilds_cache(self, browser):
        """pool_insert_card() must rebuild _category_cache so inserted rule is cached."""
        rules = [_currency_rule(), _gem_rule()]
        browser.load_rules(rules, None)

        new_rule = _rule(conditions=[["BaseType", '"Mirror"']])
        new_rules = [new_rule] + rules
        browser.pool_insert_card(0, new_rule, new_rules)

        # Cache at index 0 must be the inserted rule's category
        assert browser._category_cache.get(0) == classify_rule(new_rule), \
            "Cache[0] must reflect inserted rule after pool_insert_card()"
        # All other entries must also be correct
        for i, rule in enumerate(new_rules):
            if rule.action != "__TAIL__":
                assert browser._category_cache.get(i) == classify_rule(rule), \
                    f"Cache[{i}] must be correct after pool_insert_card()"

    def test_pool_remove_rebuilds_cache(self, browser):
        """pool_remove_card() must rebuild _category_cache so indices stay correct."""
        rules = [_currency_rule(), _gem_rule(), _rule()]
        browser.load_rules(rules, None)

        new_rules = [rules[0], rules[2]]   # remove index 1
        browser.pool_remove_card(1, new_rules)

        for i, rule in enumerate(new_rules):
            if rule.action != "__TAIL__":
                assert browser._category_cache.get(i) == classify_rule(rule), \
                    f"Cache[{i}] must be correct after pool_remove_card()"
        assert 2 not in browser._category_cache, \
            "Old index 2 must not exist in cache after removing rule"

    def test_pool_swap_rebuilds_cache(self, browser):
        """pool_swap_cards() must rebuild _category_cache so swapped indices are correct."""
        currency = _currency_rule()
        gem = _gem_rule()
        rules = [currency, gem]
        browser.load_rules(rules, None)

        cat_before_0 = browser._category_cache[0]
        cat_before_1 = browser._category_cache[1]

        swapped_rules = [gem, currency]    # after swap
        browser.pool_swap_cards(0, 1, swapped_rules)

        # After swap: index 0 has gem, index 1 has currency
        assert browser._category_cache.get(0) == classify_rule(gem), \
            "Cache[0] must reflect gem rule after swap"
        assert browser._category_cache.get(1) == classify_rule(currency), \
            "Cache[1] must reflect currency rule after swap"


# ──────────────────────────────────────────────────────────────────────
# Fast Path Regression Guards
# ──────────────────────────────────────────────────────────────────────

class TestFastPathRegressionGuards:

    def test_update_single_card_does_not_call_load_rules(self, browser, monkeypatch):
        """update_single_card() must not call load_rules()."""
        rules = [_currency_rule()]
        browser.load_rules(rules, None)
        load_calls = []
        monkeypatch.setattr(browser, "load_rules",
                            lambda *a, **kw: load_calls.append(True))
        browser.update_single_card(0, _gem_rule())
        assert not load_calls

    def test_update_single_card_does_not_rebuild_pool(self, browser, monkeypatch):
        """update_single_card() must not call _rebuild_card_pool()."""
        rules = [_currency_rule()]
        browser.load_rules(rules, None)
        rebuild_calls = []
        monkeypatch.setattr(browser, "_rebuild_card_pool",
                            lambda: rebuild_calls.append(True))
        browser.update_single_card(0, _gem_rule())
        assert not rebuild_calls, \
            "_rebuild_card_pool() must NOT be called by update_single_card()"

    def test_quick_fix_still_uses_fast_path(self, window, tmp_path, monkeypatch):
        """P17.9B must still work: quick fix must use update_single_card, not load_rules."""
        _load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        reload_calls = []
        monkeypatch.setattr(window, "_reload_rule_list", lambda: reload_calls.append(1))
        window._on_quick_fix_requested(0, QuickFix("修正為 60", "SetFontSize", "60"))
        assert not reload_calls, "Quick fix must use fast path; must not call _reload_rule_list()"


# ──────────────────────────────────────────────────────────────────────
# Performance Guards
# ──────────────────────────────────────────────────────────────────────

class TestPerformanceGuards:

    def test_category_switch_reduces_classify_calls(self, browser, monkeypatch):
        """After load_rules(), switching category must NOT call classify_rule() per rule.

        The cache is built at load time; set_category_filter + refresh() should
        read from it instead of re-classifying every rule.
        """
        from core import categorizer as cat_mod

        rules = [_currency_rule() for _ in range(20)]
        # First, load with real classify_rule to fill cache
        browser.load_rules(rules, None)

        # Now spy on classify_rule AFTER cache is warm
        calls = []
        original = cat_mod.classify_rule
        monkeypatch.setattr(cat_mod, "classify_rule",
                            lambda r: calls.append(r) or original(r))
        import ui.rule_card_browser as rcb_mod
        monkeypatch.setattr(rcb_mod, "classify_rule", cat_mod.classify_rule)

        calls.clear()
        browser.set_category_filter(Category.CURRENCY)
        browser.refresh()
        after_switch = len(calls)

        assert after_switch < len(rules), (
            f"Category switch must call classify_rule() fewer times than rule count; "
            f"got {after_switch} calls for {len(rules)} rules"
        )

    def test_browser_refresh_uses_cache(self, browser, monkeypatch):
        """refresh() with an active category filter must not classify all rules from scratch."""
        from core import categorizer as cat_mod
        import ui.rule_card_browser as rcb_mod

        rules = [_currency_rule() for _ in range(10)]
        browser.load_rules(rules, None)
        browser.set_category_filter(Category.CURRENCY)

        classify_calls = []
        original = cat_mod.classify_rule
        monkeypatch.setattr(cat_mod, "classify_rule",
                            lambda r: classify_calls.append(r) or original(r))
        monkeypatch.setattr(rcb_mod, "classify_rule", cat_mod.classify_rule)

        classify_calls.clear()
        browser.refresh()
        n_classify = len(classify_calls)

        assert n_classify < len(rules), (
            f"refresh() must use cache; expected < {len(rules)} classify calls, "
            f"got {n_classify}"
        )

    def test_update_single_card_calls_classify_exactly_once(self, browser, monkeypatch):
        """update_single_card() must call classify_rule() exactly once for the changed rule."""
        from core import categorizer as cat_mod
        import ui.rule_card_browser as rcb_mod
        import ui.rule_card_widget as rcw_mod

        rules = [_currency_rule(), _gem_rule()]
        browser.load_rules(rules, None)

        classify_calls = []
        original = cat_mod.classify_rule
        monkeypatch.setattr(cat_mod, "classify_rule",
                            lambda r: classify_calls.append(r) or original(r))
        monkeypatch.setattr(rcb_mod, "classify_rule", cat_mod.classify_rule)
        monkeypatch.setattr(rcw_mod, "classify_rule", cat_mod.classify_rule)

        classify_calls.clear()
        browser.update_single_card(0, _gem_rule())
        assert len(classify_calls) == 1, (
            f"update_single_card() must classify exactly once; got {len(classify_calls)}"
        )
