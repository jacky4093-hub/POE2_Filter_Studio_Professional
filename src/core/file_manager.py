"""FilterFileManager — v2.5.0

Handles all file-system I/O for a single .filter document.
Tracks current path and dirty state independently of FilterDocument so that
tests can verify file-layer behaviour without standing up the full UI.

Public API
----------
    mgr = FilterFileManager()

    text = mgr.open(path)          # read + set current_path + mark_clean
    text = mgr.load(path)          # read-only, does NOT update state

    mgr.save(text)  -> bool        # write to current_path; False if no path
    mgr.save_as(text, path)        # write to path, update current_path

    mgr.mark_dirty()
    mgr.mark_clean()

    text = mgr.serialize_rules(rules)   # export_filter wrapper

Properties
----------
    mgr.current_path   : str
    mgr.is_dirty       : bool
"""

from __future__ import annotations

from parser.filter_exporter import export_filter


class FilterFileManager:
    """File-system facade for one open .filter document."""

    def __init__(self) -> None:
        self._current_path: str  = ""
        self._is_dirty:     bool = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_path(self) -> str:
        return self._current_path

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    # ------------------------------------------------------------------
    # Dirty-flag management
    # ------------------------------------------------------------------

    def mark_dirty(self) -> None:
        self._is_dirty = True

    def mark_clean(self) -> None:
        self._is_dirty = False

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def load(self, path: str) -> str:
        """Read and return file text.  Raises OSError on failure.
        Does NOT update current_path or dirty state.
        """
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()

    def open(self, path: str) -> str:
        """Read file, update current_path, and mark clean.

        Equivalent to load() + set current_path + mark_clean().
        Raises OSError on failure (current_path unchanged).
        """
        text = self.load(path)   # raises before state is mutated
        self._current_path = path
        self._is_dirty = False
        return text

    def save(self, text: str) -> bool:
        """Write *text* to current_path.

        Returns False without writing if current_path is not set.
        Marks clean on success.
        """
        if not self._current_path:
            return False
        self._write(self._current_path, text)
        self._is_dirty = False
        return True

    def save_as(self, text: str, path: str) -> None:
        """Write *text* to *path*, update current_path, and mark clean."""
        self._write(path, text)
        self._current_path = path
        self._is_dirty = False

    # ------------------------------------------------------------------
    # Serialization helper
    # ------------------------------------------------------------------

    def serialize_rules(self, rules: list) -> str:
        """Convert a list of FilterRule objects to filter text.

        Delegates to export_filter; preserves pre_lines, unknown_lines,
        inline_comment, and disabled-rule formatting.
        """
        return export_filter(rules)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _write(path: str, text: str) -> None:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
