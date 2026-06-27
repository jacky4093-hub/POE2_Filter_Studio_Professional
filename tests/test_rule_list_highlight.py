"""Tests for v1.4.0 Highlight Optimization — partial background update.

All tests verify that set_highlights() / clear_highlights() do NOT rebuild
the QTreeWidget but only call setBackground() on affected items.

Key identity check: _real_to_item[idx] must return the same Python object
before and after set_highlights() / clear_highlights().  If the tree is
cleared and rebuilt, the dict is also rebuilt → different Python objects.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush

from core.models import FilterRule
from core.sections import build_section_map
from widgets.rule_list import RuleListWidget, SECTION_ROLE


# ---------------------------------------------------------------------------
# Shared fixture and helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


SEP = "#================================================"

_AMBER_CURRENT = "#5a4200"
_AMBER_OTHER   = "#2d2000"


def _rule(action: str = "Show", pre=None) -> FilterRule:
    return FilterRule(
        action=action,
        pre_lines=pre or [],
        conditions=[("Class", '"Currency"')],
        actions=[],
    )


def _tail() -> FilterRule:
    return FilterRule(action="__TAIL__", pre_lines=[], conditions=[], actions=[])


def _flat_widget(qapp, n: int = 5):
    """Widget with *n* rules in flat mode (no sections)."""
    w = RuleListWidget()
    rules = [_rule() for _ in range(n)] + [_tail()]
    w.load_rules(rules)
    return w, rules


def _sectioned_widget(qapp):
    """Widget with 2 sections: Currency (rules 0,1) and Gems (rules 2,3)."""
    w = RuleListWidget()
    r0 = _rule("Show", pre=[SEP, "# Currency", SEP])
    r1 = _rule("Hide")
    r2 = _rule("Show", pre=[SEP, "# Gems", SEP])
    r3 = _rule("Hide")
    rules = [r0, r1, r2, r3, _tail()]
    smap = build_section_map(rules)
    w.load_rules(rules, smap)
    return w, rules, smap


def _bg_name(item) -> str:
    """Return hex colour string for item background col 0, or '' if no brush."""
    brush = item.background(0)
    if brush.style() == Qt.BrushStyle.NoBrush:
        return ""
    return brush.color().name().lower()


# ---------------------------------------------------------------------------
# Test 1: set_highlights() must NOT rebuild the tree
# ---------------------------------------------------------------------------

class TestNoRebuildOnSetHighlights:
    def test_real_to_item_identity_preserved(self, qapp):
        """set_highlights() must not clear+rebuild _real_to_item."""
        w, rules = _flat_widget(qapp)
        item_before = w._real_to_item.get(0)
        assert item_before is not None

        w.set_highlights({0, 1, 2}, current=0)

        item_after = w._real_to_item.get(0)
        assert item_after is item_before, (
            "set_highlights() rebuilt the tree (different Python object)"
        )

    def test_topLevelItemCount_unchanged(self, qapp):
        """Tree item count must stay the same after partial update."""
        w, rules = _flat_widget(qapp, n=4)
        count_before = w.list_widget.topLevelItemCount()

        w.set_highlights({0, 2}, current=0)

        assert w.list_widget.topLevelItemCount() == count_before

    def test_painted_state_synced_after_call(self, qapp):
        """_painted_highlights and _painted_current must reflect the call."""
        w, rules = _flat_widget(qapp)
        w.set_highlights({1, 2, 3}, current=2)

        assert w._painted_highlights == {1, 2, 3}
        assert w._painted_current == 2


# ---------------------------------------------------------------------------
# Test 2: Background colours are correct
# ---------------------------------------------------------------------------

class TestHighlightColours:
    def test_current_match_gets_bright_amber(self, qapp):
        w, rules = _flat_widget(qapp)
        w.set_highlights({0, 1, 2}, current=1)

        item = w._real_to_item[1]
        assert _bg_name(item) == _AMBER_CURRENT

    def test_other_matches_get_dim_amber(self, qapp):
        w, rules = _flat_widget(qapp)
        w.set_highlights({0, 1, 2}, current=1)

        for idx in (0, 2):
            item = w._real_to_item[idx]
            assert _bg_name(item) == _AMBER_OTHER, (
                f"rule {idx} expected OTHER amber, got {_bg_name(item)!r}"
            )

    def test_non_match_item_has_no_amber(self, qapp):
        w, rules = _flat_widget(qapp, n=5)
        w.set_highlights({0, 1}, current=0)

        for idx in (2, 3, 4):
            item = w._real_to_item.get(idx)
            if item:
                assert _bg_name(item) not in (_AMBER_CURRENT, _AMBER_OTHER)


# ---------------------------------------------------------------------------
# Test 3: F3 / Shift+F3 cursor movement — only 2 setBackground calls
# ---------------------------------------------------------------------------

class TestCursorNavigation:
    def test_f3_upgrades_new_current_to_bright(self, qapp):
        """After cursor moves from 0→1, item 1 must be CURRENT amber."""
        w, rules = _flat_widget(qapp)
        w.set_highlights({0, 1, 2}, current=0)
        w.set_highlights({0, 1, 2}, current=1)   # F3

        assert _bg_name(w._real_to_item[1]) == _AMBER_CURRENT

    def test_f3_downgrades_old_current_to_other(self, qapp):
        """After cursor moves from 0→1, item 0 must be demoted to OTHER amber."""
        w, rules = _flat_widget(qapp)
        w.set_highlights({0, 1, 2}, current=0)
        w.set_highlights({0, 1, 2}, current=1)   # F3

        assert _bg_name(w._real_to_item[0]) == _AMBER_OTHER

    def test_f3_preserves_identity(self, qapp):
        """Cursor movement via set_highlights must not rebuild the tree."""
        w, rules = _flat_widget(qapp)
        w.set_highlights({0, 1, 2}, current=0)
        item_ref = w._real_to_item.get(0)

        w.set_highlights({0, 1, 2}, current=1)

        assert w._real_to_item.get(0) is item_ref


# ---------------------------------------------------------------------------
# Test 4: clear_highlights()
# ---------------------------------------------------------------------------

class TestClearHighlights:
    def test_clear_removes_all_amber(self, qapp):
        """clear_highlights() must remove amber background from all items."""
        w, rules = _flat_widget(qapp, n=4)
        w.set_highlights({0, 1, 2, 3}, current=0)
        w.clear_highlights()

        for idx in range(4):
            item = w._real_to_item.get(idx)
            if item:
                assert _bg_name(item) not in (_AMBER_CURRENT, _AMBER_OTHER), (
                    f"rule {idx} still has amber after clear"
                )

    def test_clear_does_not_rebuild_tree(self, qapp):
        """clear_highlights() must NOT destroy and rebuild tree items."""
        w, rules = _flat_widget(qapp)
        w.set_highlights({0, 1}, current=0)
        item_ref = w._real_to_item.get(0)

        w.clear_highlights()

        assert w._real_to_item.get(0) is item_ref

    def test_clear_resets_painted_state(self, qapp):
        """After clear, both _painted_highlights and _painted_current reset."""
        w, rules = _flat_widget(qapp)
        w.set_highlights({0, 1, 2}, current=1)
        w.clear_highlights()

        assert w._painted_highlights == set()
        assert w._painted_current == -1


# ---------------------------------------------------------------------------
# Test 5: Section auto-expand without tree rebuild
# ---------------------------------------------------------------------------

class TestSectionAutoExpand:
    def test_collapsed_section_expands_on_match(self, qapp):
        """set_highlights() must expand a collapsed section that contains a match."""
        w, rules, smap = _sectioned_widget(qapp)
        # Collapse the Gems section (first_rule_index = 2)
        w.apply_section_states({2: False})

        # Verify it's collapsed before the call
        gems_header = w._section_header_items.get(2)
        assert gems_header is not None
        assert not gems_header.isExpanded()

        # Highlight a rule inside Gems (real_index = 2)
        w.set_highlights({2}, current=2)

        assert gems_header.isExpanded(), "Gems section should be auto-expanded"

    def test_auto_expand_does_not_rebuild_tree(self, qapp):
        """Section auto-expand must not destroy tree items."""
        w, rules, smap = _sectioned_widget(qapp)
        w.apply_section_states({2: False})

        item_before = w._real_to_item.get(2)
        w.set_highlights({2}, current=2)
        item_after = w._real_to_item.get(2)

        assert item_before is item_after

    def test_clear_does_not_collapse_sections(self, qapp):
        """clear_highlights() must not collapse sections."""
        w, rules, smap = _sectioned_widget(qapp)
        # All sections start expanded; highlight then clear
        w.set_highlights({0, 2}, current=0)
        w.clear_highlights()

        # Both section headers should still be expanded
        for fid in w._section_header_items:
            header = w._section_header_items[fid]
            assert header.isExpanded(), (
                f"Section fid={fid} was unexpectedly collapsed by clear_highlights()"
            )

    def test_section_header_items_keyed_by_first_rule_index(self, qapp):
        """_section_header_items keys must be first_rule_index values."""
        w, rules, smap = _sectioned_widget(qapp)
        expected_keys = {sec.first_rule_index for sec in smap.sections}
        assert set(w._section_header_items.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Test 6: Idempotency and refresh sync
# ---------------------------------------------------------------------------

class TestIdempotencyAndSync:
    def test_same_query_twice_same_background(self, qapp):
        """Calling set_highlights twice with identical args gives same colours."""
        w, rules = _flat_widget(qapp)
        w.set_highlights({0, 1}, current=0)
        bg_first = [_bg_name(w._real_to_item[i]) for i in (0, 1)]

        w.set_highlights({0, 1}, current=0)
        bg_second = [_bg_name(w._real_to_item[i]) for i in (0, 1)]

        assert bg_first == bg_second

    def test_load_rules_syncs_painted_state(self, qapp):
        """After load_rules(), _painted_highlights must match _highlight_indices."""
        w, rules = _flat_widget(qapp, n=5)
        w.set_highlights({0, 1, 2}, current=1)
        # Simulate load_rules (data change → full rebuild)
        new_rules = [_rule() for _ in range(5)] + [_tail()]
        w.load_rules(new_rules)
        # After rebuild, painted state must equal desired state
        assert w._painted_highlights == w._highlight_indices
        assert w._painted_current == w._current_highlight

    def test_partial_update_after_full_rebuild(self, qapp):
        """After load_rules(), the next set_highlights() still does partial update."""
        w, rules = _flat_widget(qapp, n=4)
        w.set_highlights({0, 1}, current=0)
        w.load_rules(rules)    # full rebuild; _painted_highlights synced

        item_before = w._real_to_item.get(0)
        w.set_highlights({2, 3}, current=2)
        item_after = w._real_to_item.get(0)

        # same tree items; old amber cleared, new amber set
        assert item_before is item_after
        assert _bg_name(w._real_to_item[2]) == _AMBER_CURRENT
        assert _bg_name(w._real_to_item[0]) not in (_AMBER_CURRENT, _AMBER_OTHER)
