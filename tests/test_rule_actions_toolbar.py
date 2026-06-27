"""Tests for RuleActionsToolbar — v2.4.0

Covers:
- Initial enable/disable state (no selection)
- update_state: correct button enable state for all positions
- Signal emission on button click
- update_state with edge-case indices
"""

import pytest
from PySide6.QtWidgets import QApplication

from ui.rule_actions_toolbar import RuleActionsToolbar


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

def _make_toolbar(qapp) -> RuleActionsToolbar:
    return RuleActionsToolbar()


def _collect(toolbar: RuleActionsToolbar, signal_name: str) -> list:
    received: list = []
    getattr(toolbar, signal_name).connect(lambda: received.append(True))
    return received


# ---------------------------------------------------------------------------
# TestInitialState
# ---------------------------------------------------------------------------

class TestInitialState:
    def test_new_always_enabled(self, qapp):
        tb = _make_toolbar(qapp)
        assert tb._btn_new.isEnabled()

    def test_delete_disabled_initially(self, qapp):
        tb = _make_toolbar(qapp)
        assert not tb._btn_delete.isEnabled()

    def test_duplicate_disabled_initially(self, qapp):
        tb = _make_toolbar(qapp)
        assert not tb._btn_duplicate.isEnabled()

    def test_move_up_disabled_initially(self, qapp):
        tb = _make_toolbar(qapp)
        assert not tb._btn_move_up.isEnabled()

    def test_move_down_disabled_initially(self, qapp):
        tb = _make_toolbar(qapp)
        assert not tb._btn_move_down.isEnabled()


# ---------------------------------------------------------------------------
# TestUpdateState
# ---------------------------------------------------------------------------

class TestUpdateState:
    def test_no_selection(self, qapp):
        tb = _make_toolbar(qapp)
        tb.update_state(-1, 5)
        assert not tb._btn_delete.isEnabled()
        assert not tb._btn_duplicate.isEnabled()
        assert not tb._btn_move_up.isEnabled()
        assert not tb._btn_move_down.isEnabled()
        assert tb._btn_new.isEnabled()

    def test_first_rule_selected(self, qapp):
        """index=0, total=3 → up disabled, down enabled."""
        tb = _make_toolbar(qapp)
        tb.update_state(0, 3)
        assert tb._btn_delete.isEnabled()
        assert tb._btn_duplicate.isEnabled()
        assert not tb._btn_move_up.isEnabled()
        assert tb._btn_move_down.isEnabled()

    def test_middle_rule_selected(self, qapp):
        """index=1, total=3 → all 4 enabled."""
        tb = _make_toolbar(qapp)
        tb.update_state(1, 3)
        assert tb._btn_delete.isEnabled()
        assert tb._btn_duplicate.isEnabled()
        assert tb._btn_move_up.isEnabled()
        assert tb._btn_move_down.isEnabled()

    def test_last_rule_selected(self, qapp):
        """index=2, total=3 → up enabled, down disabled."""
        tb = _make_toolbar(qapp)
        tb.update_state(2, 3)
        assert tb._btn_delete.isEnabled()
        assert tb._btn_duplicate.isEnabled()
        assert tb._btn_move_up.isEnabled()
        assert not tb._btn_move_down.isEnabled()

    def test_single_rule_only(self, qapp):
        """total=1, index=0 → up/down both disabled."""
        tb = _make_toolbar(qapp)
        tb.update_state(0, 1)
        assert tb._btn_delete.isEnabled()
        assert not tb._btn_move_up.isEnabled()
        assert not tb._btn_move_down.isEnabled()

    def test_new_always_enabled_regardless_of_state(self, qapp):
        tb = _make_toolbar(qapp)
        tb.update_state(2, 3)
        assert tb._btn_new.isEnabled()

    def test_index_out_of_range_treats_as_no_selection(self, qapp):
        """selected_index >= total_movable → no selection."""
        tb = _make_toolbar(qapp)
        tb.update_state(5, 3)
        assert not tb._btn_delete.isEnabled()
        assert not tb._btn_move_up.isEnabled()

    def test_zero_total_no_selection(self, qapp):
        tb = _make_toolbar(qapp)
        tb.update_state(0, 0)
        assert not tb._btn_delete.isEnabled()

    def test_negative_index_no_selection(self, qapp):
        tb = _make_toolbar(qapp)
        tb.update_state(-1, 10)
        assert not tb._btn_delete.isEnabled()

    def test_state_resets_after_deselect(self, qapp):
        """Update from selection → no selection should disable buttons."""
        tb = _make_toolbar(qapp)
        tb.update_state(1, 3)
        assert tb._btn_delete.isEnabled()
        tb.update_state(-1, 3)
        assert not tb._btn_delete.isEnabled()


# ---------------------------------------------------------------------------
# TestSignals
# ---------------------------------------------------------------------------

class TestSignals:
    def test_new_button_emits_new_requested(self, qapp):
        tb = _make_toolbar(qapp)
        received = _collect(tb, "new_requested")
        tb._btn_new.click()
        assert received

    def test_delete_button_emits_delete_requested(self, qapp):
        tb = _make_toolbar(qapp)
        tb.update_state(0, 3)
        received = _collect(tb, "delete_requested")
        tb._btn_delete.click()
        assert received

    def test_duplicate_button_emits_duplicate_requested(self, qapp):
        tb = _make_toolbar(qapp)
        tb.update_state(0, 3)
        received = _collect(tb, "duplicate_requested")
        tb._btn_duplicate.click()
        assert received

    def test_move_up_emits_move_up_requested(self, qapp):
        tb = _make_toolbar(qapp)
        tb.update_state(1, 3)
        received = _collect(tb, "move_up_requested")
        tb._btn_move_up.click()
        assert received

    def test_move_down_emits_move_down_requested(self, qapp):
        tb = _make_toolbar(qapp)
        tb.update_state(1, 3)
        received = _collect(tb, "move_down_requested")
        tb._btn_move_down.click()
        assert received

    def test_disabled_delete_does_not_emit(self, qapp):
        """Clicking a disabled button must not emit signal."""
        tb = _make_toolbar(qapp)
        # No selection → delete is disabled
        received = _collect(tb, "delete_requested")
        tb._btn_delete.click()
        assert received == []

    def test_disabled_move_up_does_not_emit(self, qapp):
        tb = _make_toolbar(qapp)
        tb.update_state(0, 3)   # index=0 → up disabled
        received = _collect(tb, "move_up_requested")
        tb._btn_move_up.click()
        assert received == []

    def test_disabled_move_down_does_not_emit(self, qapp):
        tb = _make_toolbar(qapp)
        tb.update_state(2, 3)   # index=last → down disabled
        received = _collect(tb, "move_down_requested")
        tb._btn_move_down.click()
        assert received == []


# ---------------------------------------------------------------------------
# TestMainWindowIntegration
# ---------------------------------------------------------------------------

class TestMainWindowIntegration:
    def test_main_window_has_rule_actions_toolbar(self, qapp):
        from ui.main_window import MainWindow
        w = MainWindow()
        assert hasattr(w, "rule_actions_toolbar")
        assert isinstance(w.rule_actions_toolbar, RuleActionsToolbar)

    def test_toolbar_initial_state_in_window(self, qapp):
        """Before any file is loaded, all selection-dependent buttons must be off."""
        from ui.main_window import MainWindow
        w = MainWindow()
        tb = w.rule_actions_toolbar
        assert not tb._btn_delete.isEnabled()
        assert not tb._btn_move_up.isEnabled()
        assert not tb._btn_move_down.isEnabled()
