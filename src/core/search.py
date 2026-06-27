"""Search Engine — v0.8.0

Pure-function search over a FilterRule list. Zero Qt dependency.

Public API:
    SearchQuery   — dataclass describing a search request
    search_rules  — pure function: list[FilterRule] × SearchQuery → list[int]

Design contract:
    • search_rules() never raises
    • search_rules() never modifies any rule
    • __TAIL__ rules are always excluded from results
    • Returns [] when query.text is empty / whitespace
    • Results are in ascending real_index order

Future extensibility:
    SearchQuery fields (case_sensitive, field_filter) can be added later.
    search_rules() can grow structured-query branches without breaking callers.
    Structured patterns to support in future versions:
        "action:Hide"         → rule.action == "Hide"
        "Class=Currency"      → conditions key=="Class", value contains "Currency"
        "SetFontSize>40"      → actions key=="SetFontSize", int(value) > 40
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SearchQuery:
    text:           str  = ""
    case_sensitive: bool = False


def search_rules(rules: list, query: SearchQuery) -> list[int]:
    """Return real_indices of all rules matching *query*, in ascending order.

    Pure function — guaranteed:
      - Never raises (broken rules are silently skipped)
      - Never modifies any element of *rules*
      - __TAIL__ sentinel always excluded
      - Returns [] when query.text is empty or whitespace
    """
    needle = query.text.strip()
    if not needle:
        return []

    if not query.case_sensitive:
        needle = needle.lower()

    results: list[int] = []
    for real_idx, rule in enumerate(rules):
        try:
            if rule.action == "__TAIL__":
                continue
            if _matches(rule, needle, query.case_sensitive):
                results.append(real_idx)
        except Exception:
            pass  # never let a malformed rule crash search

    return results


# ---------------------------------------------------------------------------
# Internal helpers — pure, never raise
# ---------------------------------------------------------------------------

def _hit(s: str, needle: str, case_sensitive: bool) -> bool:
    """Return True if *needle* appears in *s* (respecting case_sensitive)."""
    if not isinstance(s, str) or not s:
        return False
    haystack = s if case_sensitive else s.lower()
    return needle in haystack


def _matches(rule, needle: str, case_sensitive: bool) -> bool:
    """Return True if any searchable field in *rule* contains *needle*."""
    # action
    if _hit(rule.action, needle, case_sensitive):
        return True

    # conditions: [[key, value], ...]
    for pair in rule.conditions:
        if len(pair) >= 1 and _hit(str(pair[0]), needle, case_sensitive):
            return True
        if len(pair) >= 2 and _hit(str(pair[1]), needle, case_sensitive):
            return True

    # actions: [[key, value], ...]
    for pair in rule.actions:
        if len(pair) >= 1 and _hit(str(pair[0]), needle, case_sensitive):
            return True
        if len(pair) >= 2 and _hit(str(pair[1]), needle, case_sensitive):
            return True

    # inline_comment
    if _hit(rule.inline_comment, needle, case_sensitive):
        return True

    # pre_lines (block comments / blank lines before the rule)
    for line in rule.pre_lines:
        if _hit(str(line), needle, case_sensitive):
            return True

    # unknown_lines (unrecognised directives preserved verbatim)
    for line in rule.unknown_lines:
        if _hit(str(line), needle, case_sensitive):
            return True

    return False
