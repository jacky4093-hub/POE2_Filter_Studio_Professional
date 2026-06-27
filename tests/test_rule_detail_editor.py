"""Tests for RuleDetailEditor — v2.3.0

Covers:
- Initial empty state
- set_rule() populates all fields correctly
- clear() returns to empty state
- Modifying enabled emits rule_changed
- Modifying action emits rule_changed with updated action
- Field changes preserve unmanaged fields (pre_lines, unknown_lines, inline_comment)
- Field changes preserve unmanaged conditions and actions
- set_rule() does NOT emit rule_changed (loading guard)
- _update_in_list helper: update, insert, remove, preserve others
- flush_pending() is a no-op (no crash)
- MainWindow can instantiate with the new editor (P1/P2/P3 not broken)
"""

import pytest
from PySide6.QtWidgets import QApplication

from core.models import FilterRule
from ui.rule_detail_editor import RuleDetailEditor


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

def _rule(
    action: str = "Show",
    enabled: bool = True,
    conditions: list | None = None,
    actions: list | None = None,
    unknown_lines: list | None = None,
    pre_lines: list | None = None,
    inline_comment: str = "",
) -> FilterRule:
    return FilterRule(
        action=action,
        enabled=enabled,
        conditions=conditions or [],
        actions=actions or [],
        unknown_lines=unknown_lines or [],
        pre_lines=pre_lines or [],
        inline_comment=inline_comment,
    )


def _make_editor(qapp) -> RuleDetailEditor:
    return RuleDetailEditor()


def _collect_signals(editor: RuleDetailEditor) -> list[tuple]:
    received: list[tuple] = []
    editor.rule_changed.connect(lambda idx, rule: received.append((idx, rule)))
    return received


# ---------------------------------------------------------------------------
# TestInitialState
# ---------------------------------------------------------------------------

class TestInitialState:
    def test_empty_page_shown_on_init(self, qapp):
        ed = _make_editor(qapp)
        # stacked widget should be on page 0 (empty)
        assert ed._stacked.currentWidget() is ed._empty_page

    def test_rule_is_none_on_init(self, qapp):
        ed = _make_editor(qapp)
        assert ed._rule is None

    def test_index_is_minus_one_on_init(self, qapp):
        ed = _make_editor(qapp)
        assert ed._index == -1


# ---------------------------------------------------------------------------
# TestSetRule
# ---------------------------------------------------------------------------

class TestSetRule:
    def test_editor_page_shown_after_set_rule(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        assert ed._stacked.currentWidget() is ed._editor_page

    def test_enabled_checkbox_populated(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(enabled=True), index=0)
        assert ed._enabled_cb.isChecked() is True

    def test_disabled_rule_unchecks_checkbox(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(enabled=False), index=0)
        assert ed._enabled_cb.isChecked() is False

    def test_action_combo_populated(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(action="Hide"), index=0)
        assert ed._action_combo.currentText() == "Hide"

    def test_class_populated(self, qapp):
        ed = _make_editor(qapp)
        rule = _rule(conditions=[["Class", '"Currency"']])
        ed.set_rule(rule, index=0)
        assert ed._class_edit.text() == '"Currency"'

    def test_basetype_populated(self, qapp):
        ed = _make_editor(qapp)
        rule = _rule(conditions=[["BaseType", '"Divine Orb"']])
        ed.set_rule(rule, index=0)
        assert ed._basetype_edit.text() == '"Divine Orb"'

    def test_setfontsize_populated(self, qapp):
        ed = _make_editor(qapp)
        rule = _rule(actions=[["SetFontSize", "36"]])
        ed.set_rule(rule, index=0)
        assert ed._fontsize_edit.text() == "36"

    def test_settextcolor_populated(self, qapp):
        ed = _make_editor(qapp)
        rule = _rule(actions=[["SetTextColor", "255 200 0 255"]])
        ed.set_rule(rule, index=0)
        assert ed._textcolor_edit.text() == "255 200 0 255"

    def test_setbordercolor_populated(self, qapp):
        ed = _make_editor(qapp)
        rule = _rule(actions=[["SetBorderColor", "100 100 100 200"]])
        ed.set_rule(rule, index=0)
        assert ed._bordercolor_edit.text() == "100 100 100 200"

    def test_setbackgroundcolor_populated(self, qapp):
        ed = _make_editor(qapp)
        rule = _rule(actions=[["SetBackgroundColor", "0 0 0 200"]])
        ed.set_rule(rule, index=0)
        assert ed._bgcolor_edit.text() == "0 0 0 200"

    def test_playalertsound_populated(self, qapp):
        ed = _make_editor(qapp)
        rule = _rule(actions=[["PlayAlertSound", "1 300"]])
        ed.set_rule(rule, index=0)
        assert ed._alert_edit.text() == "1 300"

    def test_minimapicon_populated(self, qapp):
        ed = _make_editor(qapp)
        rule = _rule(actions=[["MinimapIcon", "1 Red Circle"]])
        ed.set_rule(rule, index=0)
        assert ed._minimap_edit.text() == "1 Red Circle"

    def test_missing_field_shows_empty(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)   # no conditions or actions
        assert ed._class_edit.text() == ""
        assert ed._fontsize_edit.text() == ""

    def test_index_stored(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=7)
        assert ed._index == 7

    def test_rule_deep_copied(self, qapp):
        ed = _make_editor(qapp)
        r = _rule(conditions=[["Class", '"Currency"']])
        ed.set_rule(r, index=0)
        # Mutating original should not affect editor's copy
        r.conditions[0][1] = '"Gems"'
        assert ed._rule.conditions[0][1] == '"Currency"'


# ---------------------------------------------------------------------------
# TestSetRuleNoSignal
# ---------------------------------------------------------------------------

class TestSetRuleNoSignal:
    def test_set_rule_does_not_emit_rule_changed(self, qapp):
        ed = _make_editor(qapp)
        received = _collect_signals(ed)
        ed.set_rule(_rule(action="Show", conditions=[["Class", '"Currency"']]), index=0)
        assert received == [], "set_rule must not emit rule_changed"

    def test_repeated_set_rule_no_signal(self, qapp):
        ed = _make_editor(qapp)
        received = _collect_signals(ed)
        ed.set_rule(_rule(), index=0)
        ed.set_rule(_rule(action="Hide"), index=1)
        assert received == []


# ---------------------------------------------------------------------------
# TestClear
# ---------------------------------------------------------------------------

class TestClear:
    def test_clear_shows_empty_page(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed.clear()
        assert ed._stacked.currentWidget() is ed._empty_page

    def test_clear_resets_rule(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed.clear()
        assert ed._rule is None

    def test_clear_resets_index(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=5)
        ed.clear()
        assert ed._index == -1


# ---------------------------------------------------------------------------
# TestSignalEmission
# ---------------------------------------------------------------------------

class TestSignalEmission:
    def test_enabled_change_emits_signal(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(enabled=True), index=3)
        received = _collect_signals(ed)

        ed._enabled_cb.setChecked(False)    # triggers stateChanged → _on_any_field_changed

        assert len(received) == 1
        idx, updated = received[0]
        assert idx == 3
        assert updated.enabled is False

    def test_action_change_emits_signal(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(action="Show"), index=2)
        received = _collect_signals(ed)

        ed._action_combo.setCurrentText("Hide")

        assert len(received) == 1
        _idx, updated = received[0]
        assert updated.action == "Hide"

    def test_signal_index_matches(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=9)
        received = _collect_signals(ed)
        ed._enabled_cb.setChecked(not ed._enabled_cb.isChecked())
        assert received[0][0] == 9

    def test_editingfinished_emits_signal(self, qapp):
        """editingFinished on QLineEdit must trigger rule_changed."""
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        received = _collect_signals(ed)

        ed._class_edit.setText('"Gems"')
        ed._class_edit.editingFinished.emit()   # simulate losing focus

        assert len(received) == 1
        _idx, updated = received[0]
        # Class should be updated
        classes = [v for k, v in updated.conditions if k == "Class"]
        assert classes == ['"Gems"']


# ---------------------------------------------------------------------------
# TestFieldPreservation
# ---------------------------------------------------------------------------

class TestFieldPreservation:
    def test_enabled_change_preserves_conditions(self, qapp):
        rule = _rule(
            enabled=True,
            conditions=[["Class", '"Currency"'], ["Rarity", "Unique"]],
        )
        ed = _make_editor(qapp)
        ed.set_rule(rule, index=0)
        received = _collect_signals(ed)
        ed._enabled_cb.setChecked(False)

        _idx, updated = received[0]
        cond_keys = [k for k, v in updated.conditions]
        assert "Class" in cond_keys
        assert "Rarity" in cond_keys

    def test_action_change_preserves_actions(self, qapp):
        rule = _rule(
            action="Show",
            actions=[["SetFontSize", "36"], ["PlayAlertSound", "1 300"]],
        )
        ed = _make_editor(qapp)
        ed.set_rule(rule, index=0)
        received = _collect_signals(ed)
        ed._action_combo.setCurrentText("Hide")

        _idx, updated = received[0]
        action_keys = [k for k, v in updated.actions]
        assert "SetFontSize" in action_keys
        assert "PlayAlertSound" in action_keys

    def test_pre_lines_preserved(self, qapp):
        rule = _rule(pre_lines=["# Section", "# ==="])
        ed = _make_editor(qapp)
        ed.set_rule(rule, index=0)
        received = _collect_signals(ed)
        ed._enabled_cb.setChecked(not ed._enabled_cb.isChecked())

        _idx, updated = received[0]
        assert updated.pre_lines == ["# Section", "# ==="]

    def test_inline_comment_preserved(self, qapp):
        rule = _rule(inline_comment="# important!")
        ed = _make_editor(qapp)
        ed.set_rule(rule, index=0)
        received = _collect_signals(ed)
        ed._enabled_cb.setChecked(not ed._enabled_cb.isChecked())

        _idx, updated = received[0]
        assert updated.inline_comment == "# important!"

    def test_unknown_lines_preserved(self, qapp):
        rule = _rule(unknown_lines=["CustomUnknownLine 42"])
        ed = _make_editor(qapp)
        ed.set_rule(rule, index=0)
        received = _collect_signals(ed)
        ed._enabled_cb.setChecked(not ed._enabled_cb.isChecked())

        _idx, updated = received[0]
        assert updated.unknown_lines == ["CustomUnknownLine 42"]

    def test_unmanaged_conditions_preserved(self, qapp):
        rule = _rule(conditions=[
            ["AreaLevel", ">= 70"],
            ["Class", '"Currency"'],
        ])
        ed = _make_editor(qapp)
        ed.set_rule(rule, index=0)
        received = _collect_signals(ed)
        ed._action_combo.setCurrentText("Hide")

        _idx, updated = received[0]
        arealevel_entries = [k for k, v in updated.conditions if k == "AreaLevel"]
        assert arealevel_entries == ["AreaLevel"]
        # verify value preserved
        vals = [v for k, v in updated.conditions if k == "AreaLevel"]
        assert vals == [">= 70"]

    def test_unmanaged_actions_preserved(self, qapp):
        rule = _rule(actions=[
            ["SetFontSize", "36"],
            ["PlayEffect", "Red"],   # not managed by editor
        ])
        ed = _make_editor(qapp)
        ed.set_rule(rule, index=0)
        received = _collect_signals(ed)
        ed._action_combo.setCurrentText("Hide")

        _idx, updated = received[0]
        playeffect_keys = [k for k, v in updated.actions if k == "PlayEffect"]
        assert playeffect_keys == ["PlayEffect"]
        playeffect_vals = [v for k, v in updated.actions if k == "PlayEffect"]
        assert playeffect_vals == ["Red"]


# ---------------------------------------------------------------------------
# TestUpdateInList
# ---------------------------------------------------------------------------

class TestUpdateInList:
    """Unit tests for the _update_in_list static helper."""

    def _call(self, items, key, value):
        return RuleDetailEditor._update_in_list(items, key, value)

    def test_update_existing_key(self):
        items = [["Class", '"Currency"'], ["Rarity", "Unique"]]
        result = self._call(items, "Class", '"Gems"')
        class_vals = [v for k, v in result if k == "Class"]
        assert class_vals == ['"Gems"']

    def test_insert_new_key(self):
        items = [["Rarity", "Unique"]]
        result = self._call(items, "BaseType", '"Divine Orb"')
        assert ["BaseType", '"Divine Orb"'] in result

    def test_remove_key_when_value_empty(self):
        items = [["Class", '"Currency"'], ["Rarity", "Unique"]]
        result = self._call(items, "Class", "")
        assert not any(k == "Class" for k, v in result)
        assert any(k == "Rarity" for k, v in result)

    def test_other_keys_preserved(self):
        items = [["AreaLevel", ">= 70"], ["Class", '"Currency"']]
        result = self._call(items, "Class", '"Gems"')
        assert ["AreaLevel", ">= 70"] in result

    def test_preserves_position_of_existing(self):
        items = [["Class", '"Currency"'], ["Rarity", "Unique"]]
        result = self._call(items, "Class", '"Gems"')
        assert result[0][0] == "Class"   # position kept

    def test_deduplication(self):
        items = [["Class", '"Currency"'], ["Class", '"Gems"']]
        result = self._call(items, "Class", '"Orbs"')
        class_vals = [v for k, v in result if k == "Class"]
        assert len(class_vals) == 1
        assert class_vals[0] == '"Orbs"'

    def test_empty_list_insert(self):
        result = self._call([], "SetFontSize", "36")
        assert result == [["SetFontSize", "36"]]

    def test_empty_list_remove_noop(self):
        result = self._call([], "SetFontSize", "")
        assert result == []

    def test_whitespace_value_treated_as_empty(self):
        items = [["SetFontSize", "36"]]
        result = self._call(items, "SetFontSize", "   ")
        assert not any(k == "SetFontSize" for k, v in result)

    def test_case_insensitive_key_match(self):
        items = [["class", '"Currency"']]
        result = self._call(items, "Class", '"Gems"')
        # Should update the existing "class" entry
        assert len(result) == 1


# ---------------------------------------------------------------------------
# TestFlushPending
# ---------------------------------------------------------------------------

class TestFlushPending:
    def test_flush_pending_does_not_crash_empty(self, qapp):
        ed = _make_editor(qapp)
        ed.flush_pending()   # must not raise

    def test_flush_pending_does_not_crash_with_rule(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed.flush_pending()   # must not raise

    def test_flush_pending_does_not_emit_signal(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        received = _collect_signals(ed)
        ed.flush_pending()
        assert received == []


# ---------------------------------------------------------------------------
# TestPreviewText
# ---------------------------------------------------------------------------

class TestPreviewText:
    def test_preview_shows_action(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(action="Show"), index=0)
        assert "Show" in ed._preview_text.toPlainText()

    def test_preview_shows_conditions(self, qapp):
        ed = _make_editor(qapp)
        rule = _rule(conditions=[["Class", '"Currency"']])
        ed.set_rule(rule, index=0)
        text = ed._preview_text.toPlainText()
        assert "Class" in text
        assert '"Currency"' in text

    def test_disabled_rule_prefixes_with_hash(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(enabled=False), index=0)
        text = ed._preview_text.toPlainText()
        assert text.startswith("#")

    def test_preview_cleared_after_clear(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(conditions=[["Class", '"Currency"']]), index=0)
        ed.clear()
        assert ed._preview_text.toPlainText() == ""


# ---------------------------------------------------------------------------
# TestMainWindowIntegration
# ---------------------------------------------------------------------------

class TestMainWindowIntegration:
    def test_main_window_instantiates(self, qapp):
        """MainWindow with RuleDetailEditor should instantiate without errors."""
        from ui.main_window import MainWindow
        window = MainWindow()
        assert hasattr(window, "rule_detail_editor")
        assert isinstance(window.rule_detail_editor, RuleDetailEditor)

    def test_rule_card_browser_still_present(self, qapp):
        from ui.main_window import MainWindow
        from ui.rule_card_browser import RuleCardBrowser
        window = MainWindow()
        assert hasattr(window, "rule_card_browser")
        assert isinstance(window.rule_card_browser, RuleCardBrowser)

    def test_category_sidebar_still_present(self, qapp):
        from ui.main_window import MainWindow
        from ui.category_sidebar import CategorySidebarWidget
        window = MainWindow()
        assert isinstance(window.category_sidebar, CategorySidebarWidget)
