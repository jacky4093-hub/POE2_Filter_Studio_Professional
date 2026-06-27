"""Tests for v1.5.0 Rule Editor Auto-Save.

Covers:
  - _loading guard suppresses _on_field_changed during load_rule()
  - _on_field_changed() arms debounce timer
  - flush_pending() synchronously commits and emits rule_changed
  - has_pending_changes() reflects state correctly
  - load_rule() cancels in-progress debounce
  - Timer fires once after 750 ms idle (QTest.qWait)
  - Rapid changes produce a single emit (debounce coalescing)
  - Each panel type (conditions / appearance / audio) propagates changes
  - _SectionPanel.changed propagates from add_row, remove_row, value change
  - apply button calls flush_pending (not separate path)
"""

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QTest

from core.models import FilterRule
from editor.rule_editor import RuleEditorWidget


# ---------------------------------------------------------------------------
# Shared fixture and helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def _rule(
    action: str = "Show",
    comment: str = "",
    conditions=None,
    actions=None,
) -> FilterRule:
    return FilterRule(
        action=action,
        pre_lines=[],
        conditions=list(conditions or []),
        actions=list(actions or []),
        inline_comment=comment,
        unknown_lines=[],
    )


def _make_editor(qapp) -> tuple[RuleEditorWidget, FilterRule]:
    rule = _rule(action="Show", comment="original")
    w = RuleEditorWidget()
    w.load_rule(rule)
    return w, rule


def _flush_events():
    QCoreApplication.processEvents()
    QCoreApplication.processEvents()


# ---------------------------------------------------------------------------
# Group 1: Loading guard — load_rule() must not arm debounce
# ---------------------------------------------------------------------------

class TestLoadGuard:
    def test_load_rule_does_not_set_pending(self, qapp):
        w, rule = _make_editor(qapp)
        assert not w.has_pending_changes()

    def test_load_rule_timer_not_active(self, qapp):
        w, rule = _make_editor(qapp)
        assert not w._debounce_timer.isActive()

    def test_load_rule_does_not_emit_rule_changed(self, qapp):
        rule = _rule()
        w = RuleEditorWidget()
        emits = []
        w.rule_changed.connect(lambda: emits.append(1))
        w.load_rule(rule)
        _flush_events()
        assert emits == []

    def test_load_rule_cancels_in_progress_timer(self, qapp):
        """If a pending edit exists, load_rule() must cancel it."""
        w, rule = _make_editor(qapp)
        # Arm the debounce
        w.comment_edit.setText("mid-edit")
        assert w.has_pending_changes()
        assert w._debounce_timer.isActive()

        # Loading a new rule should cancel everything
        new_rule = _rule(comment="new")
        w.load_rule(new_rule)

        assert not w.has_pending_changes()
        assert not w._debounce_timer.isActive()

    def test_load_rule_resets_pending_apply_flag(self, qapp):
        w, rule = _make_editor(qapp)
        w.comment_edit.setText("edit")
        assert w._pending_apply is True
        w.load_rule(_rule())
        assert w._pending_apply is False


# ---------------------------------------------------------------------------
# Group 2: Field changes arm the debounce
# ---------------------------------------------------------------------------

class TestDebounceArming:
    def test_action_combo_change_sets_pending(self, qapp):
        w, rule = _make_editor(qapp)
        w.action_combo.setCurrentIndex(1)   # change from index 0
        assert w.has_pending_changes()

    def test_comment_edit_change_sets_pending(self, qapp):
        w, rule = _make_editor(qapp)
        w.comment_edit.setText("changed")
        assert w.has_pending_changes()

    def test_cond_panel_add_row_sets_pending(self, qapp):
        w, rule = _make_editor(qapp)
        # Reset pending first (load_rule already clears)
        w._pending_apply = False
        w._debounce_timer.stop()
        # Directly add a row (bypasses the menu)
        w._cond_panel.add_row("Class", '"Currency"')
        assert w.has_pending_changes()

    def test_app_panel_add_row_sets_pending(self, qapp):
        w, rule = _make_editor(qapp)
        w._pending_apply = False
        w._debounce_timer.stop()
        w._app_panel.add_row("SetFontSize", "36")
        assert w.has_pending_changes()

    def test_audio_panel_add_row_sets_pending(self, qapp):
        w, rule = _make_editor(qapp)
        w._pending_apply = False
        w._debounce_timer.stop()
        w._audio_panel.add_row("PlayAlertSound", "1 300")
        assert w.has_pending_changes()

    def test_field_change_activates_timer(self, qapp):
        w, rule = _make_editor(qapp)
        w.comment_edit.setText("x")
        assert w._debounce_timer.isActive()

    def test_multiple_changes_keep_single_timer_active(self, qapp):
        w, rule = _make_editor(qapp)
        for i in range(5):
            w.comment_edit.setText(f"edit{i}")
        # Timer should still be active (restarted each time)
        assert w._debounce_timer.isActive()
        assert w.has_pending_changes()

    def test_timer_interval_is_750ms(self, qapp):
        w = RuleEditorWidget()
        assert w._debounce_timer.interval() == 750


# ---------------------------------------------------------------------------
# Group 3: flush_pending() — synchronous commit
# ---------------------------------------------------------------------------

class TestFlushPending:
    def test_flush_emits_rule_changed(self, qapp):
        w, rule = _make_editor(qapp)
        emits = []
        w.rule_changed.connect(lambda: emits.append(1))
        w.comment_edit.setText("flushed")
        w.flush_pending()
        assert emits == [1]

    def test_flush_clears_pending_flag(self, qapp):
        w, rule = _make_editor(qapp)
        w.comment_edit.setText("x")
        assert w.has_pending_changes()
        w.flush_pending()
        assert not w.has_pending_changes()

    def test_flush_stops_timer(self, qapp):
        w, rule = _make_editor(qapp)
        w.comment_edit.setText("x")
        assert w._debounce_timer.isActive()
        w.flush_pending()
        assert not w._debounce_timer.isActive()

    def test_flush_noop_when_no_pending(self, qapp):
        w, rule = _make_editor(qapp)
        emits = []
        w.rule_changed.connect(lambda: emits.append(1))
        # No field change → flush_pending is a no-op
        w.flush_pending()
        assert emits == []

    def test_flush_writes_to_live_rule(self, qapp):
        w, rule = _make_editor(qapp)
        w.comment_edit.setText("written")
        w.flush_pending()
        # rule is the live object — must be updated
        assert rule.inline_comment == "written"

    def test_flush_writes_action_to_rule(self, qapp):
        w, rule = _make_editor(qapp)
        from core.models import BLOCK_HEADERS
        target = "Hide" if BLOCK_HEADERS[0] == "Show" else BLOCK_HEADERS[0]
        w.action_combo.setCurrentText(target)
        w.flush_pending()
        assert rule.action == target

    def test_flush_writes_conditions_to_rule(self, qapp):
        w, rule = _make_editor(qapp)
        w._cond_panel.add_row("Class", '"Currency"')
        w.flush_pending()
        keys = [k for k, _ in rule.conditions]
        assert "Class" in keys

    def test_btn_apply_calls_flush_pending(self, qapp):
        """btn_apply click must call flush_pending() (same code path)."""
        w, rule = _make_editor(qapp)
        emits = []
        w.rule_changed.connect(lambda: emits.append(1))
        w.comment_edit.setText("btn test")
        w.btn_apply.click()
        assert emits == [1]
        assert not w.has_pending_changes()


# ---------------------------------------------------------------------------
# Group 4: has_pending_changes()
# ---------------------------------------------------------------------------

class TestHasPendingChanges:
    def test_false_initially(self, qapp):
        w = RuleEditorWidget()
        assert not w.has_pending_changes()

    def test_false_after_load(self, qapp):
        w, rule = _make_editor(qapp)
        assert not w.has_pending_changes()

    def test_true_after_field_change(self, qapp):
        w, rule = _make_editor(qapp)
        w.comment_edit.setText("x")
        assert w.has_pending_changes()

    def test_false_after_flush(self, qapp):
        w, rule = _make_editor(qapp)
        w.comment_edit.setText("x")
        w.flush_pending()
        assert not w.has_pending_changes()

    def test_false_after_load_cancels_pending(self, qapp):
        w, rule = _make_editor(qapp)
        w.comment_edit.setText("x")
        w.load_rule(_rule())
        assert not w.has_pending_changes()


# ---------------------------------------------------------------------------
# Group 5: Panel change propagation
# ---------------------------------------------------------------------------

class TestPanelChangePropagation:
    def test_cond_panel_changed_propagates_to_editor(self, qapp):
        w, rule = _make_editor(qapp)
        w._pending_apply = False
        w._debounce_timer.stop()
        w._cond_panel.changed.emit()   # simulate panel change
        assert w.has_pending_changes()

    def test_app_panel_changed_propagates_to_editor(self, qapp):
        w, rule = _make_editor(qapp)
        w._pending_apply = False
        w._debounce_timer.stop()
        w._app_panel.changed.emit()
        assert w.has_pending_changes()

    def test_audio_panel_changed_propagates_to_editor(self, qapp):
        w, rule = _make_editor(qapp)
        w._pending_apply = False
        w._debounce_timer.stop()
        w._audio_panel.changed.emit()
        assert w.has_pending_changes()

    def test_section_panel_remove_row_emits_changed(self, qapp):
        rule = _rule(conditions=[["Class", '"Currency"']])
        w = RuleEditorWidget()
        w.load_rule(rule)
        # Clear pending from load
        w._pending_apply = False
        w._debounce_timer.stop()

        changed_emits = []
        w._cond_panel.changed.connect(lambda: changed_emits.append(1))

        # Trigger remove via the row's removed signal
        rows = w._cond_panel._rows
        if rows:
            rows[0].removed.emit(rows[0])

        assert len(changed_emits) >= 1


# ---------------------------------------------------------------------------
# Group 6: Timer fires after 750 ms (real-time, needs QTest.qWait)
# ---------------------------------------------------------------------------

class TestDebounceTimer:
    def test_no_emit_before_750ms(self, qapp):
        w, rule = _make_editor(qapp)
        emits = []
        w.rule_changed.connect(lambda: emits.append(1))
        w.comment_edit.setText("typing")
        # Process events without waiting full 750ms
        QTest.qWait(100)
        assert emits == []

    def test_single_emit_after_750ms(self, qapp):
        w, rule = _make_editor(qapp)
        emits = []
        w.rule_changed.connect(lambda: emits.append(1))
        w.comment_edit.setText("done typing")
        # Wait for debounce (+ 100ms buffer)
        QTest.qWait(900)
        assert len(emits) == 1

    def test_rapid_changes_coalesce_to_one_emit(self, qapp):
        """Typing 5 characters quickly should produce exactly 1 emit."""
        w, rule = _make_editor(qapp)
        emits = []
        w.rule_changed.connect(lambda: emits.append(1))
        for ch in "Hello":
            w.comment_edit.setText(w.comment_edit.text() + ch)
            QTest.qWait(50)   # 50ms between chars — well within 750ms window
        # All 5 changes should be pending, timer still running
        assert w.has_pending_changes()
        assert len(emits) == 0   # nothing committed yet
        # Now wait for debounce to fire
        QTest.qWait(900)
        assert len(emits) == 1   # exactly one undo step

    def test_timer_resets_on_each_change(self, qapp):
        """Each change restarts the 750ms window."""
        w, rule = _make_editor(qapp)
        emits = []
        w.rule_changed.connect(lambda: emits.append(1))
        # Change at t=0ms
        w.comment_edit.setText("a")
        QTest.qWait(600)   # almost at 750ms
        assert len(emits) == 0   # not yet

        # Reset timer at t=600ms with a new change
        w.comment_edit.setText("ab")
        QTest.qWait(600)   # another 600ms — still before new 750ms window
        assert len(emits) == 0   # still nothing

        # Now wait the full 750ms from the second change
        QTest.qWait(250)
        assert len(emits) == 1   # fired once for the whole sequence
