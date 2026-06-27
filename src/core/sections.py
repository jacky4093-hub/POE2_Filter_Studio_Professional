"""FilterSection and SectionMap — v1.0.0

Pure post-parse analysis of FilterRule.pre_lines to detect section boundaries.
Zero Qt dependency.  All functions are pure (no side effects, no mutations).

Section detection requires the strict "separator + title + separator" pattern
appearing as the LAST THREE non-blank lines in a rule's pre_lines:

    #================================================   <- separator line
    # Currency                                          <- title line
    #================================================   <- separator line
    Show                                                <- rule immediately follows
      Class "Currency"

Both '#===...' and '#---...' separator styles are recognised.
A line that is only '#' characters (e.g. '######') is also a valid separator.
A title line must start with '# ' followed by at least one non-separator char.

Public API:
    FilterSection            dataclass: one named section
    SectionMap               dataclass: full index for a rule list
    build_section_map(rules) pure fn: list[FilterRule] -> SectionMap
    detect_section_header(pre_lines) pure fn: list[str] -> str | None
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class FilterSection:
    """One named section in a filter file."""
    name:             str        # e.g. "Currency"
    first_rule_index: int        # real_index of first rule in this section
    rule_count:       int        # visible rules (excluding __TAIL__)
    header_lines:     list[str] = field(default_factory=list)  # original pre_lines

    @property
    def section_id(self) -> int:
        """Unique identifier within a loaded file (first_rule_index)."""
        return self.first_rule_index


@dataclass
class SectionMap:
    """Complete section index derived from a list of FilterRule objects."""
    sections:            list[FilterSection]
    rule_to_section:     dict[int, int]   # real_index -> section_index (-1 = unsectioned)
    unsectioned_indices: list[int]         # real_indices before any section header


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def build_section_map(rules: list) -> SectionMap:
    """Derive a SectionMap from rule.pre_lines.  Pure, O(n), never raises."""
    sections:            list[FilterSection] = []
    rule_to_section:     dict[int, int]      = {}
    unsectioned_indices: list[int]           = []
    current_section_idx: int                 = -1

    for real_idx, rule in enumerate(rules):
        try:
            if rule.action == "__TAIL__":
                continue

            name = detect_section_header(rule.pre_lines)
            if name is not None:
                current_section_idx = len(sections)
                sections.append(FilterSection(
                    name=name,
                    first_rule_index=real_idx,
                    rule_count=0,
                    header_lines=[l for l in rule.pre_lines if l.strip()],
                ))

            if current_section_idx >= 0:
                rule_to_section[real_idx] = current_section_idx
                sections[current_section_idx].rule_count += 1
            else:
                rule_to_section[real_idx] = -1
                unsectioned_indices.append(real_idx)

        except Exception:
            # Malformed rule — skip silently, never raise
            rule_to_section[real_idx] = current_section_idx

    return SectionMap(
        sections=sections,
        rule_to_section=rule_to_section,
        unsectioned_indices=unsectioned_indices,
    )


def detect_section_header(pre_lines: list[str]) -> str | None:
    """Return section name if pre_lines ends with [separator, title, separator].

    Specifically, checks if the LAST THREE non-blank lines of pre_lines
    form exactly:
        separator_line  e.g. #==========  or  #----------
        title_line      e.g. # Currency
        separator_line

    The title line content must contain at least one character that is not a
    separator character (=, -, #, space), so pure-separator lines are excluded.

    Returns the extracted title string (stripped), or None.
    """
    content = [ln for ln in pre_lines if ln.strip()]
    if len(content) < 3:
        return None
    a, b, c = content[-3], content[-2], content[-1]
    if _is_separator(a) and _is_title(b) and _is_separator(c):
        return _extract_title(b)
    return None


# ---------------------------------------------------------------------------
# Internal helpers — pure, never raise
# ---------------------------------------------------------------------------

# Separator: '#' followed by 3+ characters that are all in {=, -, #, space}
_SEP_RE = re.compile(r'^#[=\-\s#]{3,}$')

# Title: '# ' followed by at least one non-space character
_TITLE_RE = re.compile(r'^#\s+\S')

# "purely separator content" — only =, -, #, spaces after the leading '#'
_PURE_SEP_CONTENT = re.compile(r'^[\s=\-#]*$')


def _is_separator(line: str) -> bool:
    return bool(_SEP_RE.match(line.strip()))


def _is_title(line: str) -> bool:
    stripped = line.strip()
    if not _TITLE_RE.match(stripped):
        return False
    # The content after '# ' must not be purely separator characters
    content = stripped[1:].strip()
    return not _PURE_SEP_CONTENT.match(content)


def _extract_title(line: str) -> str:
    """Strip leading '#' and whitespace from a title line."""
    return line.strip()[1:].strip()
