import copy
from core.models import FilterRule
from parser.filter_parser import parse_filter
from parser.filter_exporter import export_filter


class FilterDocument:
    """Owns the complete state of one open .filter file.

    MainWindow talks only to FilterDocument; it never calls the parser or
    exporter directly.  All mutation goes through this class so that a
    future Command pattern (Undo/Redo) can intercept changes here without
    touching the UI layer.
    """

    def __init__(self):
        self._rules: list[FilterRule] = []
        self._file_path: str = ""
        self._dirty: bool = False

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

    def load_from_text(self, text: str, file_path: str = ""):
        self._rules = parse_filter(text)
        self._file_path = file_path
        self._dirty = False

    def export_text(self) -> str:
        return export_filter(self._rules)

    def set_file_path(self, path: str):
        self._file_path = path

    # ------------------------------------------------------------------
    # Dirty tracking
    # ------------------------------------------------------------------

    def mark_dirty(self):
        self._dirty = True

    def clear_dirty(self):
        self._dirty = False

    # ------------------------------------------------------------------
    # Rule mutations
    # (Each method marks the document dirty so callers don't have to.)
    # ------------------------------------------------------------------

    def insert_rule(self, index: int, rule: FilterRule):
        self._rules.insert(index, rule)
        self._dirty = True

    def remove_rule(self, index: int):
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

    def update_rule(self, index: int, rule: FilterRule):
        """Replace rule at *index* (the rule object is edited in-place by the
        editor widget, but this call signals that a change has occurred)."""
        self._rules[index] = rule
        self._dirty = True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def tail_insert_pos(self) -> int:
        """Index at which new rules should be appended (before __TAIL__)."""
        if self._rules and self._rules[-1].action == "__TAIL__":
            return len(self._rules) - 1
        return len(self._rules)
