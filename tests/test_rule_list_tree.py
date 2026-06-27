"""Tests for the v1.0.0 QTreeWidget-based RuleListWidget.

Requires offscreen Qt (PySide6 with -platform offscreen).
All tests use the shared qapp fixture for a single QApplication instance.
"""

import pytest

from core.models import FilterRule
from core.sections import build_section_map
from widgets.rule_list import RuleListWidget, SECTION_ROLE
from PySide6.QtCore import Qt


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def _make_rule(action: str = "Show", pre_lines=None) -> FilterRule:
    return FilterRule(
        action=action,
        pre_lines=pre_lines if pre_lines is not None else [],
        conditions=[],
        actions=[],
    )


def _make_tail() -> FilterRule:
    return FilterRule(action="__TAIL__", pre_lines=[], conditions=[], actions=[])


SEP = "#================================================"


# ---------------------------------------------------------------------------
# Test 1: Flat (no sections) — rules at top level
# ---------------------------------------------------------------------------

class TestFlatMode:
    def test_top_level_item_count_excludes_tail(self, qapp):
        w = RuleListWidget()
        rules = [_make_rule("Show"), _make_rule("Hide"), _make_tail()]
        w.load_rules(rules)
        assert w.list_widget.topLevelItemCount() == 2

    def test_real_index_stored_in_userrole(self, qapp):
        w = RuleListWidget()
        rules = [_make_rule("Show"), _make_rule("Hide"), _make_tail()]
        w.load_rules(rules)
        item = w.list_widget.topLevelItem(0)
        assert item.data(0, Qt.ItemDataRole.UserRole) == 0

    def test_select_real_index(self, qapp):
        w = RuleListWidget()
        rules = [_make_rule("Show"), _make_rule("Hide"), _make_tail()]
        w.load_rules(rules)
        w.select_real_index(1)
        current = w.list_widget.currentItem()
        assert current is not None
        assert current.data(0, Qt.ItemDataRole.UserRole) == 1


# ---------------------------------------------------------------------------
# Test 2: Sectioned mode
# ---------------------------------------------------------------------------

class TestSectionedMode:
    def _build(self, qapp):
        w = RuleListWidget()
        r0 = _make_rule("Show", pre_lines=[SEP, "# Currency", SEP])
        r1 = _make_rule("Hide")
        r2 = _make_rule("Show", pre_lines=[SEP, "# Gems", SEP])
        r3 = _make_tail()
        rules = [r0, r1, r2, r3]
        smap = build_section_map(rules)
        w.load_rules(rules, smap)
        return w, rules, smap

    def test_section_header_item_has_section_role(self, qapp):
        w, rules, smap = self._build(qapp)
        top0 = w.list_widget.topLevelItem(0)
        assert top0.data(0, SECTION_ROLE) is not None

    def test_two_sections_two_top_level_items(self, qapp):
        w, rules, smap = self._build(qapp)
        assert w.list_widget.topLevelItemCount() == 2

    def test_section_child_count(self, qapp):
        w, rules, smap = self._build(qapp)
        sec0 = w.list_widget.topLevelItem(0)
        # Currency has r0 + r1 = 2 rules
        assert sec0.childCount() == 2

    def test_section_header_not_selectable(self, qapp):
        w, rules, smap = self._build(qapp)
        sec0 = w.list_widget.topLevelItem(0)
        flags = sec0.flags()
        assert not bool(flags & Qt.ItemFlag.ItemIsSelectable)


# ---------------------------------------------------------------------------
# Test 3: Highlights
# ---------------------------------------------------------------------------

class TestHighlights:
    def test_set_highlights_does_not_crash(self, qapp):
        w = RuleListWidget()
        rules = [_make_rule("Show"), _make_rule("Hide"), _make_tail()]
        w.load_rules(rules)
        w.set_highlights({0, 1}, current=0)

    def test_clear_highlights_removes_amber(self, qapp):
        w = RuleListWidget()
        rules = [_make_rule("Show"), _make_tail()]
        w.load_rules(rules)
        w.set_highlights({0}, current=0)
        w.clear_highlights()
        item = w.list_widget.topLevelItem(0)
        bg = item.background(0).color()
        # After clear, background should not be the amber colours
        assert bg.name() not in ("#5a4200", "#2d2000")


# ---------------------------------------------------------------------------
# Test 4: Section collapse state persistence
# ---------------------------------------------------------------------------

class TestSectionCollapseState:
    def test_get_section_states_returns_first_rule_index_keys(self, qapp):
        w = RuleListWidget()
        r0 = _make_rule("Show", pre_lines=[SEP, "# Currency", SEP])
        r1 = _make_rule("Show", pre_lines=[SEP, "# Gems", SEP])
        r2 = _make_tail()
        rules = [r0, r1, r2]
        smap = build_section_map(rules)
        w.load_rules(rules, smap)
        states = w.get_section_states()
        # Keys must be first_rule_index values (0 and 1 here)
        assert 0 in states
        assert 1 in states

    def test_apply_section_states_no_crash(self, qapp):
        w = RuleListWidget()
        r0 = _make_rule("Show", pre_lines=[SEP, "# Currency", SEP])
        r1 = _make_tail()
        rules = [r0, r1]
        smap = build_section_map(rules)
        w.load_rules(rules, smap)
        # Collapse the Currency section
        w.apply_section_states({0: False})
        states = w.get_section_states()
        assert states.get(0) is False
