"""Tests for Rule Commands — v2.4.0

Unit-tests for AddRuleCommand, DeleteRuleCommand, DuplicateRuleCommand,
MoveRuleCommand — no QApplication required (pure-Python / dataclass layer).

Also covers FilterDocument.undo() / redo() stack integration.
"""

import pytest

from core.document import FilterDocument
from core.models import FilterRule
from core.commands import (
    AddRuleCommand,
    DeleteRuleCommand,
    DuplicateRuleCommand,
    MoveRuleCommand,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rule(action: str = "Show", **kwargs) -> FilterRule:
    return FilterRule(action=action, **kwargs)


def _tail() -> FilterRule:
    return FilterRule(action="__TAIL__")


def _doc(*rules: FilterRule) -> FilterDocument:
    """Build a FilterDocument from a list of rules (using insert_rule primitives)."""
    doc = FilterDocument()
    for i, r in enumerate(rules):
        doc.insert_rule(i, r)
    return doc


def _doc_with_tail(*rules: FilterRule) -> FilterDocument:
    """Build a document ending with a __TAIL__ sentinel."""
    return _doc(*rules, _tail())


def _rule_actions(doc: FilterDocument) -> list[str]:
    """Return the action of every non-TAIL rule as a quick snapshot."""
    return [r.action for r in doc.rules if r.action != "__TAIL__"]


# ---------------------------------------------------------------------------
# AddRuleCommand
# ---------------------------------------------------------------------------

class TestAddRuleCommand:
    def test_execute_inserts_at_index(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"))
        cmd = AddRuleCommand(doc, 1, _rule("Continue"))
        cmd.execute()
        assert doc.rules[1].action == "Continue"
        assert len(doc.rules) == 4   # 2 original + 1 new + tail

    def test_execute_inserts_at_start(self):
        doc = _doc_with_tail(_rule("Show"))
        cmd = AddRuleCommand(doc, 0, _rule("Hide"))
        cmd.execute()
        assert doc.rules[0].action == "Hide"
        assert doc.rules[1].action == "Show"

    def test_execute_appends_before_tail(self):
        doc = _doc_with_tail(_rule("Show"))
        tail_pos = 1
        cmd = AddRuleCommand(doc, tail_pos, _rule("Continue"))
        cmd.execute()
        assert doc.rules[1].action == "Continue"
        assert doc.rules[2].action == "__TAIL__"

    def test_execute_deep_copies_rule(self):
        original = _rule("Show")
        doc = _doc_with_tail()
        cmd = AddRuleCommand(doc, 0, original)
        cmd.execute()
        # Mutating original should not affect the inserted rule
        original.action = "Hide"
        assert doc.rules[0].action == "Show"

    def test_undo_removes_inserted_rule(self):
        doc = _doc_with_tail(_rule("Show"))
        cmd = AddRuleCommand(doc, 0, _rule("Hide"))
        cmd.execute()
        assert len(doc.rules) == 3
        cmd.undo()
        assert len(doc.rules) == 2
        assert doc.rules[0].action == "Show"

    def test_redo_reinserts_rule(self):
        doc = _doc_with_tail(_rule("Show"))
        cmd = AddRuleCommand(doc, 1, _rule("Continue"))
        cmd.execute()
        cmd.undo()
        cmd.redo()
        assert doc.rules[1].action == "Continue"

    def test_marks_dirty(self):
        doc = _doc()
        doc._dirty = False
        cmd = AddRuleCommand(doc, 0, _rule())
        cmd.execute()
        assert doc.dirty

    def test_description_contains_index(self):
        cmd = AddRuleCommand(_doc(), 5, _rule())
        assert "5" in cmd.description


# ---------------------------------------------------------------------------
# DeleteRuleCommand
# ---------------------------------------------------------------------------

class TestDeleteRuleCommand:
    def test_execute_removes_rule(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"))
        cmd = DeleteRuleCommand(doc, 0)
        cmd.execute()
        assert doc.rules[0].action == "Hide"
        assert len(doc.rules) == 2   # 1 rule + tail

    def test_execute_saves_rule_for_undo(self):
        doc = _doc_with_tail(_rule("Show"))
        cmd = DeleteRuleCommand(doc, 0)
        cmd.execute()
        assert cmd._saved_rule is not None
        assert cmd._saved_rule.action == "Show"

    def test_undo_restores_rule_at_same_index(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"))
        cmd = DeleteRuleCommand(doc, 0)
        cmd.execute()
        cmd.undo()
        assert doc.rules[0].action == "Show"
        assert doc.rules[1].action == "Hide"

    def test_undo_restores_deep_copy(self):
        doc = _doc_with_tail(_rule("Show"))
        cmd = DeleteRuleCommand(doc, 0)
        cmd.execute()
        saved = cmd._saved_rule
        cmd.undo()
        # Mutating the saved ref should not affect the restored rule
        saved.action = "Hide"
        assert doc.rules[0].action == "Show"

    def test_redo_removes_rule_again(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"))
        cmd = DeleteRuleCommand(doc, 0)
        cmd.execute()
        cmd.undo()
        cmd.redo()
        assert doc.rules[0].action == "Hide"

    def test_undo_before_execute_raises(self):
        doc = _doc_with_tail(_rule("Show"))
        cmd = DeleteRuleCommand(doc, 0)
        with pytest.raises(RuntimeError):
            cmd.undo()

    def test_description_contains_index(self):
        cmd = DeleteRuleCommand(_doc(), 3)
        assert "3" in cmd.description


# ---------------------------------------------------------------------------
# DuplicateRuleCommand
# ---------------------------------------------------------------------------

class TestDuplicateRuleCommand:
    def test_execute_inserts_copy_after_source(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"))
        cmd = DuplicateRuleCommand(doc, 0)
        cmd.execute()
        assert doc.rules[0].action == "Show"
        assert doc.rules[1].action == "Show"   # duplicate
        assert doc.rules[2].action == "Hide"

    def test_new_index_is_source_plus_one(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"))
        cmd = DuplicateRuleCommand(doc, 0)
        cmd.execute()
        assert cmd.new_index == 1

    def test_duplicate_is_deep_copy(self):
        rule = _rule("Show", conditions=[["Class", '"Currency"']])
        doc = _doc_with_tail(rule)
        cmd = DuplicateRuleCommand(doc, 0)
        cmd.execute()
        # Mutate original → duplicate must not change
        doc.rules[0].conditions = []
        assert doc.rules[1].conditions == [["Class", '"Currency"']]

    def test_undo_removes_duplicate(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"))
        cmd = DuplicateRuleCommand(doc, 0)
        cmd.execute()
        cmd.undo()
        assert _rule_actions(doc) == ["Show", "Hide"]

    def test_redo_reinserts_duplicate(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"))
        cmd = DuplicateRuleCommand(doc, 0)
        cmd.execute()
        cmd.undo()
        cmd.redo()
        assert _rule_actions(doc) == ["Show", "Show", "Hide"]

    def test_undo_before_execute_raises(self):
        doc = _doc_with_tail(_rule("Show"))
        cmd = DuplicateRuleCommand(doc, 0)
        with pytest.raises(RuntimeError):
            cmd.undo()

    def test_duplicate_last_rule(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"))
        cmd = DuplicateRuleCommand(doc, 1)   # duplicate "Hide"
        cmd.execute()
        assert doc.rules[2].action == "Hide"   # duplicate
        assert doc.rules[3].action == "__TAIL__"

    def test_description_contains_index(self):
        cmd = DuplicateRuleCommand(_doc(), 2)
        assert "2" in cmd.description


# ---------------------------------------------------------------------------
# MoveRuleCommand
# ---------------------------------------------------------------------------

class TestMoveRuleCommand:
    def test_execute_moves_rule_up(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"), _rule("Continue"))
        cmd = MoveRuleCommand(doc, 1, 0)   # move "Hide" to index 0
        cmd.execute()
        assert doc.rules[0].action == "Hide"
        assert doc.rules[1].action == "Show"

    def test_execute_moves_rule_down(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"), _rule("Continue"))
        cmd = MoveRuleCommand(doc, 0, 2)   # move "Show" to index 2
        cmd.execute()
        assert doc.rules[2].action == "Show"
        assert doc.rules[0].action == "Hide"

    def test_to_index_clamped_before_tail(self):
        """to_index pointing at or past __TAIL__ must be clamped to last real rule."""
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"))
        cmd = MoveRuleCommand(doc, 0, 99)
        assert cmd.to_index == 1   # clamped to last real index

    def test_from_equals_to_is_noop(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"))
        cmd = MoveRuleCommand(doc, 0, 0)
        assert cmd.is_noop is True

    def test_out_of_bounds_from_is_noop(self):
        doc = _doc_with_tail(_rule("Show"))
        cmd = MoveRuleCommand(doc, 99, 0)
        assert cmd.is_noop is True

    def test_noop_does_not_change_order(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"))
        original = _rule_actions(doc)
        cmd = MoveRuleCommand(doc, 0, 0)
        cmd.execute()
        assert _rule_actions(doc) == original

    def test_undo_reverses_move(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"), _rule("Continue"))
        cmd = MoveRuleCommand(doc, 0, 2)
        cmd.execute()
        cmd.undo()
        assert _rule_actions(doc) == ["Show", "Hide", "Continue"]

    def test_redo_reapplies_move(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"), _rule("Continue"))
        cmd = MoveRuleCommand(doc, 0, 2)
        cmd.execute()
        cmd.undo()
        cmd.redo()
        assert doc.rules[2].action == "Show"

    def test_description_contains_indices(self):
        cmd = MoveRuleCommand(_doc(_rule(), _rule()), 0, 1)
        assert "0" in cmd.description
        assert "1" in cmd.description

    def test_single_movable_rule_is_noop(self):
        """Only one movable rule → any move must be noop."""
        doc = _doc_with_tail(_rule("Show"))
        cmd = MoveRuleCommand(doc, 0, 1)
        assert cmd.is_noop is True

    def test_cannot_move_tail(self):
        """from_index pointing at __TAIL__ must be noop."""
        doc = _doc_with_tail(_rule("Show"))
        tail_idx = 1
        cmd = MoveRuleCommand(doc, tail_idx, 0)
        assert cmd.is_noop is True


# ---------------------------------------------------------------------------
# Undo / Redo Stack Integration
# ---------------------------------------------------------------------------

class TestUndoRedoStack:
    def test_doc_execute_pushes_to_undo_stack(self):
        doc = _doc_with_tail(_rule("Show"))
        cmd = AddRuleCommand(doc, 0, _rule("Hide"))
        doc.execute(cmd)
        assert doc.can_undo()
        assert not doc.can_redo()

    def test_undo_clears_redo_on_new_execute(self):
        doc = _doc_with_tail(_rule("Show"))
        cmd1 = AddRuleCommand(doc, 0, _rule("Hide"))
        doc.execute(cmd1)
        doc.undo()
        assert doc.can_redo()
        cmd2 = AddRuleCommand(doc, 0, _rule("Continue"))
        doc.execute(cmd2)
        assert not doc.can_redo()

    def test_multiple_undo_redo_cycle(self):
        doc = _doc_with_tail()
        doc.execute(AddRuleCommand(doc, 0, _rule("Show")))
        doc.execute(AddRuleCommand(doc, 1, _rule("Hide")))
        assert _rule_actions(doc) == ["Show", "Hide"]
        doc.undo()
        assert _rule_actions(doc) == ["Show"]
        doc.undo()
        assert _rule_actions(doc) == []
        doc.redo()
        assert _rule_actions(doc) == ["Show"]
        doc.redo()
        assert _rule_actions(doc) == ["Show", "Hide"]

    def test_delete_undo_redo(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"))
        doc.execute(DeleteRuleCommand(doc, 0))
        assert _rule_actions(doc) == ["Hide"]
        doc.undo()
        assert _rule_actions(doc) == ["Show", "Hide"]
        doc.redo()
        assert _rule_actions(doc) == ["Hide"]

    def test_duplicate_undo_redo(self):
        doc = _doc_with_tail(_rule("Show"))
        doc.execute(DuplicateRuleCommand(doc, 0))
        assert _rule_actions(doc) == ["Show", "Show"]
        doc.undo()
        assert _rule_actions(doc) == ["Show"]
        doc.redo()
        assert _rule_actions(doc) == ["Show", "Show"]

    def test_move_undo_redo(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"), _rule("Continue"))
        doc.execute(MoveRuleCommand(doc, 0, 2))
        assert _rule_actions(doc) == ["Hide", "Continue", "Show"]
        doc.undo()
        assert _rule_actions(doc) == ["Show", "Hide", "Continue"]
        doc.redo()
        assert _rule_actions(doc) == ["Hide", "Continue", "Show"]

    def test_undo_empty_stack_safe(self):
        doc = _doc_with_tail(_rule("Show"))
        doc.undo()   # must not raise
        assert _rule_actions(doc) == ["Show"]

    def test_redo_empty_stack_safe(self):
        doc = _doc_with_tail(_rule("Show"))
        doc.redo()   # must not raise
        assert _rule_actions(doc) == ["Show"]

    def test_marks_dirty_on_undo(self):
        doc = _doc_with_tail(_rule("Show"))
        doc.execute(AddRuleCommand(doc, 0, _rule("Hide")))
        doc._dirty = False
        doc.undo()
        assert doc.dirty

    def test_marks_dirty_on_redo(self):
        doc = _doc_with_tail(_rule("Show"))
        doc.execute(AddRuleCommand(doc, 0, _rule("Hide")))
        doc.undo()
        doc._dirty = False
        doc.redo()
        assert doc.dirty


# ---------------------------------------------------------------------------
# Selection Preservation (logic layer, no UI)
# ---------------------------------------------------------------------------

class TestSelectionPreservation:
    """Verify that rule ordering after operations matches expected indices
    so that the UI's select_real_index call points to the correct rule."""

    def test_add_rule_next_to_selected(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"))
        selected = 0
        insert_at = selected + 1
        doc.execute(AddRuleCommand(doc, insert_at, _rule("Continue")))
        # new rule is at insert_at
        assert doc.rules[insert_at].action == "Continue"
        # original "Hide" has shifted to index 2
        assert doc.rules[2].action == "Hide"

    def test_duplicate_selects_new_copy(self):
        doc = _doc_with_tail(_rule("Show"), _rule("Hide"))
        selected = 0
        cmd = DuplicateRuleCommand(doc, selected)
        doc.execute(cmd)
        # new rule lives at new_index = 1
        assert cmd.new_index == 1
        assert doc.rules[cmd.new_index].action == "Show"

    def test_move_up_updates_selection_target(self):
        doc = _doc_with_tail(_rule("A"), _rule("B"), _rule("C"))
        selected = 1   # "B"
        cmd = MoveRuleCommand(doc, selected, selected - 1)
        doc.execute(cmd)
        # "B" is now at index 0 (cmd.to_index)
        assert doc.rules[cmd.to_index].action == "B"

    def test_move_down_updates_selection_target(self):
        doc = _doc_with_tail(_rule("A"), _rule("B"), _rule("C"))
        selected = 1   # "B"
        cmd = MoveRuleCommand(doc, selected, selected + 1)
        doc.execute(cmd)
        # "B" is now at index 2 (cmd.to_index)
        assert doc.rules[cmd.to_index].action == "B"
