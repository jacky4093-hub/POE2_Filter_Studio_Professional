"""NavigationSearchController — P12.3

Pure-Python controller that manages the nav-bar search state
(Ctrl+F / F3 / Shift+F3).  Zero Qt dependency.

Responsibilities:
  - Run a new search over rules using core.search.search_rules
  - Apply an optional category filter to the raw results
  - Track the result list and cursor position
  - Advance / retreat the cursor with wrap-around
  - Refresh the results while preserving the cursor position when possible
  - Reset all state

What stays in MainWindow:
  - Calling Qt widget methods (set_highlights, set_count, navigate_to, …)
  - The facade methods whose signatures the test suite depends on

Public API:
    SearchState       — frozen snapshot of current search state (dataclass)
    NavigationSearchController
        run_search(rules, text, category_filter_fn=None) -> SearchState
        next()  -> SearchState
        prev()  -> SearchState
        refresh(rules, text, category_filter_fn=None)  -> SearchState
        reset() -> SearchState

        # read-only convenience properties (mirror the active SearchState)
        results      -> list[int]
        cursor       -> int
        current_real -> int
        has_results  -> bool
        state        -> SearchState
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from core.search import search_rules, SearchQuery


@dataclass
class SearchState:
    """Immutable snapshot of a single search step."""

    results: list[int] = field(default_factory=list)
    cursor:  int       = -1

    # -----------------------------------------------------------------------
    # Derived read-only properties
    # -----------------------------------------------------------------------

    @property
    def has_results(self) -> bool:
        return bool(self.results)

    @property
    def current_real(self) -> int:
        """Real-index of the cursor rule, or -1 when there are no results."""
        if self.cursor < 0 or not self.results:
            return -1
        return self.results[self.cursor]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def position(self) -> int:
        """1-based cursor position for display (0 when there are no results)."""
        if self.cursor < 0 or not self.results:
            return 0
        return self.cursor + 1


# Type alias for the optional category-filter callable
_CategoryFilterFn = Callable[[list[int]], list[int]] | None


class NavigationSearchController:
    """Manages nav-bar search state without touching any Qt widget."""

    def __init__(self) -> None:
        self._state = SearchState()

    # -----------------------------------------------------------------------
    # Read-only properties (delegates to active SearchState)
    # -----------------------------------------------------------------------

    @property
    def state(self) -> SearchState:
        return self._state

    @property
    def results(self) -> list[int]:
        return list(self._state.results)

    @property
    def cursor(self) -> int:
        return self._state.cursor

    @property
    def current_real(self) -> int:
        return self._state.current_real

    @property
    def has_results(self) -> bool:
        return self._state.has_results

    # -----------------------------------------------------------------------
    # Mutating operations
    # -----------------------------------------------------------------------

    def run_search(
        self,
        rules: list,
        text: str,
        category_filter_fn: _CategoryFilterFn = None,
    ) -> SearchState:
        """Execute a fresh search and reset cursor to 0."""
        if not text or not text.strip():
            self._state = SearchState()
            return self._state

        raw = search_rules(rules, SearchQuery(text=text))
        if category_filter_fn is not None:
            raw = category_filter_fn(raw)

        if not raw:
            self._state = SearchState(results=[], cursor=-1)
            return self._state

        self._state = SearchState(results=raw, cursor=0)
        return self._state

    def next(self) -> SearchState:
        """Advance cursor by one (wraps at end)."""
        if not self._state.results:
            return self._state
        new_cursor = (self._state.cursor + 1) % len(self._state.results)
        self._state = SearchState(results=self._state.results, cursor=new_cursor)
        return self._state

    def prev(self) -> SearchState:
        """Retreat cursor by one (wraps at beginning)."""
        if not self._state.results:
            return self._state
        new_cursor = (self._state.cursor - 1) % len(self._state.results)
        self._state = SearchState(results=self._state.results, cursor=new_cursor)
        return self._state

    def refresh(
        self,
        rules: list,
        text: str,
        category_filter_fn: _CategoryFilterFn = None,
    ) -> SearchState:
        """Re-run search over (possibly changed) rules.

        Tries to preserve the cursor at the same real_index; falls back to 0
        if the previous match no longer exists in the new results.
        """
        if not text or not text.strip():
            self._state = SearchState()
            return self._state

        old_real = self._state.current_real

        raw = search_rules(rules, SearchQuery(text=text))
        if category_filter_fn is not None:
            raw = category_filter_fn(raw)

        if not raw:
            self._state = SearchState(results=[], cursor=-1)
            return self._state

        new_cursor = raw.index(old_real) if old_real in raw else 0
        self._state = SearchState(results=raw, cursor=new_cursor)
        return self._state

    def reset(self) -> SearchState:
        """Clear all search state."""
        self._state = SearchState()
        return self._state
