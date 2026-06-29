"""Tests for ColorSwatchPicker — P19.7 compound RGBA colour input widget.

Covers:
- Default value after instantiation
- set_value() / value() round-trip
- color_changed signal emission
- Invalid RGBA string does not crash
- Dialog flow simulation (set_value replicates what _on_swatch_clicked does)
- Swatch preview updates on value change
- Alpha channel is preserved
- value() returns exact string set via set_value()
"""

import pytest
from PySide6.QtWidgets import QApplication

from widgets.color_swatch_picker import ColorSwatchPicker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def _picker(qapp) -> ColorSwatchPicker:
    return ColorSwatchPicker("TestColor", "255 255 255 255", "TestBtn")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestColorSwatchPickerBasic:

    def test_default_value(self, qapp):
        """Widget starts with an empty value (no text in edit field)."""
        p = _picker(qapp)
        assert p.value() == ""

    def test_set_value_updates_value(self, qapp):
        """set_value() stores the RGBA string and value() returns it."""
        p = _picker(qapp)
        p.set_value("255 128 0 200")
        assert p.value() == "255 128 0 200"

    def test_color_changed_signal(self, qapp):
        """color_changed fires with the new value when set_value() is called."""
        p = _picker(qapp)
        received: list[str] = []
        p.color_changed.connect(received.append)
        p.set_value("10 20 30 255")
        assert received == ["10 20 30 255"]

    def test_invalid_rgba_fallback(self, qapp):
        """Invalid RGBA string must not crash; value is stored as-is."""
        p = _picker(qapp)
        p.set_value("not_a_color")   # must not raise
        assert p.value() == "not_a_color"
        # Swatch shows error (dashed) style
        style = p._swatch.styleSheet()
        assert "dashed" in style

    def test_dialog_updates_value(self, qapp):
        """Simulates QColorDialog accept: set_value() is what _on_swatch_clicked does."""
        p = _picker(qapp)
        received: list[str] = []
        p.color_changed.connect(received.append)
        p.set_value("100 150 200 128")
        assert p.value() == "100 150 200 128"
        assert received == ["100 150 200 128"]

    def test_preview_updates(self, qapp):
        """After set_value with valid RGBA, swatch shows a colour (not transparent)."""
        p = _picker(qapp)
        p.set_value("255 0 0 255")
        style = p._swatch.styleSheet()
        assert "transparent" not in style
        assert "rgba(255,0,0,255)" in style

    def test_alpha_supported(self, qapp):
        """Alpha value is preserved and appears in the swatch style."""
        p = _picker(qapp)
        p.set_value("0 0 255 128")
        style = p._swatch.styleSheet()
        assert "rgba(0,0,255,128)" in style
        assert p.value() == "0 0 255 128"

    def test_value_roundtrip(self, qapp):
        """value() always returns exactly what was passed to set_value()."""
        p = _picker(qapp)
        for rgba in ("0 0 0 255", "128 64 32 200", "255 255 255 0"):
            p.set_value(rgba)
            assert p.value() == rgba, f"round-trip failed for {rgba!r}"
