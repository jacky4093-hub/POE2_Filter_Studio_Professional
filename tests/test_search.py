"""Tests for core.search — v0.8.0"""
import pytest
from core.models import FilterRule
from core.search import SearchQuery, search_rules


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rule(action="Show", conditions=None, actions=None,
          inline_comment="", pre_lines=None, unknown_lines=None):
    return FilterRule(
        action=action,
        conditions=conditions or [],
        actions=actions or [],
        inline_comment=inline_comment,
        pre_lines=pre_lines or [],
        unknown_lines=unknown_lines or [],
    )


# ---------------------------------------------------------------------------
# Empty / trivial cases
# ---------------------------------------------------------------------------

def test_empty_query_returns_empty():
    rules = [_rule("Show"), _rule("Hide")]
    assert search_rules(rules, SearchQuery(text="")) == []

def test_whitespace_query_returns_empty():
    rules = [_rule("Show")]
    assert search_rules(rules, SearchQuery(text="   ")) == []

def test_no_rules_returns_empty():
    assert search_rules([], SearchQuery(text="Show")) == []

# ---------------------------------------------------------------------------
# Action field
# ---------------------------------------------------------------------------

def test_match_action_show():
    rules = [_rule("Show"), _rule("Hide"), _rule("Show")]
    result = search_rules(rules, SearchQuery(text="Show"))
    assert result == [0, 2]

def test_match_action_case_insensitive():
    rules = [_rule("Show"), _rule("Hide")]
    assert search_rules(rules, SearchQuery(text="show")) == [0]

def test_match_action_case_sensitive_no_match():
    rules = [_rule("Show")]
    assert search_rules(rules, SearchQuery(text="show", case_sensitive=True)) == []

def test_match_action_case_sensitive_match():
    rules = [_rule("Show")]
    assert search_rules(rules, SearchQuery(text="Show", case_sensitive=True)) == [0]

# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------

def test_match_condition_key():
    rules = [_rule(conditions=[["Class", "Currency"]]), _rule("Hide")]
    assert search_rules(rules, SearchQuery(text="Class")) == [0]

def test_match_condition_value():
    rules = [_rule(conditions=[["Class", "Currency"]]), _rule("Hide")]
    assert search_rules(rules, SearchQuery(text="Currency")) == [0]

def test_match_condition_partial():
    rules = [_rule(conditions=[["BaseType", "Exalted Orb"]])]
    assert search_rules(rules, SearchQuery(text="Exalted")) == [0]

# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def test_match_action_key():
    rules = [_rule(actions=[["SetFontSize", "45"]])]
    assert search_rules(rules, SearchQuery(text="SetFontSize")) == [0]

def test_match_action_value():
    rules = [_rule(actions=[["SetFontSize", "45"]])]
    assert search_rules(rules, SearchQuery(text="45")) == [0]

# ---------------------------------------------------------------------------
# inline_comment and pre_lines
# ---------------------------------------------------------------------------

def test_match_inline_comment():
    rules = [_rule(inline_comment="# 貨幣規則")]
    assert search_rules(rules, SearchQuery(text="貨幣")) == [0]

def test_match_pre_lines():
    rules = [_rule(pre_lines=["# Section: Endgame Currency"])]
    assert search_rules(rules, SearchQuery(text="Endgame")) == [0]

def test_match_unknown_lines():
    rules = [_rule(unknown_lines=["EnableDropSound"])]
    assert search_rules(rules, SearchQuery(text="EnableDropSound")) == [0]

# ---------------------------------------------------------------------------
# __TAIL__ sentinel exclusion
# ---------------------------------------------------------------------------

def test_tail_sentinel_excluded():
    tail = FilterRule(action="__TAIL__")
    rules = [_rule("Show"), tail]
    result = search_rules(rules, SearchQuery(text="TAIL"))
    assert result == []

def test_tail_sentinel_index_not_returned():
    tail = FilterRule(action="__TAIL__")
    rules = [_rule("Show"), tail]
    result = search_rules(rules, SearchQuery(text="Show"))
    assert 1 not in result

# ---------------------------------------------------------------------------
# Order and indices
# ---------------------------------------------------------------------------

def test_results_in_ascending_order():
    rules = [_rule("Hide"), _rule("Show"), _rule("Hide"), _rule("Show")]
    result = search_rules(rules, SearchQuery(text="Show"))
    assert result == [1, 3]

def test_multiple_conditions_first_match_wins():
    rules = [
        _rule(conditions=[["Class", "Ring"], ["BaseType", "Iron Ring"]]),
    ]
    assert search_rules(rules, SearchQuery(text="Ring")) == [0]

# ---------------------------------------------------------------------------
# Robustness — malformed rules must not raise
# ---------------------------------------------------------------------------

def test_malformed_rule_skipped_silently():
    good = _rule("Show")
    bad = object()                       # completely wrong type
    rules = [good, bad, good]
    result = search_rules(rules, SearchQuery(text="Show"))
    assert 0 in result
    assert 2 in result
    assert 1 not in result

def test_none_condition_values_converted_to_str():
    # str(None) == "None", so a search for "None" correctly matches
    rule = _rule(conditions=[[None, None]])
    result = search_rules([rule], SearchQuery(text="None"))
    assert result == [0]

def test_none_condition_values_no_other_match():
    # But a search for something unrelated should not match
    rule = _rule(conditions=[[None, None]])
    result = search_rules([rule], SearchQuery(text="Currency"))
    assert result == []
