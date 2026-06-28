"""P18.4 Rule Detail Editor V4 tests.

Sections:
  A. V4 Visual Structure — objectNames, widget presence, scroll area config
  B. Fast Path Guard Tests — edit flow preserved, no load_rules/refresh on edit
  C. Behavior Preservation — set_rule / clear / flush_pending semantics unchanged
  D. Signal Contract — rule_changed signature, index accuracy
"""

import copy
import pytest

from PySide6.QtWidgets import (
    QApplication, QScrollArea, QStackedWidget, QGroupBox, QLabel,
)
from PySide6.QtCore import Qt

from core.models import FilterRule
from ui.rule_detail_editor import RuleDetailEditor


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def _rule(
    action: str = "Show",
    enabled: bool = True,
    conditions: list | None = None,
    actions: list | None = None,
    pre_lines: list | None = None,
    unknown_lines: list | None = None,
    inline_comment: str = "",
) -> FilterRule:
    return FilterRule(
        action=action,
        enabled=enabled,
        conditions=conditions or [],
        actions=actions or [],
        pre_lines=pre_lines or [],
        unknown_lines=unknown_lines or [],
        inline_comment=inline_comment,
    )


def _collect(editor: RuleDetailEditor) -> list[tuple]:
    """Wire a listener on rule_changed and return the list it appends to."""
    received: list[tuple] = []
    editor.rule_changed.connect(lambda idx, rule: received.append((idx, rule)))
    return received


# ──────────────────────────────────────────────────────────────────────
# A. V4 Visual Structure
# ──────────────────────────────────────────────────────────────────────

class TestV4VisualStructure:
    @pytest.fixture
    def ed(self, qapp):
        return RuleDetailEditor()

    def test_outer_widget_objectname(self, ed):
        assert ed.objectName() == "RuleDetailEditor"

    def test_stacked_widget_exists(self, ed):
        assert hasattr(ed, "_stacked")
        assert isinstance(ed._stacked, QStackedWidget)

    def test_empty_page_objectname(self, ed):
        assert hasattr(ed, "_empty_page")
        assert ed._empty_page.objectName() == "RuleDetailEmptyPage"

    def test_editor_page_is_scroll_area(self, ed):
        assert hasattr(ed, "_editor_page")
        assert isinstance(ed._editor_page, QScrollArea)

    def test_editor_page_objectname(self, ed):
        assert ed._editor_page.objectName() == "RuleDetailScrollArea"

    def test_scroll_area_no_horizontal_bar(self, ed):
        assert ed._editor_page.horizontalScrollBarPolicy() == \
               Qt.ScrollBarPolicy.ScrollBarAlwaysOff

    def test_content_widget_objectname(self, ed):
        content = ed._editor_page.widget()
        assert content is not None
        assert content.objectName() == "RuleDetailContent"

    def test_title_bar_objectname(self, ed):
        from PySide6.QtWidgets import QWidget
        bars = [c for c in ed.findChildren(QWidget)
                if c.objectName() == "RuleEditorTitleBar"]
        assert bars, "RuleEditorTitleBar widget not found"

    def test_title_label_objectname(self, ed):
        assert hasattr(ed, "_title_lbl")
        assert ed._title_lbl.objectName() == "RuleEditorTitle"

    def test_at_least_five_rule_editor_cards(self, ed):
        cards = [c for c in ed.findChildren(QGroupBox)
                 if c.objectName() == "RuleEditorCard"]
        assert len(cards) >= 5, \
            f"Expected ≥5 RuleEditorCard groups, found {len(cards)}"

    def test_preview_text_objectname(self, ed):
        assert hasattr(ed, "_preview_text")
        assert ed._preview_text.objectName() == "RuleDetailPreview"

    def test_three_color_swatches_exist(self, ed):
        swatches = [c for c in ed.findChildren(QLabel)
                    if c.objectName() == "ColorSwatch"]
        assert len(swatches) == 3, \
            f"Expected 3 ColorSwatch labels, found {len(swatches)}"

    def test_color_swatch_size_v4(self, ed):
        """V4 swatches must be at least 24 px wide (fixed by setFixedSize)."""
        swatches = [c for c in ed.findChildren(QLabel)
                    if c.objectName() == "ColorSwatch"]
        assert swatches, "No ColorSwatch labels found"
        for swatch in swatches:
            # setFixedSize sets both min and max; maximumWidth is reliable offscreen
            assert swatch.maximumWidth() >= 24, \
                f"ColorSwatch maximumWidth {swatch.maximumWidth()} < 24 (V4 minimum)"

    def test_color_swatch_has_pointing_cursor(self, ed):
        swatches = [c for c in ed.findChildren(QLabel)
                    if c.objectName() == "ColorSwatch"]
        assert swatches
        for swatch in swatches:
            assert swatch.cursor().shape() == Qt.CursorShape.PointingHandCursor


# ──────────────────────────────────────────────────────────────────────
# B. Fast Path Guard Tests
# ──────────────────────────────────────────────────────────────────────

class TestFastPathGuards:
    """Verify the critical edit flow is preserved after V4 cosmetic changes:

        field changed → rule_changed(index, updated_rule)
            → MainWindow._on_detail_rule_changed()
            → update_single_card() + preview_panel.show_rule()
            → _validation_timer.start(300)

    These tests confirm the EDITOR SIDE of that contract is intact.
    """

    @pytest.fixture
    def ed(self, qapp):
        ed = RuleDetailEditor()
        ed.set_rule(_rule(conditions=[["Class", '"Currency"']]), index=0)
        return ed

    # ── Guard 1: set_rule() must NEVER emit rule_changed ──────────────

    def test_guard_set_rule_no_emission(self, qapp):
        """set_rule() must not emit rule_changed — loading guard must be active."""
        ed = RuleDetailEditor()
        received = _collect(ed)
        ed.set_rule(_rule(), index=0)
        assert not received, "set_rule() must not emit rule_changed (loading guard broken)"

    def test_guard_set_rule_repeated_no_emission(self, qapp):
        ed = RuleDetailEditor()
        received = _collect(ed)
        ed.set_rule(_rule(), index=0)
        ed.set_rule(_rule(action="Hide"), index=1)
        assert not received

    # ── Guard 2: field edit emits rule_changed exactly once ───────────

    def test_guard_enabled_toggle_emits_once(self, ed):
        received = _collect(ed)
        ed._enabled_cb.setChecked(not ed._enabled_cb.isChecked())
        assert len(received) == 1, \
            f"Expected 1 emission on enabled toggle, got {len(received)}"

    def test_guard_action_combo_emits_once(self, ed):
        received = _collect(ed)
        cur = ed._action_combo.currentIndex()
        ed._action_combo.setCurrentIndex((cur + 1) % ed._action_combo.count())
        assert len(received) == 1

    def test_guard_fontsize_spin_emits_once(self, ed):
        received = _collect(ed)
        ed._fontsize_spin.setValue(ed._fontsize_spin.value() + 1)
        assert len(received) == 1

    # ── Guard 3: emitted signal carries correct (index, FilterRule) ───

    def test_guard_emitted_index_matches_set_rule(self, ed):
        """rule_changed must carry the same index as was passed to set_rule()."""
        received = _collect(ed)
        ed._enabled_cb.setChecked(not ed._enabled_cb.isChecked())
        assert received
        idx, _ = received[0]
        assert idx == 0  # set_rule used index=0

    def test_guard_emitted_rule_is_filter_rule(self, ed):
        received = _collect(ed)
        ed._enabled_cb.setChecked(not ed._enabled_cb.isChecked())
        assert received
        _, rule = received[0]
        assert isinstance(rule, FilterRule)

    def test_guard_updated_rule_reflects_change(self, ed):
        """The updated_rule in the signal must reflect the field value that changed."""
        assert ed._enabled_cb.isChecked() is True  # precondition
        received = _collect(ed)
        ed._enabled_cb.setChecked(False)
        assert received
        _, updated = received[0]
        assert updated.enabled is False

    def test_guard_index_updated_on_second_set_rule(self, qapp):
        """After a second set_rule(), emissions use the new index."""
        ed = RuleDetailEditor()
        ed.set_rule(_rule(), index=5)
        received = _collect(ed)
        ed._enabled_cb.setChecked(not ed._enabled_cb.isChecked())
        assert received
        idx, _ = received[0]
        assert idx == 5

    # ── Guard 4: loading flag blocks _on_any_field_changed ────────────

    def test_guard_loading_flag_true_during_populate(self, qapp):
        """_loading must be True during _populate_fields() so signals are blocked."""
        ed = RuleDetailEditor()
        loading_states: list[bool] = []

        original = ed._populate_fields

        def spy():
            loading_states.append(ed._loading)
            original()

        ed._populate_fields = spy
        ed.set_rule(_rule(), index=0)
        assert loading_states, "spy was never called"
        assert all(loading_states), "_loading must be True during _populate_fields()"

    # ── Guard 5: no internal refresh/load_rules calls on field edit ───

    def test_guard_field_edit_does_not_call_refresh(self, qapp):
        """RuleDetailEditor must not call any refresh() internally."""
        ed = RuleDetailEditor()
        # Confirm the editor has no refresh() method (would violate arch boundary)
        assert not hasattr(ed, "refresh"), \
            "RuleDetailEditor must not expose refresh() — it would couple to browser"

    def test_guard_field_edit_does_not_call_load_rules(self, qapp):
        """RuleDetailEditor must not call load_rules() internally."""
        ed = RuleDetailEditor()
        assert not hasattr(ed, "load_rules"), \
            "RuleDetailEditor must not expose load_rules() — arch boundary violation"

    def test_guard_rule_changed_signal_exists(self, qapp):
        """rule_changed Signal must exist on RuleDetailEditor (signal contract)."""
        ed = RuleDetailEditor()
        assert hasattr(ed, "rule_changed")

    def test_guard_clear_does_not_emit(self, qapp):
        """clear() must not emit rule_changed."""
        ed = RuleDetailEditor()
        ed.set_rule(_rule(), index=0)
        received = _collect(ed)
        ed.clear()
        assert not received, "clear() must not emit rule_changed"


# ──────────────────────────────────────────────────────────────────────
# C. Behavior Preservation
# ──────────────────────────────────────────────────────────────────────

class TestBehaviorPreservation:
    @pytest.fixture
    def ed(self, qapp):
        return RuleDetailEditor()

    def test_flush_pending_is_noop_no_crash(self, ed):
        received = _collect(ed)
        ed.flush_pending()
        assert not received

    def test_clear_returns_to_empty_page(self, ed):
        ed.set_rule(_rule(), index=0)
        ed.clear()
        assert ed._stacked.currentWidget() is ed._empty_page

    def test_clear_sets_rule_none(self, ed):
        ed.set_rule(_rule(), index=0)
        ed.clear()
        assert ed._rule is None

    def test_clear_sets_index_minus_one(self, ed):
        ed.set_rule(_rule(), index=3)
        ed.clear()
        assert ed._index == -1

    def test_set_rule_shows_editor_page(self, ed):
        ed.set_rule(_rule(), index=0)
        assert ed._stacked.currentWidget() is ed._editor_page

    def test_set_rule_deep_copies_rule(self, ed):
        r = _rule(conditions=[["Class", '"Currency"']])
        ed.set_rule(r, index=0)
        r.conditions[0][1] = '"Mutated"'
        assert ed._rule.conditions[0][1] == '"Currency"'

    def test_unmanaged_fields_preserved_on_edit(self, ed):
        """Editing a field must preserve pre_lines, inline_comment, unknown_lines."""
        rule = _rule(
            pre_lines=["# pre"],
            unknown_lines=["UnknownKey value"],
            inline_comment="# inline",
        )
        ed.set_rule(rule, index=0)
        received = _collect(ed)
        ed._enabled_cb.setChecked(False)
        assert received
        _, updated = received[0]
        assert updated.pre_lines == ["# pre"]
        assert updated.unknown_lines == ["UnknownKey value"]
        assert updated.inline_comment == "# inline"

    def test_update_preview_after_field_change(self, ed):
        """_preview_text must reflect the field change after emission."""
        ed.set_rule(_rule(action="Show"), index=0)
        ed._action_combo.setCurrentText("Hide")
        assert "Hide" in ed._preview_text.toPlainText()

    def test_preview_text_readonly(self, ed):
        assert ed._preview_text.isReadOnly()


# ──────────────────────────────────────────────────────────────────────
# D. Signal Contract
# ──────────────────────────────────────────────────────────────────────

class TestSignalContract:
    """Verify rule_changed(int, FilterRule) contract in detail."""

    @pytest.fixture
    def ed(self, qapp):
        ed = RuleDetailEditor()
        ed.set_rule(_rule(), index=7)
        return ed

    def test_signal_args_are_int_and_filter_rule(self, ed):
        received_args: list[tuple] = []
        ed.rule_changed.connect(lambda i, r: received_args.append((i, r)))
        ed._enabled_cb.setChecked(not ed._enabled_cb.isChecked())
        assert received_args
        idx, rule = received_args[0]
        assert isinstance(idx, int)
        assert isinstance(rule, FilterRule)

    def test_signal_index_is_seven(self, ed):
        received = _collect(ed)
        ed._enabled_cb.setChecked(not ed._enabled_cb.isChecked())
        assert received[0][0] == 7

    def test_signal_rule_not_same_as_original_input(self, qapp):
        """Updated rule is built via deep-copy — must not be the same object as the rule
        originally passed into set_rule()."""
        original = _rule()
        ed2 = RuleDetailEditor()
        ed2.set_rule(original, index=0)
        received = _collect(ed2)
        ed2._enabled_cb.setChecked(not ed2._enabled_cb.isChecked())
        assert received
        _, emitted_rule = received[0]
        assert emitted_rule is not original, \
            "emitted rule must be a deep-copy, not the original object passed to set_rule()"

    def test_signal_preserves_conditions(self, qapp):
        ed = RuleDetailEditor()
        rule = _rule(conditions=[["Class", '"Currency"'], ["BaseType", '"Orb"']])
        ed.set_rule(rule, index=0)
        received = _collect(ed)
        ed._enabled_cb.setChecked(not ed._enabled_cb.isChecked())
        assert received
        _, updated = received[0]
        class_val = next((v for k, v in updated.conditions if k == "Class"), None)
        assert class_val == '"Currency"'

    def test_signal_not_emitted_when_no_rule_loaded(self, qapp):
        """_on_any_field_changed is a no-op when no rule is loaded."""
        ed = RuleDetailEditor()
        received = _collect(ed)
        # Manually invoke the slot — should be silent
        ed._on_any_field_changed()
        assert not received
