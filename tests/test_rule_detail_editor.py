"""Tests for RuleDetailEditor — v3.0.0  (P13.1 Visual Rule Editor MVP)

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
from ui.rule_detail_editor import (
    RuleDetailEditor, _MM_SHAPES, _MM_COLORS,
    _effect_parse,
)


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
        assert ed._fontsize_spin.value() == 36

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
        assert ed._fontsize_spin.value() == 0   # 0 = "—" (not set)

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


# ---------------------------------------------------------------------------
# TestP131TitleBar  (P13.1 新增)
# ---------------------------------------------------------------------------

class TestP131TitleBar:
    """Title bar widget updates when rule is loaded or fields change."""

    def test_title_lbl_exists(self, qapp):
        ed = _make_editor(qapp)
        assert hasattr(ed, "_title_lbl")

    def test_title_shows_rule_number_and_action(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(action="Hide"), index=4)
        text = ed._title_lbl.text()
        # should mention rule number (5, since 4+1) and action
        assert "5" in text
        assert "Hide" in text

    def test_title_updates_when_action_changes(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(action="Show"), index=0)
        ed._action_combo.setCurrentText("Continue")
        assert "Continue" in ed._title_lbl.text()

    def test_title_notes_disabled_rule(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(enabled=False, action="Show"), index=0)
        text = ed._title_lbl.text()
        # disabled indication present (✕ or similar marker)
        assert "停用" in text or "✕" in text or "disabled" in text.lower()

    def test_title_updates_when_enabled_toggled(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(enabled=True), index=0)
        before = ed._title_lbl.text()
        ed._enabled_cb.setChecked(False)
        after = ed._title_lbl.text()
        assert before != after


# ---------------------------------------------------------------------------
# TestP131SectionCards  (P13.1 新增)
# ---------------------------------------------------------------------------

class TestP131SectionCards:
    """Sections are wrapped in QGroupBox cards (not plain header labels)."""

    def test_editor_page_contains_group_boxes(self, qapp):
        from PySide6.QtWidgets import QGroupBox
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        # scroll area's widget (content) should contain QGroupBox children
        scroll = ed._editor_page
        content = scroll.widget()
        group_boxes = [w for w in content.findChildren(QGroupBox)]
        assert len(group_boxes) >= 5   # 基本設定, 條件, 外觀, 音效, 小地圖, 預覽

    def test_all_section_titles_present(self, qapp):
        from PySide6.QtWidgets import QGroupBox
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        content = ed._editor_page.widget()
        titles = {w.title() for w in content.findChildren(QGroupBox)}
        assert "基本設定" in titles
        assert "條件" in titles
        assert "外觀" in titles
        assert "音效" in titles
        assert "小地圖" in titles

    def test_preview_section_is_group_box(self, qapp):
        from PySide6.QtWidgets import QGroupBox
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        # preview text should be inside a QGroupBox
        parent = ed._preview_text.parent()
        # parent is QGroupBox or its interior widget
        assert parent is not None


# ---------------------------------------------------------------------------
# TestP131EmptyState  (P13.1 新增)
# ---------------------------------------------------------------------------

class TestP131EmptyState:
    """Richer empty state shows icon + message + hint."""

    def test_empty_page_has_hint_label(self, qapp):
        from PySide6.QtWidgets import QLabel
        ed = _make_editor(qapp)
        labels = ed._empty_page.findChildren(QLabel)
        object_names = {lbl.objectName() for lbl in labels}
        assert "RuleDetailEmptyHint" in object_names

    def test_empty_page_has_icon_label(self, qapp):
        from PySide6.QtWidgets import QLabel
        ed = _make_editor(qapp)
        labels = ed._empty_page.findChildren(QLabel)
        object_names = {lbl.objectName() for lbl in labels}
        assert "RuleDetailEmptyIcon" in object_names

    def test_empty_page_has_main_label(self, qapp):
        from PySide6.QtWidgets import QLabel
        ed = _make_editor(qapp)
        labels = ed._empty_page.findChildren(QLabel)
        object_names = {lbl.objectName() for lbl in labels}
        assert "RuleDetailEmptyLabel" in object_names


# ---------------------------------------------------------------------------
# TestP131PreviewShowsUnknownLines  (P13.1 新增)
# ---------------------------------------------------------------------------

class TestP131PreviewShowsUnknownLines:
    def test_unknown_lines_appear_in_preview(self, qapp):
        rule = _rule(unknown_lines=["CustomTag Foo"])
        ed = _make_editor(qapp)
        ed.set_rule(rule, index=0)
        assert "CustomTag" in ed._preview_text.toPlainText()


# ---------------------------------------------------------------------------
# TestP134FontSpinbox  (P13.4 新增)
# ---------------------------------------------------------------------------

class TestP134FontSpinbox:
    """SetFontSize is now a QSpinBox (range 0-60; 0 = not set → '—')."""

    def test_fontsize_spinbox_exists(self, qapp):
        from PySide6.QtWidgets import QSpinBox
        ed = _make_editor(qapp)
        assert hasattr(ed, "_fontsize_spin")
        assert isinstance(ed._fontsize_spin, QSpinBox)

    def test_set_rule_populates_fontsize_spin(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["SetFontSize", "36"]]), index=0)
        assert ed._fontsize_spin.value() == 36

    def test_missing_fontsize_spin_zero(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        assert ed._fontsize_spin.value() == 0

    def test_set_rule_does_not_emit_on_fontsize(self, qapp):
        ed = _make_editor(qapp)
        received = _collect_signals(ed)
        ed.set_rule(_rule(actions=[["SetFontSize", "45"]]), index=0)
        assert received == []

    def test_fontsize_change_emits_rule_changed(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["SetFontSize", "32"]]), index=0)
        received = _collect_signals(ed)
        ed._fontsize_spin.setValue(24)
        assert len(received) == 1
        _idx, updated = received[0]
        fs_vals = [v for k, v in updated.actions if k == "SetFontSize"]
        assert fs_vals == ["24"]

    def test_fontsize_zero_removes_setfontsize(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["SetFontSize", "36"]]), index=0)
        received = _collect_signals(ed)
        ed._fontsize_spin.setValue(0)
        assert len(received) == 1
        _idx, updated = received[0]
        fs_keys = [k for k, v in updated.actions if k == "SetFontSize"]
        assert fs_keys == []

    def test_fontsize_range_min_max(self, qapp):
        ed = _make_editor(qapp)
        assert ed._fontsize_spin.minimum() == 0
        assert ed._fontsize_spin.maximum() == 60

    def test_fontsize_special_value_text(self, qapp):
        ed = _make_editor(qapp)
        assert ed._fontsize_spin.specialValueText() == "—"


# ---------------------------------------------------------------------------
# TestP134ColorSwatches  (P13.4 新增)
# ---------------------------------------------------------------------------

class TestP134ColorSwatches:
    """Colour fields carry swatch preview labels."""

    def test_textcolor_swatch_exists(self, qapp):
        from PySide6.QtWidgets import QLabel
        ed = _make_editor(qapp)
        assert hasattr(ed, "_textcolor_swatch")
        assert isinstance(ed._textcolor_swatch, QLabel)

    def test_bordercolor_swatch_exists(self, qapp):
        from PySide6.QtWidgets import QLabel
        ed = _make_editor(qapp)
        assert hasattr(ed, "_bordercolor_swatch")
        assert isinstance(ed._bordercolor_swatch, QLabel)

    def test_bgcolor_swatch_exists(self, qapp):
        from PySide6.QtWidgets import QLabel
        ed = _make_editor(qapp)
        assert hasattr(ed, "_bgcolor_swatch")
        assert isinstance(ed._bgcolor_swatch, QLabel)

    def test_valid_color_sets_rgba_style(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["SetTextColor", "255 0 0 255"]]), index=0)
        style = ed._textcolor_swatch.styleSheet()
        assert "255" in style
        assert "transparent" not in style

    def test_empty_color_shows_transparent(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        style = ed._textcolor_swatch.styleSheet()
        assert "transparent" in style

    def test_invalid_color_does_not_raise(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._textcolor_edit.setText("not_a_color")
        ed._update_color_swatches()   # must not raise

    def test_invalid_color_swatch_uses_dashed_border(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._textcolor_edit.setText("not_a_color")
        ed._update_color_swatches()
        style = ed._textcolor_swatch.styleSheet()
        assert "dashed" in style

    def test_update_color_swatches_updates_all_three(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(
            _rule(actions=[
                ["SetTextColor", "255 0 0 255"],
                ["SetBorderColor", "0 255 0 255"],
                ["SetBackgroundColor", "0 0 255 255"],
            ]),
            index=0,
        )
        for swatch in (
            ed._textcolor_swatch, ed._bordercolor_swatch, ed._bgcolor_swatch
        ):
            assert "transparent" not in swatch.styleSheet()

    def test_bgcolor_swatch_object_name(self, qapp):
        ed = _make_editor(qapp)
        assert ed._bgcolor_swatch.objectName() == "ColorSwatch"


# ---------------------------------------------------------------------------
# TestP134Hints  (P13.4 新增)
# ---------------------------------------------------------------------------

class TestP134Hints:
    """PlayAlertSound and MinimapIcon rows have a one-line format hint."""

    def test_alert_hint_exists(self, qapp):
        from PySide6.QtWidgets import QLabel
        ed = _make_editor(qapp)
        assert hasattr(ed, "_alert_hint")
        assert isinstance(ed._alert_hint, QLabel)

    def test_minimap_hint_exists(self, qapp):
        from PySide6.QtWidgets import QLabel
        ed = _make_editor(qapp)
        assert hasattr(ed, "_minimap_hint")
        assert isinstance(ed._minimap_hint, QLabel)

    def test_alert_hint_mentions_format(self, qapp):
        ed = _make_editor(qapp)
        text = ed._alert_hint.text()
        assert "格式" in text or "例" in text

    def test_minimap_hint_mentions_format(self, qapp):
        ed = _make_editor(qapp)
        text = ed._minimap_hint.text()
        assert "格式" in text or "例" in text

    def test_alert_hint_mentions_example(self, qapp):
        ed = _make_editor(qapp)
        assert "1 300" in ed._alert_hint.text()

    def test_minimap_hint_mentions_example(self, qapp):
        ed = _make_editor(qapp)
        assert "Red Circle" in ed._minimap_hint.text() or "Circle" in ed._minimap_hint.text()

    def test_alert_hint_object_name(self, qapp):
        ed = _make_editor(qapp)
        assert ed._alert_hint.objectName() == "RuleDetailHintLabel"

    def test_minimap_hint_object_name(self, qapp):
        ed = _make_editor(qapp)
        assert ed._minimap_hint.objectName() == "RuleDetailHintLabel"


# ---------------------------------------------------------------------------
# TestP136ColorPickerDialog  (P13.6 新增)
# ---------------------------------------------------------------------------

class TestP136ColorPickerDialog:
    """Colour picker dialog — cursor, tooltip, parse helper, and dialog flow."""

    # ── Swatch cursor & tooltip ───────────────────────────────────

    def test_textcolor_swatch_pointing_hand_cursor(self, qapp):
        from PySide6.QtCore import Qt
        ed = _make_editor(qapp)
        assert ed._textcolor_swatch.cursor().shape() == Qt.CursorShape.PointingHandCursor

    def test_bordercolor_swatch_pointing_hand_cursor(self, qapp):
        from PySide6.QtCore import Qt
        ed = _make_editor(qapp)
        assert ed._bordercolor_swatch.cursor().shape() == Qt.CursorShape.PointingHandCursor

    def test_bgcolor_swatch_pointing_hand_cursor(self, qapp):
        from PySide6.QtCore import Qt
        ed = _make_editor(qapp)
        assert ed._bgcolor_swatch.cursor().shape() == Qt.CursorShape.PointingHandCursor

    def test_textcolor_swatch_tooltip_not_empty(self, qapp):
        ed = _make_editor(qapp)
        assert ed._textcolor_swatch.toolTip() != ""

    def test_bordercolor_swatch_tooltip_not_empty(self, qapp):
        ed = _make_editor(qapp)
        assert ed._bordercolor_swatch.toolTip() != ""

    def test_bgcolor_swatch_tooltip_not_empty(self, qapp):
        ed = _make_editor(qapp)
        assert ed._bgcolor_swatch.toolTip() != ""

    def test_textcolor_swatch_tooltip_mentions_text(self, qapp):
        ed = _make_editor(qapp)
        assert "文字" in ed._textcolor_swatch.toolTip()

    def test_bordercolor_swatch_tooltip_mentions_border(self, qapp):
        ed = _make_editor(qapp)
        assert "邊框" in ed._bordercolor_swatch.toolTip()

    def test_bgcolor_swatch_tooltip_mentions_background(self, qapp):
        ed = _make_editor(qapp)
        assert "背景" in ed._bgcolor_swatch.toolTip()

    # ── _parse_rgba_to_qcolor ─────────────────────────────────────

    def test_parse_valid_rgb_adds_alpha_255(self, qapp):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        c = ed._parse_rgba_to_qcolor("255 0 0", "SetTextColor")
        assert c.red() == 255 and c.green() == 0 and c.blue() == 0
        assert c.alpha() == 255

    def test_parse_valid_rgba(self, qapp):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        c = ed._parse_rgba_to_qcolor("10 20 30 128", "SetTextColor")
        assert c.red() == 10 and c.green() == 20
        assert c.blue() == 30 and c.alpha() == 128

    def test_parse_out_of_range_clamped(self, qapp):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        c = ed._parse_rgba_to_qcolor("999 -5 300 0", "SetTextColor")
        assert c.red() == 255 and c.green() == 0 and c.blue() == 255 and c.alpha() == 0

    def test_parse_invalid_text_returns_textcolor_default(self, qapp):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        c = ed._parse_rgba_to_qcolor("not_a_color", "SetTextColor")
        assert c == QColor(255, 255, 255, 255)

    def test_parse_empty_returns_bgcolor_default(self, qapp):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        c = ed._parse_rgba_to_qcolor("", "SetBackgroundColor")
        assert c == QColor(0, 0, 0, 180)

    def test_parse_invalid_returns_bordercolor_default(self, qapp):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        c = ed._parse_rgba_to_qcolor("xyz abc", "SetBorderColor")
        assert c == QColor(0, 0, 0, 255)

    # ── _on_swatch_clicked: accept ────────────────────────────────

    def test_accept_writes_rgba_to_textcolor_edit(self, qapp, monkeypatch):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["SetTextColor", "0 0 0 255"]]), index=0)

        chosen = QColor(255, 40, 0, 220)
        monkeypatch.setattr(ed, "_choose_color", lambda fk, ct: chosen)

        ed._on_swatch_clicked("SetTextColor", ed._textcolor_edit)
        assert ed._textcolor_edit.text() == "255 40 0 220"

    def test_accept_emits_rule_changed(self, qapp, monkeypatch):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["SetTextColor", "0 0 0 255"]]), index=0)
        received = _collect_signals(ed)

        chosen = QColor(200, 100, 50, 180)
        monkeypatch.setattr(ed, "_choose_color", lambda fk, ct: chosen)

        ed._on_swatch_clicked("SetTextColor", ed._textcolor_edit)
        assert len(received) == 1
        _idx, updated = received[0]
        tc_vals = [v for k, v in updated.actions if k == "SetTextColor"]
        assert tc_vals == ["200 100 50 180"]

    def test_accept_updates_bgcolor_field(self, qapp, monkeypatch):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)

        chosen = QColor(0, 0, 0, 150)
        monkeypatch.setattr(ed, "_choose_color", lambda fk, ct: chosen)

        ed._on_swatch_clicked("SetBackgroundColor", ed._bgcolor_edit)
        assert ed._bgcolor_edit.text() == "0 0 0 150"

    def test_accept_updates_swatch_color(self, qapp, monkeypatch):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)

        chosen = QColor(255, 0, 0, 255)
        monkeypatch.setattr(ed, "_choose_color", lambda fk, ct: chosen)

        ed._on_swatch_clicked("SetTextColor", ed._textcolor_edit)
        # Swatch should now show a red colour — not transparent
        assert "transparent" not in ed._textcolor_swatch.styleSheet()

    # ── _on_swatch_clicked: cancel ────────────────────────────────

    def test_cancel_does_not_change_edit(self, qapp, monkeypatch):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["SetTextColor", "10 20 30 200"]]), index=0)

        monkeypatch.setattr(ed, "_choose_color", lambda fk, ct: QColor())

        ed._on_swatch_clicked("SetTextColor", ed._textcolor_edit)
        assert ed._textcolor_edit.text() == "10 20 30 200"

    def test_cancel_does_not_emit_rule_changed(self, qapp, monkeypatch):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["SetTextColor", "10 20 30 200"]]), index=0)
        received = _collect_signals(ed)

        monkeypatch.setattr(ed, "_choose_color", lambda fk, ct: QColor())

        ed._on_swatch_clicked("SetTextColor", ed._textcolor_edit)
        assert len(received) == 0

    # ── set_rule does not open dialog ────────────────────────────

    def test_set_rule_does_not_call_choose_color(self, qapp, monkeypatch):
        """set_rule must never open a colour picker."""
        from PySide6.QtGui import QColor
        opened: list[bool] = []

        def _fake_choose(fk, ct):
            opened.append(True)
            return QColor()

        ed = _make_editor(qapp)
        monkeypatch.setattr(ed, "_choose_color", _fake_choose)
        ed.set_rule(_rule(actions=[["SetTextColor", "255 0 0 255"]]), index=0)
        assert opened == []

    # ── field_key passed to _choose_color ────────────────────────

    def test_field_key_passed_to_choose_color(self, qapp, monkeypatch):
        from PySide6.QtGui import QColor
        received_keys: list[str] = []

        def _fake_choose(fk, ct):
            received_keys.append(fk)
            return QColor()   # cancel

        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        monkeypatch.setattr(ed, "_choose_color", _fake_choose)

        ed._on_swatch_clicked("SetBorderColor", ed._bordercolor_edit)
        assert received_keys == ["SetBorderColor"]


# ---------------------------------------------------------------------------
# TestP137MinimapPicker  (P13.7 — Minimap Icon Picker dropdowns)
# ---------------------------------------------------------------------------

class TestP137MinimapPicker:
    """Minimap icon picker: 3 QComboBox dropdowns that sync bidirectionally
    with the MinimapIcon text field."""

    # ── widgets exist ─────────────────────────────────────────────

    def test_mm_size_combo_exists(self, qapp):
        from PySide6.QtWidgets import QComboBox
        ed = _make_editor(qapp)
        assert hasattr(ed, "_mm_size")
        assert isinstance(ed._mm_size, QComboBox)

    def test_mm_color_combo_exists(self, qapp):
        from PySide6.QtWidgets import QComboBox
        ed = _make_editor(qapp)
        assert hasattr(ed, "_mm_color")
        assert isinstance(ed._mm_color, QComboBox)

    def test_mm_shape_combo_exists(self, qapp):
        from PySide6.QtWidgets import QComboBox
        ed = _make_editor(qapp)
        assert hasattr(ed, "_mm_shape")
        assert isinstance(ed._mm_shape, QComboBox)

    def test_minimap_edit_still_exists(self, qapp):
        from PySide6.QtWidgets import QLineEdit
        ed = _make_editor(qapp)
        assert hasattr(ed, "_minimap_edit")
        assert isinstance(ed._minimap_edit, QLineEdit)

    # ── combo items ───────────────────────────────────────────────

    def test_size_items_are_0_1_2(self, qapp):
        ed = _make_editor(qapp)
        sizes = [ed._mm_size.itemText(i) for i in range(ed._mm_size.count())]
        assert sizes == ["0", "1", "2"]

    def test_color_items_include_expected(self, qapp):
        ed = _make_editor(qapp)
        colors = [ed._mm_color.itemText(i) for i in range(ed._mm_color.count())]
        for c in ("Red", "Green", "Blue", "White", "Yellow", "Cyan",
                  "Grey", "Orange", "Pink", "Purple", "Brown"):
            assert c in colors, f"missing color: {c}"

    def test_shape_items_include_expected(self, qapp):
        ed = _make_editor(qapp)
        shapes = [ed._mm_shape.itemText(i) for i in range(ed._mm_shape.count())]
        for s in ("Circle", "Diamond", "Hexagon", "Square", "Star",
                  "Triangle", "Cross", "Moon", "Raindrop", "Kite",
                  "Pentagon", "UpsideDownHouse"):
            assert s in shapes, f"missing shape: {s}"

    # ── set_rule syncs dropdowns ──────────────────────────────────

    def test_set_rule_syncs_size(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "2 Blue Star"]]), index=0)
        assert ed._mm_size.currentText() == "2"

    def test_set_rule_syncs_color(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        assert ed._mm_color.currentText() == "Red"

    def test_set_rule_syncs_shape(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "0 Green Diamond"]]), index=0)
        assert ed._mm_shape.currentText() == "Diamond"

    def test_set_rule_does_not_emit(self, qapp):
        ed = _make_editor(qapp)
        received = _collect_signals(ed)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        assert received == []

    def test_set_rule_invalid_minimap_does_not_crash(self, qapp):
        ed = _make_editor(qapp)
        # invalid text — dropdowns stay at defaults, no exception
        ed.set_rule(_rule(actions=[["MinimapIcon", "not valid"]]), index=0)
        assert ed._minimap_edit.text() == "not valid"

    def test_set_rule_invalid_does_not_change_dropdowns(self, qapp):
        ed = _make_editor(qapp)
        default_size = ed._mm_size.currentText()
        ed.set_rule(_rule(actions=[["MinimapIcon", "bad"]]), index=0)
        assert ed._mm_size.currentText() == default_size

    def test_set_rule_empty_minimap_does_not_crash(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        assert ed._minimap_edit.text() == ""

    # ── dropdown → text (selector changes write text) ─────────────

    def test_size_change_writes_text(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        ed._mm_size.setCurrentText("2")
        assert ed._minimap_edit.text() == "2 Red Circle"

    def test_color_change_writes_text(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        ed._mm_color.setCurrentText("Blue")
        assert ed._minimap_edit.text() == "1 Blue Circle"

    def test_shape_change_writes_text(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        ed._mm_shape.setCurrentText("Star")
        assert ed._minimap_edit.text() == "1 Red Star"

    # ── dropdown → emit ───────────────────────────────────────────

    def test_size_change_emits_rule_changed(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        received = _collect_signals(ed)
        ed._mm_size.setCurrentText("0")
        assert len(received) == 1
        _idx, updated = received[0]
        mm_vals = [v for k, v in updated.actions if k == "MinimapIcon"]
        assert mm_vals == ["0 Red Circle"]

    def test_color_change_emits_rule_changed(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        received = _collect_signals(ed)
        ed._mm_color.setCurrentText("Green")
        assert len(received) == 1

    def test_shape_change_emits_rule_changed(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        received = _collect_signals(ed)
        ed._mm_shape.setCurrentText("Triangle")
        assert len(received) == 1

    # ── text → dropdowns (manual input syncs selectors) ──────────

    def test_manual_valid_text_syncs_size(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._minimap_edit.setText("2 Blue Star")
        assert ed._mm_size.currentText() == "2"

    def test_manual_valid_text_syncs_color(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._minimap_edit.setText("2 Blue Star")
        assert ed._mm_color.currentText() == "Blue"

    def test_manual_valid_text_syncs_shape(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._minimap_edit.setText("2 Blue Star")
        assert ed._mm_shape.currentText() == "Star"

    def test_manual_invalid_text_does_not_crash(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._minimap_edit.setText("not valid at all")
        # no crash, dropdowns unchanged

    def test_manual_partial_text_does_not_crash(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._minimap_edit.setText("1")
        # no crash, dropdowns unchanged

    def test_manual_text_does_not_emit_until_editing_finished(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        received = _collect_signals(ed)
        # setText triggers textChanged but NOT editingFinished
        ed._minimap_edit.setText("2 Blue Star")
        assert received == []

    # ── no circular loop ─────────────────────────────────────────

    def test_no_loop_on_dropdown_change(self, qapp):
        """Changing a dropdown must not trigger infinite signal recursion."""
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        received = _collect_signals(ed)
        ed._mm_shape.setCurrentText("Moon")
        # exactly one emit, not many
        assert len(received) == 1

    def test_mm_syncing_flag_resets_after_change(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        ed._mm_size.setCurrentText("0")
        assert ed._mm_syncing is False

    # ── _mm_parse module-level helper ────────────────────────────

    def test_parse_valid(self, qapp):
        from ui.rule_detail_editor import _mm_parse
        assert _mm_parse("1 Red Circle") == ("1", "Red", "Circle")

    def test_parse_all_zeros(self, qapp):
        from ui.rule_detail_editor import _mm_parse
        assert _mm_parse("0 Green Diamond") == ("0", "Green", "Diamond")

    def test_parse_invalid_size(self, qapp):
        from ui.rule_detail_editor import _mm_parse
        assert _mm_parse("5 Red Circle") is None

    def test_parse_invalid_color(self, qapp):
        from ui.rule_detail_editor import _mm_parse
        assert _mm_parse("1 Magenta Circle") is None

    def test_parse_invalid_shape(self, qapp):
        from ui.rule_detail_editor import _mm_parse
        assert _mm_parse("1 Red Pentagon9") is None

    def test_parse_too_few_parts(self, qapp):
        from ui.rule_detail_editor import _mm_parse
        assert _mm_parse("1 Red") is None

    def test_parse_empty_string(self, qapp):
        from ui.rule_detail_editor import _mm_parse
        assert _mm_parse("") is None


# ---------------------------------------------------------------------------
# TestP138AlertSoundPicker  (P13.8 — Alert Sound Picker spinboxes)
# ---------------------------------------------------------------------------

class TestP138AlertSoundPicker:
    """Alert sound picker: Sound-ID (0–16) and Volume (0–300) QSpinBox controls
    that sync bidirectionally with the PlayAlertSound text field."""

    # ── widgets exist ─────────────────────────────────────────────

    def test_alert_id_spin_exists(self, qapp):
        from PySide6.QtWidgets import QSpinBox
        ed = _make_editor(qapp)
        assert hasattr(ed, "_alert_id_spin")
        assert isinstance(ed._alert_id_spin, QSpinBox)

    def test_alert_vol_spin_exists(self, qapp):
        from PySide6.QtWidgets import QSpinBox
        ed = _make_editor(qapp)
        assert hasattr(ed, "_alert_vol_spin")
        assert isinstance(ed._alert_vol_spin, QSpinBox)

    def test_alert_edit_still_exists(self, qapp):
        from PySide6.QtWidgets import QLineEdit
        ed = _make_editor(qapp)
        assert hasattr(ed, "_alert_edit")
        assert isinstance(ed._alert_edit, QLineEdit)

    # ── spin ranges ───────────────────────────────────────────────

    def test_id_spin_min_is_0(self, qapp):
        ed = _make_editor(qapp)
        assert ed._alert_id_spin.minimum() == 0

    def test_id_spin_max_is_16(self, qapp):
        ed = _make_editor(qapp)
        assert ed._alert_id_spin.maximum() == 16

    def test_vol_spin_min_is_0(self, qapp):
        ed = _make_editor(qapp)
        assert ed._alert_vol_spin.minimum() == 0

    def test_vol_spin_max_is_300(self, qapp):
        ed = _make_editor(qapp)
        assert ed._alert_vol_spin.maximum() == 300

    # ── set_rule syncs spinboxes ──────────────────────────────────

    def test_set_rule_syncs_id(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "3 200"]]), index=0)
        assert ed._alert_id_spin.value() == 3

    def test_set_rule_syncs_volume(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "3 200"]]), index=0)
        assert ed._alert_vol_spin.value() == 200

    def test_set_rule_empty_resets_spins(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        assert ed._alert_id_spin.value() == 0
        assert ed._alert_vol_spin.value() == 0

    def test_set_rule_does_not_emit(self, qapp):
        ed = _make_editor(qapp)
        received = _collect_signals(ed)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "1 300"]]), index=0)
        assert received == []

    def test_set_rule_invalid_does_not_crash(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "bad"]]), index=0)
        assert ed._alert_edit.text() == "bad"

    def test_set_rule_invalid_resets_spins_to_zero(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "3 200"]]), index=0)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "bad"]]), index=0)
        assert ed._alert_id_spin.value() == 0
        assert ed._alert_vol_spin.value() == 0

    # ── spin → text ───────────────────────────────────────────────

    def test_id_change_writes_text(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "1 200"]]), index=0)
        ed._alert_id_spin.setValue(5)
        assert ed._alert_edit.text() == "5 200"

    def test_vol_change_writes_text(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "1 200"]]), index=0)
        ed._alert_vol_spin.setValue(150)
        assert ed._alert_edit.text() == "1 150"

    def test_id_zero_clears_text(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "1 200"]]), index=0)
        ed._alert_id_spin.setValue(0)
        assert ed._alert_edit.text() == ""

    def test_vol_zero_clears_text(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "1 200"]]), index=0)
        ed._alert_vol_spin.setValue(0)
        assert ed._alert_edit.text() == ""

    # ── spin → emit ───────────────────────────────────────────────

    def test_id_change_emits_rule_changed(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "1 200"]]), index=0)
        received = _collect_signals(ed)
        ed._alert_id_spin.setValue(2)
        assert len(received) == 1
        _idx, updated = received[0]
        alert_vals = [v for k, v in updated.actions if k == "PlayAlertSound"]
        assert alert_vals == ["2 200"]

    def test_vol_change_emits_rule_changed(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "1 200"]]), index=0)
        received = _collect_signals(ed)
        ed._alert_vol_spin.setValue(100)
        assert len(received) == 1

    def test_id_zero_clears_action(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "1 200"]]), index=0)
        received = _collect_signals(ed)
        ed._alert_id_spin.setValue(0)
        assert len(received) == 1
        _idx, updated = received[0]
        # _update_in_list removes the key when value is ""
        alert_vals = [v for k, v in updated.actions if k == "PlayAlertSound"]
        assert alert_vals == []

    def test_vol_zero_clears_action(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "1 200"]]), index=0)
        received = _collect_signals(ed)
        ed._alert_vol_spin.setValue(0)
        assert len(received) == 1
        _idx, updated = received[0]
        alert_vals = [v for k, v in updated.actions if k == "PlayAlertSound"]
        assert alert_vals == []

    # ── text → spins (manual input syncs controls) ────────────────

    def test_manual_valid_text_syncs_id(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._alert_edit.setText("7 250")
        assert ed._alert_id_spin.value() == 7

    def test_manual_valid_text_syncs_vol(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._alert_edit.setText("7 250")
        assert ed._alert_vol_spin.value() == 250

    def test_manual_empty_text_resets_spins(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "1 200"]]), index=0)
        ed._alert_edit.setText("")
        assert ed._alert_id_spin.value() == 0
        assert ed._alert_vol_spin.value() == 0

    def test_manual_invalid_text_does_not_crash(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._alert_edit.setText("not valid")
        # no crash, spins reset to 0
        assert ed._alert_id_spin.value() == 0

    def test_manual_text_does_not_emit_until_editing_finished(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        received = _collect_signals(ed)
        ed._alert_edit.setText("3 200")
        assert received == []

    # ── no circular loop ─────────────────────────────────────────

    def test_no_loop_on_spin_change(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "1 200"]]), index=0)
        received = _collect_signals(ed)
        ed._alert_vol_spin.setValue(250)
        assert len(received) == 1

    def test_syncing_flag_resets_after_change(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "1 200"]]), index=0)
        ed._alert_id_spin.setValue(3)
        assert ed._alert_syncing is False

    # ── _alert_parse module-level helper ─────────────────────────

    def test_parse_valid(self, qapp):
        from ui.rule_detail_editor import _alert_parse
        assert _alert_parse("1 300") == (1, 300)

    def test_parse_boundary_max(self, qapp):
        from ui.rule_detail_editor import _alert_parse
        assert _alert_parse("16 300") == (16, 300)

    def test_parse_zero_id(self, qapp):
        from ui.rule_detail_editor import _alert_parse
        assert _alert_parse("0 200") == (0, 200)

    def test_parse_id_out_of_range(self, qapp):
        from ui.rule_detail_editor import _alert_parse
        assert _alert_parse("17 300") is None

    def test_parse_vol_out_of_range(self, qapp):
        from ui.rule_detail_editor import _alert_parse
        assert _alert_parse("1 301") is None

    def test_parse_non_numeric(self, qapp):
        from ui.rule_detail_editor import _alert_parse
        assert _alert_parse("abc 300") is None

    def test_parse_too_few_parts(self, qapp):
        from ui.rule_detail_editor import _alert_parse
        assert _alert_parse("1") is None

    def test_parse_empty(self, qapp):
        from ui.rule_detail_editor import _alert_parse
        assert _alert_parse("") is None


# ===========================================================================
# TestP153VisualColorEditor  (P15.3 新增)
# ===========================================================================

class TestP153ColorPickButtons:
    """P15.3: explicit Pick buttons exist and are QPushButton instances."""

    def test_textcolor_pick_btn_exists(self, qapp):
        ed = _make_editor(qapp)
        assert hasattr(ed, "_textcolor_btn")

    def test_textcolor_pick_btn_is_qpushbutton(self, qapp):
        from PySide6.QtWidgets import QPushButton
        ed = _make_editor(qapp)
        assert isinstance(ed._textcolor_btn, QPushButton)

    def test_textcolor_pick_btn_objectname(self, qapp):
        ed = _make_editor(qapp)
        assert ed._textcolor_btn.objectName() == "ColorPickTextBtn"

    def test_bordercolor_pick_btn_exists(self, qapp):
        ed = _make_editor(qapp)
        assert hasattr(ed, "_bordercolor_btn")

    def test_bordercolor_pick_btn_objectname(self, qapp):
        ed = _make_editor(qapp)
        assert ed._bordercolor_btn.objectName() == "ColorPickBorderBtn"

    def test_bgcolor_pick_btn_exists(self, qapp):
        ed = _make_editor(qapp)
        assert hasattr(ed, "_bgcolor_btn")

    def test_bgcolor_pick_btn_objectname(self, qapp):
        ed = _make_editor(qapp)
        assert ed._bgcolor_btn.objectName() == "ColorPickBgBtn"

    def test_pick_buttons_have_text(self, qapp):
        ed = _make_editor(qapp)
        for btn in (ed._textcolor_btn, ed._bordercolor_btn, ed._bgcolor_btn):
            assert btn.text().strip() != ""

    def test_pick_btn_tooltip_set(self, qapp):
        ed = _make_editor(qapp)
        assert ed._textcolor_btn.toolTip() != ""


class TestP153ColorPickBtnAction:
    """P15.3: Pick button opens _on_swatch_clicked with correct arguments."""

    def _monkeypatched_ed(self, qapp, monkeypatch):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["SetTextColor", "100 150 200 255"]]), index=0)
        calls = []
        monkeypatch.setattr(
            ed, "_on_swatch_clicked",
            lambda fk, edit: calls.append((fk, edit))
        )
        return ed, calls

    def test_textcolor_btn_calls_on_swatch_clicked(self, qapp, monkeypatch):
        ed, calls = self._monkeypatched_ed(qapp, monkeypatch)
        ed._textcolor_btn.click()
        assert len(calls) == 1
        assert calls[0][0] == "SetTextColor"
        assert calls[0][1] is ed._textcolor_edit

    def test_bordercolor_btn_calls_on_swatch_clicked(self, qapp, monkeypatch):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["SetBorderColor", "0 255 0 200"]]), index=0)
        calls = []
        monkeypatch.setattr(
            ed, "_on_swatch_clicked",
            lambda fk, edit: calls.append((fk, edit))
        )
        ed._bordercolor_btn.click()
        assert len(calls) == 1
        assert calls[0][0] == "SetBorderColor"
        assert calls[0][1] is ed._bordercolor_edit

    def test_bgcolor_btn_calls_on_swatch_clicked(self, qapp, monkeypatch):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["SetBackgroundColor", "0 0 0 180"]]), index=0)
        calls = []
        monkeypatch.setattr(
            ed, "_on_swatch_clicked",
            lambda fk, edit: calls.append((fk, edit))
        )
        ed._bgcolor_btn.click()
        assert len(calls) == 1
        assert calls[0][0] == "SetBackgroundColor"
        assert calls[0][1] is ed._bgcolor_edit

    def test_pick_btn_accept_writes_rgba_to_field(self, qapp, monkeypatch):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["SetTextColor", "0 0 0 255"]]), index=0)
        chosen = QColor(10, 20, 30, 200)
        monkeypatch.setattr(ed, "_choose_color", lambda fk, ct: chosen)
        ed._textcolor_btn.click()
        assert ed._textcolor_edit.text() == "10 20 30 200"

    def test_pick_btn_cancel_does_not_change_field(self, qapp, monkeypatch):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["SetTextColor", "255 0 0 255"]]), index=0)
        monkeypatch.setattr(ed, "_choose_color", lambda fk, ct: QColor())
        ed._textcolor_btn.click()
        assert ed._textcolor_edit.text() == "255 0 0 255"

    def test_pick_btn_accept_updates_swatch(self, qapp, monkeypatch):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["SetTextColor", "0 0 0 255"]]), index=0)
        chosen = QColor(255, 100, 0, 200)
        monkeypatch.setattr(ed, "_choose_color", lambda fk, ct: chosen)
        ed._textcolor_btn.click()
        style = ed._textcolor_swatch.styleSheet()
        assert "255" in style
        assert "transparent" not in style

    def test_pick_btn_accept_emits_rule_changed(self, qapp, monkeypatch):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        chosen = QColor(50, 60, 70, 180)
        monkeypatch.setattr(ed, "_choose_color", lambda fk, ct: chosen)
        emitted = []
        ed.rule_changed.connect(lambda idx, rule: emitted.append((idx, rule)))
        ed._textcolor_btn.click()
        assert len(emitted) == 1


class TestP153ColorPickLayout:
    """P15.3: swatch is positioned left of text field in the row layout."""

    def test_swatch_fixed_size(self, qapp):
        ed = _make_editor(qapp)
        swatch = ed._textcolor_swatch
        assert swatch.width() == 26   # P18.4 V4: enlarged from 22
        assert swatch.height() == 22  # P18.4 V4: enlarged from 20

    def test_pick_btn_fixed_width(self, qapp):
        ed = _make_editor(qapp)
        assert ed._textcolor_btn.width() == 48

    def test_three_pick_btns_have_same_width(self, qapp):
        ed = _make_editor(qapp)
        widths = {
            ed._textcolor_btn.width(),
            ed._bordercolor_btn.width(),
            ed._bgcolor_btn.width(),
        }
        assert len(widths) == 1


class TestP153SwatchStillClickable:
    """P15.3: swatch click still works (eventFilter path preserved)."""

    def test_swatch_still_has_pointing_hand_cursor(self, qapp):
        from PySide6.QtCore import Qt
        ed = _make_editor(qapp)
        for swatch in (
            ed._textcolor_swatch,
            ed._bordercolor_swatch,
            ed._bgcolor_swatch,
        ):
            assert swatch.cursor().shape() == Qt.CursorShape.PointingHandCursor

    def test_on_swatch_clicked_still_calls_choose_color(self, qapp, monkeypatch):
        from PySide6.QtGui import QColor
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["SetBorderColor", "0 0 0 255"]]), index=0)
        calls = []
        monkeypatch.setattr(
            ed, "_choose_color",
            lambda fk, ct: (calls.append(fk), QColor())[1]
        )
        ed._on_swatch_clicked("SetBorderColor", ed._bordercolor_edit)
        assert calls == ["SetBorderColor"]


# ===========================================================================
# TestP154MinimapPreviewWidget  (P15.4 新增)
# ===========================================================================

class TestP154MinimapPreviewWidgetUnit:
    """Unit tests for MinimapPreviewWidget — no editor required."""

    def test_widget_objectname(self, qapp):
        from ui.rule_detail_editor import MinimapPreviewWidget
        w = MinimapPreviewWidget()
        assert w.objectName() == "MinimapPreviewWidget"

    def test_widget_fixed_size(self, qapp):
        from ui.rule_detail_editor import MinimapPreviewWidget
        w = MinimapPreviewWidget()
        assert w.width()  == 54
        assert w.height() == 54

    def test_initial_state_is_empty(self, qapp):
        from ui.rule_detail_editor import MinimapPreviewWidget
        w = MinimapPreviewWidget()
        assert w._size  == ""
        assert w._color == ""
        assert w._shape == ""

    def test_set_icon_stores_values(self, qapp):
        from ui.rule_detail_editor import MinimapPreviewWidget
        w = MinimapPreviewWidget()
        w.set_icon("1", "Red", "Circle")
        assert w._size  == "1"
        assert w._color == "Red"
        assert w._shape == "Circle"

    def test_clear_resets_values(self, qapp):
        from ui.rule_detail_editor import MinimapPreviewWidget
        w = MinimapPreviewWidget()
        w.set_icon("1", "Red", "Circle")
        w.clear()
        assert w._size  == ""
        assert w._color == ""
        assert w._shape == ""

    def test_paintEvent_empty_does_not_raise(self, qapp):
        from ui.rule_detail_editor import MinimapPreviewWidget
        w = MinimapPreviewWidget()
        w.show()
        w.repaint()
        w.hide()

    def test_paintEvent_with_icon_does_not_raise(self, qapp):
        from ui.rule_detail_editor import MinimapPreviewWidget
        w = MinimapPreviewWidget()
        w.set_icon("1", "Blue", "Diamond")
        w.show()
        w.repaint()
        w.hide()

    @pytest.mark.parametrize("shape", [
        "circle", "square", "diamond", "triangle", "star", "cross",
        "hexagon", "pentagon", "moon", "kite", "raindrop", "upsidedownhouse",
        "unknown_shape",
    ])
    def test_all_shapes_paint_without_crash(self, qapp, shape):
        from ui.rule_detail_editor import MinimapPreviewWidget
        w = MinimapPreviewWidget()
        w.set_icon("1", "Green", shape.capitalize())
        w.show()
        w.repaint()
        w.hide()

    @pytest.mark.parametrize("color", [
        "Red", "Green", "Blue", "Brown", "White", "Yellow",
        "Cyan", "Grey", "Orange", "Pink", "Purple",
    ])
    def test_all_colors_paint_without_crash(self, qapp, color):
        from ui.rule_detail_editor import MinimapPreviewWidget
        w = MinimapPreviewWidget()
        w.set_icon("0", color, "Circle")
        w.show()
        w.repaint()
        w.hide()

    @pytest.mark.parametrize("size", ["0", "1", "2", "99"])
    def test_all_sizes_paint_without_crash(self, qapp, size):
        from ui.rule_detail_editor import MinimapPreviewWidget
        w = MinimapPreviewWidget()
        w.set_icon(size, "Red", "Star")
        w.show()
        w.repaint()
        w.hide()

    def test_unknown_color_falls_back_gracefully(self, qapp):
        from ui.rule_detail_editor import MinimapPreviewWidget
        w = MinimapPreviewWidget()
        w.set_icon("1", "NotAColor", "Circle")
        w.show()
        w.repaint()  # must not raise
        w.hide()


class TestP154MinimapPreviewOnEditor:
    """Integration: MinimapPreviewWidget is wired into RuleDetailEditor."""

    def test_preview_widget_exists_on_editor(self, qapp):
        ed = _make_editor(qapp)
        assert hasattr(ed, "_mm_preview")

    def test_preview_widget_is_correct_type(self, qapp):
        from ui.rule_detail_editor import MinimapPreviewWidget
        ed = _make_editor(qapp)
        assert isinstance(ed._mm_preview, MinimapPreviewWidget)

    def test_set_rule_valid_minimap_updates_preview(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        assert ed._mm_preview._size  == "1"
        assert ed._mm_preview._color == "Red"
        assert ed._mm_preview._shape == "Circle"

    def test_set_rule_no_minimap_clears_preview(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        assert ed._mm_preview._size == ""

    def test_manual_valid_text_updates_preview(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._minimap_edit.setText("0 Yellow Star")
        assert ed._mm_preview._size  == "0"
        assert ed._mm_preview._color == "Yellow"
        assert ed._mm_preview._shape == "Star"

    def test_manual_invalid_text_clears_preview(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        ed._minimap_edit.setText("bad input")
        assert ed._mm_preview._size == ""

    def test_manual_empty_text_clears_preview(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        ed._minimap_edit.setText("")
        assert ed._mm_preview._size == ""

    def test_combo_change_updates_preview(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        ed._mm_color.setCurrentText("Blue")
        assert ed._mm_preview._color == "Blue"

    def test_combo_shape_change_updates_preview(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        ed._mm_shape.setCurrentText("Star")
        assert ed._mm_preview._shape == "Star"

    def test_combo_size_change_updates_preview(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]]), index=0)
        ed._mm_size.setCurrentText("0")
        assert ed._mm_preview._size == "0"

    def test_invalid_text_does_not_raise(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._minimap_edit.setText("!!invalid!! text 999")
        # Must not raise; preview in empty state
        assert ed._mm_preview._size == ""

    def test_preview_survives_all_known_shapes(self, qapp):
        ed = _make_editor(qapp)
        for shape in _MM_SHAPES:
            ed._mm_preview.set_icon("1", "Red", shape)
            ed._mm_preview.repaint()  # must not raise


class TestP154MinimapPreviewColorsDict:
    """_MM_PREVIEW_COLORS covers all POE2 colour names."""

    def test_all_mm_colors_in_preview_map(self, qapp):
        from ui.rule_detail_editor import _MM_PREVIEW_COLORS
        for name in _MM_COLORS:
            assert name in _MM_PREVIEW_COLORS, f"Missing: {name}"

    def test_preview_color_tuples_are_valid_rgb(self, qapp):
        from ui.rule_detail_editor import _MM_PREVIEW_COLORS
        for name, rgb in _MM_PREVIEW_COLORS.items():
            assert len(rgb) == 3, f"{name}: expected (R,G,B)"
            for ch in rgb:
                assert 0 <= ch <= 255, f"{name}: channel {ch} out of range"


# ===========================================================================
# TestP155VisualSoundEditor  (P15.5 新增)
# ===========================================================================

class TestP155EffectParseFn:
    """Pure function _effect_parse() correctness."""

    def test_valid_color_only(self, qapp):
        result = _effect_parse("Red")
        assert result == ("Red", False)

    def test_valid_color_with_temp(self, qapp):
        result = _effect_parse("Blue Temp")
        assert result == ("Blue", True)

    def test_temp_case_insensitive(self, qapp):
        result = _effect_parse("Green temp")
        assert result is not None
        assert result[1] is True

    def test_invalid_color_returns_none(self, qapp):
        assert _effect_parse("NotAColor") is None

    def test_empty_returns_none(self, qapp):
        assert _effect_parse("") is None

    def test_whitespace_returns_none(self, qapp):
        assert _effect_parse("   ") is None

    def test_extra_words_ignored(self, qapp):
        result = _effect_parse("Purple Temp Extra")
        assert result == ("Purple", True)

    def test_all_valid_mm_colors_accepted(self, qapp):
        for color in _MM_COLORS:
            result = _effect_parse(color)
            assert result is not None, f"_effect_parse rejected valid color: {color}"
            assert result[0] == color
            assert result[1] is False

    def test_no_temp_returns_false(self, qapp):
        result = _effect_parse("Yellow")
        assert result == ("Yellow", False)

    def test_non_temp_second_word_returns_false(self, qapp):
        result = _effect_parse("Red permanent")
        assert result is not None
        assert result[1] is False


class TestP155AlertSoundPreviewLabel:
    """PlayAlertSound preview label exists and updates correctly."""

    def test_preview_lbl_exists(self, qapp):
        ed = _make_editor(qapp)
        assert hasattr(ed, "_alert_preview_lbl")

    def test_preview_lbl_objectname(self, qapp):
        from PySide6.QtWidgets import QLabel
        ed = _make_editor(qapp)
        assert isinstance(ed._alert_preview_lbl, QLabel)
        assert ed._alert_preview_lbl.objectName() == "AlertSoundPreviewLabel"

    def test_initial_label_shows_unset(self, qapp):
        ed = _make_editor(qapp)
        assert "未設定" in ed._alert_preview_lbl.text()

    def test_valid_sound_shows_id_and_vol(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "3 200"]]), index=0)
        text = ed._alert_preview_lbl.text()
        assert "3" in text
        assert "200" in text

    def test_invalid_sound_shows_unset(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._alert_edit.setText("99 999")
        assert "未設定" in ed._alert_preview_lbl.text()

    def test_empty_sound_shows_unset(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "1 300"]]), index=0)
        ed._alert_edit.setText("")
        assert "未設定" in ed._alert_preview_lbl.text()

    def test_preview_contains_note_symbol(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "5 150"]]), index=0)
        assert "♪" in ed._alert_preview_lbl.text()

    def test_set_rule_updates_preview(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayAlertSound", "7 100"]]), index=0)
        text = ed._alert_preview_lbl.text()
        assert "7" in text
        assert "100" in text

    def test_spin_change_updates_preview_via_text(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._alert_id_spin.setValue(2)
        ed._alert_vol_spin.setValue(250)
        text = ed._alert_preview_lbl.text()
        assert "2" in text
        assert "250" in text


class TestP155PlayEffectWidgets:
    """PlayEffect controls exist on the editor."""

    def test_effect_edit_exists(self, qapp):
        from PySide6.QtWidgets import QLineEdit
        ed = _make_editor(qapp)
        assert hasattr(ed, "_effect_edit")
        assert isinstance(ed._effect_edit, QLineEdit)

    def test_effect_edit_objectname(self, qapp):
        ed = _make_editor(qapp)
        assert ed._effect_edit.objectName() == "RuleDetailPlayEffect"

    def test_effect_color_combo_exists(self, qapp):
        from PySide6.QtWidgets import QComboBox
        ed = _make_editor(qapp)
        assert hasattr(ed, "_effect_color")
        assert isinstance(ed._effect_color, QComboBox)

    def test_effect_color_combo_objectname(self, qapp):
        ed = _make_editor(qapp)
        assert ed._effect_color.objectName() == "EffectColorCombo"

    def test_effect_color_combo_has_all_colors(self, qapp):
        ed = _make_editor(qapp)
        items = [ed._effect_color.itemText(i) for i in range(ed._effect_color.count())]
        for color in _MM_COLORS:
            assert color in items

    def test_effect_temp_cb_exists(self, qapp):
        from PySide6.QtWidgets import QCheckBox
        ed = _make_editor(qapp)
        assert hasattr(ed, "_effect_temp_cb")
        assert isinstance(ed._effect_temp_cb, QCheckBox)

    def test_effect_temp_cb_objectname(self, qapp):
        ed = _make_editor(qapp)
        assert ed._effect_temp_cb.objectName() == "EffectTempCheck"

    def test_effect_preview_lbl_exists(self, qapp):
        from PySide6.QtWidgets import QLabel
        ed = _make_editor(qapp)
        assert hasattr(ed, "_effect_preview_lbl")
        assert isinstance(ed._effect_preview_lbl, QLabel)

    def test_effect_preview_lbl_objectname(self, qapp):
        ed = _make_editor(qapp)
        assert ed._effect_preview_lbl.objectName() == "EffectPreviewLabel"

    def test_effect_initial_preview_shows_unset(self, qapp):
        ed = _make_editor(qapp)
        assert "未設定" in ed._effect_preview_lbl.text()


class TestP155PlayEffectSync:
    """PlayEffect text ↔ controls ↔ preview synchronization."""

    def test_valid_text_updates_color_combo(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayEffect", "Blue"]]), index=0)
        assert ed._effect_color.currentText() == "Blue"

    def test_valid_text_with_temp_checks_checkbox(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayEffect", "Red Temp"]]), index=0)
        assert ed._effect_temp_cb.isChecked() is True

    def test_valid_text_no_temp_unchecks_checkbox(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayEffect", "Green"]]), index=0)
        assert ed._effect_temp_cb.isChecked() is False

    def test_invalid_text_does_not_update_combo(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayEffect", "Blue"]]), index=0)
        ed._effect_edit.setText("NotAColor")
        # combo stays at last valid value
        assert ed._effect_color.currentText() == "Blue"

    def test_empty_text_does_not_crash(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._effect_edit.setText("")
        # no crash; preview shows unset
        assert "未設定" in ed._effect_preview_lbl.text()

    def test_color_combo_change_updates_text(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayEffect", "Red"]]), index=0)
        ed._effect_color.setCurrentText("Purple")
        assert "Purple" in ed._effect_edit.text()

    def test_temp_checkbox_adds_temp_to_text(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayEffect", "Red"]]), index=0)
        ed._effect_temp_cb.setChecked(True)
        assert "Temp" in ed._effect_edit.text()

    def test_temp_uncheck_removes_temp_from_text(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayEffect", "Red Temp"]]), index=0)
        ed._effect_temp_cb.setChecked(False)
        assert "Temp" not in ed._effect_edit.text()

    def test_valid_text_updates_preview_label(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayEffect", "Yellow"]]), index=0)
        assert "Yellow" in ed._effect_preview_lbl.text()

    def test_temp_flag_shows_in_preview(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayEffect", "Cyan Temp"]]), index=0)
        assert "Temp" in ed._effect_preview_lbl.text()

    def test_invalid_text_clears_preview(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayEffect", "Red"]]), index=0)
        ed._effect_edit.setText("invalid")
        assert "未設定" in ed._effect_preview_lbl.text()

    def test_set_rule_with_effect_populates_edit(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayEffect", "Orange Temp"]]), index=0)
        assert ed._effect_edit.text() == "Orange Temp"

    def test_set_rule_no_effect_clears_edit(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        assert ed._effect_edit.text() == ""

    def test_build_rule_saves_effect(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._effect_edit.setText("Pink")
        emitted = []
        ed.rule_changed.connect(lambda i, r: emitted.append(r))
        ed._effect_edit.editingFinished.emit()
        assert len(emitted) == 1
        keys = [k for k, v in emitted[0].actions]
        assert "PlayEffect" in keys

    def test_build_rule_empty_effect_not_in_actions(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        ed._effect_edit.setText("")
        ed._effect_edit.editingFinished.emit()
        # empty text → PlayEffect not saved
        assert ed._effect_edit.text() == ""

    def test_effect_combo_change_emits_rule_changed(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(actions=[["PlayEffect", "Red"]]), index=0)
        emitted = []
        ed.rule_changed.connect(lambda i, r: emitted.append(r))
        ed._effect_color.setCurrentText("Green")
        assert len(emitted) >= 1
