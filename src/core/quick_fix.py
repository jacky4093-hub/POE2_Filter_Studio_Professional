"""Quick Fix — P16.4 Validation Quick Fix Foundation

Pure module; no UI or Qt imports.

Public API
----------
QuickFix         — dataclass describing one safe, auto-applicable fix
get_quick_fixes  — derive available fixes from a (rule, issue) pair
apply_quick_fix  — return a new FilterRule with the fix applied

Supported fixes (low-risk, deterministic):
  SetFontSize      — clamp integer value to [1, 45]  (non-integer → no fix)
  SetTextColor /
  SetBorderColor /
  SetBackgroundColor — clamp each channel to [0, 255]
                       (wrong part count or non-integer → no fix)
  PlayAlertSound   — clamp volume to [0, 300] when ID is already valid
                     (invalid ID, non-integer, or format error → no fix)
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from core.models import FilterRule
from core.validator import ValidationIssue, ValidationSeverity


_COLOR_KEYS = frozenset({
    "settextcolor",
    "setbordercolor",
    "setbackgroundcolor",
})


# ─────────────────────────────────────────────────────────────────────────────
# Public types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class QuickFix:
    """A safe, one-click fix for a single ValidationIssue.

    Attributes:
        label      — Button label shown in the UI (e.g. "修正為 45").
        field      — The action key to update (e.g. "SetFontSize").
        new_value  — The replacement value string (e.g. "45").
    """
    label:     str
    field:     str
    new_value: str


# ─────────────────────────────────────────────────────────────────────────────
# Internal fix-generators (one per action type)
# ─────────────────────────────────────────────────────────────────────────────

def _fontsize_fixes(key: str, value: str) -> list[QuickFix]:
    try:
        size = int(value.strip())
    except ValueError:
        return []  # non-integer → not safe to auto-fix
    if 1 <= size <= 45:
        return []  # already valid
    clamped = max(1, min(45, size))
    return [QuickFix(label=f"修正為 {clamped}", field=key, new_value=str(clamped))]


def _color_fixes(key: str, value: str) -> list[QuickFix]:
    parts = value.strip().split()
    if not (3 <= len(parts) <= 4):
        return []  # wrong number of channels → not safe
    try:
        channels = [int(p) for p in parts]
    except ValueError:
        return []  # non-integer → not safe
    clamped = [max(0, min(255, ch)) for ch in channels]
    if clamped == channels:
        return []  # no out-of-range channel
    new_val = " ".join(str(c) for c in clamped)
    return [QuickFix(label="色彩值修正至 0–255", field=key, new_value=new_val)]


def _alert_fixes(key: str, value: str) -> list[QuickFix]:
    parts = value.strip().split()
    if len(parts) < 2:
        return []  # format error → not safe
    try:
        sound_id = int(parts[0])
        volume   = int(parts[1])
    except ValueError:
        return []  # non-integer → not safe
    if not (1 <= sound_id <= 16):
        return []  # invalid ID → not safe to guess correct ID
    if 0 <= volume <= 300:
        return []  # volume already valid
    clamped_vol = max(0, min(300, volume))
    new_val = f"{sound_id} {clamped_vol}"
    return [QuickFix(
        label=f"音量修正為 {clamped_vol}",
        field=key,
        new_value=new_val,
    )]


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_quick_fixes(rule: FilterRule, issue: ValidationIssue) -> list[QuickFix]:
    """Return available quick fixes for *issue* in the context of *rule*.

    Returns an empty list when no safe automatic fix exists.
    Typically returns 0 or 1 fix; the list form is for API flexibility.
    """
    field     = issue.field
    key_lower = field.lower()

    for item in rule.actions:
        if len(item) < 2:
            continue
        if str(item[0]) != field:
            continue
        value = str(item[1])
        if key_lower == "setfontsize":
            return _fontsize_fixes(field, value)
        if key_lower in _COLOR_KEYS:
            return _color_fixes(field, value)
        if key_lower == "playalertsound":
            return _alert_fixes(field, value)
        return []

    return []


def apply_quick_fix(rule: FilterRule, fix: QuickFix) -> FilterRule:
    """Return a deep copy of *rule* with *fix* applied.

    Updates the value of the first action whose key matches ``fix.field``.
    If no matching action is found, returns an unchanged copy.
    """
    new_rule = copy.deepcopy(rule)
    for i, item in enumerate(new_rule.actions):
        if len(item) >= 2 and str(item[0]) == fix.field:
            new_rule.actions[i] = [item[0], fix.new_value]
            return new_rule
    return new_rule
