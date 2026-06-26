from core.models import FilterRule


def export_filter(rules: list) -> str:
    """Export a list of FilterRule objects back to POE2 filter text.

    Pre-lines (blank lines and comments stored before each block) are
    emitted verbatim.  Unknown lines inside a block are re-indented and
    appended after known conditions/actions so no content is lost.
    """
    lines: list[str] = []

    for rule in rules:
        # Emit stored pre-block content (blank lines, comments, etc.)
        lines.extend(rule.pre_lines)

        if rule.action == "__TAIL__":
            continue  # pre_lines already written above

        # Block header
        header_line = rule.action
        if not rule.enabled:
            header_line = f"# {header_line}"
        if rule.inline_comment:
            header_line += f" # {rule.inline_comment}"
        lines.append(header_line)

        # Conditions
        for key, value in rule.conditions:
            entry = f"    {key}"
            if value:
                entry += f" {value}"
            lines.append(entry)

        # Display actions
        for key, value in rule.actions:
            entry = f"    {key}"
            if value:
                entry += f" {value}"
            lines.append(entry)

        # Unknown / unrecognised lines — preserved verbatim with indent
        for ul in rule.unknown_lines:
            if ul:
                lines.append(f"    {ul}")

    return '\n'.join(lines)
