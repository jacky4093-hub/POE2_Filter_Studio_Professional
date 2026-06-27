"""Unit tests for core.categorizer — v2.1.0"""

import pytest

from core.models import FilterRule
from core.categorizer import (
    Category,
    classify_rule,
    count_by_category,
    total_visible_rules,
)


def _rule(**kwargs) -> FilterRule:
    return FilterRule(**kwargs)


class TestClassifyCurrency:
    def test_class_currency(self):
        r = _rule(conditions=[["Class", '"Currency"']])
        assert classify_rule(r) == Category.CURRENCY

    def test_class_stackable_currency(self):
        r = _rule(conditions=[["Class", '"Stackable Currency"']])
        assert classify_rule(r) == Category.CURRENCY

    def test_basetype_orb(self):
        r = _rule(conditions=[["BaseType", '"Divine Orb"']])
        assert classify_rule(r) == Category.CURRENCY

    def test_basetype_splinter(self):
        r = _rule(conditions=[["BaseType", '"Simulacrum Splinter"']])
        assert classify_rule(r) == Category.CURRENCY


class TestClassifyMaps:
    def test_class_waystones(self):
        r = _rule(conditions=[["Class", '"Waystones"']])
        assert classify_rule(r) == Category.MAPS

    def test_waystone_tier_condition(self):
        r = _rule(conditions=[["WaystoneTier", ">= 10"]])
        assert classify_rule(r) == Category.MAPS

    def test_map_tier_condition(self):
        r = _rule(conditions=[["MapTier", ">= 5"]])
        assert classify_rule(r) == Category.MAPS


class TestClassifyFragments:
    def test_class_map_fragments(self):
        r = _rule(conditions=[["Class", '"Map Fragments"']])
        assert classify_rule(r) == Category.FRAGMENTS

    def test_class_scarab(self):
        r = _rule(conditions=[["Class", '"Scarab"']])
        assert classify_rule(r) == Category.FRAGMENTS


class TestClassifyGems:
    def test_skill_gem(self):
        r = _rule(conditions=[["Class", '"Skill Gem"']])
        assert classify_rule(r) == Category.GEMS


class TestClassifyEssences:
    def test_class_essence(self):
        r = _rule(conditions=[["Class", '"Essence"']])
        assert classify_rule(r) == Category.ESSENCES


class TestClassifyRunes:
    def test_basetype_rune(self):
        r = _rule(conditions=[["BaseType", '"Greater Rune"']])
        assert classify_rule(r) == Category.RUNES


class TestClassifyUnique:
    def test_rarity_unique(self):
        r = _rule(conditions=[["Rarity", "Unique"]])
        assert classify_rule(r) == Category.UNIQUE


class TestClassifyEquipment:
    def test_class_helmet(self):
        r = _rule(conditions=[["Class", '"Helmet"']])
        assert classify_rule(r) == Category.EQUIPMENT

    def test_class_body_armour(self):
        r = _rule(conditions=[["Class", '"Body Armours"']])
        assert classify_rule(r) == Category.EQUIPMENT


class TestClassifyOther:
    def test_empty_rule(self):
        r = _rule()
        assert classify_rule(r) == Category.OTHER

    def test_tail_sentinel(self):
        r = _rule(action="__TAIL__")
        assert classify_rule(r) == Category.OTHER


class TestPriority:
    def test_currency_before_fragments_piece(self):
        """Piece appears in both currency and fragments — currency wins."""
        r = _rule(conditions=[["Class", '"Piece"']])
        assert classify_rule(r) == Category.CURRENCY

    def test_unique_before_equipment(self):
        r = _rule(conditions=[
            ["Rarity", "Unique"],
            ["Class", '"Helmet"'],
        ])
        assert classify_rule(r) == Category.UNIQUE


class TestCountByCategory:
    def test_counts_exclude_tail(self):
        rules = [
            _rule(conditions=[["Class", '"Currency"']]),
            _rule(conditions=[["Class", '"Waystones"']]),
            _rule(action="__TAIL__"),
        ]
        counts = count_by_category(rules)
        assert counts[Category.CURRENCY] == 1
        assert counts[Category.MAPS] == 1
        assert total_visible_rules(rules) == 2
