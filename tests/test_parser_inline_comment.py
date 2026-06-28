"""Regression tests — P17.5 Parser inline comment stripping

Verifies that body-line inline comments (after ' #') are stripped from
action/condition values before storage, matching the behaviour of
_detect_block_header for block headers.

Root cause: _parse_body_line did not partition on '#', so values like
  SetTextColor 255 255 255 # my comment
were stored as '255 255 255 # my comment', causing 1643 false-positive
validation errors on real-world filters.
"""

import os
import pytest

from parser.filter_parser import parse_filter
from core.validator import validate_document, ValidationSeverity
from core.document import FilterDocument


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _doc_from_text(text: str) -> FilterDocument:
    doc = FilterDocument()
    doc.load_from_text(text)
    return doc


def _parse_single(text: str):
    """Return first non-TAIL rule from filter text."""
    rules = parse_filter(text)
    return next(r for r in rules if r.action != "__TAIL__")


# ---------------------------------------------------------------------------
# TestParserInlineCommentStripping
# ---------------------------------------------------------------------------

class TestParserInlineCommentStripping:
    """_parse_body_line must strip inline comments from values."""

    def test_action_value_without_comment_unchanged(self):
        rule = _parse_single("Show\n    SetFontSize 32\n")
        val = next(v for k, v in rule.actions if k == "SetFontSize")
        assert val == "32"

    def test_action_value_inline_comment_stripped(self):
        rule = _parse_single("Show\n    SetFontSize 70 # large icon\n")
        val = next(v for k, v in rule.actions if k == "SetFontSize")
        assert val == "70"

    def test_color_action_inline_comment_stripped(self):
        rule = _parse_single("Show\n    SetTextColor 255 255 255 # white\n")
        val = next(v for k, v in rule.actions if k == "SetTextColor")
        assert val == "255 255 255"

    def test_rgba_action_inline_comment_stripped(self):
        rule = _parse_single("Show\n    SetBackgroundColor 255 40 0 220 # red tint\n")
        val = next(v for k, v in rule.actions if k == "SetBackgroundColor")
        assert val == "255 40 0 220"

    def test_border_color_inline_comment_stripped(self):
        rule = _parse_single("Show\n    SetBorderColor 0 200 100 255 # green border\n")
        val = next(v for k, v in rule.actions if k == "SetBorderColor")
        assert val == "0 200 100 255"

    def test_sound_inline_comment_stripped(self):
        rule = _parse_single("Show\n    PlayAlertSound 6 250 # crit sound\n")
        val = next(v for k, v in rule.actions if k == "PlayAlertSound")
        assert val == "6 250"

    def test_condition_value_inline_comment_stripped(self):
        rule = _parse_single('Show\n    Class "Currency" # stackable\n')
        val = next(v for k, v in rule.conditions if k == "Class")
        assert val.strip() == '"Currency"'

    def test_chinese_comment_stripped(self):
        rule = _parse_single("Show\n    SetTextColor 255 255 255 # 魔镜色\n")
        val = next(v for k, v in rule.actions if k == "SetTextColor")
        assert val == "255 255 255"

    def test_comment_with_no_leading_space_stripped(self):
        # Even '#' directly adjacent to value should be stripped
        rule = _parse_single("Show\n    SetFontSize 32#nospace\n")
        val = next(v for k, v in rule.actions if k == "SetFontSize")
        assert val == "32"

    def test_hash_only_line_goes_to_unknown(self):
        rule = _parse_single("Show\n    # pure comment line\n")
        assert any("pure comment" in l for l in rule.unknown_lines)

    def test_multi_action_all_stripped(self):
        text = (
            "Show\n"
            "    SetTextColor 255 255 255 # text\n"
            "    SetBackgroundColor 0 0 0 200 # bg\n"
            "    SetFontSize 45 # size\n"
        )
        rule = _parse_single(text)
        vals = {k: v for k, v in rule.actions}
        assert vals["SetTextColor"] == "255 255 255"
        assert vals["SetBackgroundColor"] == "0 0 0 200"
        assert vals["SetFontSize"] == "45"

    def test_value_with_no_hash_unchanged(self):
        rule = _parse_single('Show\n    BaseType "Mirror of Kalandra"\n')
        val = next(v for k, v in rule.conditions if k == "BaseType")
        assert val == '"Mirror of Kalandra"'


# ---------------------------------------------------------------------------
# TestValidationAfterCommentStrip
# ---------------------------------------------------------------------------

class TestValidationAfterCommentStrip:
    """After parsing, validation must see clean values — no false positives."""

    def test_valid_rgba_with_comment_no_issue(self):
        doc = _doc_from_text("Show\n    SetTextColor 255 255 255 # white\n")
        issues = validate_document(doc)
        assert not any(i.field == "SetTextColor" for i in issues)

    def test_valid_rgba_bg_with_comment_no_issue(self):
        doc = _doc_from_text("Show\n    SetBackgroundColor 0 0 0 200 # dark\n")
        issues = validate_document(doc)
        assert not any(i.field == "SetBackgroundColor" for i in issues)

    def test_valid_rgba_border_with_comment_no_issue(self):
        doc = _doc_from_text("Show\n    SetBorderColor 255 200 0 255 # gold\n")
        issues = validate_document(doc)
        assert not any(i.field == "SetBorderColor" for i in issues)

    def test_valid_fontsize_with_comment_no_issue(self):
        doc = _doc_from_text("Show\n    SetFontSize 32 # normal\n")
        issues = validate_document(doc)
        assert not any(i.field == "SetFontSize" for i in issues)

    def test_fontsize_70_with_comment_is_real_warning(self):
        """SetFontSize 70 is genuinely out of range, even with a comment stripped."""
        doc = _doc_from_text("Show\n    SetFontSize 70 # large\n")
        issues = validate_document(doc)
        fs_issues = [i for i in issues if i.field == "SetFontSize"]
        assert len(fs_issues) == 1
        assert fs_issues[0].severity == ValidationSeverity.WARNING

    def test_fontsize_70_comment_warning_message_shows_numeric_value(self):
        doc = _doc_from_text("Show\n    SetFontSize 70 # large\n")
        issues = validate_document(doc)
        fs_issues = [i for i in issues if i.field == "SetFontSize"]
        # Should say "70" in message, not "70 # large"
        assert "70" in fs_issues[0].message
        assert "#" not in fs_issues[0].message

    def test_out_of_range_rgba_still_detected(self):
        doc = _doc_from_text("Show\n    SetTextColor 300 255 255\n")
        issues = validate_document(doc)
        assert any(i.field == "SetTextColor" for i in issues)

    def test_out_of_range_fontsize_no_comment_still_detected(self):
        # P17.9A: valid range is 1–60; use 61 to ensure warning is still detected
        doc = _doc_from_text("Show\n    SetFontSize 61\n")
        issues = validate_document(doc)
        assert any(i.field == "SetFontSize" for i in issues)

    def test_empty_rule_info_not_affected(self):
        doc = _doc_from_text("Show\n")
        issues = validate_document(doc)
        # Empty rule generates INFO — independent of comment fix
        info_issues = [i for i in issues if i.severity == ValidationSeverity.INFO]
        assert len(info_issues) == 1


# ---------------------------------------------------------------------------
# TestRealWorldFilterIssueCount
# ---------------------------------------------------------------------------

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "real_world_546_rules.filter"
)


@pytest.mark.skipif(
    not os.path.exists(FIXTURE_PATH),
    reason="real_world_546_rules.filter fixture not found",
)
class TestRealWorldFilterIssueCount:

    @pytest.fixture(scope="class")
    def real_doc(self):
        doc = FilterDocument()
        with open(FIXTURE_PATH, encoding="utf-8") as f:
            doc.load_from_text(f.read())
        return doc

    def test_rule_count(self, real_doc):
        rules = [r for r in real_doc.rules if r.action != "__TAIL__"]
        assert len(rules) == 546

    def test_no_inline_comment_in_action_values(self, real_doc):
        bad = [
            (r.action, k, v)
            for r in real_doc.rules
            for k, v in r.actions
            if "#" in v
        ]
        assert bad == [], f"Action values still contain '#': {bad[:3]}"

    def test_validation_issue_count_drops_to_below_300(self, real_doc):
        """After parser fix, false positives from inline comments are gone.

        Pre-fix: 1654 issues (1643 false positives from comment-in-value).
        Post-fix: ~191 issues (all real SetFontSize > 45 WARNINGs).
        """
        issues = validate_document(real_doc)
        assert len(issues) < 300, (
            f"Expected <300 issues after parser fix, got {len(issues)}"
        )

    def test_no_errors_only_warnings(self, real_doc):
        """After fix, all remaining issues should be WARNINGs (SetFontSize), no ERRORs."""
        issues = validate_document(real_doc)
        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert errors == [], f"Unexpected ERRORs: {errors[:3]}"

    def test_all_remaining_issues_are_fontsize(self, real_doc):
        """After fix, all issues should be SetFontSize range violations."""
        issues = validate_document(real_doc)
        non_fs = [i for i in issues if i.field != "SetFontSize"]
        assert non_fs == [], f"Unexpected non-FontSize issues: {non_fs[:3]}"

    def test_all_remaining_issues_have_quick_fix(self, real_doc):
        """SetFontSize > 45 with numeric value → Quick Fix available."""
        from core.quick_fix import get_quick_fixes
        issues = validate_document(real_doc)
        rules = real_doc.rules
        missing_fix = [
            i for i in issues
            if i.rule_index is not None
            and i.rule_index < len(rules)
            and not get_quick_fixes(rules[i.rule_index], i)
        ]
        assert missing_fix == [], f"Issues without Fix button: {missing_fix[:3]}"
