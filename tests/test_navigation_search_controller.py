"""Tests for NavigationSearchController — P12.3

Covers:
- SearchState dataclass properties
- run_search: basic match, empty query, no match, category filter, cursor init
- next / prev: advance, wrap-around, noop when empty, single result
- refresh: cursor preserved, cursor reset when gone, empty query
- reset: clears state
- MainWindow facade methods still exist (smoke test)
"""

import pytest

from core.models import FilterRule
from controllers.navigation_search_controller import NavigationSearchController, SearchState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rule(action: str = "Show", cls: str = "") -> FilterRule:
    conditions = [["Class", cls]] if cls else []
    return FilterRule(action=action, conditions=conditions)


def _currency() -> FilterRule:
    return _rule(cls='"Currency"')


def _gem() -> FilterRule:
    return _rule(cls='"Gem"')


def _tail() -> FilterRule:
    return FilterRule(action="__TAIL__")


def _ctrl() -> NavigationSearchController:
    return NavigationSearchController()


# ---------------------------------------------------------------------------
# TestSearchState
# ---------------------------------------------------------------------------

class TestSearchState:
    def test_default_is_empty(self):
        s = SearchState()
        assert s.results == []
        assert s.cursor == -1
        assert s.has_results is False
        assert s.current_real == -1
        assert s.total == 0
        assert s.position == 0

    def test_with_results(self):
        s = SearchState(results=[2, 5, 8], cursor=1)
        assert s.has_results is True
        assert s.current_real == 5
        assert s.total == 3
        assert s.position == 2

    def test_cursor_zero(self):
        s = SearchState(results=[10, 20], cursor=0)
        assert s.current_real == 10
        assert s.position == 1

    def test_cursor_last(self):
        s = SearchState(results=[0, 1, 2], cursor=2)
        assert s.current_real == 2
        assert s.position == 3

    def test_empty_results_current_real_minus_one(self):
        s = SearchState(results=[], cursor=0)
        assert s.current_real == -1
        assert s.position == 0


# ---------------------------------------------------------------------------
# TestRunSearch
# ---------------------------------------------------------------------------

class TestRunSearch:
    def test_empty_query_returns_empty_state(self):
        rules = [_currency(), _gem()]
        state = _ctrl().run_search(rules, "")
        assert state.results == []
        assert state.cursor == -1

    def test_whitespace_query_returns_empty_state(self):
        rules = [_currency()]
        state = _ctrl().run_search(rules, "   ")
        assert state.results == []

    def test_matching_query_returns_correct_indices(self):
        rules = [_currency(), _gem(), _currency(), _tail()]
        state = _ctrl().run_search(rules, "Currency")
        assert state.results == [0, 2]
        assert state.cursor == 0
        assert state.current_real == 0

    def test_no_match_returns_empty(self):
        rules = [_gem()]
        state = _ctrl().run_search(rules, "Currency")
        assert state.results == []
        assert state.cursor == -1

    def test_tail_excluded(self):
        rules = [_tail()]
        state = _ctrl().run_search(rules, "TAIL")
        assert state.results == []

    def test_cursor_starts_at_zero_on_match(self):
        rules = [_currency(), _currency()]
        state = _ctrl().run_search(rules, "Currency")
        assert state.cursor == 0

    def test_total_and_position(self):
        rules = [_currency(), _currency(), _currency()]
        state = _ctrl().run_search(rules, "Currency")
        assert state.total == 3
        assert state.position == 1

    def test_category_filter_restricts_results(self):
        rules = [_currency(), _currency(), _currency()]
        # Only allow index 1
        state = _ctrl().run_search(rules, "Currency", lambda idxs: [i for i in idxs if i == 1])
        assert state.results == [1]
        assert state.cursor == 0
        assert state.current_real == 1

    def test_category_filter_excludes_all(self):
        rules = [_currency()]
        state = _ctrl().run_search(rules, "Currency", lambda idxs: [])
        assert state.results == []

    def test_none_category_filter_includes_all(self):
        rules = [_currency(), _gem()]
        state = _ctrl().run_search(rules, "Currency")
        assert state.results == [0]

    def test_case_insensitive_by_default(self):
        rules = [_currency()]
        state = _ctrl().run_search(rules, "currency")
        assert state.results == [0]

    def test_run_overwrites_previous_results(self):
        rules = [_currency(), _gem()]
        ctrl = _ctrl()
        ctrl.run_search(rules, "Currency")
        state = ctrl.run_search(rules, "Gem")
        assert state.results == [1]


# ---------------------------------------------------------------------------
# TestNext
# ---------------------------------------------------------------------------

class TestNext:
    def _loaded(self, n: int = 3) -> NavigationSearchController:
        rules = [_currency()] * n
        ctrl = _ctrl()
        ctrl.run_search(rules, "Currency")
        return ctrl

    def test_next_advances_cursor(self):
        ctrl = self._loaded(3)
        state = ctrl.next()
        assert state.cursor == 1

    def test_next_wraps_at_end(self):
        ctrl = self._loaded(3)
        ctrl.next()
        ctrl.next()
        state = ctrl.next()   # was at 2, wraps to 0
        assert state.cursor == 0

    def test_next_noop_when_no_results(self):
        ctrl = _ctrl()
        state = ctrl.next()
        assert state.results == []
        assert state.cursor == -1

    def test_single_result_next_stays_at_zero(self):
        ctrl = self._loaded(1)
        state = ctrl.next()
        assert state.cursor == 0

    def test_next_updates_current_real(self):
        rules = [_currency(), _gem(), _currency()]
        ctrl = _ctrl()
        ctrl.run_search(rules, "Currency")  # results=[0,2], cursor=0
        state = ctrl.next()
        assert state.current_real == 2


# ---------------------------------------------------------------------------
# TestPrev
# ---------------------------------------------------------------------------

class TestPrev:
    def _loaded(self, n: int = 3) -> NavigationSearchController:
        rules = [_currency()] * n
        ctrl = _ctrl()
        ctrl.run_search(rules, "Currency")
        return ctrl

    def test_prev_wraps_to_last(self):
        ctrl = self._loaded(3)
        state = ctrl.prev()    # from 0 → wraps to 2
        assert state.cursor == 2

    def test_prev_decrements(self):
        ctrl = self._loaded(3)
        ctrl.next()            # cursor=1
        state = ctrl.prev()   # → 0
        assert state.cursor == 0

    def test_prev_noop_when_no_results(self):
        ctrl = _ctrl()
        state = ctrl.prev()
        assert state.results == []

    def test_single_result_prev_stays_at_zero(self):
        ctrl = self._loaded(1)
        state = ctrl.prev()
        assert state.cursor == 0

    def test_prev_updates_current_real(self):
        rules = [_currency(), _gem(), _currency()]
        ctrl = _ctrl()
        ctrl.run_search(rules, "Currency")  # results=[0,2], cursor=0
        state = ctrl.prev()                 # wraps to last → cursor=1, current_real=2
        assert state.current_real == 2


# ---------------------------------------------------------------------------
# TestRefresh
# ---------------------------------------------------------------------------

class TestRefresh:
    def test_refresh_preserves_cursor_when_result_still_exists(self):
        rules = [_currency(), _currency(), _currency()]
        ctrl = _ctrl()
        ctrl.run_search(rules, "Currency")  # results=[0,1,2], cursor=0
        ctrl.next()                          # cursor=1, current_real=1
        state = ctrl.refresh(rules, "Currency")
        assert state.cursor == 1
        assert state.current_real == 1

    def test_refresh_resets_cursor_when_previous_real_gone(self):
        rules = [_currency(), _gem()]
        ctrl = _ctrl()
        ctrl.run_search(rules, "Currency")  # results=[0]
        state = ctrl.refresh(rules, "Currency", lambda idxs: [])
        assert state.results == []
        assert state.cursor == -1

    def test_refresh_defaults_cursor_to_zero_when_old_real_not_in_new(self):
        rules = [_currency(), _currency(), _currency()]
        ctrl = _ctrl()
        ctrl.run_search(rules, "Currency")  # cursor=0, current_real=0
        ctrl.next()                          # cursor=1, current_real=1
        # Filter so only index 2 remains
        state = ctrl.refresh(rules, "Currency", lambda idxs: [i for i in idxs if i == 2])
        assert state.results == [2]
        assert state.cursor == 0

    def test_refresh_empty_query_resets(self):
        rules = [_currency()]
        ctrl = _ctrl()
        ctrl.run_search(rules, "Currency")
        state = ctrl.refresh(rules, "")
        assert state.results == []
        assert state.cursor == -1

    def test_refresh_whitespace_query_resets(self):
        rules = [_currency()]
        ctrl = _ctrl()
        ctrl.run_search(rules, "Currency")
        state = ctrl.refresh(rules, "   ")
        assert state.results == []

    def test_refresh_updates_results_after_rule_change(self):
        rules_before = [_currency(), _gem()]
        rules_after  = [_currency(), _gem(), _currency()]
        ctrl = _ctrl()
        ctrl.run_search(rules_before, "Currency")
        state = ctrl.refresh(rules_after, "Currency")
        assert state.results == [0, 2]


# ---------------------------------------------------------------------------
# TestReset
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_clears_results(self):
        rules = [_currency()]
        ctrl = _ctrl()
        ctrl.run_search(rules, "Currency")
        state = ctrl.reset()
        assert state.results == []
        assert state.cursor == -1
        assert state.has_results is False

    def test_reset_on_empty_is_noop(self):
        ctrl = _ctrl()
        state = ctrl.reset()
        assert state.results == []

    def test_reset_updates_properties(self):
        rules = [_currency()]
        ctrl = _ctrl()
        ctrl.run_search(rules, "Currency")
        ctrl.reset()
        assert ctrl.results == []
        assert ctrl.cursor == -1
        assert ctrl.current_real == -1
        assert ctrl.has_results is False


# ---------------------------------------------------------------------------
# TestProperties
# ---------------------------------------------------------------------------

class TestProperties:
    def test_properties_reflect_state(self):
        rules = [_currency(), _gem(), _currency()]
        ctrl = _ctrl()
        ctrl.run_search(rules, "Currency")
        assert ctrl.results == [0, 2]
        assert ctrl.cursor == 0
        assert ctrl.current_real == 0
        assert ctrl.has_results is True
        assert ctrl.state.total == 2

    def test_results_returns_copy(self):
        rules = [_currency()]
        ctrl = _ctrl()
        ctrl.run_search(rules, "Currency")
        r = ctrl.results
        r.append(999)
        assert 999 not in ctrl.results


# ---------------------------------------------------------------------------
# TestMainWindowFacade — smoke test that MainWindow facade methods still exist
# ---------------------------------------------------------------------------

class TestMainWindowFacade:
    @pytest.fixture(scope="class")
    def qapp(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(["-platform", "offscreen"])
        return app

    @pytest.fixture
    def window(self, qapp, tmp_path):
        from core.settings_manager import SettingsManager
        from ui.main_window import MainWindow
        mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
        return MainWindow(settings_mgr=mgr)

    def test_facade_on_search_changed_exists(self, window):
        assert callable(getattr(window, "_on_search_changed", None))

    def test_facade_on_search_next_exists(self, window):
        assert callable(getattr(window, "_on_search_next", None))

    def test_facade_on_search_prev_exists(self, window):
        assert callable(getattr(window, "_on_search_prev", None))

    def test_facade_refresh_search_exists(self, window):
        assert callable(getattr(window, "_refresh_search", None))

    def test_facade_filter_indices_by_category_exists(self, window):
        assert callable(getattr(window, "_filter_indices_by_category", None))

    def test_facade_go_to_cursor_exists(self, window):
        assert callable(getattr(window, "_go_to_cursor", None))

    def test_nav_search_controller_attached(self, window):
        from controllers.navigation_search_controller import NavigationSearchController
        assert isinstance(window._nav_search, NavigationSearchController)

    def test_on_search_changed_empty_clears_results(self, window):
        window._on_search_changed("")
        assert window._search_results == []
        assert window._search_cursor == -1

    def test_on_search_changed_noop_when_no_rules(self, window):
        window._on_search_changed("Currency")
        assert window._search_results == []

    def test_on_search_next_noop_when_no_results(self, window):
        window._on_search_next()   # must not raise

    def test_on_search_prev_noop_when_no_results(self, window):
        window._on_search_prev()   # must not raise

    def test_filter_indices_by_category_all_passes_through(self, window):
        from core.categorizer import Category
        window._active_category = Category.ALL
        result = window._filter_indices_by_category([0, 1, 2])
        assert result == [0, 1, 2]

    def test_search_results_and_cursor_sync_after_search(self, window, tmp_path):
        # Load a file with rules so search has something to find
        f = tmp_path / "test.filter"
        f.write_text("Show\n    Class Currency\nShow\n    Class Gem\n", encoding="utf-8")
        window.load_file(str(f))
        window._on_search_changed("Currency")
        assert window._search_results == window._nav_search.results
        assert window._search_cursor  == window._nav_search.cursor

    def test_refresh_search_resets_on_empty_bar(self, window):
        window._refresh_search()   # search_bar is empty → must not raise
        assert window._search_results == []
