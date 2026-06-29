"""Tests for VisualEffectPicker — P19.5 PlayEffect 2×4 visual grid.

Covers:
- Widget instantiation
- value() / set_value() API
- Invalid / unknown colour fallback to ""
- effect_changed signal emission
- No duplicate emission on same-value set_value
- All 8 colour buttons exist and are selectable
"""

import pytest
from PySide6.QtWidgets import QApplication

from widgets.visual_effect_picker import VisualEffectPicker, _EFFECT_COLORS


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
# Tests
# ---------------------------------------------------------------------------

class TestVisualEffectPickerBasic:

    def test_widget_instantiates_without_crash(self, qapp):
        picker = VisualEffectPicker()
        assert picker is not None

    def test_value_returns_empty_on_init(self, qapp):
        picker = VisualEffectPicker()
        assert picker.value() == ""

    def test_set_value_updates_value(self, qapp):
        picker = VisualEffectPicker()
        picker.set_value("Red")
        assert picker.value() == "Red"

    def test_set_value_invalid_falls_back_to_none(self, qapp):
        picker = VisualEffectPicker()
        picker.set_value("NotAColor")
        assert picker.value() == ""

    def test_set_value_empty_string_selects_none(self, qapp):
        picker = VisualEffectPicker()
        picker.set_value("Blue")
        picker.set_value("")
        assert picker.value() == ""

    def test_set_value_checks_correct_button(self, qapp):
        picker = VisualEffectPicker()
        picker.set_value("Purple")
        assert picker._buttons["Purple"].isChecked()
        assert not picker._buttons["Red"].isChecked()

    def test_effect_changed_emitted_on_value_change(self, qapp):
        picker = VisualEffectPicker()
        received: list[str] = []
        picker.effect_changed.connect(lambda v: received.append(v))
        picker.set_value("Orange")
        assert received == ["Orange"]

    def test_effect_changed_not_emitted_for_same_value(self, qapp):
        picker = VisualEffectPicker()
        received: list[str] = []
        picker.effect_changed.connect(lambda v: received.append(v))
        picker.set_value("")   # already "" on init → no emit
        assert received == []

    def test_all_eight_colors_settable(self, qapp):
        picker = VisualEffectPicker()
        for color in _EFFECT_COLORS:
            picker.set_value(color)
            assert picker.value() == color, f"set_value({color!r}) failed"
