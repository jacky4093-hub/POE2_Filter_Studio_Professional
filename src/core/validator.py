"""Filter rule validation — P16.1 Validation Foundation

Public API
----------
ValidationSeverity  — INFO / WARNING / ERROR
ValidationIssue     — dataclass: severity, field, message, rule_index
validate_rule(rule)         -> list[ValidationIssue]
validate_document(document) -> list[ValidationIssue]

Design notes
------------
- Pure functions; no UI imports; no side effects.
- validate_rule() returns issues with rule_index = -1.
- validate_document() stamps the correct rule_index on each issue.
- Disabled rules have every issue downgraded one level
  (ERROR → WARNING, WARNING → INFO).
- Never blocks saving; callers decide what to do with the issues.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.models import FilterRule


# ─────────────────────────────────────────────────────────────────────────────
# Public types
# ─────────────────────────────────────────────────────────────────────────────

class ValidationSeverity(Enum):
    INFO    = "info"
    WARNING = "warning"
    ERROR   = "error"


@dataclass
class ValidationIssue:
    severity:   ValidationSeverity
    field:      str
    message:    str
    rule_index: int = -1


# ─────────────────────────────────────────────────────────────────────────────
# Internal constants — kept in sync with rule_detail_editor.py constants
# ─────────────────────────────────────────────────────────────────────────────

_COLOR_KEYS = frozenset({
    "settextcolor",
    "setbordercolor",
    "setbackgroundcolor",
})

_MM_SIZES = frozenset({"0", "1", "2"})

_MM_COLORS = frozenset({
    "Red", "Green", "Blue", "Brown", "White", "Yellow",
    "Cyan", "Grey", "Orange", "Pink", "Purple",
})

_MM_SHAPES = frozenset({
    "Circle", "Diamond", "Hexagon", "Square", "Star",
    "Triangle", "Cross", "Moon", "Raindrop", "Kite",
    "Pentagon", "UpsideDownHouse",
})


# ─────────────────────────────────────────────────────────────────────────────
# Internal checker helpers — each returns one ValidationIssue or None
# ─────────────────────────────────────────────────────────────────────────────

def _check_fontsize(value: str) -> ValidationIssue | None:
    try:
        size = int(value.strip())
    except ValueError:
        return ValidationIssue(
            severity=ValidationSeverity.WARNING,
            field="SetFontSize",
            message=f"SetFontSize 值無效：{value!r}",
        )
    if not (1 <= size <= 45):
        return ValidationIssue(
            severity=ValidationSeverity.WARNING,
            field="SetFontSize",
            message=f"SetFontSize {size} 超出建議範圍（1–45）",
        )
    return None


def _check_color(key: str, value: str) -> ValidationIssue | None:
    """Validate 'R G B' or 'R G B A' colour strings (each 0–255)."""
    parts = value.strip().split()
    if not (3 <= len(parts) <= 4):
        return ValidationIssue(
            severity=ValidationSeverity.ERROR,
            field=key,
            message=f"{key} 格式錯誤（需要 R G B 或 R G B A，各值 0–255）",
        )
    try:
        channels = [int(p) for p in parts]
    except ValueError:
        return ValidationIssue(
            severity=ValidationSeverity.ERROR,
            field=key,
            message=f"{key} 包含非整數值：{value!r}",
        )
    for ch in channels:
        if not (0 <= ch <= 255):
            return ValidationIssue(
                severity=ValidationSeverity.ERROR,
                field=key,
                message=f"{key} 色彩值超出範圍（0–255）：{value!r}",
            )
    return None


def _check_alert_sound(value: str) -> ValidationIssue | None:
    """Validate 'ID Volume' (ID 1–16, Volume 0–300)."""
    parts = value.strip().split()
    if len(parts) < 2:
        return ValidationIssue(
            severity=ValidationSeverity.WARNING,
            field="PlayAlertSound",
            message=f"PlayAlertSound 格式錯誤（需要 ID 音量）：{value!r}",
        )
    try:
        sound_id = int(parts[0])
        volume   = int(parts[1])
    except ValueError:
        return ValidationIssue(
            severity=ValidationSeverity.WARNING,
            field="PlayAlertSound",
            message=f"PlayAlertSound 包含非整數值：{value!r}",
        )
    if not (1 <= sound_id <= 16):
        return ValidationIssue(
            severity=ValidationSeverity.WARNING,
            field="PlayAlertSound",
            message=f"PlayAlertSound 音效 ID 應為 1–16，得到 {sound_id}",
        )
    if not (0 <= volume <= 300):
        return ValidationIssue(
            severity=ValidationSeverity.WARNING,
            field="PlayAlertSound",
            message=f"PlayAlertSound 音量應為 0–300，得到 {volume}",
        )
    return None


def _check_minimap(value: str) -> ValidationIssue | None:
    """Validate 'Size Color Shape' minimap icon."""
    parts = value.strip().split()
    if len(parts) < 3:
        return ValidationIssue(
            severity=ValidationSeverity.WARNING,
            field="MinimapIcon",
            message=f"MinimapIcon 格式錯誤（需要 大小 顏色 形狀）：{value!r}",
        )
    size, color, shape = parts[0], parts[1], parts[2]
    errors: list[str] = []
    if size not in _MM_SIZES:
        errors.append(f"大小 {size!r} 無效（應為 0/1/2）")
    if color not in _MM_COLORS:
        errors.append(f"顏色 {color!r} 無效")
    if shape not in _MM_SHAPES:
        errors.append(f"形狀 {shape!r} 無效")
    if errors:
        return ValidationIssue(
            severity=ValidationSeverity.WARNING,
            field="MinimapIcon",
            message="MinimapIcon：" + "；".join(errors),
        )
    return None


def _check_empty(rule: FilterRule) -> ValidationIssue | None:
    """Return INFO if the rule has no conditions and no managed actions."""
    if not rule.conditions and not rule.actions:
        return ValidationIssue(
            severity=ValidationSeverity.INFO,
            field="rule",
            message="規則無任何條件與動作",
        )
    return None


def _downgrade(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    """Downgrade each issue one severity level (for disabled rules)."""
    result: list[ValidationIssue] = []
    for iss in issues:
        if iss.severity == ValidationSeverity.ERROR:
            result.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field=iss.field,
                message=f"[停用規則] {iss.message}",
                rule_index=iss.rule_index,
            ))
        elif iss.severity == ValidationSeverity.WARNING:
            result.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                field=iss.field,
                message=f"[停用規則] {iss.message}",
                rule_index=iss.rule_index,
            ))
        else:
            result.append(iss)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def validate_rule(rule: FilterRule) -> list[ValidationIssue]:
    """Return validation issues for a single FilterRule.

    Returned issues have rule_index == -1.  The caller (usually
    validate_document) is responsible for stamping the correct index.

    __TAIL__ rules (synthetic trailing-content placeholders used by the
    parser) are silently skipped and always return an empty list.
    """
    if rule.action == "__TAIL__":
        return []

    issues: list[ValidationIssue] = []

    # Structure check: empty rule
    empty = _check_empty(rule)
    if empty is not None:
        issues.append(empty)

    # Per-action checks
    for item in rule.actions:
        if len(item) < 2:
            continue
        key, value = str(item[0]), str(item[1])
        key_lower = key.lower()

        if key_lower == "setfontsize":
            issue = _check_fontsize(value)
        elif key_lower in _COLOR_KEYS:
            issue = _check_color(key, value)
        elif key_lower == "playalertsound":
            issue = _check_alert_sound(value)
        elif key_lower == "minimapicon":
            issue = _check_minimap(value)
        else:
            issue = None

        if issue is not None:
            issues.append(issue)

    # Disabled rule: downgrade every issue one level
    if not rule.enabled:
        issues = _downgrade(issues)

    return issues


def validate_document(document) -> list[ValidationIssue]:
    """Return aggregated issues for all rules in *document*.

    *document* must expose a ``rules`` attribute (list[FilterRule]).
    Each returned issue's rule_index is set to the rule's position.
    """
    issues: list[ValidationIssue] = []
    for idx, rule in enumerate(document.rules):
        for iss in validate_rule(rule):
            issues.append(ValidationIssue(
                severity=iss.severity,
                field=iss.field,
                message=iss.message,
                rule_index=idx,
            ))
    return issues
