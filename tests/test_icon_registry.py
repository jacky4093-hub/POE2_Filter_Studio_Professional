"""Tests for IconRegistry and widget integration — P15.1 Icon System

Covers:
- IconRegistry returns QIcon for every category / action / template
- SVG source files exist on disk
- No widget hardcodes paths (they receive QIcon from registry)
- Widgets expose icon on list items / pixmap labels
"""

import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from core.categorizer import Category, CATEGORY_SIDEBAR_ORDER
from assets.icon_registry import IconRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    """Ensure a clean icon cache before each test."""
    IconRegistry.clear_cache()
    yield
    IconRegistry.clear_cache()


# ---------------------------------------------------------------------------
# TestIconRegistryInterface
# ---------------------------------------------------------------------------

class TestIconRegistryInterface:
    """Public methods exist and return QIcon."""

    def test_get_category_icon_returns_qicon(self, qapp):
        icon = IconRegistry.get_category_icon(Category.CURRENCY)
        assert isinstance(icon, QIcon)

    def test_get_rule_action_icon_returns_qicon(self, qapp):
        icon = IconRegistry.get_rule_action_icon("Show")
        assert isinstance(icon, QIcon)

    def test_get_template_icon_returns_qicon(self, qapp):
        icon = IconRegistry.get_template_icon("Currency")
        assert isinstance(icon, QIcon)

    def test_unknown_action_returns_null_qicon(self, qapp):
        icon = IconRegistry.get_rule_action_icon("__TAIL__")
        assert icon.isNull()

    def test_unknown_template_falls_back_to_empty(self, qapp):
        icon = IconRegistry.get_template_icon("NoSuchTemplate")
        assert isinstance(icon, QIcon)

    def test_icon_registry_caches_result(self, qapp):
        a = IconRegistry.get_category_icon(Category.CURRENCY)
        b = IconRegistry.get_category_icon(Category.CURRENCY)
        assert a is b   # same cached object

    def test_clear_cache_allows_reload(self, qapp):
        a = IconRegistry.get_category_icon(Category.MAPS)
        IconRegistry.clear_cache()
        b = IconRegistry.get_category_icon(Category.MAPS)
        # different object instances after cache clear
        assert a is not b


# ---------------------------------------------------------------------------
# TestSvgFilesExist
# ---------------------------------------------------------------------------

class TestSvgFilesExist:
    """Verify every SVG placeholder file is present on disk."""

    def test_icons_directory_exists(self):
        icons_dir = IconRegistry.icon_path("category_currency").parent
        assert icons_dir.is_dir()

    @pytest.mark.parametrize("cat", [Category.ALL] + CATEGORY_SIDEBAR_ORDER)
    def test_category_svg_file_exists(self, cat):
        path = IconRegistry.icon_path(f"category_{cat.value}")
        assert path.exists(), f"Missing: {path.name}"

    @pytest.mark.parametrize("action", ["show", "hide", "continue"])
    def test_action_svg_file_exists(self, action):
        path = IconRegistry.icon_path(f"action_{action}")
        assert path.exists(), f"Missing: {path.name}"

    @pytest.mark.parametrize("stem", [
        "category_currency", "category_unique",
        "template_rare", "template_magic", "template_empty",
        "category_gems", "category_maps",
    ])
    def test_template_backing_svg_exists(self, stem):
        path = IconRegistry.icon_path(stem)
        assert path.exists(), f"Missing: {path.name}"


# ---------------------------------------------------------------------------
# TestCategoryIcons
# ---------------------------------------------------------------------------

class TestCategoryIcons:
    """get_category_icon() returns a non-null icon for every sidebar category."""

    @pytest.mark.parametrize("cat", [Category.ALL] + CATEGORY_SIDEBAR_ORDER)
    def test_category_icon_not_null(self, qapp, cat):
        icon = IconRegistry.get_category_icon(cat)
        assert not icon.isNull(), f"Null icon for {cat}"

    def test_all_category_returns_icon(self, qapp):
        icon = IconRegistry.get_category_icon(Category.ALL)
        assert isinstance(icon, QIcon)
        assert not icon.isNull()

    def test_currency_icon_file_has_svg_content(self):
        path = IconRegistry.icon_path("category_currency")
        content = path.read_text(encoding="utf-8")
        assert "<svg" in content
        assert "<circle" in content


# ---------------------------------------------------------------------------
# TestActionIcons
# ---------------------------------------------------------------------------

class TestActionIcons:
    """get_rule_action_icon() returns correct icons for the three rule actions."""

    def test_show_icon_not_null(self, qapp):
        assert not IconRegistry.get_rule_action_icon("Show").isNull()

    def test_hide_icon_not_null(self, qapp):
        assert not IconRegistry.get_rule_action_icon("Hide").isNull()

    def test_continue_icon_not_null(self, qapp):
        assert not IconRegistry.get_rule_action_icon("Continue").isNull()

    def test_case_insensitive_lookup(self, qapp):
        icon_upper = IconRegistry.get_rule_action_icon("SHOW")
        # action_show.svg exists; this should not be null
        assert not icon_upper.isNull()


# ---------------------------------------------------------------------------
# TestTemplateIcons
# ---------------------------------------------------------------------------

class TestTemplateIcons:
    """get_template_icon() returns icons for all 7 wizard templates."""

    _TEMPLATE_NAMES = [
        "Currency",
        "Unique 物品",
        "Rare 物品",
        "Magic 物品",
        "Gem",
        "Waystone",
        "空規則",
    ]

    @pytest.mark.parametrize("name", _TEMPLATE_NAMES)
    def test_template_icon_not_null(self, qapp, name):
        icon = IconRegistry.get_template_icon(name)
        assert not icon.isNull(), f"Null icon for template '{name}'"

    def test_currency_template_reuses_category_icon(self, qapp):
        currency_cat  = IconRegistry.get_category_icon(Category.CURRENCY)
        currency_tmpl = IconRegistry.get_template_icon("Currency")
        # Both resolve to the same cached QIcon object
        assert currency_cat is currency_tmpl

    def test_gem_template_reuses_category_gem_icon(self, qapp):
        gem_cat  = IconRegistry.get_category_icon(Category.GEMS)
        gem_tmpl = IconRegistry.get_template_icon("Gem")
        assert gem_cat is gem_tmpl


# ---------------------------------------------------------------------------
# TestWidgetsUseRegistry
# ---------------------------------------------------------------------------

class TestWidgetsUseRegistry:
    """Widgets integrate with IconRegistry — no hardcoded paths."""

    def test_category_sidebar_items_have_emoji(self, qapp):
        """P19.1: sidebar uses emoji-in-text instead of SVG icons.
        Each item text must contain the category's emoji from _CATEGORY_EMOJI."""
        from ui.category_sidebar import CategorySidebarWidget, _CATEGORY_EMOJI
        from PySide6.QtCore import Qt
        _ROLE = Qt.ItemDataRole.UserRole + 10
        sidebar = CategorySidebarWidget()
        for row in range(sidebar._list.count()):
            item = sidebar._list.item(row)
            cat = item.data(_ROLE)
            if cat is not None:
                emoji = _CATEGORY_EMOJI.get(cat, "")
                assert emoji and emoji in item.text(), (
                    f"Sidebar row {row} (cat={cat}) must have emoji '{emoji}' "
                    f"in text: '{item.text()}'"
                )

    def test_rule_creation_dialog_items_have_icons(self, qapp):
        from ui.rule_creation_dialog import RuleCreationDialog
        dlg = RuleCreationDialog()
        for row in range(dlg._list.count()):
            item = dlg._list.item(row)
            assert not item.icon().isNull(), (
                f"Template row {row} has null icon: '{item.text()}'"
            )

    def test_rule_card_widget_has_action_icon_label(self, qapp):
        from core.models import FilterRule
        from ui.rule_card_widget import RuleCardWidget
        rule = FilterRule(action="Show", conditions=[["Class", "Currency"]])
        card = RuleCardWidget(0, rule, 1)
        # Verify at least one RuleCardActionIcon label exists in the widget tree
        labels = card.findChildren(__import__("PySide6.QtWidgets", fromlist=["QLabel"]).QLabel,
                                   "RuleCardActionIcon")
        assert len(labels) >= 1

    def test_rule_card_widget_hide_has_action_icon(self, qapp):
        from core.models import FilterRule
        from ui.rule_card_widget import RuleCardWidget
        rule = FilterRule(action="Hide", conditions=[["Rarity", "Unique"]])
        card = RuleCardWidget(0, rule, 1)
        from PySide6.QtWidgets import QLabel
        labels = card.findChildren(QLabel, "RuleCardActionIcon")
        assert len(labels) >= 1

    def test_tail_card_has_no_action_icon(self, qapp):
        """__TAIL__ pseudo-rule has no visible icon (null QIcon guard).

        P17.6: the icon label is always created for in-place updates, but
        must be hidden when the icon registry returns a null icon (__TAIL__).
        """
        from core.models import FilterRule
        from ui.rule_card_widget import RuleCardWidget
        rule = FilterRule(action="__TAIL__")
        card = RuleCardWidget(0, rule, 1)
        from PySide6.QtWidgets import QLabel
        labels = card.findChildren(QLabel, "RuleCardActionIcon")
        visible = [lbl for lbl in labels if not lbl.isHidden()]
        assert len(visible) == 0, "__TAIL__ must have no visible action icon"
