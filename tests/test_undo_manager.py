"""Tests for UndoManager — P14.2 Undo / Redo Foundation

Pure-Python tests (no Qt). Verifies the standalone UndoManager class
in isolation using a simple stub command.
"""

import pytest
from core.undo_manager import UndoManager
from core.commands import AbstractCommand


# ---------------------------------------------------------------------------
# Stub command — records calls without touching a FilterDocument
# ---------------------------------------------------------------------------

class _Stub(AbstractCommand):
    description = "stub"

    def __init__(self, label: str = "x"):
        self.label = label
        self.executed = 0
        self.undone   = 0
        self.redone   = 0

    def execute(self) -> None: self.executed += 1
    def undo(self)    -> None: self.undone   += 1
    def redo(self)    -> None: self.redone   += 1


# ---------------------------------------------------------------------------
# TestUndoManagerConstruction
# ---------------------------------------------------------------------------

class TestUndoManagerConstruction:

    def test_default_empty(self):
        mgr = UndoManager()
        assert not mgr.can_undo()
        assert not mgr.can_redo()

    def test_initial_depths_are_zero(self):
        mgr = UndoManager()
        assert mgr.undo_depth == 0
        assert mgr.redo_depth == 0

    def test_peek_empty_returns_none(self):
        mgr = UndoManager()
        assert mgr.peek_undo() is None
        assert mgr.peek_redo() is None


# ---------------------------------------------------------------------------
# TestPush
# ---------------------------------------------------------------------------

class TestPush:

    def test_push_enables_can_undo(self):
        mgr = UndoManager()
        mgr.push(_Stub())
        assert mgr.can_undo()

    def test_push_does_not_enable_can_redo(self):
        mgr = UndoManager()
        mgr.push(_Stub())
        assert not mgr.can_redo()

    def test_push_increments_undo_depth(self):
        mgr = UndoManager()
        mgr.push(_Stub())
        mgr.push(_Stub())
        assert mgr.undo_depth == 2

    def test_push_wipes_redo_stack(self):
        mgr = UndoManager()
        cmd = _Stub()
        mgr.push(cmd)
        mgr.undo()          # moves cmd to redo
        assert mgr.can_redo()
        mgr.push(_Stub())   # new command → redo must be cleared
        assert not mgr.can_redo()
        assert mgr.redo_depth == 0

    def test_push_peek_undo_returns_latest(self):
        mgr = UndoManager()
        a, b = _Stub("a"), _Stub("b")
        mgr.push(a)
        mgr.push(b)
        assert mgr.peek_undo() is b


# ---------------------------------------------------------------------------
# TestUndo
# ---------------------------------------------------------------------------

class TestUndo:

    def test_undo_returns_command(self):
        mgr = UndoManager()
        cmd = _Stub()
        mgr.push(cmd)
        result = mgr.undo()
        assert result is cmd

    def test_undo_empty_returns_none(self):
        mgr = UndoManager()
        assert mgr.undo() is None

    def test_undo_moves_to_redo(self):
        mgr = UndoManager()
        cmd = _Stub()
        mgr.push(cmd)
        mgr.undo()
        assert mgr.can_redo()
        assert not mgr.can_undo()

    def test_undo_lifo_order(self):
        mgr = UndoManager()
        a, b = _Stub("a"), _Stub("b")
        mgr.push(a)
        mgr.push(b)
        assert mgr.undo() is b
        assert mgr.undo() is a

    def test_undo_decrements_undo_depth(self):
        mgr = UndoManager()
        mgr.push(_Stub())
        mgr.push(_Stub())
        mgr.undo()
        assert mgr.undo_depth == 1

    def test_undo_increments_redo_depth(self):
        mgr = UndoManager()
        mgr.push(_Stub())
        mgr.undo()
        assert mgr.redo_depth == 1

    def test_undo_does_not_call_cmd_undo(self):
        """UndoManager only moves the command; caller must invoke cmd.undo()."""
        mgr = UndoManager()
        cmd = _Stub()
        mgr.push(cmd)
        mgr.undo()
        assert cmd.undone == 0  # UndoManager is not responsible for calling undo()


# ---------------------------------------------------------------------------
# TestRedo
# ---------------------------------------------------------------------------

class TestRedo:

    def test_redo_returns_command(self):
        mgr = UndoManager()
        cmd = _Stub()
        mgr.push(cmd)
        mgr.undo()
        result = mgr.redo()
        assert result is cmd

    def test_redo_empty_returns_none(self):
        mgr = UndoManager()
        assert mgr.redo() is None

    def test_redo_moves_back_to_undo(self):
        mgr = UndoManager()
        cmd = _Stub()
        mgr.push(cmd)
        mgr.undo()
        mgr.redo()
        assert mgr.can_undo()
        assert not mgr.can_redo()

    def test_redo_lifo_order(self):
        mgr = UndoManager()
        a, b = _Stub("a"), _Stub("b")
        mgr.push(a)
        mgr.push(b)
        mgr.undo()  # b → redo
        mgr.undo()  # a → redo
        assert mgr.redo() is a   # last-undone is first-redone
        assert mgr.redo() is b

    def test_redo_does_not_call_cmd_redo(self):
        """UndoManager only moves the command; caller must invoke cmd.redo()."""
        mgr = UndoManager()
        cmd = _Stub()
        mgr.push(cmd)
        mgr.undo()
        mgr.redo()
        assert cmd.redone == 0


# ---------------------------------------------------------------------------
# TestClear
# ---------------------------------------------------------------------------

class TestClear:

    def test_clear_wipes_undo(self):
        mgr = UndoManager()
        mgr.push(_Stub())
        mgr.clear()
        assert not mgr.can_undo()
        assert mgr.undo_depth == 0

    def test_clear_wipes_redo(self):
        mgr = UndoManager()
        mgr.push(_Stub())
        mgr.undo()
        mgr.clear()
        assert not mgr.can_redo()
        assert mgr.redo_depth == 0

    def test_clear_on_empty_is_safe(self):
        mgr = UndoManager()
        mgr.clear()  # must not raise
        assert mgr.undo_depth == 0


# ---------------------------------------------------------------------------
# TestStackLimit
# ---------------------------------------------------------------------------

class TestStackLimit:

    def test_limit_respected(self):
        limit = 5
        mgr = UndoManager(limit=limit)
        for _ in range(10):
            mgr.push(_Stub())
        assert mgr.undo_depth == limit

    def test_oldest_dropped_when_limit_exceeded(self):
        """When the limit is hit, the oldest command is dropped (deque behavior)."""
        limit = 3
        mgr = UndoManager(limit=limit)
        cmds = [_Stub(str(i)) for i in range(5)]
        for cmd in cmds:
            mgr.push(cmd)
        # Undo 3 times — should get cmds[4], cmds[3], cmds[2] in that order
        assert mgr.undo() is cmds[4]
        assert mgr.undo() is cmds[3]
        assert mgr.undo() is cmds[2]
        assert not mgr.can_undo()
