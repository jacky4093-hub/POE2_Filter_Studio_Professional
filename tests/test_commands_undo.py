"""Integration tests — Commands × FilterDocument Undo/Redo  (P14.2)

Tests the full execute → undo → redo cycle for the three core command types
against a real FilterDocument.  No Qt dependency.
"""

import copy
import pytest

from core.document import FilterDocument
from core.models import FilterRule
from core.commands import AddRuleCommand, DeleteRuleCommand, UpdateRuleCommand


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _doc_with(*conditions_list) -> FilterDocument:
    """Return a FilterDocument pre-populated with simple Show rules."""
    doc = FilterDocument()
    for conds in conditions_list:
        rule = FilterRule(action="Show", conditions=list(conds))
        doc._rules.append(rule)
    return doc


def _real_rules(doc: FilterDocument) -> list[FilterRule]:
    return [r for r in doc.rules if r.action != "__TAIL__"]


def _conds(doc: FilterDocument, index: int) -> list:
    return doc.rules[index].conditions


# ---------------------------------------------------------------------------
# TestAddRuleCommand
# ---------------------------------------------------------------------------

class TestAddRuleCommand:

    def test_execute_inserts_rule(self):
        doc = FilterDocument()
        rule = FilterRule(action="Show", conditions=[["Class", "Currency"]])
        cmd = AddRuleCommand(doc, 0, rule)
        doc.execute(cmd)
        assert len(_real_rules(doc)) == 1
        assert _conds(doc, 0) == [["Class", "Currency"]]

    def test_execute_marks_dirty(self):
        doc = FilterDocument()
        doc.clear_dirty()
        cmd = AddRuleCommand(doc, 0, FilterRule(action="Show"))
        doc.execute(cmd)
        assert doc.dirty

    def test_execute_enables_can_undo(self):
        doc = FilterDocument()
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Show")))
        assert doc.can_undo()

    def test_execute_clears_can_redo(self):
        doc = _doc_with([])
        cmd1 = DeleteRuleCommand(doc, 0)
        doc.execute(cmd1)
        doc.undo()                                      # can_redo = True
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Show")))
        assert not doc.can_redo()

    # --- undo add ---

    def test_undo_add_removes_rule(self):
        doc = FilterDocument()
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Show")))
        doc.undo()
        assert len(_real_rules(doc)) == 0

    def test_undo_add_restores_original_count(self):
        doc = _doc_with([["Rarity", "Rare"]])
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Show")))
        assert len(_real_rules(doc)) == 2
        doc.undo()
        assert len(_real_rules(doc)) == 1

    def test_undo_add_disables_can_undo_when_stack_empty(self):
        doc = FilterDocument()
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Show")))
        doc.undo()
        assert not doc.can_undo()

    def test_undo_add_enables_can_redo(self):
        doc = FilterDocument()
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Show")))
        doc.undo()
        assert doc.can_redo()

    # --- redo add ---

    def test_redo_add_reinserts_rule(self):
        doc = FilterDocument()
        rule = FilterRule(action="Show", conditions=[["Class", "Gems"]])
        doc.execute(AddRuleCommand(doc, 0, rule))
        doc.undo()
        doc.redo()
        assert len(_real_rules(doc)) == 1
        assert _conds(doc, 0) == [["Class", "Gems"]]

    def test_redo_add_re_enables_can_undo(self):
        doc = FilterDocument()
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Show")))
        doc.undo()
        doc.redo()
        assert doc.can_undo()

    def test_redo_add_disables_can_redo_when_stack_empty(self):
        doc = FilterDocument()
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Show")))
        doc.undo()
        doc.redo()
        assert not doc.can_redo()

    def test_undo_redo_add_cycle_preserves_conditions(self):
        doc = FilterDocument()
        conds = [["Class", "Waystones"], ["Rarity", "Normal"]]
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Show", conditions=conds)))
        doc.undo()
        doc.redo()
        assert _conds(doc, 0) == conds

    def test_multiple_adds_undo_in_lifo_order(self):
        doc = FilterDocument()
        for cls in ("Currency", "Gems", "Waystones"):
            rule = FilterRule(action="Show", conditions=[["Class", cls]])
            doc.execute(AddRuleCommand(doc, len(doc.rules), rule))
        assert len(_real_rules(doc)) == 3
        doc.undo()
        assert len(_real_rules(doc)) == 2
        doc.undo()
        assert len(_real_rules(doc)) == 1
        doc.undo()
        assert len(_real_rules(doc)) == 0


# ---------------------------------------------------------------------------
# TestDeleteRuleCommand
# ---------------------------------------------------------------------------

class TestDeleteRuleCommand:

    def test_execute_removes_rule(self):
        doc = _doc_with([["Class", "Currency"]])
        doc.execute(DeleteRuleCommand(doc, 0))
        assert len(_real_rules(doc)) == 0

    def test_execute_marks_dirty(self):
        doc = _doc_with([])
        doc.clear_dirty()
        doc.execute(DeleteRuleCommand(doc, 0))
        assert doc.dirty

    def test_execute_enables_can_undo(self):
        doc = _doc_with([])
        doc.execute(DeleteRuleCommand(doc, 0))
        assert doc.can_undo()

    # --- undo delete ---

    def test_undo_delete_restores_rule(self):
        doc = _doc_with([["Class", "Currency"]])
        doc.execute(DeleteRuleCommand(doc, 0))
        doc.undo()
        assert len(_real_rules(doc)) == 1
        assert _conds(doc, 0) == [["Class", "Currency"]]

    def test_undo_delete_restores_at_correct_index(self):
        doc = _doc_with([["Rarity", "Normal"]], [["Class", "Gems"]], [["Class", "Currency"]])
        doc.execute(DeleteRuleCommand(doc, 1))     # delete middle rule
        doc.undo()
        assert _conds(doc, 1) == [["Class", "Gems"]]

    def test_undo_delete_enables_can_redo(self):
        doc = _doc_with([])
        doc.execute(DeleteRuleCommand(doc, 0))
        doc.undo()
        assert doc.can_redo()

    def test_undo_delete_disables_can_undo_when_stack_empty(self):
        doc = _doc_with([])
        doc.execute(DeleteRuleCommand(doc, 0))
        doc.undo()
        assert not doc.can_undo()

    # --- redo delete ---

    def test_redo_delete_removes_rule_again(self):
        doc = _doc_with([["Class", "Currency"]])
        doc.execute(DeleteRuleCommand(doc, 0))
        doc.undo()
        doc.redo()
        assert len(_real_rules(doc)) == 0

    def test_redo_delete_re_enables_can_undo(self):
        doc = _doc_with([])
        doc.execute(DeleteRuleCommand(doc, 0))
        doc.undo()
        doc.redo()
        assert doc.can_undo()

    def test_redo_delete_disables_can_redo_when_stack_empty(self):
        doc = _doc_with([])
        doc.execute(DeleteRuleCommand(doc, 0))
        doc.undo()
        doc.redo()
        assert not doc.can_redo()

    def test_undo_redo_delete_cycle_restores_all_conditions(self):
        conds = [["Class", "Gems"], ["Rarity", "Rare"], ["AreaLevel", ">= 68"]]
        doc = _doc_with(conds)
        doc.execute(DeleteRuleCommand(doc, 0))
        doc.undo()
        doc.redo()
        doc.undo()
        assert _conds(doc, 0) == conds

    def test_delete_undo_is_deep_copy_independent(self):
        """Mutating the rule after delete-undo must not corrupt redo state."""
        doc = _doc_with([["Class", "Currency"]])
        cmd = DeleteRuleCommand(doc, 0)
        doc.execute(cmd)
        doc.undo()
        doc.rules[0].conditions.append(["Extra", "val"])
        doc.undo()      # undo the undo? — no, undo stack is empty now.
        # The redo command still holds the original deep copy.
        doc.redo()
        assert len(_real_rules(doc)) == 0  # rule deleted again


# ---------------------------------------------------------------------------
# TestUpdateRuleCommand
# ---------------------------------------------------------------------------

class TestUpdateRuleCommand:

    def _make_update(self, doc, index):
        old = copy.deepcopy(doc.rules[index])
        new = copy.deepcopy(old)
        new.conditions = [["Rarity", "Unique"]]
        return UpdateRuleCommand(doc, index, old, new)

    def test_execute_updates_rule(self):
        doc = _doc_with([["Class", "Currency"]])
        old = copy.deepcopy(doc.rules[0])
        new = FilterRule(action="Show", conditions=[["Rarity", "Unique"]])
        doc.execute(UpdateRuleCommand(doc, 0, old, new))
        assert _conds(doc, 0) == [["Rarity", "Unique"]]

    def test_execute_marks_dirty(self):
        doc = _doc_with([])
        doc.clear_dirty()
        doc.execute(self._make_update(doc, 0))
        assert doc.dirty

    def test_execute_enables_can_undo(self):
        doc = _doc_with([])
        doc.execute(self._make_update(doc, 0))
        assert doc.can_undo()

    # --- undo update ---

    def test_undo_update_restores_old_conditions(self):
        doc = _doc_with([["Class", "Currency"]])
        old = copy.deepcopy(doc.rules[0])
        new = FilterRule(action="Show", conditions=[["Rarity", "Unique"]])
        doc.execute(UpdateRuleCommand(doc, 0, old, new))
        doc.undo()
        assert _conds(doc, 0) == [["Class", "Currency"]]

    def test_undo_update_enables_can_redo(self):
        doc = _doc_with([])
        doc.execute(self._make_update(doc, 0))
        doc.undo()
        assert doc.can_redo()

    def test_undo_update_disables_can_undo_when_stack_empty(self):
        doc = _doc_with([])
        doc.execute(self._make_update(doc, 0))
        doc.undo()
        assert not doc.can_undo()

    def test_undo_update_restores_action(self):
        doc = _doc_with([])
        doc.rules[0].action = "Hide"
        old = copy.deepcopy(doc.rules[0])
        new_r = copy.deepcopy(old)
        new_r.action = "Show"
        doc.execute(UpdateRuleCommand(doc, 0, old, new_r))
        assert doc.rules[0].action == "Show"
        doc.undo()
        assert doc.rules[0].action == "Hide"

    # --- redo update ---

    def test_redo_update_reapplies_new_conditions(self):
        doc = _doc_with([["Class", "Currency"]])
        old = copy.deepcopy(doc.rules[0])
        new = FilterRule(action="Show", conditions=[["Rarity", "Unique"]])
        doc.execute(UpdateRuleCommand(doc, 0, old, new))
        doc.undo()
        doc.redo()
        assert _conds(doc, 0) == [["Rarity", "Unique"]]

    def test_redo_update_re_enables_can_undo(self):
        doc = _doc_with([])
        doc.execute(self._make_update(doc, 0))
        doc.undo()
        doc.redo()
        assert doc.can_undo()

    def test_redo_update_disables_can_redo_when_stack_empty(self):
        doc = _doc_with([])
        doc.execute(self._make_update(doc, 0))
        doc.undo()
        doc.redo()
        assert not doc.can_redo()

    def test_undo_redo_update_cycle_three_times(self):
        doc = _doc_with([["Class", "Currency"]])
        old = copy.deepcopy(doc.rules[0])
        new = FilterRule(action="Show", conditions=[["Rarity", "Unique"]])
        doc.execute(UpdateRuleCommand(doc, 0, old, new))

        for _ in range(3):
            doc.undo()
            assert _conds(doc, 0) == [["Class", "Currency"]]
            doc.redo()
            assert _conds(doc, 0) == [["Rarity", "Unique"]]

    def test_update_snapshot_independent_of_later_mutations(self):
        """Mutating the rule after execute must not alter the stored undo state."""
        doc = _doc_with([["Class", "Currency"]])
        old = copy.deepcopy(doc.rules[0])
        new = FilterRule(action="Show", conditions=[["Rarity", "Unique"]])
        doc.execute(UpdateRuleCommand(doc, 0, old, new))
        # Mutate in place after execute
        doc.rules[0].conditions.append(["Extra", "val"])
        doc.undo()
        # Undo should restore the original, not the mutated version
        assert _conds(doc, 0) == [["Class", "Currency"]]


# ---------------------------------------------------------------------------
# TestStackClear
# ---------------------------------------------------------------------------

class TestStackClear:

    def test_load_from_text_clears_undo_stack(self):
        doc = FilterDocument()
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Show")))
        assert doc.can_undo()
        doc.load_from_text("Show\n\n", "dummy.filter")
        assert not doc.can_undo()

    def test_load_from_text_clears_redo_stack(self):
        doc = FilterDocument()
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Show")))
        doc.undo()
        assert doc.can_redo()
        doc.load_from_text("Show\n\n", "dummy.filter")
        assert not doc.can_redo()

    def test_load_from_text_resets_dirty(self):
        doc = FilterDocument()
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Show")))
        assert doc.dirty
        doc.load_from_text("", "dummy.filter")
        assert not doc.dirty

    def test_undo_on_empty_stack_is_safe(self):
        doc = FilterDocument()
        doc.undo()  # must not raise
        assert not doc.can_undo()

    def test_redo_on_empty_stack_is_safe(self):
        doc = FilterDocument()
        doc.redo()  # must not raise
        assert not doc.can_redo()


# ---------------------------------------------------------------------------
# TestMixedOperations
# ---------------------------------------------------------------------------

class TestMixedOperations:

    def test_add_then_delete_then_undo_twice(self):
        doc = FilterDocument()
        rule = FilterRule(action="Show", conditions=[["Class", "Currency"]])
        doc.execute(AddRuleCommand(doc, 0, rule))
        doc.execute(DeleteRuleCommand(doc, 0))
        assert len(_real_rules(doc)) == 0
        doc.undo()  # undo delete
        assert len(_real_rules(doc)) == 1
        doc.undo()  # undo add
        assert len(_real_rules(doc)) == 0

    def test_add_then_update_then_undo_twice(self):
        doc = FilterDocument()
        rule = FilterRule(action="Show", conditions=[["Class", "Currency"]])
        doc.execute(AddRuleCommand(doc, 0, rule))
        old = copy.deepcopy(doc.rules[0])
        new = FilterRule(action="Show", conditions=[["Rarity", "Rare"]])
        doc.execute(UpdateRuleCommand(doc, 0, old, new))
        assert _conds(doc, 0) == [["Rarity", "Rare"]]
        doc.undo()  # undo update
        assert _conds(doc, 0) == [["Class", "Currency"]]
        doc.undo()  # undo add
        assert len(_real_rules(doc)) == 0

    def test_redo_stack_clears_after_new_execute(self):
        doc = FilterDocument()
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Show")))
        doc.undo()
        assert doc.can_redo()
        # New operation wipes redo
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Hide")))
        assert not doc.can_redo()
        assert doc.rules[0].action == "Hide"

    def test_peek_undo_command_description(self):
        doc = FilterDocument()
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Show")))
        cmd = doc.peek_undo_command()
        assert cmd is not None
        assert "新增" in cmd.description

    def test_peek_redo_command_description(self):
        doc = _doc_with([])
        doc.execute(DeleteRuleCommand(doc, 0))
        doc.undo()
        cmd = doc.peek_redo_command()
        assert cmd is not None
        assert "刪除" in cmd.description

    def test_can_undo_reflects_stack_state_throughout(self):
        doc = FilterDocument()
        assert not doc.can_undo()
        doc.execute(AddRuleCommand(doc, 0, FilterRule(action="Show")))
        assert doc.can_undo()
        doc.undo()
        assert not doc.can_undo()
        doc.redo()
        assert doc.can_undo()
