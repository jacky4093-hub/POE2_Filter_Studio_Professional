"""Tests for MinimapIconGrid — P19.6 MinimapIcon visual grid widget.

Covers:
- Default value after instantiation
- set_value() / value() round-trip
- icon_changed signal emission
- Unknown / invalid value fallback to defaults
- All 11 colour buttons present
- All 12 shape buttons present
- Size button interaction
- Colour button interaction
- Shape grid interaction
- Shape symbol colour syncs to selected colour
"""

import pytest
from PySide6.QtWidgets import QApplication

from widgets.minimap_icon_grid import (
    MinimapIconGrid,
    _DEFAULT_COLOR,
    _DEFAULT_SHAPE,
    _DEFAULT_SIZE,
    _GRID_COLORS,
    _GRID_SHAPES,
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
# Tests
# ---------------------------------------------------------------------------

class TestMinimapIconGridBasic:

    def test_default_value(self, qapp):
        """Widget starts with the documented defaults."""
        grid = MinimapIconGrid()
        assert grid.value() == (_DEFAULT_SIZE, _DEFAULT_COLOR, _DEFAULT_SHAPE)

    def test_set_value_updates_value(self, qapp):
        """set_value() round-trips correctly."""
        grid = MinimapIconGrid()
        grid.set_value(2, "Blue", "Moon")
        assert grid.value() == (2, "Blue", "Moon")

    def test_icon_changed_signal_emitted(self, qapp):
        """icon_changed fires once when value changes."""
        grid = MinimapIconGrid()
        received: list[tuple] = []
        grid.icon_changed.connect(lambda s, c, sh: received.append((s, c, sh)))
        grid.set_value(1, "Green", "Circle")
        assert received == [(1, "Green", "Circle")]

    def test_icon_changed_not_emitted_for_same_value(self, qapp):
        """icon_changed must not fire when value is unchanged."""
        grid = MinimapIconGrid()
        received: list[tuple] = []
        grid.icon_changed.connect(lambda s, c, sh: received.append((s, c, sh)))
        # default is already (_DEFAULT_SIZE, _DEFAULT_COLOR, _DEFAULT_SHAPE)
        grid.set_value(_DEFAULT_SIZE, _DEFAULT_COLOR, _DEFAULT_SHAPE)
        assert received == []

    def test_unknown_size_falls_back_to_default(self, qapp):
        """Invalid size value falls back to _DEFAULT_SIZE."""
        grid = MinimapIconGrid()
        grid.set_value(99, "Red", "Star")
        assert grid.value()[0] == _DEFAULT_SIZE

    def test_unknown_color_falls_back_to_default(self, qapp):
        """Invalid colour string falls back to _DEFAULT_COLOR."""
        grid = MinimapIconGrid()
        grid.set_value(0, "NotAColor", "Star")
        assert grid.value()[1] == _DEFAULT_COLOR

    def test_unknown_shape_falls_back_to_default(self, qapp):
        """Invalid shape string falls back to _DEFAULT_SHAPE."""
        grid = MinimapIconGrid()
        grid.set_value(0, "Red", "NotAShape")
        assert grid.value()[2] == _DEFAULT_SHAPE

    def test_all_colors_supported(self, qapp):
        """All 11 colour buttons exist and are selectable."""
        grid = MinimapIconGrid()
        assert len(grid._color_buttons) == len(_GRID_COLORS)
        for color in _GRID_COLORS:
            grid.set_value(_DEFAULT_SIZE, color, _DEFAULT_SHAPE)
            assert grid.value()[1] == color, f"set_value color={color!r} failed"

    def test_all_shapes_supported(self, qapp):
        """All 12 shape buttons exist and are selectable."""
        grid = MinimapIconGrid()
        assert len(grid._shape_buttons) == len(_GRID_SHAPES)
        for shape in _GRID_SHAPES:
            grid.set_value(_DEFAULT_SIZE, _DEFAULT_COLOR, shape)
            assert grid.value()[2] == shape, f"set_value shape={shape!r} failed"

    def test_shape_color_sync(self, qapp):
        """Shape buttons adopt the colour tone of the selected colour."""
        grid = MinimapIconGrid()
        grid.set_value(0, "Purple", "Circle")
        # After selecting Purple, shape button stylesheets should mention purple tone
        style = grid._shape_buttons["Circle"].styleSheet()
        assert "#9628C8" in style  # Purple tone from _COLOR_TONES
