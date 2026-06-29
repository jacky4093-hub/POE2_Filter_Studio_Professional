"""P18.2 Category Sidebar V4 tests.

Covers:
  1.  Widget can be instantiated
  2.  V4 header exists (CategorySidebarHeader)
  3.  CategorySearchInput exists
  4.  CategorySearchClearButton exists
  5.  CategorySidebarList still exists
  6.  CategoryActiveFilterChip exists
  7.  update_counts() still updates category counts
  8.  set_active_category() still sets the active category
  9.  active_category() still returns correct value
  10. Category search filters only sidebar list rows
  11. Category search does NOT emit category_selected
  12. Clear-search button clears the search input
  13. Active chip clear resets to Category.ALL
  14. Category search does NOT trigger RuleCardBrowser search
  15. Category search does NOT trigger validation
"""

import pytest

from PySide6.QtWidgets import QApplication, QListWidget, QLineEdit, QPushButton

from core.categorizer import Category, CATEGORY_LABELS, CATEGORY_SIDEBAR_ORDER
from core.models import FilterRule


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.fixture
def sidebar(qapp):
    from ui.category_sidebar import CategorySidebarWidget
    return CategorySidebarWidget()


def _make_rules(*classes) -> list[FilterRule]:
    """Create FilterRules with Class conditions. conditions = list of [key, string_value]."""
    return [FilterRule(action="Show", conditions=[["Class", c]]) for c in classes]


# ──────────────────────────────────────────────────────────────────────
# 1. Widget instantiation
# ──────────────────────────────────────────────────────────────────────

class TestV4Structure:
    def test_1_widget_can_be_created(self, sidebar):
        assert sidebar is not None
        assert sidebar.objectName() == "CategorySidebar"

    def test_2_header_exists(self, sidebar):
        hdr = sidebar.findChild(type(sidebar).__mro__[1], "CategorySidebarHeader")
        # Find by scanning children with matching objectName
        found = any(
            c.objectName() == "CategorySidebarHeader"
            for c in sidebar.findChildren(type(sidebar).__mro__[1])
        )
        # Use a more robust search via findChildren
        from PySide6.QtWidgets import QWidget
        headers = [c for c in sidebar.findChildren(QWidget) if c.objectName() == "CategorySidebarHeader"]
        assert headers, "CategorySidebarHeader widget not found"

    def test_3_search_input_exists(self, sidebar):
        inputs = [c for c in sidebar.findChildren(QLineEdit) if c.objectName() == "CategorySearchInput"]
        assert inputs, "CategorySearchInput not found"
        assert sidebar._search_input is inputs[0]

    def test_4_search_clear_button_exists(self, sidebar):
        btns = [c for c in sidebar.findChildren(QPushButton) if c.objectName() == "CategorySearchClearButton"]
        assert btns, "CategorySearchClearButton not found"
        assert sidebar._search_clear_btn is btns[0]

    def test_5_category_list_still_exists(self, sidebar):
        assert hasattr(sidebar, "_list")
        assert isinstance(sidebar._list, QListWidget)
        assert sidebar._list.objectName() == "CategorySidebarList"

    def test_6_active_filter_chip_exists(self, sidebar):
        from PySide6.QtWidgets import QWidget
        chips = [c for c in sidebar.findChildren(QWidget) if c.objectName() == "CategoryActiveFilterChip"]
        assert chips, "CategoryActiveFilterChip not found"
        assert sidebar._chip_container is chips[0]

    def test_quick_search_section_exists(self, sidebar):
        from PySide6.QtWidgets import QWidget
        sections = [c for c in sidebar.findChildren(QWidget) if c.objectName() == "CategoryQuickSearchSection"]
        assert sections, "CategoryQuickSearchSection not found"

    def test_quick_search_input_is_disabled(self, sidebar):
        inputs = [c for c in sidebar.findChildren(QLineEdit) if c.objectName() == "CategoryQuickSearchInput"]
        assert inputs, "CategoryQuickSearchInput not found"
        assert not inputs[0].isEnabled(), "CategoryQuickSearchInput must be disabled (P18.3 placeholder)"


# ──────────────────────────────────────────────────────────────────────
# 2. Preserved public API
# ──────────────────────────────────────────────────────────────────────

class TestPreservedAPI:
    def test_7_update_counts_updates_list(self, sidebar):
        rules = _make_rules("Currency", "Currency", "Gems")
        sidebar.update_counts(rules)
        # Find the ALL row and Currency row
        list_widget = sidebar._list
        all_row_text = list_widget.item(0).text()
        assert "全部規則" in all_row_text

        # Find Currency row
        for row in range(list_widget.count()):
            cat = list_widget.item(row).data(0x200 + 10)  # _CATEGORY_ROLE
            if cat == Category.CURRENCY:
                assert "2" in list_widget.item(row).text()
                break

    def test_8_set_active_category_works(self, sidebar):
        sidebar.set_active_category(Category.CURRENCY, emit_signal=False)
        assert sidebar._active == Category.CURRENCY

    def test_9_active_category_returns_correct(self, sidebar):
        sidebar.set_active_category(Category.GEMS, emit_signal=False)
        assert sidebar.active_category() == Category.GEMS

    def test_set_active_category_emits_signal_when_requested(self, sidebar):
        received = []
        sidebar.category_selected.connect(lambda c: received.append(c))
        sidebar.set_active_category(Category.MAPS, emit_signal=True)
        assert Category.MAPS in received

    def test_set_active_category_no_signal_by_default(self, sidebar):
        received = []
        sidebar.category_selected.connect(lambda c: received.append(c))
        sidebar.set_active_category(Category.UNIQUE, emit_signal=False)
        assert not received

    def test_all_categories_present_in_list(self, sidebar):
        from core.categorizer import CATEGORY_SIDEBAR_ORDER
        from PySide6.QtCore import Qt
        count = sidebar._list.count()
        # ALL + all sidebar categories
        assert count == 1 + len(CATEGORY_SIDEBAR_ORDER)


# ──────────────────────────────────────────────────────────────────────
# 3. Category Search behaviour
# ──────────────────────────────────────────────────────────────────────

class TestCategorySearch:
    def test_10_search_filters_list_rows(self, sidebar):
        # Reset sidebar state
        sidebar.set_active_category(Category.ALL, emit_signal=False)
        sidebar._search_input.clear()

        # Type a query that matches "通貨" (Currency)
        sidebar._search_input.setText("通貨")

        visible_rows = [
            row for row in range(sidebar._list.count())
            if not sidebar._list.isRowHidden(row)
        ]
        assert len(visible_rows) >= 1
        # The visible row must be for Currency (通貨)
        from PySide6.QtCore import Qt
        _ROLE = Qt.ItemDataRole.UserRole + 10
        visible_cats = [sidebar._list.item(r).data(_ROLE) for r in visible_rows]
        assert Category.CURRENCY in visible_cats

    def test_10b_search_hides_non_matching_rows(self, sidebar):
        sidebar._search_input.setText("通貨")
        from PySide6.QtCore import Qt
        _ROLE = Qt.ItemDataRole.UserRole + 10
        hidden_rows = [
            row for row in range(sidebar._list.count())
            if sidebar._list.isRowHidden(row)
        ]
        # At least some rows should be hidden
        assert len(hidden_rows) > 0
        # None of the hidden rows should be Currency
        for row in hidden_rows:
            cat = sidebar._list.item(row).data(_ROLE)
            assert cat != Category.CURRENCY

    def test_11_search_does_not_emit_category_selected(self, sidebar):
        received = []
        sidebar.category_selected.connect(lambda c: received.append(c))
        # Ensure clean state
        sidebar._search_input.clear()
        sidebar._search_input.setText("通貨")
        sidebar._search_input.setText("地圖")
        sidebar._search_input.clear()
        assert not received, "Category search must not emit category_selected"

    def test_empty_query_shows_all_rows(self, sidebar):
        sidebar._search_input.setText("通貨")
        sidebar._search_input.clear()
        hidden_rows = [
            row for row in range(sidebar._list.count())
            if sidebar._list.isRowHidden(row)
        ]
        assert not hidden_rows, "All rows should be visible when search is empty"

    def test_12_clear_button_clears_search(self, sidebar):
        sidebar._search_input.setText("通貨")
        assert sidebar._search_input.text() == "通貨"
        assert sidebar._search_clear_btn.isEnabled()

        sidebar._search_clear_btn.click()

        assert sidebar._search_input.text() == ""
        assert not sidebar._search_clear_btn.isEnabled()

    def test_clear_button_enabled_only_when_text_present(self, sidebar):
        sidebar._search_input.clear()
        assert not sidebar._search_clear_btn.isEnabled()
        sidebar._search_input.setText("x")
        assert sidebar._search_clear_btn.isEnabled()
        sidebar._search_input.clear()
        assert not sidebar._search_clear_btn.isEnabled()


# ──────────────────────────────────────────────────────────────────────
# 4. Active Filter Chip
# ──────────────────────────────────────────────────────────────────────

class TestActiveFilterChip:
    def test_chip_hidden_when_all(self, sidebar):
        sidebar.set_active_category(Category.ALL, emit_signal=False)
        # isHidden() reflects explicit hide() state independent of whether parent is shown
        assert sidebar._chip_container.isHidden()

    def test_chip_shown_when_category_selected(self, sidebar):
        sidebar.set_active_category(Category.CURRENCY, emit_signal=False)
        assert not sidebar._chip_container.isHidden()

    def test_chip_text_shows_category_label(self, sidebar):
        sidebar.set_active_category(Category.GEMS, emit_signal=False)
        assert "技能石" in sidebar._chip_label.text()

    def test_13_chip_clear_resets_to_all(self, sidebar):
        sidebar.set_active_category(Category.CURRENCY, emit_signal=False)
        assert sidebar._active == Category.CURRENCY

        received = []
        sidebar.category_selected.connect(lambda c: received.append(c))
        sidebar._chip_clear_btn.click()

        assert sidebar._active == Category.ALL
        assert not sidebar._chip_container.isVisible()
        assert Category.ALL in received

    def test_chip_clear_from_all_does_not_emit(self, sidebar):
        """Clicking clear when already on ALL must not double-emit."""
        sidebar.set_active_category(Category.ALL, emit_signal=False)
        received = []
        sidebar.category_selected.connect(lambda c: received.append(c))
        sidebar._chip_clear_btn.click()
        # chip clear from ALL: was_filtered=False, so nothing emitted
        assert not received

    def test_chip_clear_also_clears_search(self, sidebar):
        sidebar.set_active_category(Category.MAPS, emit_signal=False)
        sidebar._search_input.setText("地圖")
        sidebar._chip_clear_btn.click()
        assert sidebar._search_input.text() == ""


# ──────────────────────────────────────────────────────────────────────
# 5. Isolation — no RuleCardBrowser or validation side-effects
# ──────────────────────────────────────────────────────────────────────

class TestIsolation:
    def test_14_sidebar_has_no_rule_browser_reference(self, sidebar):
        """CategorySidebarWidget must not hold a reference to RuleCardBrowser."""
        assert not hasattr(sidebar, "rule_card_browser")
        assert not hasattr(sidebar, "_browser")

    def test_15_sidebar_has_no_validator_reference(self, sidebar):
        """CategorySidebarWidget must not hold a reference to a validator."""
        assert not hasattr(sidebar, "_validator")
        assert not hasattr(sidebar, "validation_panel")

    def test_category_search_changes_only_row_visibility(self, sidebar):
        """Search must only toggle row visibility — no external calls."""
        sidebar._search_input.clear()
        initial_count = sidebar._list.count()
        sidebar._search_input.setText("通貨")
        # Item count must not change (hiding != removing)
        assert sidebar._list.count() == initial_count
        sidebar._search_input.clear()
        assert sidebar._list.count() == initial_count

    def test_update_counts_does_not_affect_row_visibility(self, sidebar):
        """update_counts() must not reset the category search filter."""
        sidebar._search_input.setText("通貨")
        hidden_before = [row for row in range(sidebar._list.count()) if sidebar._list.isRowHidden(row)]
        rules = _make_rules("Currency", "Gems")
        sidebar.update_counts(rules)
        hidden_after = [row for row in range(sidebar._list.count()) if sidebar._list.isRowHidden(row)]
        assert hidden_before == hidden_after


# ──────────────────────────────────────────────────────────────────────
# 6. P19.1 Emoji Icons & Text Format
# ──────────────────────────────────────────────────────────────────────

class TestP19Icons:
    """P19.1: verify emoji mapping, text format, and backward-compat of all public API."""

    def test_all_categories_have_emoji_mapping(self, qapp):
        """Every Category in the enum must have an entry in _CATEGORY_EMOJI."""
        from ui.category_sidebar import _CATEGORY_EMOJI
        for cat in Category:
            assert cat in _CATEGORY_EMOJI, f"_CATEGORY_EMOJI missing mapping for {cat}"

    def test_format_item_text_contains_emoji_and_label(self, qapp):
        """_format_item_text() must include the emoji and the Chinese label."""
        from ui.category_sidebar import _format_item_text, _CATEGORY_EMOJI
        for cat in Category:
            text = _format_item_text(cat, 42)
            assert _CATEGORY_EMOJI[cat] in text, f"Emoji missing in text for {cat}"
            assert CATEGORY_LABELS[cat] in text, f"Label missing in text for {cat}"
            assert "42" in text, f"Count missing in text for {cat}"

    def test_format_item_text_never_crashes(self, qapp):
        """_format_item_text() must not raise for any Category value."""
        from ui.category_sidebar import _format_item_text
        for cat in Category:
            text = _format_item_text(cat, 0)
            assert isinstance(text, str) and text, f"Must return non-empty str for {cat}"

    def test_sidebar_items_contain_emoji(self, sidebar):
        """After construction, every list item must have an emoji in its text."""
        from ui.category_sidebar import _CATEGORY_EMOJI
        from PySide6.QtCore import Qt
        _ROLE = Qt.ItemDataRole.UserRole + 10
        for row in range(sidebar._list.count()):
            item = sidebar._list.item(row)
            cat = item.data(_ROLE)
            if cat is not None:
                emoji = _CATEGORY_EMOJI.get(cat, "")
                assert emoji in item.text(), \
                    f"Item text for {cat} must contain emoji '{emoji}', got: {item.text()!r}"

    def test_sidebar_items_contain_label(self, sidebar):
        """After construction, every list item must contain the category label."""
        from PySide6.QtCore import Qt
        _ROLE = Qt.ItemDataRole.UserRole + 10
        for row in range(sidebar._list.count()):
            item = sidebar._list.item(row)
            cat = item.data(_ROLE)
            if cat is not None:
                assert CATEGORY_LABELS[cat] in item.text(), \
                    f"Item text for {cat} must contain label '{CATEGORY_LABELS[cat]}'"

    def test_update_counts_preserves_emoji(self, sidebar):
        """update_counts() must keep the emoji in every item's text."""
        from ui.category_sidebar import _CATEGORY_EMOJI
        from PySide6.QtCore import Qt
        _ROLE = Qt.ItemDataRole.UserRole + 10
        rules = _make_rules("Currency", "Currency", "Gems")
        sidebar.update_counts(rules)
        for row in range(sidebar._list.count()):
            item = sidebar._list.item(row)
            cat = item.data(_ROLE)
            if cat is not None:
                emoji = _CATEGORY_EMOJI.get(cat, "")
                assert emoji in item.text(), \
                    f"Emoji must remain after update_counts() for {cat}"

    def test_update_counts_has_correct_count(self, sidebar):
        """update_counts() must embed the correct count number in item text."""
        from PySide6.QtCore import Qt
        _ROLE = Qt.ItemDataRole.UserRole + 10
        rules = _make_rules("Currency", "Currency", "Currency")
        sidebar.update_counts(rules)
        found = False
        for row in range(sidebar._list.count()):
            item = sidebar._list.item(row)
            cat = item.data(_ROLE)
            if cat == Category.CURRENCY:
                assert "3" in item.text(), \
                    f"Currency item must show count 3, got: {item.text()!r}"
                found = True
                break
        assert found, "Currency row must exist in sidebar list"

    def test_set_active_category_still_works_with_emoji_items(self, sidebar):
        """set_active_category() must set _active correctly with new emoji item format."""
        sidebar.set_active_category(Category.MAPS, emit_signal=False)
        assert sidebar.active_category() == Category.MAPS

    def test_category_selected_signal_still_fires_with_emoji_items(self, sidebar):
        """category_selected must emit the correct Category with emoji item format."""
        received = []
        sidebar.category_selected.connect(lambda c: received.append(c))
        sidebar.set_active_category(Category.RUNES, emit_signal=True)
        assert Category.RUNES in received, "signal must carry Category.RUNES"

    def test_search_filter_still_works_with_emoji_items(self, sidebar):
        """Category search must still filter by label, not emoji text."""
        sidebar._search_input.clear()
        sidebar._search_input.setText("通貨")
        from PySide6.QtCore import Qt
        _ROLE = Qt.ItemDataRole.UserRole + 10
        visible = [
            sidebar._list.item(r).data(_ROLE)
            for r in range(sidebar._list.count())
            if not sidebar._list.isRowHidden(r)
        ]
        assert Category.CURRENCY in visible, "Currency must be visible when searching '通貨'"
        sidebar._search_input.clear()

    def test_active_filter_chip_text_unchanged(self, sidebar):
        """Chip label must still show the plain label (no emoji) after P19.1."""
        sidebar.set_active_category(Category.GEMS, emit_signal=False)
        assert "技能石" in sidebar._chip_label.text()

    def test_no_icon_registry_dependency(self, qapp):
        """category_sidebar module must not import IconRegistry after P19.1."""
        import ui.category_sidebar as mod
        assert not hasattr(mod, "IconRegistry"), \
            "category_sidebar must not reference IconRegistry after P19.1 emoji migration"
