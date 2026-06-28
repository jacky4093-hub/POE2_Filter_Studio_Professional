"""Editor interaction performance tests — P17.6

Verifies that single-field edits use the fast code path:
- Cards are updated in-place (not destroyed/recreated on every edit)
- Only the edited card is updated (not all 546 rebuilt via refresh())
- validate_document() is NOT called immediately on edit (debounced)
- preview_panel.show_rule() IS called immediately
- category_sidebar.update_counts() is deferred, not immediate
"""

import copy
import time
import pytest

from PySide6.QtWidgets import QApplication

from core.models import FilterRule
from core.settings_manager import SettingsManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.fixture
def window(qapp, tmp_path):
    from ui.main_window import MainWindow
    mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
    w = MainWindow(settings_mgr=mgr)
    return w


@pytest.fixture
def loaded_window(window, tmp_path):
    """Window with a small multi-rule filter already loaded."""
    f = tmp_path / "test.filter"
    f.write_text(
        "Show\n"
        "    Class \"Currency\"\n"
        "    SetTextColor 255 200 0 255\n"
        "    SetFontSize 32\n"
        "\n"
        "Show\n"
        "    Class \"Equipment\"\n"
        "    SetBorderColor 0 255 0 255\n"
        "\n"
        "Hide\n"
        "    Class \"Gems\"\n"
        "\n",
        encoding="utf-8",
    )
    window.load_file(str(f))
    return window


def _make_rule(text_color="255 200 0 255", font_size="32") -> FilterRule:
    return FilterRule(
        action="Show",
        enabled=True,
        conditions=[["Class", '"Currency"']],
        actions=[
            ["SetTextColor", text_color],
            ["SetFontSize", font_size],
        ],
        pre_lines=[],
        inline_comment="",
        unknown_lines=[],
    )


# ---------------------------------------------------------------------------
# TestUpdateSingleCard
# ---------------------------------------------------------------------------

class TestUpdateSingleCard:

    def test_update_single_card_returns_true_for_loaded_rule(self, loaded_window):
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()

        updated_rule = copy.deepcopy(w._doc.rules[0])
        result = w.rule_card_browser.update_single_card(0, updated_rule)
        assert result is True

    def test_update_single_card_returns_false_for_missing_index(self, loaded_window):
        w = loaded_window
        result = w.rule_card_browser.update_single_card(9999, _make_rule())
        assert result is False

    def test_update_single_card_card_count_unchanged(self, loaded_window):
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()
        before = len(w.rule_card_browser._cards)

        w.rule_card_browser.update_single_card(0, copy.deepcopy(w._doc.rules[0]))
        after = len(w.rule_card_browser._cards)
        assert after == before

    def test_update_single_card_preserves_selection(self, loaded_window):
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()
        w.rule_card_browser.select_real_index(0)

        updated = copy.deepcopy(w._doc.rules[0])
        w.rule_card_browser.update_single_card(0, updated)
        assert w.rule_card_browser._selected_real == 0

    def test_update_single_card_updates_card_in_place(self, loaded_window):
        """update_single_card() must update card content in-place (same widget object)."""
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()

        old_card = w.rule_card_browser._cards.get(0)
        updated = copy.deepcopy(w._doc.rules[0])
        updated.actions = [["SetFontSize", "45"]]
        w.rule_card_browser.update_single_card(0, updated)
        current_card = w.rule_card_browser._cards.get(0)

        # Same widget object — in-place update, NOT destroy/recreate
        assert current_card is old_card, (
            "update_single_card() must update the card in-place, not replace the widget"
        )
        assert current_card._rule.actions == [["SetFontSize", "45"]], (
            "Card's rule must reflect the updated data"
        )

    def test_update_single_card_preserves_display_num(self, loaded_window):
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()

        old_num = w.rule_card_browser._cards[0]._display_num
        updated = copy.deepcopy(w._doc.rules[0])
        w.rule_card_browser.update_single_card(0, updated)
        new_num = w.rule_card_browser._cards[0]._display_num
        assert new_num == old_num

    def test_update_single_card_sound_badge_toggles(self, loaded_window):
        """Sound badge visibility must follow PlayAlertSound presence.

        Uses isHidden() rather than isVisible() because the latter also checks
        parent visibility — which is always False in offscreen test mode.
        """
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()

        # Without sound
        no_sound = copy.deepcopy(w._doc.rules[0])
        no_sound.actions = [["SetTextColor", "255 200 0 255"]]
        w.rule_card_browser.update_single_card(0, no_sound)
        card = w.rule_card_browser._cards[0]
        assert card._sound_badge_lbl.isHidden()

        # With sound
        with_sound = copy.deepcopy(w._doc.rules[0])
        with_sound.actions = [["PlayAlertSound", "1 300"]]
        w.rule_card_browser.update_single_card(0, with_sound)
        assert not card._sound_badge_lbl.isHidden()

    def test_update_single_card_minimap_badge_toggles(self, loaded_window):
        """Minimap badge visibility must follow MinimapIcon presence.

        Uses isHidden() rather than isVisible() — see sound badge test comment.
        """
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()

        no_mm = copy.deepcopy(w._doc.rules[0])
        no_mm.actions = [["SetTextColor", "255 200 0 255"]]
        w.rule_card_browser.update_single_card(0, no_mm)
        card = w.rule_card_browser._cards[0]
        assert card._minimap_badge_lbl.isHidden()

        with_mm = copy.deepcopy(w._doc.rules[0])
        with_mm.actions = [["MinimapIcon", "1 Red Circle"]]
        w.rule_card_browser.update_single_card(0, with_mm)
        assert not card._minimap_badge_lbl.isHidden()


# ---------------------------------------------------------------------------
# TestFieldEditDoesNotRebuildAllCards
# ---------------------------------------------------------------------------

class TestFieldEditDoesNotRebuildAllCards:

    def test_rule_card_browser_refresh_not_called_on_field_edit(
        self, loaded_window, monkeypatch
    ):
        """Editing a field must not trigger rule_card_browser.refresh()."""
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()
        w._load_rule_to_ui(0)

        refresh_calls = []
        monkeypatch.setattr(
            w.rule_card_browser, "refresh", lambda: refresh_calls.append(True)
        )

        # Simulate field edit via rule_changed signal
        updated = copy.deepcopy(w._doc.rules[0])
        updated.actions = [["SetTextColor", "200 100 50 255"], ["SetFontSize", "32"]]
        w._on_detail_rule_changed(0, updated)

        assert refresh_calls == [], (
            "rule_card_browser.refresh() must NOT be called on single field edit"
        )

    def test_update_single_card_called_on_field_edit(
        self, loaded_window, monkeypatch
    ):
        """Editing a field must call update_single_card() for the edited index."""
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()
        w._load_rule_to_ui(0)

        single_card_calls = []
        orig = w.rule_card_browser.update_single_card
        monkeypatch.setattr(
            w.rule_card_browser,
            "update_single_card",
            lambda idx, rule: single_card_calls.append(idx) or orig(idx, rule),
        )

        updated = copy.deepcopy(w._doc.rules[0])
        updated.actions = [["SetTextColor", "100 200 50 255"], ["SetFontSize", "32"]]
        w._on_detail_rule_changed(0, updated)

        assert 0 in single_card_calls, (
            "update_single_card() must be called with the edited rule's index"
        )


# ---------------------------------------------------------------------------
# TestValidationDebounce
# ---------------------------------------------------------------------------

class TestValidationDebounce:

    def test_validate_document_not_called_immediately_on_field_edit(
        self, loaded_window, monkeypatch
    ):
        """validate_document() must NOT be called immediately on field edit."""
        from core import validator
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()
        w._load_rule_to_ui(0)

        validate_calls = []
        monkeypatch.setattr(
            validator, "validate_document", lambda doc: validate_calls.append(1) or []
        )

        updated = copy.deepcopy(w._doc.rules[0])
        updated.actions = [["SetBorderColor", "0 255 0 255"], ["SetFontSize", "32"]]
        w._on_detail_rule_changed(0, updated)

        assert validate_calls == [], (
            "validate_document() must be deferred (debounced), not called immediately"
        )

    def test_validation_timer_started_on_field_edit(self, loaded_window):
        """_validation_timer must be active after a field edit."""
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()
        w._load_rule_to_ui(0)

        updated = copy.deepcopy(w._doc.rules[0])
        updated.actions = [["SetTextColor", "255 0 0 255"], ["SetFontSize", "32"]]
        w._on_detail_rule_changed(0, updated)

        assert w._validation_timer.isActive(), (
            "_validation_timer must be running after field edit"
        )

    def test_validation_timer_stopped_by_full_refresh(self, loaded_window):
        """_refresh_validation() cancels the debounce timer."""
        w = loaded_window
        w._validation_timer.start(60000)    # artificially long
        assert w._validation_timer.isActive()

        w._refresh_validation()
        assert not w._validation_timer.isActive()

    def test_validation_timer_restarted_on_multiple_edits(self, loaded_window):
        """Multiple rapid edits keep the timer alive; it should not fire mid-sequence."""
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()
        w._load_rule_to_ui(0)

        for color in ("255 0 0 255", "0 255 0 255", "0 0 255 255"):
            updated = copy.deepcopy(w._doc.rules[0])
            updated.actions = [["SetTextColor", color], ["SetFontSize", "32"]]
            w._on_detail_rule_changed(0, updated)

        assert w._validation_timer.isActive()


# ---------------------------------------------------------------------------
# TestPreviewPanelImmediate
# ---------------------------------------------------------------------------

class TestPreviewPanelImmediate:

    def test_preview_updated_immediately_on_field_edit(
        self, loaded_window, monkeypatch
    ):
        """show_rule() must be called on every field edit (no deferral)."""
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()
        w._load_rule_to_ui(0)

        show_calls = []
        monkeypatch.setattr(
            w.preview_panel, "show_rule", lambda rule: show_calls.append(rule)
        )

        updated = copy.deepcopy(w._doc.rules[0])
        updated.actions = [["SetTextColor", "100 150 200 255"], ["SetFontSize", "32"]]
        w._on_detail_rule_changed(0, updated)

        assert len(show_calls) == 1, (
            "preview_panel.show_rule() must be called immediately on field edit"
        )

    def test_category_counts_not_updated_immediately(
        self, loaded_window, monkeypatch
    ):
        """category_sidebar.update_counts() must be deferred, not called immediately."""
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()
        w._load_rule_to_ui(0)

        count_calls = []
        monkeypatch.setattr(
            w.category_sidebar,
            "update_counts",
            lambda rules: count_calls.append(len(rules)),
        )

        updated = copy.deepcopy(w._doc.rules[0])
        updated.actions = [["SetFontSize", "36"]]
        w._on_detail_rule_changed(0, updated)

        assert count_calls == [], (
            "category_sidebar.update_counts() must be deferred on field edit"
        )


# ---------------------------------------------------------------------------
# TestInPlaceUpdatePerformance
# ---------------------------------------------------------------------------

class TestInPlaceUpdatePerformance:

    def test_100_rapid_color_edits_complete_quickly(self, loaded_window):
        """100 rapid SetTextColor edits must complete in under 3 seconds.

        SetTextColor does not change any card-visible badge — this path must
        be extremely cheap (just label text update, no Qt widget allocation).
        """
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()
        w._load_rule_to_ui(0)

        start = time.perf_counter()
        for i in range(100):
            updated = copy.deepcopy(w._doc.rules[0])
            updated.actions = [
                ["SetTextColor", f"{i % 256} 100 100 255"],
                ["SetFontSize", "32"],
            ]
            w._on_detail_rule_changed(0, updated)
        elapsed = time.perf_counter() - start

        assert elapsed < 3.0, (
            f"100 color edits took {elapsed:.2f}s — expected < 3.0s. "
            "In-place update should avoid Qt widget allocation entirely."
        )

    def test_50_rapid_minimap_edits_complete_quickly(self, loaded_window):
        """50 rapid MinimapIcon edits must complete in under 2 seconds.

        MinimapIcon changes toggle the minimap badge — still cheap since we
        toggle label visibility instead of destroying/recreating the widget.
        """
        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()
        w._load_rule_to_ui(0)

        minimap_values = ["1 Red Circle", "2 Blue Diamond", "", "0 Green Star"] * 13
        start = time.perf_counter()
        for mm_val in minimap_values[:50]:
            updated = copy.deepcopy(w._doc.rules[0])
            updated.actions = [["MinimapIcon", mm_val]] if mm_val else []
            w._on_detail_rule_changed(0, updated)
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, (
            f"50 minimap edits took {elapsed:.2f}s — expected < 2.0s."
        )

    def test_no_new_widgets_allocated_on_color_edit(self, loaded_window, monkeypatch):
        """Editing SetTextColor must NOT create any new RuleCardWidget instances.

        The whole point of in-place update: zero widget allocation for
        fields that don't affect card-visible content.
        """
        from ui import rule_card_widget as rcw_module

        w = loaded_window
        w.rule_card_browser.load_rules(w._doc.rules)
        w.rule_card_browser.refresh()
        w._load_rule_to_ui(0)

        widget_creations = []
        original_init = rcw_module.RuleCardWidget.__init__

        def tracking_init(self_, *args, **kwargs):
            widget_creations.append(True)
            original_init(self_, *args, **kwargs)

        monkeypatch.setattr(rcw_module.RuleCardWidget, "__init__", tracking_init)

        updated = copy.deepcopy(w._doc.rules[0])
        updated.actions = [["SetTextColor", "200 100 50 255"], ["SetFontSize", "32"]]
        w._on_detail_rule_changed(0, updated)

        assert widget_creations == [], (
            "Editing SetTextColor must not allocate any new RuleCardWidget. "
            "update_rule() must update the existing widget in-place."
        )
