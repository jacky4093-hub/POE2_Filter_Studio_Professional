"""Command Pattern — v0.5.0

All FilterDocument mutations are expressed as Command objects.
Each command captures everything needed to execute, undo, and redo
an operation without holding live references that could be mutated
by the editor after the command is created.

Usage:
    cmd = AddRuleCommand(doc, index, rule)
    doc.execute(cmd)     # runs cmd.execute(), pushes to undo stack

    doc.undo()           # pops undo stack, calls cmd.undo()
    doc.redo()           # pops redo stack, calls cmd.redo()

Public interface (all no-arg):
    cmd.execute()
    cmd.undo()
    cmd.redo()
    cmd.description  -> str  (for future Undo menu label)
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.document import FilterDocument
    from core.models import FilterRule


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class AbstractCommand(ABC):
    description: str = ""

    @abstractmethod
    def execute(self) -> None: ...

    @abstractmethod
    def undo(self) -> None: ...

    def redo(self) -> None:
        self.execute()


# ---------------------------------------------------------------------------
# AddRuleCommand
# ---------------------------------------------------------------------------

class AddRuleCommand(AbstractCommand):
    """Insert a new rule at *index*."""

    def __init__(self, doc: "FilterDocument", index: int, rule: "FilterRule"):
        self._doc   = doc
        self._index = index
        self._rule  = copy.deepcopy(rule)
        self.description = f"新增規則 [{index}]"

    def execute(self) -> None:
        self._doc.insert_rule(self._index, copy.deepcopy(self._rule))

    def undo(self) -> None:
        self._doc.remove_rule(self._index)

    def redo(self) -> None:
        self.execute()


# ---------------------------------------------------------------------------
# DeleteRuleCommand
# ---------------------------------------------------------------------------

class DeleteRuleCommand(AbstractCommand):
    """Remove the rule at *index*; saves a deep-copy for undo."""

    def __init__(self, doc: "FilterDocument", index: int):
        self._doc          = doc
        self._index        = index
        self._saved_rule:  "FilterRule | None" = None
        self.description = f"刪除規則 [{index}]"

    def execute(self) -> None:
        self._saved_rule = copy.deepcopy(self._doc.rules[self._index])
        self._doc.remove_rule(self._index)

    def undo(self) -> None:
        if self._saved_rule is None:
            raise RuntimeError("DeleteRuleCommand.undo() called before execute()")
        self._doc.insert_rule(self._index, copy.deepcopy(self._saved_rule))

    def redo(self) -> None:
        self.execute()


# ---------------------------------------------------------------------------
# DuplicateRuleCommand
# ---------------------------------------------------------------------------

class DuplicateRuleCommand(AbstractCommand):
    """Deep-copy rule at *source_index* and insert after it.

    The actual new_index is only known after execute() runs, so undo
    removes whatever index was returned by duplicate_rule().
    """

    def __init__(self, doc: "FilterDocument", source_index: int):
        self._doc          = doc
        self._source_index = source_index
        self._new_index:   int = -1
        self.description = f"複製規則 [{source_index}]"

    def execute(self) -> None:
        self._new_index = self._doc.duplicate_rule(self._source_index)

    def undo(self) -> None:
        if self._new_index < 0:
            raise RuntimeError("DuplicateRuleCommand.undo() called before execute()")
        self._doc.remove_rule(self._new_index)

    def redo(self) -> None:
        self.execute()

    @property
    def new_index(self) -> int:
        return self._new_index


# ---------------------------------------------------------------------------
# UpdateRuleCommand
# ---------------------------------------------------------------------------

class UpdateRuleCommand(AbstractCommand):
    """Replace the rule at *index* with a new snapshot.

    Both old_rule and new_rule are deep-copied at construction time so
    that subsequent in-place edits by RuleEditor cannot corrupt the
    stored undo/redo state.
    """

    def __init__(
        self,
        doc: "FilterDocument",
        index: int,
        old_rule: "FilterRule",
        new_rule: "FilterRule",
    ):
        self._doc      = doc
        self._index    = index
        self._old_rule = copy.deepcopy(old_rule)
        self._new_rule = copy.deepcopy(new_rule)
        self.description = f"修改規則 [{index}]"

    def execute(self) -> None:
        self._doc.update_rule(self._index, copy.deepcopy(self._new_rule))

    def undo(self) -> None:
        self._doc.update_rule(self._index, copy.deepcopy(self._old_rule))

    def redo(self) -> None:
        self._doc.update_rule(self._index, copy.deepcopy(self._new_rule))


# ---------------------------------------------------------------------------
# MoveRuleCommand  (reserved for v0.6.0 Drag & Drop)
# ---------------------------------------------------------------------------

class MoveRuleCommand(AbstractCommand):
    """Reserved — not yet implemented."""

    description = "移動規則（預留）"

    def __init__(self, doc: "FilterDocument", from_index: int, to_index: int):
        self._doc        = doc
        self._from_index = from_index
        self._to_index   = to_index

    def execute(self) -> None:
        raise NotImplementedError("MoveRuleCommand not yet implemented")

    def undo(self) -> None:
        raise NotImplementedError("MoveRuleCommand not yet implemented")


# ---------------------------------------------------------------------------
# BatchCommand  (reserved — multiple commands as one undo unit)
# ---------------------------------------------------------------------------

class BatchCommand(AbstractCommand):
    """Reserved — group multiple commands into a single undo unit."""

    def __init__(self, commands: list[AbstractCommand], description: str = "批次操作"):
        self._commands   = list(commands)
        self.description = description

    def execute(self) -> None:
        for cmd in self._commands:
            cmd.execute()

    def undo(self) -> None:
        for cmd in reversed(self._commands):
            cmd.undo()

    def redo(self) -> None:
        for cmd in self._commands:
            cmd.redo()
