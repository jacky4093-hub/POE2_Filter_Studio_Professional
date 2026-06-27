"""Tests for preview parsing and PreviewPanel rendering behavior."""

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
