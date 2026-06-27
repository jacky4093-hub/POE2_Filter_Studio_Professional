"""Tests for src/core/sections.py — pure logic, no Qt required.

Covers:
  A. detect_section_header()  — 9 tests
  B. build_section_map()      — 7 tests
"""

import pytest
from core.sections import detect_section_header, build_section_map, FilterSection, SectionMap
from core.models import FilterRule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rule(action: str = "Show", pre_lines: list[str] | None = None) -> FilterRule:
    return FilterRule(
        action=action,
        pre_lines=pre_lines if pre_lines is not None else [],
        conditions=[],
        actions=[],
    )


def _make_tail() -> FilterRule:
    return FilterRule(action="__TAIL__", pre_lines=[], conditions=[], actions=[])


SEP = "#================================================"
SEP_DASH = "#------------------------------------------------"


# ===========================================================================
# A. detect_section_header
# ===========================================================================

class TestDetectSectionHeader:
    def test_basic_separator_equals(self):
        pre = [SEP, "# Currency", SEP]
        assert detect_section_header(pre) == "Currency"

    def test_basic_separator_dash(self):
        pre = [SEP_DASH, "# Gems", SEP_DASH]
        assert detect_section_header(pre) == "Gems"

    def test_title_with_spaces(self):
        pre = [SEP, "# High Value Uniques", SEP]
        assert detect_section_header(pre) == "High Value Uniques"

    def test_blank_lines_around_pattern_ignored(self):
        # Blank lines before the pattern — still detects correctly
        pre = ["", SEP, "# Flasks", SEP]
        assert detect_section_header(pre) == "Flasks"

    def test_requires_three_nonblank_lines(self):
        # Only two non-blank lines
        pre = [SEP, "# Currency"]
        assert detect_section_header(pre) is None

    def test_empty_pre_lines_returns_none(self):
        assert detect_section_header([]) is None

    def test_plain_comment_not_detected(self):
        pre = ["# just a note", "# about gems"]
        assert detect_section_header(pre) is None

    def test_title_must_not_be_separator(self):
        # Middle line is a separator, not a title → should NOT detect
        pre = [SEP, SEP, SEP]
        assert detect_section_header(pre) is None

    def test_extra_comment_after_pattern_fails(self):
        # The pattern must be the LAST three non-blank lines
        # Extra comment after means pattern is no longer last
        pre = [SEP, "# Currency", SEP, "# unrelated comment"]
        assert detect_section_header(pre) is None


# ===========================================================================
# B. build_section_map
# ===========================================================================

class TestBuildSectionMap:
    def test_no_rules_returns_empty_map(self):
        smap = build_section_map([])
        assert smap.sections == []
        assert smap.rule_to_section == {}
        assert smap.unsectioned_indices == []

    def test_all_rules_unsectioned(self):
        rules = [_make_rule("Show"), _make_rule("Hide"), _make_tail()]
        smap = build_section_map(rules)
        assert smap.sections == []
        assert smap.rule_to_section[0] == -1
        assert smap.rule_to_section[1] == -1
        assert smap.unsectioned_indices == [0, 1]
        assert 2 not in smap.rule_to_section   # __TAIL__ excluded

    def test_single_section_all_rules(self):
        r1 = _make_rule("Show", pre_lines=[SEP, "# Currency", SEP])
        r2 = _make_rule("Show")
        r3 = _make_tail()
        rules = [r1, r2, r3]
        smap = build_section_map(rules)
        assert len(smap.sections) == 1
        sec = smap.sections[0]
        assert sec.name == "Currency"
        assert sec.first_rule_index == 0
        assert sec.rule_count == 2
        assert smap.rule_to_section[0] == 0
        assert smap.rule_to_section[1] == 0
        assert smap.unsectioned_indices == []

    def test_two_sections(self):
        r0 = _make_rule("Show", pre_lines=[SEP, "# Currency", SEP])
        r1 = _make_rule("Show")
        r2 = _make_rule("Show", pre_lines=[SEP, "# Gems", SEP])
        r3 = _make_rule("Hide")
        r4 = _make_tail()
        smap = build_section_map([r0, r1, r2, r3, r4])
        assert len(smap.sections) == 2
        assert smap.sections[0].name == "Currency"
        assert smap.sections[0].first_rule_index == 0
        assert smap.sections[0].rule_count == 2
        assert smap.sections[1].name == "Gems"
        assert smap.sections[1].first_rule_index == 2
        assert smap.sections[1].rule_count == 2
        assert smap.rule_to_section[0] == 0
        assert smap.rule_to_section[1] == 0
        assert smap.rule_to_section[2] == 1
        assert smap.rule_to_section[3] == 1

    def test_rules_before_first_section_are_unsectioned(self):
        r0 = _make_rule("Show")
        r1 = _make_rule("Show", pre_lines=[SEP, "# Currency", SEP])
        smap = build_section_map([r0, r1, _make_tail()])
        assert smap.unsectioned_indices == [0]
        assert smap.rule_to_section[0] == -1
        assert smap.rule_to_section[1] == 0

    def test_tail_excluded_from_map(self):
        rules = [_make_tail()]
        smap = build_section_map(rules)
        assert 0 not in smap.rule_to_section

    def test_section_id_matches_first_rule_index(self):
        r0 = _make_rule("Show", pre_lines=[SEP, "# Currency", SEP])
        r1 = _make_rule("Show", pre_lines=[SEP, "# Gems", SEP])
        smap = build_section_map([r0, r1, _make_tail()])
        assert smap.sections[0].section_id == 0
        assert smap.sections[1].section_id == 1
