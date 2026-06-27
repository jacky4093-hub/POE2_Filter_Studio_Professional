"""Tests for core.rule_search — P10 pure search functions"""

import pytest

from core.models import FilterRule
from core.rule_search import build_search_text, rule_matches_query, filter_rules_by_query


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rule(action="Show", conditions=None, actions=None, unknown_lines=None, enabled=True):
    return FilterRule(
        action=action,
        conditions=conditions or [],
        actions=actions or [],
        unknown_lines=unknown_lines or [],
        enabled=enabled,
    )


def _dict_rule(**kwargs):
    """Return a plain dict that mimics a FilterRule."""
    return {
        "action":        kwargs.get("action", "Show"),
        "conditions":    kwargs.get("conditions", []),
        "actions":       kwargs.get("actions", []),
        "unknown_lines": kwargs.get("unknown_lines", []),
        "enabled":       kwargs.get("enabled", True),
    }


# ---------------------------------------------------------------------------
# TestBuildSearchText
# ---------------------------------------------------------------------------

class TestBuildSearchText:
    def test_action_included_by_default(self):
        rule = _rule(action="Hide")
        text = build_search_text(rule)
        assert "Hide" in text

    def test_disabled_included_by_default(self):
        rule = _rule(enabled=False)
        text = build_search_text(rule)
        assert "disabled" in text

    def test_class_condition_included(self):
        rule = _rule(conditions=[["Class", '"Currency"']])
        text = build_search_text(rule)
        assert "Currency" in text

    def test_basetype_condition_included(self):
        rule = _rule(conditions=[["BaseType", '"Chaos Orb"']])
        text = build_search_text(rule)
        assert "Chaos Orb" in text

    def test_action_field_included(self):
        rule = _rule(actions=[["SetTextColor", "255 0 0 255"]])
        text = build_search_text(rule)
        assert "SetTextColor" in text

    def test_playalertsound_included(self):
        rule = _rule(actions=[["PlayAlertSound", "1 300"]])
        text = build_search_text(rule)
        assert "PlayAlertSound" in text

    def test_unknown_lines_included(self):
        rule = _rule(unknown_lines=["CustomLine abc"])
        text = build_search_text(rule)
        assert "CustomLine abc" in text

    def test_tail_action_excluded_from_text(self):
        rule = _rule(action="__TAIL__")
        text = build_search_text(rule)
        assert "__TAIL__" not in text

    def test_dict_rule_works(self):
        rule = _dict_rule(conditions=[["Class", '"Gem"']])
        text = build_search_text(rule)
        assert "Gem" in text

    def test_class_only_flag(self):
        rule = _rule(
            conditions=[["Class", '"Currency"'], ["BaseType", '"Orb"']],
            actions=[["SetTextColor", "255 0 0"]],
        )
        text = build_search_text(rule, {"class": True})
        assert "Currency" in text
        assert "Orb" not in text
        assert "SetTextColor" not in text

    def test_basetype_only_flag(self):
        rule = _rule(conditions=[["Class", '"Currency"'], ["BaseType", '"Orb"']])
        text = build_search_text(rule, {"basetype": True})
        assert "Orb" in text
        assert "Currency" not in text

    def test_action_flag_includes_show_hide(self):
        rule = _rule(action="Hide")
        text = build_search_text(rule, {"action": True})
        assert "Hide" in text

    def test_raw_text_flag_includes_unknown_lines(self):
        rule = _rule(unknown_lines=["RawLine xyz"])
        text = build_search_text(rule, {"raw_text": True})
        assert "RawLine xyz" in text

    def test_raw_text_flag_excludes_conditions(self):
        rule = _rule(
            conditions=[["Class", '"Gem"']],
            unknown_lines=["RawLine xyz"],
        )
        text = build_search_text(rule, {"raw_text": True})
        # "raw_text" flag alone — conditions not included
        assert "Gem" not in text
        assert "RawLine xyz" in text


# ---------------------------------------------------------------------------
# TestRuleMatchesQuery
# ---------------------------------------------------------------------------

class TestRuleMatchesQuery:
    def test_empty_query_matches_all(self):
        rule = _rule()
        assert rule_matches_query(rule, "") is True
        assert rule_matches_query(rule, "   ") is True

    def test_none_query_matches_all(self):
        rule = _rule()
        assert rule_matches_query(rule, None) is True

    def test_case_insensitive_by_default(self):
        rule = _rule(conditions=[["Class", '"Currency"']])
        assert rule_matches_query(rule, "currency") is True
        assert rule_matches_query(rule, "CURRENCY") is True

    def test_match_case_sensitive(self):
        rule = _rule(conditions=[["Class", '"Currency"']])
        assert rule_matches_query(rule, "Currency", {"match_case": True}) is True
        assert rule_matches_query(rule, "currency", {"match_case": True}) is False

    def test_class_search(self):
        rule = _rule(conditions=[["Class", '"Skill Gem"']])
        assert rule_matches_query(rule, "Skill Gem") is True
        assert rule_matches_query(rule, "Currency") is False

    def test_basetype_search(self):
        rule = _rule(conditions=[["BaseType", '"Chaos Orb"']])
        assert rule_matches_query(rule, "Chaos") is True

    def test_action_keyword_show(self):
        rule = _rule(action="Show")
        assert rule_matches_query(rule, "Show") is True

    def test_action_keyword_hide(self):
        rule = _rule(action="Hide")
        assert rule_matches_query(rule, "Hide") is True

    def test_color_action_search(self):
        rule = _rule(actions=[["SetTextColor", "255 0 0 255"]])
        assert rule_matches_query(rule, "SetTextColor") is True
        assert rule_matches_query(rule, "255 0 0") is True

    def test_border_color_search(self):
        rule = _rule(actions=[["SetBorderColor", "0 255 0 255"]])
        assert rule_matches_query(rule, "SetBorderColor") is True

    def test_background_color_search(self):
        rule = _rule(actions=[["SetBackgroundColor", "0 0 255 255"]])
        assert rule_matches_query(rule, "SetBackgroundColor") is True

    def test_playalertsound_search(self):
        rule = _rule(actions=[["PlayAlertSound", "6 300"]])
        assert rule_matches_query(rule, "PlayAlertSound") is True

    def test_minimap_icon_search(self):
        rule = _rule(actions=[["MinimapIcon", "0 Blue Star"]])
        assert rule_matches_query(rule, "MinimapIcon") is True
        assert rule_matches_query(rule, "Blue Star") is True

    def test_unknown_lines_search(self):
        rule = _rule(unknown_lines=["SomeCustom keyword"])
        assert rule_matches_query(rule, "keyword") is True

    def test_raw_text_option_searches_unknown_lines(self):
        rule = _rule(unknown_lines=["RawContent abc"])
        assert rule_matches_query(rule, "abc", {"raw_text": True}) is True

    def test_dict_rule_compatible(self):
        rule = _dict_rule(conditions=[["Class", '"Maps"']])
        assert rule_matches_query(rule, "Maps") is True

    def test_object_rule_not_modified(self):
        rule = _rule(conditions=[["Class", '"Currency"']])
        original_conditions = list(rule.conditions)
        rule_matches_query(rule, "Currency")
        assert rule.conditions == original_conditions

    def test_dict_rule_not_modified(self):
        rule = _dict_rule(conditions=[["Class", '"Currency"']])
        original = list(rule["conditions"])
        rule_matches_query(rule, "Currency")
        assert rule["conditions"] == original

    def test_no_match_returns_false(self):
        rule = _rule(conditions=[["Class", '"Gem"']])
        assert rule_matches_query(rule, "Currency") is False


# ---------------------------------------------------------------------------
# TestFilterRulesByQuery
# ---------------------------------------------------------------------------

class TestFilterRulesByQuery:
    def test_empty_query_returns_all_indices(self):
        rules = [_rule(), _rule(), _rule()]
        result = filter_rules_by_query(rules, "")
        assert result == [0, 1, 2]

    def test_matching_rules_returned(self):
        rules = [
            _rule(conditions=[["Class", '"Currency"']]),
            _rule(conditions=[["Class", '"Gem"']]),
            _rule(conditions=[["Class", '"Currency"']]),
        ]
        result = filter_rules_by_query(rules, "Currency")
        assert result == [0, 2]

    def test_no_matches_returns_empty(self):
        rules = [_rule(conditions=[["Class", '"Gem"']])]
        result = filter_rules_by_query(rules, "Currency")
        assert result == []

    def test_empty_rules_list(self):
        result = filter_rules_by_query([], "Currency")
        assert result == []

    def test_options_forwarded(self):
        rules = [
            _rule(conditions=[["Class", '"Currency"']]),
            _rule(conditions=[["Class", '"currency"']]),
        ]
        result = filter_rules_by_query(rules, "Currency", {"match_case": True})
        assert 0 in result
        assert 1 not in result

    def test_whitespace_query_returns_all(self):
        rules = [_rule(), _rule()]
        assert filter_rules_by_query(rules, "   ") == [0, 1]
