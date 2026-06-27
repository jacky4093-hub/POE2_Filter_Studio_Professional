import pytest

from parser.filter_exporter import export_filter
from parser.filter_parser import parse_filter


def _assert_roundtrip_semantics(original_rules, roundtrip_rules):
    assert len(original_rules) == len(roundtrip_rules)
    for original, roundtrip in zip(original_rules, roundtrip_rules):
        assert original.action == roundtrip.action
        assert original.enabled == roundtrip.enabled
        assert original.inline_comment == roundtrip.inline_comment
        assert original.conditions == roundtrip.conditions
        assert original.actions == roundtrip.actions
        assert original.unknown_lines == roundtrip.unknown_lines
        assert original.pre_lines == roundtrip.pre_lines


def _roundtrip(text: str):
    parsed = parse_filter(text)
    exported = export_filter(parsed)
    reparsed = parse_filter(exported)
    _assert_roundtrip_semantics(parsed, reparsed)
    return parsed, exported, reparsed


def test_basic_single_show_roundtrip():
    source = """
# Basic filter header
Show
    BaseType "Amethyst Flask"
    Class Flasks
    SetFontSize 45
    SetTextColor 255 128 64 255
""".lstrip()

    parsed, exported, reparsed = _roundtrip(source)
    assert len(parsed) == 1

    rule = parsed[0]
    assert rule.action == "Show"
    assert rule.enabled is True
    assert rule.inline_comment == ""
    assert rule.conditions == [
        ["BaseType", '"Amethyst Flask"'],
        ["Class", "Flasks"],
    ]
    assert rule.actions == [
        ["SetFontSize", "45"],
        ["SetTextColor", "255 128 64 255"],
    ]
    assert rule.pre_lines == ["# Basic filter header"]
    assert rule.unknown_lines == []
    assert "# Basic filter header" in exported


def test_block_order_preserved_across_roundtrip():
    source = """
Show
    BaseType Sapphire Ring
Hide
    Class Gems
Continue
    SetFontSize 50
""".lstrip()

    parsed, exported, reparsed = _roundtrip(source)
    assert [rule.action for rule in parsed] == ["Show", "Hide", "Continue"]
    assert [rule.action for rule in reparsed] == ["Show", "Hide", "Continue"]
    assert len(parsed) == 3
    assert len(reparsed) == 3
    assert "Continue" in exported


@pytest.mark.xfail(
    reason="Parser currently does not recognize disabled block headers like '# Show' / '# Hide'",
    strict=False,
)
def test_disabled_block_roundtrip():
    source = """
# Show
    Class Flasks
# Hide
    BaseType "Ruby Ring"
""".lstrip()

    parsed, exported, reparsed = _roundtrip(source)

    # The exporter can render disabled block headers, but current parser support
    # for reading '# Show' / '# Hide' is not implemented.
    assert len(parsed) == 2
    assert parsed[0].action == "Show"
    assert parsed[0].enabled is False
    assert parsed[0].conditions == [["Class", "Flasks"]]

    assert parsed[1].action == "Hide"
    assert parsed[1].enabled is False
    assert parsed[1].conditions == [["BaseType", '"Ruby Ring"']]

    assert all(rule.enabled is False for rule in reparsed)
    assert exported.count("# Show") == 1
    assert exported.count("# Hide") == 1


def test_unknown_directive_preserved():
    source = """
Show
    BaseType Sapphire Ring
    CustomVisualEffect Blue
    SetFontSize 30
""".lstrip()

    parsed, exported, reparsed = _roundtrip(source)
    assert len(parsed) == 1
    assert parsed[0].unknown_lines == ["CustomVisualEffect Blue"]
    assert parsed[0].actions == [["SetFontSize", "30"]]
    assert "CustomVisualEffect Blue" in exported
    assert reparsed[0].unknown_lines == ["CustomVisualEffect Blue"]


def test_comments_blank_lines_and_tail_content_preserved():
    source = """
# Filter description header
Show
    Class Jewels
    # preserve this inline block comment
    SetTextColor 0 255 0 255

# block separator comment
Hide
    BaseType "Rustic Sash"

# final tail comment
""".lstrip()

    parsed, exported, reparsed = _roundtrip(source)
    assert len(parsed) == 3

    show_rule, hide_rule, tail_rule = parsed
    assert show_rule.action == "Show"
    assert show_rule.unknown_lines == ["# preserve this inline block comment"]
    assert show_rule.pre_lines == ["# Filter description header"]
    assert hide_rule.pre_lines == ["", "# block separator comment"]
    assert tail_rule.action == "__TAIL__"
    assert tail_rule.pre_lines == ["", "# final tail comment"]

    assert "# Filter description header" in exported
    assert "# preserve this inline block comment" in exported
    assert "# block separator comment" in exported
    assert "# final tail comment" in exported

    assert [rule.action for rule in reparsed] == ["Show", "Hide", "__TAIL__"]
    assert reparsed[0].unknown_lines == show_rule.unknown_lines
    assert reparsed[1].pre_lines == hide_rule.pre_lines
    assert reparsed[2].pre_lines == tail_rule.pre_lines
