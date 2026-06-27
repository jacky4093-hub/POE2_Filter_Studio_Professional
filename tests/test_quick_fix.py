"""Tests for core/quick_fix.py — P16.4 Validation Quick Fix Foundation"""

import pytest

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from core.models import FilterRule
from core.validator import ValidationIssue, ValidationSeverity
from core.quick_fix import QuickFix, get_quick_fixes, apply_quick_fix


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def _rule(actions: list | None = None, conditions: list | None = None) -> FilterRule:
    return FilterRule(
        action="Show",
        enabled=True,
        conditions=conditions or [],
        actions=actions or [],
        pre_lines=[],
        inline_comment="",
        unknown_lines=[],
    )


def _issue(sev: ValidationSeverity, field: str, msg: str = "m", idx: int = 0) -> ValidationIssue:
    return ValidationIssue(sev, field, msg, rule_index=idx)


# ---------------------------------------------------------------------------
# TestQuickFixDataclass
# ---------------------------------------------------------------------------

class TestQuickFixDataclass:

    def test_fields_accessible(self):
        fix = QuickFix(label="修正為 45", field="SetFontSize", new_value="45")
        assert fix.label     == "修正為 45"
        assert fix.field     == "SetFontSize"
        assert fix.new_value == "45"

    def test_is_frozen(self):
        fix = QuickFix(label="x", field="y", new_value="z")
        with pytest.raises(Exception):
            fix.label = "changed"  # type: ignore[misc]

    def test_equality(self):
        a = QuickFix("x", "SetFontSize", "1")
        b = QuickFix("x", "SetFontSize", "1")
        assert a == b

    def test_inequality_different_value(self):
        a = QuickFix("x", "SetFontSize", "1")
        b = QuickFix("x", "SetFontSize", "45")
        assert a != b


# ---------------------------------------------------------------------------
# TestGetQuickFixes — SetFontSize
# ---------------------------------------------------------------------------

class TestGetQuickFixesFontSize:

    def test_valid_fontsize_no_fix(self):
        rule = _rule(actions=[["SetFontSize", "32"]])
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        assert get_quick_fixes(rule, issue) == []

    def test_size_0_clamp_to_1(self):
        rule = _rule(actions=[["SetFontSize", "0"]])
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        fixes = get_quick_fixes(rule, issue)
        assert len(fixes) == 1
        assert fixes[0].new_value == "1"
        assert fixes[0].field == "SetFontSize"

    def test_size_46_clamp_to_45(self):
        rule = _rule(actions=[["SetFontSize", "46"]])
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        fixes = get_quick_fixes(rule, issue)
        assert fixes[0].new_value == "45"

    def test_size_negative_clamp_to_1(self):
        rule = _rule(actions=[["SetFontSize", "-10"]])
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        fixes = get_quick_fixes(rule, issue)
        assert fixes[0].new_value == "1"

    def test_size_100_clamp_to_45(self):
        rule = _rule(actions=[["SetFontSize", "100"]])
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        fixes = get_quick_fixes(rule, issue)
        assert fixes[0].new_value == "45"

    def test_non_integer_no_fix(self):
        rule = _rule(actions=[["SetFontSize", "large"]])
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        assert get_quick_fixes(rule, issue) == []

    def test_float_string_no_fix(self):
        rule = _rule(actions=[["SetFontSize", "12.5"]])
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        assert get_quick_fixes(rule, issue) == []

    def test_fix_label_contains_clamped_value(self):
        rule = _rule(actions=[["SetFontSize", "100"]])
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        fixes = get_quick_fixes(rule, issue)
        assert "45" in fixes[0].label

    @pytest.mark.parametrize("size", [1, 22, 45])
    def test_boundary_valid_no_fix(self, size):
        rule = _rule(actions=[["SetFontSize", str(size)]])
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        assert get_quick_fixes(rule, issue) == []


# ---------------------------------------------------------------------------
# TestGetQuickFixes — Color
# ---------------------------------------------------------------------------

class TestGetQuickFixesColor:

    @pytest.mark.parametrize("key", [
        "SetTextColor", "SetBorderColor", "SetBackgroundColor",
    ])
    def test_valid_color_no_fix(self, key):
        rule = _rule(actions=[[key, "255 0 0 255"]])
        issue = _issue(ValidationSeverity.ERROR, key)
        assert get_quick_fixes(rule, issue) == []

    @pytest.mark.parametrize("key", [
        "SetTextColor", "SetBorderColor", "SetBackgroundColor",
    ])
    def test_over_255_clamps(self, key):
        rule = _rule(actions=[[key, "300 0 0 255"]])
        issue = _issue(ValidationSeverity.ERROR, key)
        fixes = get_quick_fixes(rule, issue)
        assert len(fixes) == 1
        assert fixes[0].new_value == "255 0 0 255"

    def test_negative_channel_clamps_to_0(self):
        rule = _rule(actions=[["SetTextColor", "-10 100 200 255"]])
        issue = _issue(ValidationSeverity.ERROR, "SetTextColor")
        fixes = get_quick_fixes(rule, issue)
        assert fixes[0].new_value == "0 100 200 255"

    def test_multiple_channels_all_clamped(self):
        rule = _rule(actions=[["SetTextColor", "300 -5 256 100"]])
        issue = _issue(ValidationSeverity.ERROR, "SetTextColor")
        fixes = get_quick_fixes(rule, issue)
        assert fixes[0].new_value == "255 0 255 100"

    def test_rgb_three_parts_clamped(self):
        rule = _rule(actions=[["SetBorderColor", "300 0 0"]])
        issue = _issue(ValidationSeverity.ERROR, "SetBorderColor")
        fixes = get_quick_fixes(rule, issue)
        assert fixes[0].new_value == "255 0 0"

    def test_wrong_part_count_no_fix(self):
        rule = _rule(actions=[["SetTextColor", "255 0"]])   # only 2 parts
        issue = _issue(ValidationSeverity.ERROR, "SetTextColor")
        assert get_quick_fixes(rule, issue) == []

    def test_five_parts_no_fix(self):
        rule = _rule(actions=[["SetTextColor", "255 0 0 255 99"]])
        issue = _issue(ValidationSeverity.ERROR, "SetTextColor")
        assert get_quick_fixes(rule, issue) == []

    def test_non_integer_channel_no_fix(self):
        rule = _rule(actions=[["SetTextColor", "red green blue"]])
        issue = _issue(ValidationSeverity.ERROR, "SetTextColor")
        assert get_quick_fixes(rule, issue) == []

    def test_field_preserved_in_fix(self):
        rule = _rule(actions=[["SetBorderColor", "300 0 0 255"]])
        issue = _issue(ValidationSeverity.ERROR, "SetBorderColor")
        fixes = get_quick_fixes(rule, issue)
        assert fixes[0].field == "SetBorderColor"

    def test_boundary_0_all_valid_no_fix(self):
        rule = _rule(actions=[["SetTextColor", "0 0 0 0"]])
        issue = _issue(ValidationSeverity.ERROR, "SetTextColor")
        assert get_quick_fixes(rule, issue) == []

    def test_boundary_255_all_valid_no_fix(self):
        rule = _rule(actions=[["SetTextColor", "255 255 255 255"]])
        issue = _issue(ValidationSeverity.ERROR, "SetTextColor")
        assert get_quick_fixes(rule, issue) == []


# ---------------------------------------------------------------------------
# TestGetQuickFixes — PlayAlertSound
# ---------------------------------------------------------------------------

class TestGetQuickFixesAlertSound:

    def test_valid_alert_no_fix(self):
        rule = _rule(actions=[["PlayAlertSound", "3 200"]])
        issue = _issue(ValidationSeverity.WARNING, "PlayAlertSound")
        assert get_quick_fixes(rule, issue) == []

    def test_volume_over_300_clamps(self):
        rule = _rule(actions=[["PlayAlertSound", "3 500"]])
        issue = _issue(ValidationSeverity.WARNING, "PlayAlertSound")
        fixes = get_quick_fixes(rule, issue)
        assert len(fixes) == 1
        assert fixes[0].new_value == "3 300"

    def test_volume_negative_clamps_to_0(self):
        rule = _rule(actions=[["PlayAlertSound", "5 -50"]])
        issue = _issue(ValidationSeverity.WARNING, "PlayAlertSound")
        fixes = get_quick_fixes(rule, issue)
        assert fixes[0].new_value == "5 0"

    def test_invalid_id_no_fix(self):
        rule = _rule(actions=[["PlayAlertSound", "0 200"]])    # ID 0 invalid
        issue = _issue(ValidationSeverity.WARNING, "PlayAlertSound")
        assert get_quick_fixes(rule, issue) == []

    def test_id_17_no_fix(self):
        rule = _rule(actions=[["PlayAlertSound", "17 200"]])
        issue = _issue(ValidationSeverity.WARNING, "PlayAlertSound")
        assert get_quick_fixes(rule, issue) == []

    def test_non_integer_no_fix(self):
        rule = _rule(actions=[["PlayAlertSound", "beep loud"]])
        issue = _issue(ValidationSeverity.WARNING, "PlayAlertSound")
        assert get_quick_fixes(rule, issue) == []

    def test_only_one_part_no_fix(self):
        rule = _rule(actions=[["PlayAlertSound", "5"]])
        issue = _issue(ValidationSeverity.WARNING, "PlayAlertSound")
        assert get_quick_fixes(rule, issue) == []

    def test_fix_preserves_id(self):
        rule = _rule(actions=[["PlayAlertSound", "7 999"]])
        issue = _issue(ValidationSeverity.WARNING, "PlayAlertSound")
        fixes = get_quick_fixes(rule, issue)
        assert fixes[0].new_value.startswith("7 ")

    def test_fix_label_contains_clamped_volume(self):
        rule = _rule(actions=[["PlayAlertSound", "3 999"]])
        issue = _issue(ValidationSeverity.WARNING, "PlayAlertSound")
        fixes = get_quick_fixes(rule, issue)
        assert "300" in fixes[0].label

    def test_boundary_volume_0_valid_no_fix(self):
        rule = _rule(actions=[["PlayAlertSound", "1 0"]])
        issue = _issue(ValidationSeverity.WARNING, "PlayAlertSound")
        assert get_quick_fixes(rule, issue) == []

    def test_boundary_volume_300_valid_no_fix(self):
        rule = _rule(actions=[["PlayAlertSound", "16 300"]])
        issue = _issue(ValidationSeverity.WARNING, "PlayAlertSound")
        assert get_quick_fixes(rule, issue) == []


# ---------------------------------------------------------------------------
# TestGetQuickFixes — edge cases
# ---------------------------------------------------------------------------

class TestGetQuickFixesEdgeCases:

    def test_field_not_in_actions_returns_empty(self):
        rule = _rule(actions=[])
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        assert get_quick_fixes(rule, issue) == []

    def test_minimap_no_fix(self):
        rule = _rule(actions=[["MinimapIcon", "9 Red Circle"]])
        issue = _issue(ValidationSeverity.WARNING, "MinimapIcon")
        assert get_quick_fixes(rule, issue) == []

    def test_unknown_field_no_fix(self):
        rule = _rule(actions=[["SomeFutureAction", "value"]])
        issue = _issue(ValidationSeverity.WARNING, "SomeFutureAction")
        assert get_quick_fixes(rule, issue) == []

    def test_empty_rule_info_no_fix(self):
        rule = _rule()
        issue = _issue(ValidationSeverity.INFO, "rule")
        assert get_quick_fixes(rule, issue) == []

    def test_returns_list(self):
        rule = _rule(actions=[["SetFontSize", "0"]])
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        result = get_quick_fixes(rule, issue)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# TestApplyQuickFix
# ---------------------------------------------------------------------------

class TestApplyQuickFix:

    def test_apply_fontsize_fix(self):
        rule = _rule(actions=[["SetFontSize", "100"]])
        fix = QuickFix(label="修正為 45", field="SetFontSize", new_value="45")
        new_rule = apply_quick_fix(rule, fix)
        vals = {str(k): str(v) for k, v in new_rule.actions}
        assert vals["SetFontSize"] == "45"

    def test_original_rule_unchanged(self):
        rule = _rule(actions=[["SetFontSize", "100"]])
        fix = QuickFix(label="x", field="SetFontSize", new_value="45")
        apply_quick_fix(rule, fix)
        assert rule.actions[0][1] == "100"

    def test_apply_color_fix(self):
        rule = _rule(actions=[["SetTextColor", "300 0 0 255"]])
        fix = QuickFix(label="x", field="SetTextColor", new_value="255 0 0 255")
        new_rule = apply_quick_fix(rule, fix)
        assert new_rule.actions[0][1] == "255 0 0 255"

    def test_apply_alert_sound_fix(self):
        rule = _rule(actions=[["PlayAlertSound", "3 999"]])
        fix = QuickFix(label="x", field="PlayAlertSound", new_value="3 300")
        new_rule = apply_quick_fix(rule, fix)
        assert new_rule.actions[0][1] == "3 300"

    def test_non_matching_field_rule_unchanged(self):
        rule = _rule(actions=[["SetFontSize", "32"]])
        fix = QuickFix(label="x", field="SetTextColor", new_value="0 0 0 255")
        new_rule = apply_quick_fix(rule, fix)
        assert new_rule.actions[0][1] == "32"

    def test_returns_filterlule(self):
        rule = _rule(actions=[["SetFontSize", "100"]])
        fix = QuickFix(label="x", field="SetFontSize", new_value="45")
        result = apply_quick_fix(rule, fix)
        assert isinstance(result, FilterRule)

    def test_other_actions_preserved(self):
        rule = _rule(actions=[
            ["SetFontSize",  "100"],
            ["SetTextColor", "255 0 0 255"],
        ])
        fix = QuickFix(label="x", field="SetFontSize", new_value="45")
        new_rule = apply_quick_fix(rule, fix)
        assert len(new_rule.actions) == 2
        # SetTextColor unchanged
        assert new_rule.actions[1][1] == "255 0 0 255"

    def test_first_matching_action_updated(self):
        rule = _rule(actions=[["SetFontSize", "100"]])
        fix = QuickFix(label="x", field="SetFontSize", new_value="1")
        new_rule = apply_quick_fix(rule, fix)
        assert new_rule.actions[0][1] == "1"

    def test_conditions_preserved(self):
        rule = _rule(
            conditions=[["Class", '"Currency"']],
            actions=[["SetFontSize", "100"]],
        )
        fix = QuickFix(label="x", field="SetFontSize", new_value="45")
        new_rule = apply_quick_fix(rule, fix)
        assert new_rule.conditions == [["Class", '"Currency"']]


# ---------------------------------------------------------------------------
# TestValidationPanelFixButton — panel shows Fix button only when available
# ---------------------------------------------------------------------------

class TestValidationPanelFixButton:

    def test_no_fixes_no_item_widget(self, qapp):
        from ui.validation_panel import ValidationPanel
        panel = ValidationPanel()
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        panel.refresh([issue], quick_fixes=[[]])  # empty fix list → no button
        assert panel._list.itemWidget(panel._list.item(0)) is None

    def test_fix_available_item_has_widget(self, qapp):
        from ui.validation_panel import ValidationPanel
        panel = ValidationPanel()
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        fix = QuickFix("修正為 45", "SetFontSize", "45")
        panel.refresh([issue], quick_fixes=[[fix]])
        widget = panel._list.itemWidget(panel._list.item(0))
        assert widget is not None

    def test_fix_widget_has_fix_button(self, qapp):
        from ui.validation_panel import ValidationPanel
        from PySide6.QtWidgets import QPushButton
        panel = ValidationPanel()
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        fix = QuickFix("修正為 45", "SetFontSize", "45")
        panel.refresh([issue], quick_fixes=[[fix]])
        widget = panel._list.itemWidget(panel._list.item(0))
        btns = widget.findChildren(QPushButton)
        fix_btns = [b for b in btns if b.objectName() == "ValidationFixBtn"]
        assert len(fix_btns) == 1

    def test_fix_button_label_matches_fix(self, qapp):
        from ui.validation_panel import ValidationPanel
        from PySide6.QtWidgets import QPushButton
        panel = ValidationPanel()
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        fix = QuickFix("修正為 45", "SetFontSize", "45")
        panel.refresh([issue], quick_fixes=[[fix]])
        widget = panel._list.itemWidget(panel._list.item(0))
        btn = widget.findChild(QPushButton, "ValidationFixBtn")
        assert btn.text() == "修正為 45"

    def test_clicking_fix_btn_emits_fix_requested(self, qapp):
        from ui.validation_panel import ValidationPanel
        from PySide6.QtWidgets import QPushButton
        panel = ValidationPanel()
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize", idx=3)
        fix = QuickFix("修正為 45", "SetFontSize", "45")
        panel.refresh([issue], quick_fixes=[[fix]])

        received = []
        panel.fix_requested.connect(lambda ri, f: received.append((ri, f)))

        widget = panel._list.itemWidget(panel._list.item(0))
        btn = widget.findChild(QPushButton, "ValidationFixBtn")
        btn.click()

        assert len(received) == 1
        ri, f = received[0]
        assert ri == 3
        assert f == fix

    def test_no_fixes_kwarg_no_button(self, qapp):
        from ui.validation_panel import ValidationPanel
        panel = ValidationPanel()
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize")
        panel.refresh([issue])  # no quick_fixes kwarg → None
        assert panel._list.itemWidget(panel._list.item(0)) is None

    def test_item_text_still_set_with_fix_widget(self, qapp):
        from ui.validation_panel import ValidationPanel
        panel = ValidationPanel()
        issue = _issue(ValidationSeverity.WARNING, "SetFontSize", msg="out of range")
        fix = QuickFix("修正", "SetFontSize", "45")
        panel.refresh([issue], quick_fixes=[[fix]])
        assert "SetFontSize" in panel._list.item(0).text()

    def test_mixed_fixes_and_no_fixes(self, qapp):
        from ui.validation_panel import ValidationPanel
        panel = ValidationPanel()
        issues = [
            _issue(ValidationSeverity.WARNING, "SetFontSize"),
            _issue(ValidationSeverity.ERROR,   "MinimapIcon"),   # no fix
        ]
        fixes_per = [
            [QuickFix("修正為 45", "SetFontSize", "45")],
            [],
        ]
        panel.refresh(issues, quick_fixes=fixes_per)
        assert panel._list.itemWidget(panel._list.item(0)) is not None
        assert panel._list.itemWidget(panel._list.item(1)) is None

    def test_fix_requested_signal_exists(self, qapp):
        from ui.validation_panel import ValidationPanel
        assert hasattr(ValidationPanel, "fix_requested")


# ---------------------------------------------------------------------------
# TestMainWindowQuickFix — apply via undo command
# ---------------------------------------------------------------------------

class TestMainWindowQuickFix:

    @pytest.fixture(scope="class")
    def qapp(self):
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

    def _load(self, window, tmp_path, text: str) -> None:
        f = tmp_path / "t.filter"
        f.write_text(text, encoding="utf-8")
        window.load_file(str(f))

    def test_on_quick_fix_requested_method_exists(self, window):
        assert callable(getattr(window, "_on_quick_fix_requested", None))

    def test_apply_fix_updates_rule_value(self, window, tmp_path):
        self._load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        fix = QuickFix("修正為 45", "SetFontSize", "45")
        window._on_quick_fix_requested(0, fix)
        vals = {str(k): str(v) for k, v in window._doc.rules[0].actions}
        assert vals["SetFontSize"] == "45"

    def test_apply_fix_is_undoable(self, window, tmp_path):
        self._load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        fix = QuickFix("修正為 45", "SetFontSize", "45")
        window._on_quick_fix_requested(0, fix)
        assert window._doc.can_undo()

    def test_undo_restores_original_value(self, window, tmp_path):
        self._load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        fix = QuickFix("修正為 45", "SetFontSize", "45")
        window._on_quick_fix_requested(0, fix)
        window._on_undo()
        vals = {str(k): str(v) for k, v in window._doc.rules[0].actions}
        assert vals["SetFontSize"] == "99"

    def test_apply_fix_refreshes_validation(self, window, tmp_path):
        self._load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        # Before fix: should show a warning
        assert window.validation_panel._list.count() >= 1
        fix = QuickFix("修正為 45", "SetFontSize", "45")
        window._on_quick_fix_requested(0, fix)
        # After fix: validation panel should be clean
        assert "0" in window.validation_panel._error_chip.text()
        assert "0" in window.validation_panel._warning_chip.text()

    def test_invalid_rule_index_ignored(self, window, tmp_path):
        self._load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        fix = QuickFix("x", "SetFontSize", "45")
        # Should not raise
        window._on_quick_fix_requested(-1, fix)
        window._on_quick_fix_requested(9999, fix)

    def test_refresh_validation_passes_fixes_to_panel(self, window, tmp_path):
        self._load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        # After load, panel should have the issue with a fix button available
        lw = window.validation_panel._list
        assert lw.count() >= 1
        # First item should have a fix widget (SetFontSize 99 → clamp fix)
        item = lw.item(0)
        widget = lw.itemWidget(item)
        assert widget is not None, "Expected a Fix row widget for SetFontSize 99"
