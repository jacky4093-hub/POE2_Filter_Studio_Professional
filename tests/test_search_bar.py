"""Tests for ui.search_bar.SearchBarWidget — P10"""

import pytest
from PySide6.QtWidgets import QApplication

from ui.search_bar import SearchBarWidget


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
# TestSearchBarWidgetInit
# ---------------------------------------------------------------------------

class TestSearchBarWidgetInit:
    def test_widget_creates(self, qapp):
        w = SearchBarWidget()
        assert w is not None

    def test_initial_query_empty(self, qapp):
        w = SearchBarWidget()
        assert w.get_query() == ""

    def test_initial_options_all_false(self, qapp):
        w = SearchBarWidget()
        opts = w.get_options()
        assert opts["match_case"] is False
        assert opts["raw_text"] is False
        assert opts["action"] is False
        assert opts["class"] is False
        assert opts["basetype"] is False


# ---------------------------------------------------------------------------
# TestSearchBarWidgetSignals
# ---------------------------------------------------------------------------

class TestSearchBarWidgetSignals:
    def test_text_input_emits_search_changed(self, qapp):
        """P17.7: text input debounced at 150 ms; flush timer to test emission."""
        w = SearchBarWidget()
        received = []
        w.search_changed.connect(lambda q, o: received.append((q, o)))
        w._input.setText("gem")
        # Debounce timer is now active; fire it immediately for this test
        w._debounce_timer.stop()
        w._emit_search()
        assert len(received) == 1
        assert received[0][0] == "gem"

    def test_search_changed_includes_options(self, qapp):
        w = SearchBarWidget()
        received = []
        w.search_changed.connect(lambda q, o: received.append(o))
        w._cb_case.setChecked(True)   # option changes fire immediately (no debounce)
        # last emission should have match_case=True
        assert received[-1]["match_case"] is True

    def test_clear_button_emits_clear_requested(self, qapp):
        w = SearchBarWidget()
        received = []
        w.clear_requested.connect(lambda: received.append(True))
        w._input.setText("hello")
        w._clear_btn.click()
        assert len(received) == 1

    def test_clear_button_emits_search_changed_empty(self, qapp):
        w = SearchBarWidget()
        received = []
        w.search_changed.connect(lambda q, o: received.append(q))
        w._input.setText("hello")
        received.clear()
        w._clear_btn.click()
        assert received[-1] == ""

    def test_clear_button_resets_query(self, qapp):
        w = SearchBarWidget()
        w._input.setText("hello")
        w._clear_btn.click()
        assert w.get_query() == ""

    def test_option_change_emits_search_changed(self, qapp):
        w = SearchBarWidget()
        w._input.setText("test")
        received = []
        w.search_changed.connect(lambda q, o: received.append((q, o)))
        w._cb_cls.setChecked(True)
        assert len(received) >= 1
        assert received[-1][1]["class"] is True


# ---------------------------------------------------------------------------
# TestSearchBarWidgetAPI
# ---------------------------------------------------------------------------

class TestSearchBarWidgetAPI:
    def test_set_result_count_with_results(self, qapp):
        w = SearchBarWidget()
        w._input.setText("test")  # non-empty query
        w.set_result_count(3, 10)
        assert "3" in w._count_lbl.text()
        assert "10" in w._count_lbl.text()

    def test_set_result_count_zero(self, qapp):
        w = SearchBarWidget()
        w.set_result_count(0, 5)
        assert "0" in w._count_lbl.text()

    def test_clear_does_not_emit_signal(self, qapp):
        w = SearchBarWidget()
        w._input.setText("test")
        received = []
        w.search_changed.connect(lambda q, o: received.append(q))
        w.clear()
        assert len(received) == 0

    def test_clear_resets_query(self, qapp):
        w = SearchBarWidget()
        w._input.setText("test")
        w.clear()
        assert w.get_query() == ""

    def test_get_options_reflects_checkboxes(self, qapp):
        w = SearchBarWidget()
        w._cb_base.setChecked(True)
        w._cb_raw.setChecked(True)
        opts = w.get_options()
        assert opts["basetype"] is True
        assert opts["raw_text"] is True
        assert opts["class"] is False
