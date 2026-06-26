import copy
from collections import deque

from core.models import FilterRule
from parser.filter_parser import parse_filter
from parser.filter_exporter import export_filter


_UNDO_LIMIT = 100   # max undo/redo depth


class FilterDocument:
    """Owns the complete state of one open .filter file.

    v0.5.0: all rule mutations from the UI layer must go through execute().
    The low-level primitives (insert_rule / remove_rule / duplicate_rule /
    update_rule) remain public so that Command objects can call them directly,
    but the UI layer must not call them anymore.

    Undo / Redo stacks live here.  FilterDocument is intentionally NOT a
    QObject — callers are responsible for refreshing the UI after undo/redo.
    """

    def __init__(self):
        self._rules:      list[FilterRule] = []
        self._file_path:  str  = ""
        self._dirty:      bool = False
        self._undo_stack: deque = deque(maxlen=_UNDO_LIMIT)
        self._redo_stack: deque = deque(maxlen=_UNDO_LIMIT)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def rules(self) -> list[FilterRule]:
        return self._rules

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def dirty(self) -> bool:
        return self._dirty

    @property
    def visible_count(self) -> int:
        return sum(1 for r in self._rules if r.action != "__TAIL__")

    # ------------------------------------------------------------------
    # Load / export
    # ------------------------------------------------------------------

    def load_from_text(self, text: str, file_path: str = "") -> None:
        self._rules = parse_filter(text)
        self._file_path = file_path
        self._dirty = False
        self._undo_stack.clear()
        self._redo_stack.clear()

    def export_text(self) -> str:
        return export_filter(self._rules)

    def set_file_path(self, path: str) -> None:
        self._file_path = path

    # ------------------------------------------------------------------
    # Dirty tracking
    # ------------------------------------------------------------------

    def mark_dirty(self) -> None:
        self._dirty = True

    def clear_dirty(self) -> None:
        self._dirty = False

    # ------------------------------------------------------------------
    # Command execution  (v0.5.0 — UI must use this)
    # ------------------------------------------------------------------

    def execute(self, cmd) -> None:
        """Run *cmd*, push it onto the undo stack, clear the redo stack."""
        cmd.execute()
        self._undo_stack.append(cmd)
        self._redo_stack.clear()
        self._dirty = True

    def undo(self) -> None:
        """Pop the undo stack and reverse the last command."""
        if not self._undo_stack:
            return
        cmd = self._undo_stack.pop()
        cmd.undo()
        self._redo_stack.append(cmd)
        self._dirty = True

    def redo(self) -> None:
        """Pop the redo stack and re-apply the command."""
        if not self._redo_stack:
            return
        cmd = self._redo_stack.pop()
        cmd.redo()
        self._undo_stack.append(cmd)
        self._dirty = True

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def peek_undo_command(self):
        """Return the command that would be undone next, or None.
        Does not modify the stack.
        """
        return self._undo_stack[-1] if self._undo_stack else None

    def peek_redo_command(self):
        """Return the command that would be redone next, or None.
        Does not modify the stack.
        """
        return self._redo_stack[-1] if self._redo_stack else None

    # ------------------------------------------------------------------
    # Rule mutation primitives
    # (Called by Command objects — UI layer must use execute() instead.)
    # ------------------------------------------------------------------

    def insert_rule(self, index: int, rule: FilterRule) -> None:
        self._rules.insert(index, rule)
        self._dirty = True

    def remove_rule(self, index: int) -> None:
        self._rules.pop(index)
        self._dirty = True

    def duplicate_rule(self, index: int) -> int:
        """Deep-copy rule at *index*, insert after it, return new index."""
        dup = copy.deepcopy(self._rules[index])
        dup.pre_lines = [""]
        new_index = index + 1
        self._rules.insert(new_index, dup)
        self._dirty = True
        return new_index

    def update_rule(self, index: int, rule: FilterRule) -> None:
        self._rules[index] = rule
        self._dirty = True

    def move_rule(self, from_index: int, to_index: int) -> None:
        """Move rule at from_index to to_index.

        __TAIL__ protection (all violations are silently ignored):
          - Cannot move the __TAIL__ sentinel (from_index pointing to it)
          - to_index is clamped to stay before __TAIL__
          - from_index == to_index after clamping → no-op
        """
        n = len(self._rules)
        if n == 0:
            return
        has_tail = self._rules[-1].action == "__TAIL__"
        max_real = n - 1 if has_tail else n   # valid real indices: [0, max_real)

        if not (0 <= from_index < max_real):
            return
        if self._rules[from_index].action == "__TAIL__":
            return

        to_index = max(0, min(to_index, max_real - 1))
        if from_index == to_index:
            return

        rule = self._rules.pop(from_index)
        self._rules.insert(to_index, rule)
        self._dirty = True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def tail_insert_pos(self) -> int:
        """Index at which new rules should be appended (before __TAIL__)."""
        if self._rules and self._rules[-1].action == "__TAIL__":
            return len(self._rules) - 1
        return len(self._rules)
