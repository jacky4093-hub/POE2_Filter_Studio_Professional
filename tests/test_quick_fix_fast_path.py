"""P17.9B Quick Fix Fast Path tests.

Verifies that _on_quick_fix_requested() uses the fast path
(update_single_card) instead of _reload_rule_list(), matching the
edit flow architecture established in P17.7/P17.8.

Fast path contract for quick fix:
    apply fix → UpdateRuleCommand → update_single_card(index, updated)
    → [if selected] set_rule + show_rule → _refresh_status_fast
    → _refresh_undo_actions → _validation_timer.start(300)
"""

import pytest

from PySide6.QtWidgets import QApplication

from core.quick_fix import QuickFix


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.fixture
def window(qapp, tmp_path):
    from core.settings_manager import SettingsManager
    from ui.main_window import MainWindow
    mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
    return MainWindow(settings_mgr=mgr)


def _load(window, tmp_path, text: str) -> None:
    f = tmp_path / "t.filter"
    f.write_text(text, encoding="utf-8")
    window.load_file(str(f))


# ──────────────────────────────────────────────────────────────────────
# TestQuickFixFastPath — P17.9B architecture guards
# ──────────────────────────────────────────────────────────────────────

class TestQuickFixFastPath:

    def test_fix_does_not_call_reload_rule_list(self, window, tmp_path, monkeypatch):
        """_on_quick_fix_requested must NOT call _reload_rule_list()."""
        _load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        calls = []
        monkeypatch.setattr(window, "_reload_rule_list", lambda: calls.append(True))
        window._on_quick_fix_requested(0, QuickFix("修正為 60", "SetFontSize", "60"))
        assert not calls, "_on_quick_fix_requested must not call _reload_rule_list()"

    def test_fix_calls_update_single_card(self, window, tmp_path, monkeypatch):
        """_on_quick_fix_requested must call rule_card_browser.update_single_card()."""
        _load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        calls = []
        original = window.rule_card_browser.update_single_card
        monkeypatch.setattr(
            window.rule_card_browser,
            "update_single_card",
            lambda *a, **kw: calls.append(a) or original(*a, **kw),
        )
        window._on_quick_fix_requested(0, QuickFix("修正為 60", "SetFontSize", "60"))
        assert calls, "update_single_card() must be called after quick fix"
        assert calls[0][0] == 0, "update_single_card() must receive the correct rule_index"

    def test_fix_starts_validation_timer(self, window, tmp_path):
        """_on_quick_fix_requested must start _validation_timer (300ms defer)."""
        _load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        window._on_quick_fix_requested(0, QuickFix("修正為 60", "SetFontSize", "60"))
        assert window._validation_timer.isActive(), \
            "_validation_timer must be running after quick fix"

    def test_fix_does_not_call_refresh_validation_immediately(
        self, window, tmp_path, monkeypatch
    ):
        """Validation must be deferred — _refresh_validation() NOT called synchronously."""
        _load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        calls = []
        original = window._refresh_validation
        monkeypatch.setattr(
            window,
            "_refresh_validation",
            lambda: calls.append(True) or original(),
        )
        window._on_quick_fix_requested(0, QuickFix("修正為 60", "SetFontSize", "60"))
        assert not calls, "_refresh_validation() must NOT be called synchronously on quick fix"

    def test_fix_updates_editor_when_rule_is_selected(self, window, tmp_path, monkeypatch):
        """When fixing the currently selected rule, set_rule() must be called."""
        _load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        window._navigate_to(0)
        assert window._selected_index == 0

        set_rule_calls = []
        original = window.rule_detail_editor.set_rule
        monkeypatch.setattr(
            window.rule_detail_editor,
            "set_rule",
            lambda *a, **kw: set_rule_calls.append(a) or original(*a, **kw),
        )
        window._on_quick_fix_requested(0, QuickFix("修正為 60", "SetFontSize", "60"))
        assert set_rule_calls, \
            "rule_detail_editor.set_rule() must be called when fixing the selected rule"

    def test_fix_does_not_update_editor_for_unselected_rule(
        self, window, tmp_path, monkeypatch
    ):
        """When fixing a non-selected rule, set_rule() must NOT be called."""
        _load(window, tmp_path,
              "Show\n    SetFontSize 99\n\n"
              "Show\n    SetFontSize 99\n\n")
        window._navigate_to(0)
        assert window._selected_index == 0

        set_rule_calls = []
        original = window.rule_detail_editor.set_rule
        monkeypatch.setattr(
            window.rule_detail_editor,
            "set_rule",
            lambda *a, **kw: set_rule_calls.append(a) or original(*a, **kw),
        )
        window._on_quick_fix_requested(1, QuickFix("修正為 60", "SetFontSize", "60"))
        assert not set_rule_calls, \
            "rule_detail_editor.set_rule() must NOT be called for a non-selected rule"

    def test_fix_updates_preview_when_rule_is_selected(self, window, tmp_path, monkeypatch):
        """When fixing the selected rule, preview_panel.show_rule() must be called."""
        _load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        window._navigate_to(0)

        show_calls = []
        original = window.preview_panel.show_rule
        monkeypatch.setattr(
            window.preview_panel,
            "show_rule",
            lambda *a, **kw: show_calls.append(a) or original(*a, **kw),
        )
        window._on_quick_fix_requested(0, QuickFix("修正為 60", "SetFontSize", "60"))
        assert show_calls, "preview_panel.show_rule() must be called for the selected rule"

    def test_fix_applies_correct_value_in_document(self, window, tmp_path):
        """The rule in the document must reflect the fix after _on_quick_fix_requested."""
        _load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        window._on_quick_fix_requested(0, QuickFix("修正為 60", "SetFontSize", "60"))
        vals = {str(k): str(v) for k, v in window._doc.rules[0].actions}
        assert vals["SetFontSize"] == "60"

    def test_fix_is_undoable_via_fast_path(self, window, tmp_path):
        """Even with the fast path, the fix must be undo-able."""
        _load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        window._on_quick_fix_requested(0, QuickFix("修正為 60", "SetFontSize", "60"))
        assert window._doc.can_undo()

    def test_validation_panel_updates_after_deferred_callback(self, window, tmp_path):
        """After fixing to a valid value, deferred callback must clear the warning."""
        _load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        # P17.10A: load_file() defers validation; fire it now to populate the panel
        QApplication.processEvents()
        assert window.validation_panel._list.count() >= 1
        window._on_quick_fix_requested(0, QuickFix("修正為 60", "SetFontSize", "60"))
        # Simulate timer firing
        window._on_deferred_post_edit()
        assert "0" in window.validation_panel._warning_chip.text(), \
            "After fixing SetFontSize to 60 (valid), warning count must be 0"

    def test_invalid_rule_index_ignored_fast_path(self, window, tmp_path):
        """Out-of-range rule_index must be silently ignored."""
        _load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        fix = QuickFix("x", "SetFontSize", "60")
        window._on_quick_fix_requested(-1, fix)
        window._on_quick_fix_requested(9999, fix)
