"""UndoManager — v1.0.0

Standalone command stack for Undo / Redo.  Knows nothing about FilterDocument
or Qt — it only stores AbstractCommand objects in two deques and routes calls.

Usage (inside FilterDocument):
    self._undo_mgr = UndoManager()
    self._undo_mgr.push(cmd)    # after cmd.execute()
    self._undo_mgr.undo()       # returns cmd; caller must call cmd.undo()
    self._undo_mgr.redo()       # returns cmd; caller must call cmd.redo()

Callers are responsible for invoking the returned command's undo()/redo().
This decoupling keeps UndoManager unit-testable without needing FilterDocument.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.commands import AbstractCommand

_DEFAULT_LIMIT = 100


class UndoManager:
    """LIFO undo / redo command stack.

    push() appends to the undo stack and wipes the redo stack.
    undo() moves the top item from undo → redo and returns it.
    redo() moves the top item from redo → undo and returns it.
    """

    def __init__(self, limit: int = _DEFAULT_LIMIT) -> None:
        self._undo: deque["AbstractCommand"] = deque(maxlen=limit)
        self._redo: deque["AbstractCommand"] = deque(maxlen=limit)

    # ------------------------------------------------------------------
    # Core stack operations
    # ------------------------------------------------------------------

    def push(self, cmd: "AbstractCommand") -> None:
        """Record a newly executed command; clears the redo stack."""
        self._undo.append(cmd)
        self._redo.clear()

    def undo(self) -> "AbstractCommand | None":
        """Pop from undo stack, push to redo stack, return the command.

        Returns None if the undo stack is empty — caller should check
        can_undo() first or handle None safely.
        """
        if not self._undo:
            return None
        cmd = self._undo.pop()
        self._redo.append(cmd)
        return cmd

    def redo(self) -> "AbstractCommand | None":
        """Pop from redo stack, push back to undo stack, return the command.

        Returns None if the redo stack is empty.
        """
        if not self._redo:
            return None
        cmd = self._redo.pop()
        self._undo.append(cmd)
        return cmd

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def peek_undo(self) -> "AbstractCommand | None":
        """Return the command that would be undone next, without modifying the stack."""
        return self._undo[-1] if self._undo else None

    def peek_redo(self) -> "AbstractCommand | None":
        """Return the command that would be redone next, without modifying the stack."""
        return self._redo[-1] if self._redo else None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Wipe both stacks (call after load_from_text)."""
        self._undo.clear()
        self._redo.clear()

    @property
    def undo_depth(self) -> int:
        return len(self._undo)

    @property
    def redo_depth(self) -> int:
        return len(self._redo)
