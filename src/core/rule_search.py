"""rule_search.py — pure rule search/filter functions (no Qt dependency)

Public API:
    build_search_text(rule, options) -> str
    rule_matches_query(rule, query, options) -> bool
    filter_rules_by_query(rules, query, options) -> list[int]

Supports both dict rules and FilterRule dataclass objects.
options dict keys:
    match_case (bool)  — case-sensitive match (default False)
    raw_text   (bool)  — include unknown_lines / raw preview in search
    action     (bool)  — include Show/Hide action keyword
    class      (bool)  — include Class condition values
    basetype   (bool)  — include BaseType condition values
When all option flags are False (default), all fields are included.
When one or more flags are True, only flagged fields are searched.
"""

from __future__ import annotations

from typing import Any


def _get(rule: Any, attr: str, default: Any = "") -> Any:
    if isinstance(rule, dict):
        return rule.get(attr, default)
    return getattr(rule, attr, default)


def build_search_text(rule: Any, options: dict | None = None) -> str:
    """Build a flat searchable text string from a rule."""
    options = options or {}

    # Determine which field groups to include.
    # If no specific flag is set, include everything.
    want_action   = options.get("action",   False)
    want_class    = options.get("class",    False)
    want_basetype = options.get("basetype", False)
    want_raw      = options.get("raw_text", False)
    # "action" option also covers the Show/Hide keyword
    specific_flags = want_action or want_class or want_basetype or want_raw
    include_all = not specific_flags

    parts: list[str] = []

    # --- action / enabled ---
    if include_all or want_action:
        action = _get(rule, "action", "")
        if action and action != "__TAIL__":
            parts.append(action)
        enabled = _get(rule, "enabled", True)
        if not enabled:
            parts.append("disabled")

    # --- conditions ---
    conditions = _get(rule, "conditions", [])
    for item in conditions:
        if not (isinstance(item, (list, tuple)) and len(item) >= 2):
            continue
        key, val = str(item[0]), str(item[1])
        key_low = key.lower()

        if include_all:
            parts.append(key)
            parts.append(val)
        else:
            if want_class and key_low == "class":
                parts.append(val)
            if want_basetype and key_low == "basetype":
                parts.append(val)

    # --- actions (SetTextColor, PlayAlertSound, etc.) ---
    actions = _get(rule, "actions", [])
    for item in actions:
        if not (isinstance(item, (list, tuple)) and len(item) >= 2):
            continue
        key, val = str(item[0]), str(item[1])
        if include_all:
            parts.append(key)
            parts.append(val)

    # --- unknown_lines / raw preview ---
    if include_all or want_raw:
        unknown = _get(rule, "unknown_lines", [])
        for line in unknown:
            parts.append(str(line))

        for attr in ("raw_preview", "raw_lines", "raw_text"):
            raw = _get(rule, attr, None)
            if raw:
                if isinstance(raw, list):
                    parts.extend(str(x) for x in raw)
                else:
                    parts.append(str(raw))

    return " ".join(parts)


def rule_matches_query(rule: Any, query: str, options: dict | None = None) -> bool:
    """Return True if *rule* contains *query* in its searchable text."""
    if not query or not query.strip():
        return True

    options = options or {}
    match_case = options.get("match_case", False)

    text = build_search_text(rule, options)
    if match_case:
        return query in text
    return query.lower() in text.lower()


def filter_rules_by_query(
    rules: list[Any], query: str, options: dict | None = None
) -> list[int]:
    """Return indices of rules that match *query*.

    Returns all indices when query is empty/whitespace.
    """
    if not query or not query.strip():
        return list(range(len(rules)))

    return [i for i, rule in enumerate(rules) if rule_matches_query(rule, query, options)]
