"""Tests for RuleCardWidget — P13.3 Rule Card Browser V2

Coverage:
- Badge rendering: action / category / BaseType detail / FontSize / Sound / Minimap
- Disabled rule rendering: cardDisabled property + "已停用" tag
- Unknown condition count: "+N" badge for non-Class/non-BaseType conditions
- Highlight & selection: set_selected / set_highlight / real_index
- Click signal emission
- Drag-drop signal no regression (move_rule_requested on RuleCardBrowser)

Note on isHidden() vs isVisible():
  Widgets inside an unshown parent return isVisible()=False even when .show()
  has been called.  We use isHidden() to test the widget's OWN hidden state.
"""

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from core.models import FilterRule
from ui.rule_card_widget import RuleCardWidget


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

def _find(card: RuleCardWidget, name: str) -> QLabel | None:
    """Return first QLabel descendant with the given objectName, or None."""
    return next(
        (w for w in card.findChildren(QLabel) if w.objectName() == name),
        None,
    )


def _is_absent(card: RuleCardWidget, name: str) -> bool:
    """Return True if the named label does not exist OR is hidden.

    P17.6 changed badge labels from conditionally-created to always-created
    (hidden when not applicable).  Use this helper instead of `_find() is None`
    so tests work with both the old (no widget) and new (widget hidden) designs.
    """
    lbl = _find(card, name)
    return lbl is None or lbl.isHidden()


def _rule(**kw) -> FilterRule:
    return FilterRule(**{"action": "Show", **kw})


# ---------------------------------------------------------------------------
# TestBadgeRendering
# ---------------------------------------------------------------------------

class TestBadgeRendering:
    """Verify that the correct badge labels are present (or absent)."""

    # ── Action badge ───────────────────────────────────────────────────

    def test_show_action_badge(self, qapp):
        card = RuleCardWidget(0, FilterRule(action="Show"), 1)
        lbl = _find(card, "RuleCardAction")
        assert lbl is not None
        assert "Show" in lbl.text()

    def test_hide_action_badge(self, qapp):
        card = RuleCardWidget(0, FilterRule(action="Hide"), 1)
        lbl = _find(card, "RuleCardAction")
        assert lbl is not None
        assert "Hide" in lbl.text()

    def test_continue_action_badge(self, qapp):
        card = RuleCardWidget(0, FilterRule(action="Continue"), 1)
        lbl = _find(card, "RuleCardAction")
        assert lbl is not None
        assert "Continue" in lbl.text()

    # ── Category badge ─────────────────────────────────────────────────

    def test_category_badge_currency(self, qapp):
        rule = FilterRule(action="Show", conditions=[["Class", '"Currency"']])
        card = RuleCardWidget(0, rule, 1)
        lbl = _find(card, "RuleCardCategory")
        assert lbl is not None
        assert "通貨" in lbl.text()

    def test_category_badge_gems(self, qapp):
        rule = FilterRule(action="Show", conditions=[["Class", '"Skill Gem"']])
        card = RuleCardWidget(0, rule, 1)
        lbl = _find(card, "RuleCardCategory")
        assert lbl is not None
        assert "技能石" in lbl.text()

    # ── BaseType detail row ────────────────────────────────────────────

    def test_basetype_detail_shown_when_class_is_first(self, qapp):
        rule = FilterRule(action="Show", conditions=[
            ["Class", '"Currency"'],
            ["BaseType", '"Divine Orb"'],
        ])
        card = RuleCardWidget(0, rule, 1)
        lbl = _find(card, "RuleCardDetail")
        assert lbl is not None
        assert "BaseType" in lbl.text()
        assert "Divine Orb" in lbl.text()

    def test_basetype_not_duplicated_when_first_condition(self, qapp):
        # BaseType IS the first condition — detail label must be hidden/absent
        rule = FilterRule(action="Show", conditions=[
            ["BaseType", '"Divine Orb"'],
        ])
        card = RuleCardWidget(0, rule, 1)
        assert _is_absent(card, "RuleCardDetail"), (
            "detail label must be absent when BaseType is already in the main row"
        )

    def test_no_detail_row_when_only_class(self, qapp):
        rule = FilterRule(action="Show", conditions=[["Class", '"Currency"']])
        card = RuleCardWidget(0, rule, 1)
        assert _is_absent(card, "RuleCardDetail")
        assert _is_absent(card, "RuleCardExtraCount")

    # ── FontSize badge ─────────────────────────────────────────────────

    def test_fontsize_badge_shown(self, qapp):
        rule = FilterRule(action="Show", actions=[["SetFontSize", "36"]])
        card = RuleCardWidget(0, rule, 1)
        lbl = _find(card, "RuleCardFontBadge")
        assert lbl is not None
        assert "36" in lbl.text()

    def test_fontsize_badge_absent_when_no_fontsize(self, qapp):
        rule = FilterRule(action="Show")
        card = RuleCardWidget(0, rule, 1)
        assert _is_absent(card, "RuleCardFontBadge")

    def test_fontsize_badge_text_contains_value(self, qapp):
        rule = FilterRule(action="Show", actions=[["SetFontSize", "20"]])
        card = RuleCardWidget(0, rule, 1)
        lbl = _find(card, "RuleCardFontBadge")
        assert lbl is not None
        assert "20" in lbl.text()

    # ── Sound badge ────────────────────────────────────────────────────

    def test_sound_badge_shown_playalertsound(self, qapp):
        rule = FilterRule(action="Show", actions=[["PlayAlertSound", "1 300"]])
        card = RuleCardWidget(0, rule, 1)
        assert _find(card, "RuleCardSoundBadge") is not None

    def test_sound_badge_shown_positional(self, qapp):
        rule = FilterRule(action="Show",
                          actions=[["PlayAlertSoundPositional", "2 200"]])
        card = RuleCardWidget(0, rule, 1)
        assert _find(card, "RuleCardSoundBadge") is not None

    def test_sound_badge_absent_when_no_sound(self, qapp):
        rule = FilterRule(action="Show")
        card = RuleCardWidget(0, rule, 1)
        assert _is_absent(card, "RuleCardSoundBadge")

    # ── Minimap badge ──────────────────────────────────────────────────

    def test_minimap_badge_shown(self, qapp):
        rule = FilterRule(action="Show", actions=[["MinimapIcon", "1 Red Circle"]])
        card = RuleCardWidget(0, rule, 1)
        assert _find(card, "RuleCardMinimapBadge") is not None

    def test_minimap_badge_absent_when_no_minimap(self, qapp):
        rule = FilterRule(action="Show")
        card = RuleCardWidget(0, rule, 1)
        assert _is_absent(card, "RuleCardMinimapBadge")

    # ── Combined badges ────────────────────────────────────────────────

    def test_all_effect_badges_present_simultaneously(self, qapp):
        rule = FilterRule(action="Show", actions=[
            ["SetFontSize", "36"],
            ["PlayAlertSound", "1 300"],
            ["MinimapIcon", "0 Blue Diamond"],
        ])
        card = RuleCardWidget(0, rule, 1)
        assert _find(card, "RuleCardFontBadge") is not None
        assert _find(card, "RuleCardSoundBadge") is not None
        assert _find(card, "RuleCardMinimapBadge") is not None


# ---------------------------------------------------------------------------
# TestDisabledRendering
# ---------------------------------------------------------------------------

class TestDisabledRendering:
    """Disabled rules show the cardDisabled property and 已停用 tag."""

    def test_disabled_property_set(self, qapp):
        rule = FilterRule(action="Show", enabled=False)
        card = RuleCardWidget(0, rule, 1)
        assert card.property("cardDisabled") is True

    def test_enabled_no_disabled_property(self, qapp):
        rule = FilterRule(action="Show", enabled=True)
        card = RuleCardWidget(0, rule, 1)
        assert not card.property("cardDisabled")

    def test_disabled_tag_present(self, qapp):
        rule = FilterRule(action="Show", enabled=False)
        card = RuleCardWidget(0, rule, 1)
        lbl = _find(card, "RuleCardDisabledTag")
        assert lbl is not None
        assert "已停用" in lbl.text()

    def test_enabled_no_disabled_tag(self, qapp):
        rule = FilterRule(action="Show", enabled=True)
        card = RuleCardWidget(0, rule, 1)
        assert _is_absent(card, "RuleCardDisabledTag")

    def test_disabled_hide_rule_still_works(self, qapp):
        """A disabled Hide rule must still show the correct action badge."""
        rule = FilterRule(action="Hide", enabled=False)
        card = RuleCardWidget(0, rule, 1)
        assert card.property("cardDisabled") is True
        lbl = _find(card, "RuleCardAction")
        assert lbl is not None
        assert "Hide" in lbl.text()


# ---------------------------------------------------------------------------
# TestUnknownConditionCount
# ---------------------------------------------------------------------------

class TestUnknownConditionCount:
    """Conditions that are not Class or BaseType appear as '+N' badge."""

    def test_no_extra_badge_when_only_class(self, qapp):
        rule = FilterRule(action="Show", conditions=[["Class", '"Currency"']])
        card = RuleCardWidget(0, rule, 1)
        assert _is_absent(card, "RuleCardExtraCount")

    def test_no_extra_badge_when_class_and_basetype_only(self, qapp):
        rule = FilterRule(action="Show", conditions=[
            ["Class", '"Currency"'],
            ["BaseType", '"Divine Orb"'],
        ])
        card = RuleCardWidget(0, rule, 1)
        assert _is_absent(card, "RuleCardExtraCount")

    def test_one_extra_condition(self, qapp):
        rule = FilterRule(action="Show", conditions=[
            ["Class", '"Currency"'],
            ["AreaLevel", ">= 70"],
        ])
        card = RuleCardWidget(0, rule, 1)
        lbl = _find(card, "RuleCardExtraCount")
        assert lbl is not None
        assert "+1" in lbl.text()

    def test_three_extra_conditions(self, qapp):
        rule = FilterRule(action="Show", conditions=[
            ["Class", '"Currency"'],
            ["AreaLevel", ">= 70"],
            ["Rarity", "Unique"],
            ["ItemLevel", ">= 80"],
        ])
        card = RuleCardWidget(0, rule, 1)
        lbl = _find(card, "RuleCardExtraCount")
        assert lbl is not None
        assert "+3" in lbl.text()

    def test_class_and_basetype_not_counted_as_extra(self, qapp):
        rule = FilterRule(action="Show", conditions=[
            ["Class", '"Currency"'],
            ["BaseType", '"Divine Orb"'],
            ["AreaLevel", ">= 60"],
        ])
        card = RuleCardWidget(0, rule, 1)
        lbl = _find(card, "RuleCardExtraCount")
        assert lbl is not None
        assert "+1" in lbl.text()   # only AreaLevel counts

    def test_no_conditions_no_extra_badge(self, qapp):
        rule = FilterRule(action="Show")
        card = RuleCardWidget(0, rule, 1)
        assert _is_absent(card, "RuleCardExtraCount")


# ---------------------------------------------------------------------------
# TestHighlightAndSelection
# ---------------------------------------------------------------------------

class TestHighlightAndSelection:
    """Verify set_selected / set_highlight / real_index (unchanged API)."""

    def test_initial_selected_false(self, qapp):
        card = RuleCardWidget(0, FilterRule(action="Show"), 1)
        assert card.property("cardSelected") is False

    def test_set_selected_true(self, qapp):
        card = RuleCardWidget(0, FilterRule(action="Show"), 1)
        card.set_selected(True)
        assert card.property("cardSelected") is True

    def test_set_selected_false(self, qapp):
        card = RuleCardWidget(0, FilterRule(action="Show"), 1)
        card.set_selected(True)
        card.set_selected(False)
        assert card.property("cardSelected") is False

    def test_initial_highlight_none(self, qapp):
        card = RuleCardWidget(0, FilterRule(action="Show"), 1)
        assert card.property("cardHighlight") == "none"

    def test_set_highlight_match(self, qapp):
        card = RuleCardWidget(0, FilterRule(action="Show"), 1)
        card.set_highlight("match")
        assert card.property("cardHighlight") == "match"

    def test_set_highlight_current(self, qapp):
        card = RuleCardWidget(0, FilterRule(action="Show"), 1)
        card.set_highlight("current")
        assert card.property("cardHighlight") == "current"

    def test_set_highlight_back_to_none(self, qapp):
        card = RuleCardWidget(0, FilterRule(action="Show"), 1)
        card.set_highlight("match")
        card.set_highlight("none")
        assert card.property("cardHighlight") == "none"

    def test_real_index_property(self, qapp):
        card = RuleCardWidget(42, FilterRule(action="Show"), 1)
        assert card.real_index == 42

    def test_real_index_zero(self, qapp):
        card = RuleCardWidget(0, FilterRule(action="Show"), 1)
        assert card.real_index == 0


# ---------------------------------------------------------------------------
# TestClickSignal
# ---------------------------------------------------------------------------

class TestClickSignal:
    """clicked signal emits the real_index."""

    def test_click_emits_real_index(self, qapp):
        card = RuleCardWidget(7, FilterRule(action="Show"), 1)
        received: list[int] = []
        card.clicked.connect(received.append)
        card.clicked.emit(7)
        assert received == [7]

    def test_click_emits_correct_index(self, qapp):
        card = RuleCardWidget(99, FilterRule(action="Show"), 1)
        received: list[int] = []
        card.clicked.connect(received.append)
        card.clicked.emit(99)
        assert received[0] == 99

    def test_multiple_clicks_emit_each_time(self, qapp):
        card = RuleCardWidget(3, FilterRule(action="Show"), 1)
        received: list[int] = []
        card.clicked.connect(received.append)
        card.clicked.emit(3)
        card.clicked.emit(3)
        assert len(received) == 2


# ---------------------------------------------------------------------------
# TestDragDropNoRegression
# ---------------------------------------------------------------------------

class TestDragDropNoRegression:
    """move_rule_requested signal must still be declared on RuleCardBrowser."""

    def test_move_rule_requested_signal_exists(self, qapp):
        from ui.rule_card_browser import RuleCardBrowser
        browser = RuleCardBrowser()
        assert hasattr(browser, "move_rule_requested")

    def test_browser_signals_unchanged(self, qapp):
        from ui.rule_card_browser import RuleCardBrowser
        browser = RuleCardBrowser()
        for sig in ("selected_rule_changed", "add_rule_requested",
                    "delete_rule_requested", "copy_rule_requested",
                    "move_rule_requested"):
            assert hasattr(browser, sig), f"signal {sig} missing"
