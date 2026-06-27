"""Tests for filter_parser and filter_exporter — P11.4: disabled block support"""

from parser.filter_parser import parse_filter
from parser.filter_exporter import export_filter


# ---------------------------------------------------------------------------
# Parser: enabled block headers (existing behaviour, must not regress)
# ---------------------------------------------------------------------------

class TestParserEnabledHeaders:
    def test_show_parsed(self):
        rules = parse_filter("Show\n")
        assert len(rules) == 1
        assert rules[0].action == "Show"
        assert rules[0].enabled is True

    def test_hide_parsed(self):
        rules = parse_filter("Hide\n")
        assert len(rules) == 1
        assert rules[0].action == "Hide"
        assert rules[0].enabled is True

    def test_continue_parsed(self):
        rules = parse_filter("Continue\n")
        assert len(rules) == 1
        assert rules[0].action == "Continue"
        assert rules[0].enabled is True

    def test_inline_comment_on_enabled_header(self):
        rules = parse_filter("Show # my note\n")
        assert rules[0].action == "Show"
        assert rules[0].enabled is True
        assert rules[0].inline_comment == "my note"

    def test_enabled_block_keeps_conditions(self):
        text = "Show\n    Class Currency\n"
        rules = parse_filter(text)
        assert rules[0].conditions == [["Class", "Currency"]]


# ---------------------------------------------------------------------------
# Parser: disabled block headers (P11.4)
# ---------------------------------------------------------------------------

class TestParserDisabledHeaders:
    def test_hash_show_is_disabled(self):
        rules = parse_filter("# Show\n")
        assert len(rules) == 1
        assert rules[0].action == "Show"
        assert rules[0].enabled is False

    def test_hash_hide_is_disabled(self):
        rules = parse_filter("# Hide\n")
        assert len(rules) == 1
        assert rules[0].action == "Hide"
        assert rules[0].enabled is False

    def test_hash_continue_is_disabled(self):
        rules = parse_filter("# Continue\n")
        assert len(rules) == 1
        assert rules[0].action == "Continue"
        assert rules[0].enabled is False

    def test_disabled_block_retains_conditions(self):
        text = "# Show\n    Class Flasks\n    SetFontSize 45\n"
        rules = parse_filter(text)
        assert rules[0].action == "Show"
        assert rules[0].enabled is False
        assert rules[0].conditions == [["Class", "Flasks"]]
        assert rules[0].actions == [["SetFontSize", "45"]]

    def test_disabled_block_inline_comment(self):
        rules = parse_filter("# Show # my inline note\n")
        assert rules[0].action == "Show"
        assert rules[0].enabled is False
        assert rules[0].inline_comment == "my inline note"

    def test_disabled_block_no_inline_comment(self):
        rules = parse_filter("# Hide\n")
        assert rules[0].inline_comment == ""

    def test_two_consecutive_disabled_blocks(self):
        text = "# Show\n    Class Flasks\n# Hide\n    BaseType \"Ruby Ring\"\n"
        rules = parse_filter(text)
        assert len(rules) == 2
        assert rules[0].action == "Show"
        assert rules[0].enabled is False
        assert rules[0].conditions == [["Class", "Flasks"]]
        assert rules[1].action == "Hide"
        assert rules[1].enabled is False
        assert rules[1].conditions == [["BaseType", '"Ruby Ring"']]

    def test_disabled_block_pre_lines_preserved(self):
        text = "# section header\n# Show\n    Class Flasks\n"
        rules = parse_filter(text)
        assert rules[0].action == "Show"
        assert rules[0].enabled is False
        assert rules[0].pre_lines == ["# section header"]

    def test_generic_comment_not_treated_as_disabled_block(self):
        """A comment whose first word is not a header keyword stays in pre_lines."""
        text = "# This is a general comment\nShow\n"
        rules = parse_filter(text)
        assert len(rules) == 1
        assert rules[0].action == "Show"
        assert rules[0].enabled is True
        assert rules[0].pre_lines == ["# This is a general comment"]

    def test_hash_show_with_extra_words_is_comment(self):
        """'# Show me the money' should NOT be a disabled block header."""
        text = "# Show me the money\nShow\n"
        rules = parse_filter(text)
        assert len(rules) == 1
        assert rules[0].action == "Show"
        assert rules[0].pre_lines == ["# Show me the money"]

    def test_mixed_enabled_and_disabled_blocks(self):
        text = (
            "Show\n    Class Currency\n"
            "# Hide\n    BaseType \"Orb\"\n"
            "Continue\n    SetFontSize 30\n"
        )
        rules = parse_filter(text)
        assert len(rules) == 3
        assert rules[0].enabled is True
        assert rules[1].enabled is False
        assert rules[2].enabled is True


# ---------------------------------------------------------------------------
# Exporter: disabled block output (P11.4)
# ---------------------------------------------------------------------------

class TestExporterDisabledHeaders:
    def _make_rule(self, action, enabled, conditions=None, actions=None, pre_lines=None):
        from core.models import FilterRule
        return FilterRule(
            action=action,
            enabled=enabled,
            conditions=conditions or [],
            actions=actions or [],
            pre_lines=pre_lines or [],
        )

    def test_enabled_rule_no_hash(self):
        rule = self._make_rule("Show", True)
        out = export_filter([rule])
        assert out.startswith("Show")
        assert "# Show" not in out

    def test_disabled_show_outputs_hash(self):
        rule = self._make_rule("Show", False)
        out = export_filter([rule])
        assert "# Show" in out

    def test_disabled_hide_outputs_hash(self):
        rule = self._make_rule("Hide", False)
        out = export_filter([rule])
        assert "# Hide" in out

    def test_disabled_continue_outputs_hash(self):
        rule = self._make_rule("Continue", False)
        out = export_filter([rule])
        assert "# Continue" in out

    def test_disabled_rule_conditions_indented(self):
        rule = self._make_rule("Show", False, conditions=[["Class", "Currency"]])
        out = export_filter([rule])
        lines = out.splitlines()
        assert lines[0] == "# Show"
        assert lines[1] == "    Class Currency"

    def test_inline_comment_preserved_on_disabled(self):
        from core.models import FilterRule
        rule = FilterRule(action="Show", enabled=False, inline_comment="note")
        out = export_filter([rule])
        assert "# Show # note" in out


# ---------------------------------------------------------------------------
# Round-trip: parse → export → parse identity for disabled blocks
# ---------------------------------------------------------------------------

class TestDisabledBlockRoundtrip:
    def _roundtrip(self, text):
        parsed = parse_filter(text)
        exported = export_filter(parsed)
        reparsed = parse_filter(exported)
        return parsed, exported, reparsed

    def test_disabled_show_survives_roundtrip(self):
        text = "# Show\n    Class Flasks\n"
        parsed, exported, reparsed = self._roundtrip(text)
        assert reparsed[0].action == "Show"
        assert reparsed[0].enabled is False
        assert reparsed[0].conditions == [["Class", "Flasks"]]

    def test_disabled_hide_survives_roundtrip(self):
        text = "# Hide\n    BaseType \"Chaos Orb\"\n"
        parsed, exported, reparsed = self._roundtrip(text)
        assert reparsed[0].action == "Hide"
        assert reparsed[0].enabled is False

    def test_block_count_preserved(self):
        text = "# Show\n    Class Flasks\n# Hide\n    Class Gems\n"
        parsed, exported, reparsed = self._roundtrip(text)
        assert len(parsed) == len(reparsed) == 2

    def test_block_order_preserved(self):
        text = "Show\n    Class Currency\n# Hide\n    Class Gems\nContinue\n"
        parsed, exported, reparsed = self._roundtrip(text)
        assert [r.action for r in reparsed] == ["Show", "Hide", "Continue"]
        assert [r.enabled for r in reparsed] == [True, False, True]

    def test_unknown_lines_not_lost(self):
        text = "# Show\n    Class Flasks\n    CustomDirective value\n"
        parsed, exported, reparsed = self._roundtrip(text)
        assert parsed[0].unknown_lines == ["CustomDirective value"]
        assert reparsed[0].unknown_lines == ["CustomDirective value"]

    def test_pre_lines_not_lost(self):
        text = "# section\n# Show\n    Class Flasks\n"
        parsed, exported, reparsed = self._roundtrip(text)
        assert parsed[0].pre_lines == ["# section"]
        assert reparsed[0].pre_lines == ["# section"]
