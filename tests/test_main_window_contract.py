"""Guardrail tests for MainWindow behavior contract.

These tests document and protect a small set of high-value façade behaviors
for the upcoming P12 refactor without over-testing internals.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from core.document import FilterDocument
from core.models import FilterRule
from ui.main_window import MainWindow
from ui.preview_panel import PreviewPanel
from ui.rule_card_browser import RuleCardBrowser
from ui.rule_detail_editor import RuleDetailEditor


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


class TestMainWindowContractFacade:
    def test_main_window_exposes_core_widget_attributes(self, qapp):
        window = MainWindow()

        assert hasattr(window, "welcome_screen")
        assert hasattr(window, "rule_card_browser")
        assert hasattr(window, "filter_search_bar")
        assert hasattr(window, "search_bar")
        assert hasattr(window, "category_sidebar")
        assert hasattr(window, "rule_detail_editor")
        assert hasattr(window, "preview_panel")

        assert isinstance(window.rule_card_browser, RuleCardBrowser)
        assert isinstance(window.rule_detail_editor, RuleDetailEditor)
        assert isinstance(window.preview_panel, PreviewPanel)

    def test_load_invalid_file_silent_true_does_not_show_message_box(self, qapp, monkeypatch):
        window = MainWindow()
        called = False

        def fake_warning(*args, **kwargs):
            nonlocal called
            called = True
            return None

        monkeypatch.setattr(QMessageBox, "critical", fake_warning)
        result = window.load_file("/definitely/missing.filter", silent=True)

        assert result is False
        assert called is False

    def test_filtered_out_selection_clears_editor_and_preview(self, qapp):
        window = MainWindow()
        rule = FilterRule(action="Show", conditions=[["Class", '"Currency"']])
        window._doc = FilterDocument()
        window._doc.rules.append(rule)
        window._doc.rules.append(FilterRule(action="Show", conditions=[["Class", '"Waystones"']]))
        window._section_map = None
        window._selected_index = 0
        window._editing_snapshot = None

        window.rule_card_browser.load_rules(window._doc.rules, window._section_map)
        window.rule_detail_editor.set_rule(rule, 0)
        window.preview_panel.show_rule(rule)
        window.show()
        window.preview_panel.show()
        QApplication.processEvents()

        window.rule_card_browser.set_search_filter("Waystones")
        window._on_filter_search_changed("Waystones", {})
        QApplication.processEvents()

        assert window._selected_index == -1
        assert window.rule_detail_editor._stacked.currentWidget() is window.rule_detail_editor._empty_page
        assert window.preview_panel._empty_label.isHidden() is False
        assert window.preview_panel._action_label.isHidden() is True
        assert window.preview_panel._item_label.isHidden() is True

    def test_save_clears_dirty_state_after_success(self, qapp, tmp_path):
        window = MainWindow()
        path = tmp_path / "sample.filter"
        window._doc = FilterDocument()
        window._doc.rules.append(FilterRule(action="Show"))
        window._doc.set_file_path(str(path))
        window._doc.mark_dirty()

        window._file_mgr = type("DummyFileManager", (), {
            "serialize_rules": lambda self, rules: "Show\n",
            "save_as": lambda self, text, target: open(target, "w", encoding="utf-8").write(text),
        })()

        window._write_to(str(path))

        assert window._doc.dirty is False
