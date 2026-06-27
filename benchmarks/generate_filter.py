"""Synthetic filter generator for benchmarks.

Generates realistic .filter content at any scale.
Produces a mix of:
  - ~10% rules with section headers (#===)
  - ~40% Show rules with conditions + appearance
  - ~30% Hide rules with conditions only
  - ~20% rules with comments / blank pre_lines only

Usage:
    from benchmarks.generate_filter import make_filter_text
    text = make_filter_text(n_rules=1000)
"""

import random
import string

# Deterministic seed for reproducible benchmarks
_RNG = random.Random(42)

# Pools drawn from real PoE2 filter vocabulary
_CLASSES = [
    '"Currency"', '"Stackable Currency"', '"Gem"', '"Skill Gem"',
    '"Flask"', '"Map"', '"Tablet"', '"Amulet"', '"Ring"', '"Belt"',
    '"Helmet"', '"Body Armour"', '"Gloves"', '"Boots"', '"Weapon"',
    '"Shield"', '"Waystones"', '"Sanctum Relic"',
]
_BASE_TYPES = [
    '"Chaos Orb"', '"Orb of Alteration"', '"Divine Orb"',
    '"Mirror of Kalandra"', '"Exalted Orb"', '"Orb of Annulment"',
    '"Vaal Orb"', '"Regal Orb"', '"Blessed Orb"', '"Transmutation Orb"',
    '"Quicksilver Flask"', '"Life Flask"', '"Mana Flask"',
]
_RARITIES   = ["Normal", "Magic", "Rare", "Unique"]
_SOUNDS     = ["1", "2", "3", "4", "6", "9", "10", "16"]
_MINIMAP    = ["Circle", "Diamond", "Hexagon", "Square", "Star", "Triangle"]
_COLOURS_MM = ["Blue", "Brown", "Cyan", "Green", "Grey", "Orange",
               "Pink", "Purple", "Red", "White", "Yellow"]
_BEAM_COLS  = ["Blue", "Brown", "Cyan", "Green", "Grey", "Orange",
               "Pink", "Purple", "Red", "White", "Yellow"]

_SECTION_NAMES = [
    "Currency", "Stackable Currency", "Fragments", "Maps",
    "Gems", "Unique Items", "Rare Items", "Magic Items",
    "Normal Items", "Flasks", "Waystones", "Jewels",
    "Amulets", "Rings", "Belts", "Weapons", "Armour",
    "Sanctum Relics", "End-Game", "Levelling Gear",
    "Hidden Items", "Quest Items", "Endgame Maps",
    "Economy Picks", "Boss Drops", "League Mechanics",
]


def _rgba(bright: bool = False) -> str:
    if bright:
        return f"{_RNG.randint(180,255)} {_RNG.randint(180,255)} {_RNG.randint(180,255)} 255"
    return f"{_RNG.randint(0,180)} {_RNG.randint(0,180)} {_RNG.randint(0,180)} 255"


def _make_show_rule(idx: int) -> list[str]:
    lines = [""]  # blank pre_line
    lines.append("Show")
    # Pick 1-2 conditions
    n_cond = _RNG.randint(1, 2)
    if n_cond >= 1:
        lines.append(f"    Class {_RNG.choice(_CLASSES)}")
    if n_cond >= 2:
        lines.append(f"    ItemLevel >= {_RNG.randint(1, 80)}")
    # Appearance
    lines.append(f"    SetTextColor {_rgba(bright=True)}")
    lines.append(f"    SetBorderColor {_rgba()}")
    if _RNG.random() > 0.5:
        lines.append(f"    SetFontSize {_RNG.choice([32, 36, 40, 45])}")
    if _RNG.random() > 0.6:
        lines.append(
            f"    SetMinimapIcon 1 {_RNG.choice(_COLOURS_MM)} {_RNG.choice(_MINIMAP)}"
        )
    if _RNG.random() > 0.7:
        lines.append(
            f"    SetBeam {_RNG.choice(_BEAM_COLS)} Temporary"
        )
    if _RNG.random() > 0.5:
        lines.append(
            f"    PlayAlertSound {_RNG.choice(_SOUNDS)} {_RNG.randint(100, 300)}"
        )
    return lines


def _make_hide_rule(idx: int) -> list[str]:
    lines = [""]
    lines.append("Hide")
    # 1-3 conditions
    n_cond = _RNG.randint(1, 3)
    opts = [
        f"    Class {_RNG.choice(_CLASSES)}",
        f"    Rarity {_RNG.choice(_RARITIES)}",
        f"    ItemLevel <= {_RNG.randint(1, 50)}",
        f"    AreaLevel >= {_RNG.randint(1, 80)}",
        f"    BaseType {_RNG.choice(_BASE_TYPES)}",
    ]
    _RNG.shuffle(opts)
    lines.extend(opts[:n_cond])
    return lines


def _make_commented_rule(idx: int) -> list[str]:
    lines = ["", f"# Rule {idx} disabled"]
    lines.append("# Show")
    lines.append(f"#     Class {_RNG.choice(_CLASSES)}")
    return lines


def _make_section_header(name: str) -> list[str]:
    sep = "#" + "=" * 48
    return ["", sep, f"# {name}", sep]


def make_filter_text(
    n_rules: int,
    section_every: int = 10,
) -> str:
    """Return .filter text string containing approximately *n_rules* visible rules.

    A section header is injected every *section_every* rules (default 10).
    section_every=0 disables sections entirely.
    """
    lines: list[str] = [
        "# POE2 Filter Studio — Synthetic Benchmark Filter",
        f"# n_rules={n_rules}",
        "",
    ]

    section_names = list(_SECTION_NAMES)
    _RNG.shuffle(section_names)
    sec_cycle = (section_names * ((n_rules // section_every + 2))
                 if section_every > 0 else [])
    sec_idx = 0

    for i in range(n_rules):
        # Inject section header
        if section_every > 0 and i % section_every == 0:
            name = sec_cycle[sec_idx % len(sec_cycle)]
            sec_idx += 1
            lines.extend(_make_section_header(name))

        # Rule type distribution
        r = _RNG.random()
        if r < 0.40:
            lines.extend(_make_show_rule(i))
        elif r < 0.70:
            lines.extend(_make_hide_rule(i))
        else:
            lines.extend(_make_commented_rule(i))

    lines.append("")
    return "\n".join(lines)
