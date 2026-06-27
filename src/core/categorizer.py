"""Rule category classification — v2.1.0

Pure functions that map FilterRule conditions to item categories.
Used by CategorySidebarWidget and RuleListWidget category filtering.
"""

from __future__ import annotations

from enum import Enum

from core.models import FilterRule


class Category(str, Enum):
    ALL = "all"
    CURRENCY = "currency"
    MAPS = "maps"
    FRAGMENTS = "fragments"
    GEMS = "gems"
    ESSENCES = "essences"
    RUNES = "runes"
    UNIQUE = "unique"
    EQUIPMENT = "equipment"
    OTHER = "other"


# Display order and sidebar metadata (label, accent dot color)
CATEGORY_SIDEBAR_ORDER: list[Category] = [
    Category.CURRENCY,
    Category.MAPS,
    Category.FRAGMENTS,
    Category.GEMS,
    Category.ESSENCES,
    Category.RUNES,
    Category.UNIQUE,
    Category.EQUIPMENT,
    Category.OTHER,
]

CATEGORY_LABELS: dict[Category, str] = {
    Category.ALL: "全部規則",
    Category.CURRENCY: "通貨",
    Category.MAPS: "地圖",
    Category.FRAGMENTS: "碎片",
    Category.GEMS: "技能石",
    Category.ESSENCES: "精華",
    Category.RUNES: "符文",
    Category.UNIQUE: "傳奇",
    Category.EQUIPMENT: "裝備",
    Category.OTHER: "其他",
}

CATEGORY_COLORS: dict[Category, str] = {
    Category.ALL: "#7c3aed",
    Category.CURRENCY: "#f6c90e",
    Category.MAPS: "#60a5fa",
    Category.FRAGMENTS: "#a855f7",
    Category.GEMS: "#4ade80",
    Category.ESSENCES: "#c084fc",
    Category.RUNES: "#38bdf8",
    Category.UNIQUE: "#f97316",
    Category.EQUIPMENT: "#94a3b8",
    Category.OTHER: "#64748b",
}

_CURRENCY_CLASSES = {
    "currency", "stackable currency", "shard", "piece",
}
_CURRENCY_BASETYPES = {"orb", "shard", "splinter", "stone"}

_MAP_CLASSES = {"maps", "waystones", "tablet", "atlas"}
_MAP_CONDITION_KEYS = {"waystonetier", "maptier"}

_FRAGMENT_CLASSES = {
    "map fragments", "breachstone", "scarab", "simulacrum",
    "offering", "vial", "piece",
}

_GEM_CLASSES = {"gem", "skill gem", "support gem", "miniature gem"}

_ESSENCE_TOKENS = {"essence"}

_RUNE_TOKENS = {"rune"}

_EQUIPMENT_CLASSES = {
    "helmet", "body armour", "gloves", "boots", "weapon",
    "two hand", "one hand", "shield", "belt", "amulet", "ring", "flask",
}


def _strip_quotes(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        return v[1:-1].strip()
    return v


def _condition_values(rule: FilterRule, key: str) -> list[str]:
    key_lower = key.lower()
    return [
        _strip_quotes(v)
        for k, v in rule.conditions
        if k.lower() == key_lower
    ]


def _has_condition_key(rule: FilterRule, key: str) -> bool:
    key_lower = key.lower()
    return any(k.lower() == key_lower for k, _ in rule.conditions)


def _values_contain_token(values: list[str], tokens: set[str]) -> bool:
    for raw in values:
        lower = raw.lower()
        for token in tokens:
            if token in lower:
                return True
    return False


def _class_matches(rule: FilterRule, tokens: set[str]) -> bool:
    return _values_contain_token(_condition_values(rule, "Class"), tokens)


def _basetype_matches(rule: FilterRule, tokens: set[str]) -> bool:
    return _values_contain_token(_condition_values(rule, "BaseType"), tokens)


def _rarity_is_unique(rule: FilterRule) -> bool:
    for val in _condition_values(rule, "Rarity"):
        if "unique" in val.lower():
            return True
    return False


def classify_rule(rule: FilterRule) -> Category:
    """Classify a single rule. Priority: first matching category wins."""
    if rule.action == "__TAIL__":
        return Category.OTHER

    if _class_matches(rule, _CURRENCY_CLASSES) or _basetype_matches(rule, _CURRENCY_BASETYPES):
        return Category.CURRENCY

    if _class_matches(rule, _MAP_CLASSES):
        return Category.MAPS
    if any(_has_condition_key(rule, k) for k in _MAP_CONDITION_KEYS):
        return Category.MAPS

    if _class_matches(rule, _FRAGMENT_CLASSES):
        return Category.FRAGMENTS

    if _class_matches(rule, _GEM_CLASSES):
        return Category.GEMS

    if _class_matches(rule, _ESSENCE_TOKENS) or _basetype_matches(rule, _ESSENCE_TOKENS):
        return Category.ESSENCES

    if _class_matches(rule, _RUNE_TOKENS) or _basetype_matches(rule, _RUNE_TOKENS):
        return Category.RUNES

    if _rarity_is_unique(rule):
        return Category.UNIQUE

    if _class_matches(rule, _EQUIPMENT_CLASSES):
        return Category.EQUIPMENT

    return Category.OTHER


def count_by_category(rules: list[FilterRule]) -> dict[Category, int]:
    """Return visible rule counts per category (excludes __TAIL__ sentinel)."""
    counts = {cat: 0 for cat in CATEGORY_SIDEBAR_ORDER}
    for rule in rules:
        if rule.action == "__TAIL__":
            continue
        counts[classify_rule(rule)] += 1
    return counts


def total_visible_rules(rules: list[FilterRule]) -> int:
    return sum(1 for r in rules if r.action != "__TAIL__")
