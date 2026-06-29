"""Tests for P19.3A dual-tab layout in RuleDetailEditor.

Tests cover:
- Tab bar exists with two buttons
- Tab 1: "Rule Editor", Tab 2: "Raw Filter"
- set_rule() populates raw filter text
- rule_changed updates raw filter text
- Raw filter is read-only
- Switching tabs preserves form state
- Tab bar visibility (hidden until rule loaded)
"""

import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from core.models import FilterRule
from ui.rule_detail_editor import RuleDetailEditor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rule(
    action: str = "Show",
    enabled: bool = True,
    conditions: list | None = None,
    actions: list | None = None,
    unknown_lines: list | None = None,
) -> FilterRule:
    return FilterRule(
        action=action,
        enabled=enabled,
        conditions=conditions or [],
        actions=actions or [],
        unknown_lines=unknown_lines or [],
        pre_lines=[],
        inline_comment="",
    )


def _make_editor(qapp) -> RuleDetailEditor:
    return RuleDetailEditor()


# ---------------------------------------------------------------------------
# TestP193ATabs
# ---------------------------------------------------------------------------

class TestP193ATabs:
    def test_editor_has_two_tabs(self, qapp):
        ed = _make_editor(qapp)
        assert hasattr(ed, "_tab1_btn"), "缺少 _tab1_btn"
        assert hasattr(ed, "_tab2_btn"), "缺少 _tab2_btn"
        assert isinstance(ed._tab1_btn, QPushButton)
        assert isinstance(ed._tab2_btn, QPushButton)

    def test_rule_editor_tab_exists(self, qapp):
        ed = _make_editor(qapp)
        assert "規則編輯" in ed._tab1_btn.text()

    def test_raw_filter_tab_exists(self, qapp):
        ed = _make_editor(qapp)
        assert "原始內容" in ed._tab2_btn.text()

    def test_set_rule_updates_raw_filter(self, qapp):
        ed = _make_editor(qapp)
        r = _rule(action="Show", conditions=[["ItemLevel", ">= 60"]])
        ed.set_rule(r, index=0)
        raw = ed._raw_filter_text.toPlainText()
        assert "Show" in raw
        assert "ItemLevel" in raw
        assert ">= 60" in raw

    def test_rule_changed_updates_raw_filter(self, qapp):
        ed = _make_editor(qapp)
        r = _rule(action="Show", actions=[["SetTextColor", "255 0 0 255"]])
        ed.set_rule(r, index=0)
        # Change a field and trigger update
        ed._textcolor_edit.setText("0 255 0 255")
        ed._on_any_field_changed()
        raw = ed._raw_filter_text.toPlainText()
        assert "0 255 0 255" in raw

    def test_raw_filter_read_only(self, qapp):
        ed = _make_editor(qapp)
        assert ed._raw_filter_text.isReadOnly(), "_raw_filter_text 必須是唯讀"

    def test_tab_switching_preserves_state(self, qapp):
        ed = _make_editor(qapp)
        r = _rule(action="Show", actions=[["SetTextColor", "200 100 50 255"]])
        ed.set_rule(r, index=0)

        # Switch to Raw Filter tab
        ed._tab2_btn.click()
        assert ed._stacked.currentWidget() is ed._raw_filter_page

        # Switch back to Rule Editor tab
        ed._tab1_btn.click()
        assert ed._stacked.currentWidget() is ed._editor_page

        # Form state preserved
        assert ed._textcolor_edit.text() == "200 100 50 255"

    def test_tab_bar_hidden_on_init(self, qapp):
        ed = _make_editor(qapp)
        # Tab bar should be invisible before any rule is loaded
        assert not ed._tab_bar_widget.isVisibleTo(ed), "初始化時 tab bar 應隱藏"

    def test_tab_bar_visible_after_set_rule(self, qapp):
        ed = _make_editor(qapp)
        r = _rule()
        ed.set_rule(r, index=0)
        assert ed._tab_bar_widget.isVisibleTo(ed), "set_rule 後 tab bar 應顯示"

    def test_raw_filter_disabled_action_prefix(self, qapp):
        ed = _make_editor(qapp)
        r = _rule(action="Hide", enabled=False)
        ed.set_rule(r, index=0)
        raw = ed._raw_filter_text.toPlainText()
        assert raw.startswith("# Hide")

    def test_set_rule_resets_to_tab1(self, qapp):
        ed = _make_editor(qapp)
        ed.set_rule(_rule(), index=0)
        # Switch to raw filter tab
        ed._tab2_btn.click()
        assert ed._stacked.currentWidget() is ed._raw_filter_page
        # Loading a new rule should reset to Rule Editor tab
        ed.set_rule(_rule(action="Hide"), index=1)
        assert ed._stacked.currentWidget() is ed._editor_page
        assert ed._tab1_btn.isChecked()
