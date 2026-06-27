from core.models import FilterRule, KNOWN_CONDITIONS, KNOWN_ACTIONS, BLOCK_HEADERS

_CONDITION_SET = set(KNOWN_CONDITIONS)
_ACTION_SET = set(KNOWN_ACTIONS)
_HEADER_SET = set(BLOCK_HEADERS)


def _detect_block_header(stripped: str):
    """Return (keyword, inline_comment, enabled) or (None, None, None).

    Handles both enabled ('Show') and disabled ('# Show') block headers.
    A disabled header is a line whose first non-whitespace token is '#'
    followed immediately by a recognised block keyword.  Any text after
    a second '#' on the same line is treated as an inline comment.
    """
    if not stripped:
        return None, None, None

    enabled = True
    rest = stripped

    # Disabled block: line starts with '#' — check if the remainder is a keyword
    if stripped.startswith('#'):
        rest = stripped[1:].strip()
        enabled = False

    # Split off optional inline comment (the part after the next '#')
    main_part, _, comment_part = rest.partition('#')
    keyword = main_part.strip()
    inline = comment_part.strip()

    if keyword in _HEADER_SET:
        return keyword, inline, enabled
    return None, None, None


def _parse_body_line(stripped: str, rule: FilterRule):
    if not stripped:
        return
    if stripped.startswith('#'):
        rule.unknown_lines.append(stripped)
        return
    parts = stripped.split(None, 1)
    keyword = parts[0]
    value = parts[1] if len(parts) > 1 else ''
    # Strip inline comment from value (consistent with _detect_block_header).
    # Inline comments in POE2 filters always start with ' #' after the value.
    value = value.partition('#')[0].rstrip()
    if keyword in _CONDITION_SET:
        rule.conditions.append([keyword, value])
    elif keyword in _ACTION_SET:
        rule.actions.append([keyword, value])
    else:
        rule.unknown_lines.append(stripped)


def parse_filter(text: str) -> list:
    """Parse POE2 filter text into a list of FilterRule objects.

    Blank lines / comments between blocks are stored as pre_lines on the
    next rule.  Trailing content after the last block is stored in a
    sentinel rule with action='__TAIL__'.
    Unknown indented lines are kept in unknown_lines so they survive
    a round-trip through the exporter without data loss.
    """
    rules: list[FilterRule] = []
    pre_buffer: list[str] = []
    current_rule: FilterRule | None = None

    def flush_rule():
        nonlocal current_rule
        if current_rule is not None:
            rules.append(current_rule)
            current_rule = None

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        is_indented = bool(raw_line) and raw_line[0] in (' ', '\t')

        if is_indented:
            if current_rule is not None:
                _parse_body_line(stripped, current_rule)
            else:
                # orphan indented line - preserve as-is
                pre_buffer.append(raw_line)
            continue

        keyword, inline, enabled = _detect_block_header(stripped)
        if keyword is not None:
            flush_rule()
            current_rule = FilterRule(
                action=keyword,
                inline_comment=inline,
                pre_lines=pre_buffer[:],
                enabled=enabled,
            )
            pre_buffer = []
            continue

        # blank line or comment at column 0 — ends current block
        flush_rule()
        pre_buffer.append(raw_line)

    flush_rule()

    if pre_buffer:
        rules.append(FilterRule(action="__TAIL__", pre_lines=pre_buffer[:]))

    return rules
