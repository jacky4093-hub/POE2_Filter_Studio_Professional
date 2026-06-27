"""Tests for core/validator.py — P16.1 Filter Validation Foundation"""

import pytest

from core.models import FilterRule
from core.validator import (
    ValidationSeverity,
    ValidationIssue,
    validate_rule,
    validate_document,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rule(
    action: str = "Show",
    enabled: bool = True,
    conditions: list | None = None,
    actions: list | None = None,
    pre_lines: list | None = None,
) -> FilterRule:
    return FilterRule(
        action=action,
        enabled=enabled,
        conditions=conditions or [],
        actions=actions or [],
        pre_lines=pre_lines or [],
        inline_comment="",
        unknown_lines=[],
    )


class _FakeDoc:
    """Minimal stand-in for FilterDocument (duck-typed)."""
    def __init__(self, rules: list[FilterRule]) -> None:
        self.rules = rules


# ---------------------------------------------------------------------------
# TestValidationSeverityEnum
# ---------------------------------------------------------------------------

class TestValidationSeverityEnum:

    def test_info_value(self):
        assert ValidationSeverity.INFO.value == "info"

    def test_warning_value(self):
        assert ValidationSeverity.WARNING.value == "warning"

    def test_error_value(self):
        assert ValidationSeverity.ERROR.value == "error"

    def test_three_members(self):
        assert len(list(ValidationSeverity)) == 3

    def test_ordering_comparable(self):
        members = list(ValidationSeverity)
        assert ValidationSeverity.INFO in members
        assert ValidationSeverity.WARNING in members
        assert ValidationSeverity.ERROR in members


# ---------------------------------------------------------------------------
# TestValidationIssueDataclass
# ---------------------------------------------------------------------------

class TestValidationIssueDataclass:

    def test_default_rule_index_is_minus_one(self):
        iss = ValidationIssue(ValidationSeverity.INFO, "rule", "msg")
        assert iss.rule_index == -1

    def test_explicit_rule_index(self):
        iss = ValidationIssue(ValidationSeverity.ERROR, "f", "m", rule_index=7)
        assert iss.rule_index == 7

    def test_equality(self):
        a = ValidationIssue(ValidationSeverity.WARNING, "SetFontSize", "msg")
        b = ValidationIssue(ValidationSeverity.WARNING, "SetFontSize", "msg")
        assert a == b

    def test_inequality_severity(self):
        a = ValidationIssue(ValidationSeverity.WARNING, "f", "msg")
        b = ValidationIssue(ValidationSeverity.ERROR,   "f", "msg")
        assert a != b

    def test_fields_accessible(self):
        iss = ValidationIssue(ValidationSeverity.ERROR, "SetTextColor", "bad")
        assert iss.severity == ValidationSeverity.ERROR
        assert iss.field    == "SetTextColor"
        assert iss.message  == "bad"


# ---------------------------------------------------------------------------
# TestValidRuleNoIssues
# ---------------------------------------------------------------------------

class TestValidRuleNoIssues:

    def test_empty_actions_no_issues_except_empty_rule(self):
        # An empty rule gives INFO (empty-rule issue), not WARNING/ERROR
        issues = validate_rule(_rule())
        assert all(i.severity == ValidationSeverity.INFO for i in issues)

    def test_fontsize_boundary_1(self):
        assert validate_rule(_rule(actions=[["SetFontSize", "1"]])) == []

    def test_fontsize_boundary_45(self):
        assert validate_rule(_rule(actions=[["SetFontSize", "45"]])) == []

    def test_valid_text_color_rgba(self):
        assert validate_rule(_rule(actions=[["SetTextColor", "255 200 0 255"]])) == []

    def test_valid_border_color_rgb(self):
        assert validate_rule(_rule(actions=[["SetBorderColor", "0 0 0"]])) == []

    def test_valid_bg_color(self):
        assert validate_rule(_rule(actions=[["SetBackgroundColor", "100 100 100 200"]])) == []

    def test_valid_alert_sound_boundary_low(self):
        assert validate_rule(_rule(actions=[["PlayAlertSound", "1 0"]])) == []

    def test_valid_alert_sound_boundary_high(self):
        assert validate_rule(_rule(actions=[["PlayAlertSound", "16 300"]])) == []

    def test_valid_minimap_icon(self):
        assert validate_rule(_rule(actions=[["MinimapIcon", "1 Red Circle"]])) == []

    def test_unknown_action_key_no_issue(self):
        assert validate_rule(_rule(actions=[["CustomAction", "foo"]])) == []

    def test_all_valid_together(self):
        issues = validate_rule(_rule(
            conditions=[["Class", '"Currency"']],
            actions=[
                ["SetFontSize",       "40"],
                ["SetTextColor",      "255 200 0 255"],
                ["PlayAlertSound",    "3 200"],
                ["MinimapIcon",       "0 Yellow Star"],
            ],
        ))
        assert issues == []


# ---------------------------------------------------------------------------
# TestFontSizeValidation
# ---------------------------------------------------------------------------

class TestFontSizeValidation:

    def test_size_0_is_warning(self):
        issues = validate_rule(_rule(actions=[["SetFontSize", "0"]]))
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_size_46_is_warning(self):
        issues = validate_rule(_rule(actions=[["SetFontSize", "46"]]))
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_size_100_is_warning(self):
        issues = validate_rule(_rule(actions=[["SetFontSize", "100"]]))
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_nonnumeric_is_warning(self):
        issues = validate_rule(_rule(actions=[["SetFontSize", "large"]]))
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_field_name_is_setfontsize(self):
        issues = validate_rule(_rule(actions=[["SetFontSize", "0"]]))
        assert issues[0].field == "SetFontSize"

    def test_case_insensitive_key(self):
        issues = validate_rule(_rule(actions=[["setfontsize", "0"]]))
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_negative_is_warning(self):
        issues = validate_rule(_rule(actions=[["SetFontSize", "-1"]]))
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_float_string_is_warning(self):
        issues = validate_rule(_rule(actions=[["SetFontSize", "12.5"]]))
        assert issues[0].severity == ValidationSeverity.WARNING

    @pytest.mark.parametrize("size", range(1, 46))
    def test_valid_range_1_to_45(self, size):
        assert validate_rule(_rule(actions=[["SetFontSize", str(size)]])) == []


# ---------------------------------------------------------------------------
# TestColorValidation
# ---------------------------------------------------------------------------

class TestColorValidation:

    @pytest.mark.parametrize("key", [
        "SetTextColor", "SetBorderColor", "SetBackgroundColor",
    ])
    def test_too_few_parts_is_error(self, key):
        issues = validate_rule(_rule(actions=[[key, "255 0"]]))
        assert issues[0].severity == ValidationSeverity.ERROR

    @pytest.mark.parametrize("key", [
        "SetTextColor", "SetBorderColor", "SetBackgroundColor",
    ])
    def test_five_parts_is_error(self, key):
        issues = validate_rule(_rule(actions=[[key, "255 0 0 255 99"]]))
        assert issues[0].severity == ValidationSeverity.ERROR

    def test_value_256_is_error(self):
        issues = validate_rule(_rule(actions=[["SetTextColor", "256 0 0 255"]]))
        assert issues[0].severity == ValidationSeverity.ERROR

    def test_negative_value_is_error(self):
        issues = validate_rule(_rule(actions=[["SetTextColor", "-1 0 0 255"]]))
        assert issues[0].severity == ValidationSeverity.ERROR

    def test_nonnumeric_is_error(self):
        issues = validate_rule(_rule(actions=[["SetTextColor", "red green blue"]]))
        assert issues[0].severity == ValidationSeverity.ERROR

    def test_field_preserved_in_issue(self):
        issues = validate_rule(_rule(actions=[["SetBorderColor", "999 0 0"]]))
        assert issues[0].field == "SetBorderColor"

    def test_lowercase_key_still_checked(self):
        issues = validate_rule(_rule(actions=[["settextcolor", "999 0 0"]]))
        assert issues[0].severity == ValidationSeverity.ERROR

    def test_boundary_0_all_channels_valid(self):
        assert validate_rule(_rule(actions=[["SetTextColor", "0 0 0 0"]])) == []

    def test_boundary_255_all_channels_valid(self):
        assert validate_rule(_rule(actions=[["SetTextColor", "255 255 255 255"]])) == []

    def test_rgb_three_parts_valid(self):
        assert validate_rule(_rule(actions=[["SetTextColor", "128 64 32"]])) == []


# ---------------------------------------------------------------------------
# TestAlertSoundValidation
# ---------------------------------------------------------------------------

class TestAlertSoundValidation:

    def test_id_0_is_warning(self):
        issues = validate_rule(_rule(actions=[["PlayAlertSound", "0 200"]]))
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_id_17_is_warning(self):
        issues = validate_rule(_rule(actions=[["PlayAlertSound", "17 200"]]))
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_vol_301_is_warning(self):
        issues = validate_rule(_rule(actions=[["PlayAlertSound", "1 301"]]))
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_only_id_is_warning(self):
        issues = validate_rule(_rule(actions=[["PlayAlertSound", "1"]]))
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_nonnumeric_is_warning(self):
        issues = validate_rule(_rule(actions=[["PlayAlertSound", "beep loud"]]))
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_field_name_playalertsound(self):
        issues = validate_rule(_rule(actions=[["PlayAlertSound", "0 200"]]))
        assert issues[0].field == "PlayAlertSound"

    def test_id_1_vol_0_valid(self):
        assert validate_rule(_rule(actions=[["PlayAlertSound", "1 0"]])) == []

    def test_id_16_vol_300_valid(self):
        assert validate_rule(_rule(actions=[["PlayAlertSound", "16 300"]])) == []

    def test_vol_negative_is_warning(self):
        issues = validate_rule(_rule(actions=[["PlayAlertSound", "1 -1"]]))
        assert issues[0].severity == ValidationSeverity.WARNING


# ---------------------------------------------------------------------------
# TestMinimapValidation
# ---------------------------------------------------------------------------

class TestMinimapValidation:

    def test_too_few_parts_is_warning(self):
        issues = validate_rule(_rule(actions=[["MinimapIcon", "1 Red"]]))
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_invalid_size_is_warning(self):
        issues = validate_rule(_rule(actions=[["MinimapIcon", "3 Red Circle"]]))
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_invalid_color_is_warning(self):
        issues = validate_rule(_rule(actions=[["MinimapIcon", "1 Silver Circle"]]))
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_invalid_shape_is_warning(self):
        issues = validate_rule(_rule(actions=[["MinimapIcon", "1 Red Octagon"]]))
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_all_invalid_one_combined_issue(self):
        issues = validate_rule(_rule(actions=[["MinimapIcon", "9 Silver Octagon"]]))
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_field_name_minimapicon(self):
        issues = validate_rule(_rule(actions=[["MinimapIcon", "9 Red Circle"]]))
        assert issues[0].field == "MinimapIcon"

    @pytest.mark.parametrize("size", ["0", "1", "2"])
    def test_all_valid_sizes(self, size):
        assert validate_rule(_rule(actions=[["MinimapIcon", f"{size} Red Circle"]])) == []

    def test_all_valid_minimap_icon(self):
        assert validate_rule(_rule(actions=[["MinimapIcon", "0 Yellow Star"]])) == []


# ---------------------------------------------------------------------------
# TestEmptyRuleValidation
# ---------------------------------------------------------------------------

class TestEmptyRuleValidation:

    def test_no_conditions_no_actions_is_info(self):
        issues = validate_rule(_rule())
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.INFO
        assert issues[0].field == "rule"

    def test_with_condition_no_empty_issue(self):
        issues = validate_rule(_rule(conditions=[["Class", '"Currency"']]))
        assert all(i.field != "rule" for i in issues)

    def test_with_action_no_empty_issue(self):
        issues = validate_rule(_rule(actions=[["SetFontSize", "32"]]))
        assert all(i.field != "rule" for i in issues)

    def test_empty_rule_with_pre_lines_still_info(self):
        issues = validate_rule(_rule(pre_lines=["# comment"]))
        assert any(i.field == "rule" for i in issues)

    def test_empty_rule_info_message_not_empty(self):
        issues = validate_rule(_rule())
        assert issues[0].message.strip() != ""


# ---------------------------------------------------------------------------
# TestDisabledRuleDowngrade
# ---------------------------------------------------------------------------

class TestDisabledRuleDowngrade:

    def test_error_becomes_warning_when_disabled(self):
        rule = _rule(enabled=False, actions=[["SetTextColor", "999 0 0 255"]])
        issues = validate_rule(rule)
        assert issues[0].severity == ValidationSeverity.WARNING

    def test_warning_becomes_info_when_disabled(self):
        rule = _rule(enabled=False, actions=[["SetFontSize", "100"]])
        issues = validate_rule(rule)
        assert issues[0].severity == ValidationSeverity.INFO

    def test_info_stays_info_when_disabled(self):
        rule = _rule(enabled=False)  # empty → INFO
        issues = validate_rule(rule)
        assert all(i.severity == ValidationSeverity.INFO for i in issues)

    def test_enabled_rule_keeps_error(self):
        rule = _rule(enabled=True, actions=[["SetTextColor", "999 0 0 255"]])
        issues = validate_rule(rule)
        assert issues[0].severity == ValidationSeverity.ERROR

    def test_disabled_message_contains_marker(self):
        rule = _rule(enabled=False, actions=[["SetTextColor", "999 0 0"]])
        issues = validate_rule(rule)
        assert "停用規則" in issues[0].message

    def test_disabled_no_error_severity_at_all(self):
        rule = _rule(enabled=False, actions=[
            ["SetTextColor", "999 0 0"],  # ERROR → WARNING
            ["SetFontSize",  "100"],      # WARNING → INFO
        ])
        issues = validate_rule(rule)
        severities = {i.severity for i in issues}
        assert ValidationSeverity.ERROR not in severities

    def test_disabled_multiple_downgrades(self):
        rule = _rule(enabled=False, actions=[
            ["SetTextColor",      "999 0 0"],
            ["SetBorderColor",    "0 999 0"],
            ["SetBackgroundColor", "0 0 999"],
        ])
        issues = validate_rule(rule)
        assert all(i.severity == ValidationSeverity.WARNING for i in issues)


# ---------------------------------------------------------------------------
# TestDocumentValidation
# ---------------------------------------------------------------------------

class TestDocumentValidation:

    def test_empty_document_no_issues(self):
        assert validate_document(_FakeDoc([])) == []

    def test_document_with_valid_rules_no_issues(self):
        rules = [
            _rule(actions=[["SetFontSize", "32"]]),
            _rule(conditions=[["Class", '"Currency"']]),
        ]
        assert validate_document(_FakeDoc(rules)) == []

    def test_document_sets_rule_index(self):
        rules = [
            _rule(actions=[["SetFontSize", "32"]]),  # valid → idx 0
            _rule(actions=[["SetFontSize", "0"]]),   # warning → idx 1
        ]
        issues = validate_document(_FakeDoc(rules))
        assert len(issues) == 1
        assert issues[0].rule_index == 1

    def test_document_aggregates_all_issues(self):
        rules = [
            _rule(actions=[["SetFontSize",   "0"]]),
            _rule(actions=[["SetTextColor",  "999 0 0"]]),
            _rule(actions=[["PlayAlertSound", "0 200"]]),
        ]
        issues = validate_document(_FakeDoc(rules))
        assert len(issues) == 3

    def test_document_rule_indices_match_positions(self):
        rules = [
            _rule(actions=[["SetFontSize", "0"]]),   # idx 0
            _rule(actions=[["SetFontSize", "32"]]),  # idx 1 — valid
            _rule(actions=[["SetFontSize", "50"]]),  # idx 2
        ]
        issues = validate_document(_FakeDoc(rules))
        indices = {i.rule_index for i in issues}
        assert indices == {0, 2}

    def test_document_rule_index_not_minus_one(self):
        rules = [_rule(actions=[["SetFontSize", "0"]])]
        issues = validate_document(_FakeDoc(rules))
        assert issues[0].rule_index == 0

    def test_document_with_real_filterdocument(self):
        from core.document import FilterDocument
        doc = FilterDocument()
        doc.load_from_text("Show\n    SetFontSize 99\n\n")
        issues = validate_document(doc)
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.WARNING
        assert issues[0].rule_index == 0

    def test_document_multi_rule_mixed(self):
        from core.document import FilterDocument
        doc = FilterDocument()
        doc.load_from_text(
            "Show\n    SetFontSize 99\n\n"
            "Show\n    SetTextColor 255 0 0 255\n\n"
            "Show\n    SetFontSize 0\n\n"
        )
        issues = validate_document(doc)
        # Expect warnings at indices 0 and 2
        warning_indices = {i.rule_index for i in issues}
        assert 0 in warning_indices
        assert 2 in warning_indices
        assert 1 not in warning_indices

    def test_document_severity_types_preserved(self):
        rules = [
            _rule(actions=[["SetTextColor", "999 0 0"]]),  # ERROR
        ]
        issues = validate_document(_FakeDoc(rules))
        assert issues[0].severity == ValidationSeverity.ERROR


# ---------------------------------------------------------------------------
# TestValidateRuleEdgeCases
# ---------------------------------------------------------------------------

class TestValidateRuleEdgeCases:

    def test_multiple_issues_on_same_rule(self):
        rule = _rule(actions=[
            ["SetFontSize",  "100"],
            ["SetTextColor", "999 0 0 255"],
        ])
        issues = validate_rule(rule)
        assert len(issues) == 2

    def test_only_invalid_action_counted(self):
        rule = _rule(actions=[
            ["SetFontSize",    "0"],
            ["SetBorderColor", "0 0 0 255"],  # valid
        ])
        issues = validate_rule(rule)
        assert len(issues) == 1

    def test_default_rule_index_is_minus_one(self):
        rule = _rule(actions=[["SetFontSize", "0"]])
        issues = validate_rule(rule)
        assert all(i.rule_index == -1 for i in issues)

    def test_actions_list_empty_item_skipped(self):
        # Malformed action with fewer than 2 elements should not crash
        rule = FilterRule(
            action="Show",
            enabled=True,
            conditions=[],
            actions=[["SetFontSize"]],  # missing value — only 1 element
            pre_lines=[],
            inline_comment="",
            unknown_lines=[],
        )
        # Must not raise
        issues = validate_rule(rule)
        assert isinstance(issues, list)
