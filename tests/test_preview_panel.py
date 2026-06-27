"""Tests for preview parsing and PreviewPanel rendering behavior.

v2.0.0 additions (P13.2):
- Disabled rule shows _disabled_banner
- Invalid colour strings do not raise
- Unknown actions appear in _unknown_lbl
- show_empty() hides all new P13.2 widgets
- Condition label shows Class / BaseType
- show_rule does not mutate the rule object
"""

import pytest
from PySide6.QtWidgets import QApplication

from core.models import FilterRule
from ui.preview_panel import PreviewPanel, parse_rule_style


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def test_parse_rule_style_basic_actions():
    rule = FilterRule(
        action="Show",
        conditions=[["Class", '"Currency"']],
        actions=[
            ["SetTextColor", "255 0 0 128"],
            ["SetBackgroundColor", "0 0 255"],
            ["SetBorderColor", "10 20 30 40"],
            ["SetFontSize", "24"],
        ],
    )

    style = parse_rule_style(rule)

    assert style.text_color == (255, 0, 0, 128)
    assert style.background_color == (0, 0, 255, 255)
    assert style.border_color == (10, 20, 30, 40)
    assert style.font_size == 24
    assert style.item_action == "Show"


def test_parse_rule_style_minimap_effect_and_sound():
    rule = FilterRule(
        action="Hide",
        actions=[
            ["MinimapIcon", "red_circle"],
            ["PlayEffect", "red"],
            ["PlayAlertSound", "1 2 3"],
        ],
    )

    style = parse_rule_style(rule)

    assert style.minimap_icon == "red_circle"
    assert style.play_effect == "red"
    assert style.alert_sound == "PlayAlertSound: 1 2 3"
    assert style.item_action == "Hide"


def test_parse_rule_style_missing_actions_fallbacks_to_defaults():
    rule = FilterRule(action="Show", conditions=[["BaseType", '"Rings"']])

    style = parse_rule_style(rule)

    assert style.text_color == (200, 200, 200, 255)
    assert style.background_color == (0, 0, 0, 210)
    assert style.border_color == (0, 0, 0, 0)
    assert style.font_size == 32
    assert style.item_name == "Rings"


def test_parse_rule_style_unknown_actions_are_ignored():
    rule = FilterRule(
        action="Continue",
        actions=[["UnknownDirective", "value"]],
    )

    style = parse_rule_style(rule)

    assert style.item_action == "Continue"
    assert style.minimap_icon == ""
    assert style.play_effect == ""
    assert style.alert_sound == ""


def test_preview_panel_show_empty_hides_content_and_shows_placeholder(qapp):
    panel = PreviewPanel()
    panel.show()
    QApplication.processEvents()

    assert panel._empty_label.isVisible() is True
    assert panel._action_label.isVisible() is False
    assert panel._item_label.isVisible() is False

    panel.show_empty()
    QApplication.processEvents()

    assert panel._empty_label.isVisible() is True
    assert panel._action_label.isVisible() is False
    assert panel._item_label.isVisible() is False


def test_preview_panel_show_rule_updates_text_and_badges(qapp):
    panel = PreviewPanel()
    panel.show()
    QApplication.processEvents()
    rule = FilterRule(
        action="Show",
        conditions=[["Class", '"Currency"']],
        actions=[
            ["SetTextColor", "255 255 255 255"],
            ["SetBackgroundColor", "0 0 0 255"],
            ["MinimapIcon", "diamond"],
            ["PlayEffect", "fire"],
            ["PlayAlertSound", "1 2 3"],
        ],
    )

    panel.show_rule(rule)

    assert panel._empty_label.isVisible() is False
    assert panel._action_label.isVisible() is True
    assert panel._item_label.isVisible() is True
    assert panel._item_label.text() == "Currency"
    assert panel._minimap_badge.isVisible() is True
    assert panel._effect_badge.isVisible() is True
    assert panel._sound_badge.isVisible() is True


# ---------------------------------------------------------------------------
# P13.2 new tests
# ---------------------------------------------------------------------------

class TestP132DisabledRule:
    """Disabled rule (enabled=False) shows the disabled banner.

    Uses isHidden() instead of isVisible() because isVisible() requires
    the parent widget to be shown (not reliable in headless offscreen tests).
    isHidden() reflects the widget's own explicit hide/show state.
    """

    def test_disabled_rule_shows_banner(self, qapp):
        panel = PreviewPanel()
        rule = FilterRule(action="Show", enabled=False)
        panel.show_rule(rule)
        assert not panel._disabled_banner.isHidden()

    def test_enabled_rule_hides_banner(self, qapp):
        panel = PreviewPanel()
        rule = FilterRule(action="Show", enabled=True)
        panel.show_rule(rule)
        assert panel._disabled_banner.isHidden()

    def test_disabled_rule_still_shows_item_label(self, qapp):
        panel = PreviewPanel()
        rule = FilterRule(action="Show", enabled=False,
                          conditions=[["Class", '"Currency"']])
        panel.show_rule(rule)
        assert not panel._item_label.isHidden()
        assert "Currency" in panel._item_label.text()

    def test_show_empty_hides_disabled_banner(self, qapp):
        panel = PreviewPanel()
        panel.show_rule(FilterRule(action="Show", enabled=False))
        panel.show_empty()
        assert panel._disabled_banner.isHidden()


class TestP132InvalidColor:
    """Invalid colour strings silently fall back; no crash."""

    def test_invalid_text_color_does_not_raise(self, qapp):
        panel = PreviewPanel()
        rule = FilterRule(action="Show",
                          actions=[["SetTextColor", "not_a_color"]])
        panel.show_rule(rule)   # must not raise
        assert not panel._item_label.isHidden()

    def test_invalid_background_color_does_not_raise(self, qapp):
        panel = PreviewPanel()
        rule = FilterRule(action="Show",
                          actions=[["SetBackgroundColor", "abc xyz"]])
        panel.show_rule(rule)
        assert not panel._item_label.isHidden()

    def test_invalid_font_size_falls_back_to_default(self):
        rule = FilterRule(action="Show", actions=[["SetFontSize", "not_an_int"]])
        style = parse_rule_style(rule)
        assert style.font_size == 32   # default

    def test_out_of_range_color_values_are_clamped(self):
        rule = FilterRule(action="Show",
                          actions=[["SetTextColor", "999 -5 300 0"]])
        style = parse_rule_style(rule)
        r, g, b, a = style.text_color
        assert r == 255
        assert g == 0
        assert b == 255
        assert a == 0


class TestP132UnknownActions:
    """Unknown actions and unknown_lines appear in _unknown_lbl."""

    def test_unknown_action_shown_in_unknown_lbl(self, qapp):
        panel = PreviewPanel()
        rule = FilterRule(action="Show",
                          actions=[["PlayEffect", "Red"],
                                   ["FutureDirective", "some_value"]])
        panel.show_rule(rule)
        assert not panel._unknown_lbl.isHidden()
        assert "FutureDirective" in panel._unknown_lbl.text()

    def test_unknown_lines_shown_in_unknown_lbl(self, qapp):
        panel = PreviewPanel()
        rule = FilterRule(action="Show",
                          unknown_lines=["SomeRawLine 42"])
        panel.show_rule(rule)
        assert not panel._unknown_lbl.isHidden()
        assert "SomeRawLine" in panel._unknown_lbl.text()

    def test_no_unknown_hides_unknown_lbl(self, qapp):
        panel = PreviewPanel()
        rule = FilterRule(action="Show",
                          actions=[["SetFontSize", "24"]])
        panel.show_rule(rule)
        assert panel._unknown_lbl.isHidden()

    def test_show_empty_hides_unknown_lbl(self, qapp):
        panel = PreviewPanel()
        rule = FilterRule(action="Show", unknown_lines=["X 1"])
        panel.show_rule(rule)
        panel.show_empty()
        assert panel._unknown_lbl.isHidden()


class TestP132ConditionLabel:
    """_condition_lbl shows Class / BaseType summary."""

    def test_class_shown_in_condition_lbl(self, qapp):
        panel = PreviewPanel()
        rule = FilterRule(action="Show",
                          conditions=[["Class", '"Currency"']])
        panel.show_rule(rule)
        assert not panel._condition_lbl.isHidden()
        assert "Class" in panel._condition_lbl.text()

    def test_basetype_shown_in_condition_lbl(self, qapp):
        panel = PreviewPanel()
        rule = FilterRule(action="Show",
                          conditions=[["BaseType", '"Divine Orb"']])
        panel.show_rule(rule)
        assert not panel._condition_lbl.isHidden()
        assert "BaseType" in panel._condition_lbl.text()

    def test_no_conditions_hides_condition_lbl(self, qapp):
        panel = PreviewPanel()
        rule = FilterRule(action="Show")
        panel.show_rule(rule)
        assert panel._condition_lbl.isHidden()

    def test_show_empty_hides_condition_lbl(self, qapp):
        panel = PreviewPanel()
        rule = FilterRule(action="Show", conditions=[["Class", '"Gems"']])
        panel.show_rule(rule)
        panel.show_empty()
        assert panel._condition_lbl.isHidden()


class TestP132ShowRuleDoesNotMutateRule:
    """show_rule must not modify the FilterRule object."""

    def test_rule_conditions_unchanged(self, qapp):
        import copy
        panel = PreviewPanel()
        rule = FilterRule(
            action="Show",
            conditions=[["Class", '"Currency"']],
            actions=[["SetFontSize", "24"]],
        )
        original = copy.deepcopy(rule)
        panel.show_rule(rule)
        assert rule.conditions == original.conditions
        assert rule.actions == original.actions
        assert rule.action == original.action
        assert rule.enabled == original.enabled

    def test_tail_rule_shows_empty(self, qapp):
        panel = PreviewPanel()
        panel.show_rule(FilterRule(action="__TAIL__"))
        assert not panel._empty_label.isHidden()

    def test_none_rule_shows_empty(self, qapp):
        panel = PreviewPanel()
        panel.show_rule(None)
        assert not panel._empty_label.isHidden()


class TestP132ActionBadge:
    """Action badge uses the right label text for each action."""

    def test_show_action_text(self, qapp):
        panel = PreviewPanel()
        panel.show_rule(FilterRule(action="Show"))
        assert "Show" in panel._action_label.text()

    def test_hide_action_text(self, qapp):
        panel = PreviewPanel()
        panel.show_rule(FilterRule(action="Hide"))
        assert "Hide" in panel._action_label.text()

    def test_continue_action_text(self, qapp):
        panel = PreviewPanel()
        panel.show_rule(FilterRule(action="Continue"))
        assert "Continue" in panel._action_label.text()
