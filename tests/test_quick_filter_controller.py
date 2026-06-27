"""Tests for QuickFilterController — P12.4

Coverage:
- apply_filter: pushes filter to browser, refreshes count, clears editor when
  selected rule is filtered out, does NOT clear editor when rule is still visible
- clear_filter: removes filter from browser, refreshes count
- refresh_count: reads browser counts and pushes to search bar
- MainWindow facade methods still exist and delegate to controller
"""

import pytest

from controllers.quick_filter_controller import QuickFilterController


# ---------------------------------------------------------------------------
# Lightweight mock objects (no Qt dependency)
# ---------------------------------------------------------------------------

class _MockBrowser:
    """Minimal stand-in for RuleCardBrowser's quick-filter surface."""

    def __init__(self):
        self.last_query:    str  = ""
        self.last_options:  dict = {}
        self.filter_cleared: bool = False
        self._visible: set[int] = set()   # indices considered visible
        self._visible_count: int = 3
        self._total_count:   int = 5

    def set_search_filter(self, query: str, options: dict) -> None:
        self.last_query   = query
        self.last_options = options
        self.filter_cleared = False

    def clear_search_filter(self) -> None:
        self.last_query = ""
        self.last_options = {}
        self.filter_cleared = True

    def get_visible_count(self) -> int:
        return self._visible_count

    def get_total_count(self) -> int:
        return self._total_count

    def is_rule_visible(self, index: int) -> bool:
        return index in self._visible


class _MockSearchBar:
    """Minimal stand-in for SearchBarWidget's count-display surface."""

    def __init__(self):
        self.last_visible: int | None = None
        self.last_total:   int | None = None

    def set_result_count(self, visible: int, total: int) -> None:
        self.last_visible = visible
        self.last_total   = total


class _MockWindow:
    """Minimal window stand-in accepted by QuickFilterController."""

    def __init__(self):
        self.rule_card_browser = _MockBrowser()
        self.filter_search_bar = _MockSearchBar()
        self._selected_index   = -1
        self.ui_cleared        = False

    def _clear_rule_ui(self) -> None:
        self.ui_cleared = True


def _ctrl() -> tuple[QuickFilterController, _MockWindow]:
    w = _MockWindow()
    return QuickFilterController(w), w


# ---------------------------------------------------------------------------
# TestApplyFilter
# ---------------------------------------------------------------------------

class TestApplyFilter:
    def test_pushes_query_and_options_to_browser(self):
        ctrl, w = _ctrl()
        ctrl.apply_filter("Currency", {"match_case": True})
        assert w.rule_card_browser.last_query   == "Currency"
        assert w.rule_card_browser.last_options == {"match_case": True}

    def test_empty_query_still_forwarded(self):
        ctrl, w = _ctrl()
        ctrl.apply_filter("", {})
        assert w.rule_card_browser.last_query == ""

    def test_refreshes_count_after_filter(self):
        ctrl, w = _ctrl()
        w.rule_card_browser._visible_count = 2
        w.rule_card_browser._total_count   = 7
        ctrl.apply_filter("gem", {})
        assert w.filter_search_bar.last_visible == 2
        assert w.filter_search_bar.last_total   == 7

    def test_clears_editor_when_selected_rule_not_visible(self):
        ctrl, w = _ctrl()
        w._selected_index = 0          # rule 0 is selected
        # rule 0 is NOT in _visible → filtered out
        w.rule_card_browser._visible = {1, 2}
        ctrl.apply_filter("test", {})
        assert w.ui_cleared is True

    def test_does_not_clear_editor_when_selected_rule_still_visible(self):
        ctrl, w = _ctrl()
        w._selected_index = 0
        w.rule_card_browser._visible = {0, 1}  # rule 0 is still visible
        ctrl.apply_filter("test", {})
        assert w.ui_cleared is False

    def test_does_not_clear_editor_when_no_rule_selected(self):
        ctrl, w = _ctrl()
        w._selected_index = -1        # nothing selected
        w.rule_card_browser._visible = set()
        ctrl.apply_filter("test", {})
        assert w.ui_cleared is False

    def test_options_empty_dict_accepted(self):
        ctrl, w = _ctrl()
        ctrl.apply_filter("hide", {})
        assert w.rule_card_browser.last_options == {}


# ---------------------------------------------------------------------------
# TestClearFilter
# ---------------------------------------------------------------------------

class TestClearFilter:
    def test_calls_browser_clear_search_filter(self):
        ctrl, w = _ctrl()
        ctrl.apply_filter("something", {})
        ctrl.clear_filter()
        assert w.rule_card_browser.filter_cleared is True

    def test_refreshes_count_after_clear(self):
        ctrl, w = _ctrl()
        w.rule_card_browser._visible_count = 4
        w.rule_card_browser._total_count   = 4
        ctrl.clear_filter()
        assert w.filter_search_bar.last_visible == 4
        assert w.filter_search_bar.last_total   == 4

    def test_clear_does_not_clear_editor(self):
        ctrl, w = _ctrl()
        w._selected_index = 0
        ctrl.clear_filter()
        assert w.ui_cleared is False


# ---------------------------------------------------------------------------
# TestRefreshCount
# ---------------------------------------------------------------------------

class TestRefreshCount:
    def test_reads_visible_and_total_from_browser(self):
        ctrl, w = _ctrl()
        w.rule_card_browser._visible_count = 6
        w.rule_card_browser._total_count   = 10
        ctrl.refresh_count()
        assert w.filter_search_bar.last_visible == 6
        assert w.filter_search_bar.last_total   == 10

    def test_zero_visible_still_pushed(self):
        ctrl, w = _ctrl()
        w.rule_card_browser._visible_count = 0
        w.rule_card_browser._total_count   = 3
        ctrl.refresh_count()
        assert w.filter_search_bar.last_visible == 0
        assert w.filter_search_bar.last_total   == 3

    def test_both_zero(self):
        ctrl, w = _ctrl()
        w.rule_card_browser._visible_count = 0
        w.rule_card_browser._total_count   = 0
        ctrl.refresh_count()
        assert w.filter_search_bar.last_visible == 0
        assert w.filter_search_bar.last_total   == 0


# ---------------------------------------------------------------------------
# TestMainWindowFacade — smoke tests that facade methods still exist and work
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

    def test_facade_on_filter_search_changed_exists(self, window):
        assert callable(getattr(window, "_on_filter_search_changed", None))

    def test_facade_on_filter_search_clear_exists(self, window):
        assert callable(getattr(window, "_on_filter_search_clear", None))

    def test_facade_update_filter_search_count_exists(self, window):
        assert callable(getattr(window, "_update_filter_search_count", None))

    def test_quick_filter_controller_attached(self, window):
        from controllers.quick_filter_controller import QuickFilterController
        assert isinstance(window._quick_filter, QuickFilterController)

    def test_on_filter_search_changed_does_not_raise(self, window):
        window._on_filter_search_changed("Currency", {})   # no rules loaded → safe

    def test_on_filter_search_clear_does_not_raise(self, window):
        window._on_filter_search_clear()

    def test_update_filter_search_count_does_not_raise(self, window):
        window._update_filter_search_count()

    def test_apply_filter_with_rules(self, window, tmp_path):
        f = tmp_path / "t.filter"
        f.write_text("Show\n    Class Currency\nShow\n    Class Gem\n", encoding="utf-8")
        window.load_file(str(f))
        window._on_filter_search_changed("Currency", {})
        # Browser should now show only the Currency rule
        assert window.rule_card_browser.get_visible_count() == 1

    def test_clear_filter_restores_all(self, window, tmp_path):
        f = tmp_path / "t2.filter"
        f.write_text("Show\n    Class Currency\nShow\n    Class Gem\n", encoding="utf-8")
        window.load_file(str(f))
        window._on_filter_search_changed("Currency", {})
        window._on_filter_search_clear()
        assert window.rule_card_browser.get_visible_count() == 2

    def test_count_label_updated_after_filter(self, window, tmp_path):
        f = tmp_path / "t3.filter"
        f.write_text("Show\n    Class Currency\nShow\n    Class Gem\n", encoding="utf-8")
        window.load_file(str(f))
        window._on_filter_search_changed("Currency", {})
        # The SearchBarWidget count label should reflect 1/2
        lbl_text = window.filter_search_bar._count_lbl.text()
        assert "1" in lbl_text
        assert "2" in lbl_text
