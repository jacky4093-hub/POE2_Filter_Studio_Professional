"""QuickFilterController — P12.4

Manages the left-column Quick Filter (SearchBarWidget + RuleCardBrowser
interaction) that was extracted from MainWindow._on_filter_search_changed,
._on_filter_search_clear, and ._update_filter_search_count.

Zero Qt import: the controller works through a structural Protocol so it
can be tested with plain mock objects.

Responsibilities:
  - apply_filter(query, options)  — push search filter to browser, refresh count,
                                    clear editor if selected rule is no longer visible
  - clear_filter()                — remove filter from browser, refresh count
  - refresh_count()               — read visible/total counts and update the search bar label

What stays in MainWindow:
  - All three facade methods (_on_filter_search_changed, _on_filter_search_clear,
    _update_filter_search_count) whose names are used by signal connections and tests
  - Widget ownership and layout
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class _RuleCardBrowserProtocol(Protocol):
    def set_search_filter(self, query: str, options: dict) -> None: ...
    def clear_search_filter(self) -> None: ...
    def get_visible_count(self) -> int: ...
    def get_total_count(self) -> int: ...
    def is_rule_visible(self, index: int) -> bool: ...


@runtime_checkable
class _FilterSearchBarProtocol(Protocol):
    def set_result_count(self, visible_count: int, total_count: int) -> None: ...


class _WindowProtocol(Protocol):
    rule_card_browser: _RuleCardBrowserProtocol
    filter_search_bar: _FilterSearchBarProtocol
    _selected_index:   int

    def _clear_rule_ui(self) -> None: ...


class QuickFilterController:
    """Coordinates quick-filter state between SearchBarWidget and RuleCardBrowser."""

    def __init__(self, window: _WindowProtocol) -> None:
        self._window = window

    # ------------------------------------------------------------------
    # Public API (called by MainWindow facade methods)
    # ------------------------------------------------------------------

    def apply_filter(self, query: str, options: dict) -> None:
        """Apply *query*/*options* to the browser, refresh the count label,
        and clear the rule editor if the currently selected rule is no longer visible.
        """
        self._window.rule_card_browser.set_search_filter(query, options)
        self.refresh_count()
        if (
            self._window._selected_index >= 0
            and not self._window.rule_card_browser.is_rule_visible(self._window._selected_index)
        ):
            self._window._clear_rule_ui()

    def clear_filter(self) -> None:
        """Remove the search filter from the browser and refresh the count label."""
        self._window.rule_card_browser.clear_search_filter()
        self.refresh_count()

    def refresh_count(self) -> None:
        """Read visible/total counts from the browser and push them to the search bar."""
        visible = self._window.rule_card_browser.get_visible_count()
        total   = self._window.rule_card_browser.get_total_count()
        self._window.filter_search_bar.set_result_count(visible, total)
