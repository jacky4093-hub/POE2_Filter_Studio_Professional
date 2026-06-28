"""P17.10A Large File Loading Optimization tests.

Verifies three low-risk optimizations introduced in P17.10A:

  A-1  Deferred Validation — load_file() no longer calls _refresh_validation()
       synchronously; it is scheduled via QTimer.singleShot(0, ...) instead.

  A-2  setUpdatesEnabled guard — RuleCardBrowser._rebuild_card_pool() disables
       Qt updates on the content widget during bulk widget creation and restores
       them unconditionally (even on exception) via try/finally.

  A-3  Deferred Category Count — load_file() no longer calls
       category_sidebar.update_counts() synchronously; it is scheduled via
       QTimer.singleShot(0, ...) with a stale-data guard.

Also verifies that the P17.9B (quick fix) and P17.8 (detail editor) fast paths
are NOT regressed by these changes.
"""

from __future__ import annotations

import pytest

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from core.models import FilterRule
from core.quick_fix import QuickFix


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

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


@pytest.fixture
def browser(qapp):
    from ui.rule_card_browser import RuleCardBrowser
    return RuleCardBrowser()


def _load(window, tmp_path, text: str) -> None:
    f = tmp_path / "t.filter"
    f.write_text(text, encoding="utf-8")
    window.load_file(str(f))


def _rule(**kwargs) -> FilterRule:
    return FilterRule(
        action=kwargs.get("action", "Show"),
        enabled=kwargs.get("enabled", True),
        conditions=kwargs.get("conditions", [["Class", '"Currency"']]),
        actions=kwargs.get("actions", []),
        pre_lines=[],
        inline_comment="",
        unknown_lines=[],
    )


# ──────────────────────────────────────────────────────────────────────
# A-1  Deferred Validation
# ──────────────────────────────────────────────────────────────────────

class TestDeferredValidation:

    def test_load_file_does_not_refresh_validation_synchronously(
        self, window, tmp_path, monkeypatch
    ):
        """_refresh_validation() must NOT be called during load_file()."""
        calls = []
        original = window._refresh_validation
        monkeypatch.setattr(
            window,
            "_refresh_validation",
            lambda: calls.append(True) or original(),
        )
        _load(window, tmp_path, "Show\n    Class \"Currency\"\n\n")
        assert not calls, \
            "load_file() must NOT call _refresh_validation() synchronously"

    def test_load_file_schedules_deferred_validation(
        self, window, tmp_path, monkeypatch
    ):
        """After load_file(), _refresh_validation() fires on the next event loop."""
        calls = []
        original = window._refresh_validation
        monkeypatch.setattr(
            window,
            "_refresh_validation",
            lambda: calls.append(True) or original(),
        )
        _load(window, tmp_path, "Show\n    Class \"Currency\"\n\n")
        assert not calls, "precondition: no synchronous call"
        # Let the QTimer.singleShot(0, ...) fire
        QApplication.processEvents()
        assert len(calls) >= 1, \
            "Deferred _refresh_validation() must fire after processEvents()"

    def test_validation_panel_eventually_shows_issues(self, window, tmp_path):
        """Validation panel must be populated once the deferred callback fires."""
        _load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        # Before deferred fire: panel may still show previous state
        QApplication.processEvents()
        # After deferred fire: 99 > 60 so one warning
        count = window.validation_panel._list.count()
        assert count >= 1, "Validation panel must show issues after deferred refresh"

    def test_load_file_stops_pending_validation_timer(self, window, tmp_path):
        """load_file() must stop any running _validation_timer to prevent double fire."""
        # Start the timer (simulates a pending debounce from previous edit)
        window._validation_timer.start(300)
        assert window._validation_timer.isActive()
        _load(window, tmp_path, "Show\n    Class \"Currency\"\n\n")
        # The timer must be stopped by load_file()
        assert not window._validation_timer.isActive(), \
            "load_file() must stop _validation_timer to cancel stale debounce"


# ──────────────────────────────────────────────────────────────────────
# A-2  setUpdatesEnabled guard
# ──────────────────────────────────────────────────────────────────────

class TestSetUpdatesEnabledGuard:

    def test_content_updates_enabled_after_load(self, browser):
        """After load_rules(), _content.updatesEnabled() must be True."""
        rules = [_rule()]
        browser.load_rules(rules, None)
        assert browser._content.updatesEnabled(), \
            "_content.setUpdatesEnabled(True) must be called after _rebuild_card_pool()"

    def test_rebuild_card_pool_disables_updates_during_bulk_build(self, browser):
        """Updates must be disabled on _content while cards are being created."""
        states = []
        original_clear = browser._clear_all_layout_items

        def spy_clear():
            # Capture the state at the very start of the pool build
            states.append(browser._content.updatesEnabled())
            return original_clear()

        browser._clear_all_layout_items = spy_clear
        browser.load_rules([_rule()], None)

        assert states, "spy must have been invoked"
        assert states[0] is False, \
            "_content.setUpdatesEnabled(False) must be called before pool construction"

    def test_rebuild_card_pool_restores_updates_enabled_on_exception(
        self, browser, monkeypatch
    ):
        """setUpdatesEnabled(True) must be called even when _make_card() raises."""
        call_count = [0]
        original_make_card = browser._make_card

        def raising_make_card(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] >= 1:
                raise RuntimeError("simulated widget creation error")
            return original_make_card(*args, **kwargs)

        monkeypatch.setattr(browser, "_make_card", raising_make_card)

        with pytest.raises(RuntimeError):
            browser.load_rules([_rule()], None)

        assert browser._content.updatesEnabled(), \
            "_content.setUpdatesEnabled(True) must be restored after exception"

    def test_updates_enabled_before_first_load(self, browser):
        """Newly constructed browser must have updates enabled (baseline)."""
        assert browser._content.updatesEnabled()

    def test_load_rules_twice_leaves_updates_enabled(self, browser):
        """Multiple load_rules() calls must not leave updates disabled."""
        browser.load_rules([_rule()], None)
        browser.load_rules([_rule(), _rule(action="Hide")], None)
        assert browser._content.updatesEnabled()

    def test_update_single_card_unaffected_by_guard(self, browser):
        """update_single_card() (fast path) must still work normally after the guard."""
        import copy
        rules = [_rule()]
        browser.load_rules(rules, None)
        updated = copy.deepcopy(rules[0])
        updated.inline_comment = "# updated"
        result = browser.update_single_card(0, updated)
        assert result is True
        assert browser._content.updatesEnabled()


# ──────────────────────────────────────────────────────────────────────
# A-3  Deferred Category Count
# ──────────────────────────────────────────────────────────────────────

class TestDeferredCategoryCount:

    def test_load_file_does_not_update_category_counts_synchronously(
        self, window, tmp_path, monkeypatch
    ):
        """category_sidebar.update_counts() must NOT be called during load_file()."""
        calls = []
        original = window.category_sidebar.update_counts
        monkeypatch.setattr(
            window.category_sidebar,
            "update_counts",
            lambda rules: calls.append(rules) or original(rules),
        )
        _load(window, tmp_path, "Show\n    Class \"Currency\"\n\n")
        assert not calls, \
            "load_file() must NOT call category_sidebar.update_counts() synchronously"

    def test_category_counts_updated_after_deferred_callback(
        self, window, tmp_path, monkeypatch
    ):
        """update_counts() must be called once the deferred callback fires."""
        calls = []
        original = window.category_sidebar.update_counts
        monkeypatch.setattr(
            window.category_sidebar,
            "update_counts",
            lambda rules: calls.append(rules) or original(rules),
        )
        _load(window, tmp_path, "Show\n    Class \"Currency\"\n\n")
        assert not calls, "precondition: no synchronous call"
        QApplication.processEvents()
        assert len(calls) >= 1, \
            "Deferred update_counts() must fire after processEvents()"

    def test_deferred_category_count_ignores_stale_rules(self, window, tmp_path):
        """Deferred callback from file A must not update sidebar after file B loads."""
        # Load file A
        fa = tmp_path / "a.filter"
        fa.write_text("Show\n    Class \"Currency\"\n\n", encoding="utf-8")
        window.load_file(str(fa))
        snap_A = window._doc.rules   # capture the rules list object

        # Load file B (replaces _doc.rules with a new list)
        fb = tmp_path / "b.filter"
        fb.write_text("Hide\n\n", encoding="utf-8")
        window.load_file(str(fb))

        # Simulate the deferred callback from file A arriving late
        update_calls = []
        original = window.category_sidebar.update_counts
        window.category_sidebar.update_counts = lambda r: update_calls.append(r)
        try:
            window._apply_deferred_category_count(snap_A)  # stale — must be no-op
        finally:
            window.category_sidebar.update_counts = original

        assert not update_calls, \
            "Stale deferred callback must NOT call update_counts() for old rules"

    def test_deferred_category_count_fires_for_current_rules(self, window, tmp_path):
        """_apply_deferred_category_count() must execute when rules match current doc."""
        _load(window, tmp_path, "Show\n    Class \"Currency\"\n\n")
        snap = window._doc.rules  # same reference as current doc

        update_calls = []
        original = window.category_sidebar.update_counts
        window.category_sidebar.update_counts = lambda r: update_calls.append(r)
        try:
            window._apply_deferred_category_count(snap)
        finally:
            window.category_sidebar.update_counts = original

        assert len(update_calls) == 1, \
            "_apply_deferred_category_count() must fire when rules snapshot matches"

    def test_schedule_deferred_category_count_method_exists(self, window):
        assert callable(getattr(window, "_schedule_deferred_category_count", None))

    def test_apply_deferred_category_count_method_exists(self, window):
        assert callable(getattr(window, "_apply_deferred_category_count", None))


# ──────────────────────────────────────────────────────────────────────
# Fast-path regression guards — P17.9B and P17.8 must still work
# ──────────────────────────────────────────────────────────────────────

class TestFastPathRegressionGuards:

    def test_quick_fix_fast_path_still_uses_update_single_card(
        self, window, tmp_path, monkeypatch
    ):
        """P17.9B must be intact: quick fix uses update_single_card, not reload."""
        _load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        reload_calls = []
        monkeypatch.setattr(window, "_reload_rule_list", lambda: reload_calls.append(1))
        window._on_quick_fix_requested(0, QuickFix("修正為 60", "SetFontSize", "60"))
        assert not reload_calls, "_reload_rule_list() must NOT be called by quick fix"

    def test_quick_fix_still_starts_validation_timer_300(
        self, window, tmp_path
    ):
        """P17.9B: quick fix must start _validation_timer (not direct validation)."""
        _load(window, tmp_path, "Show\n    SetFontSize 99\n\n")
        window._on_quick_fix_requested(0, QuickFix("修正為 60", "SetFontSize", "60"))
        assert window._validation_timer.isActive(), \
            "_validation_timer must be active after quick fix (deferred validation)"

    def test_detail_editor_fast_path_still_deferred_validation(
        self, window, tmp_path, monkeypatch
    ):
        """P17.8: field edit must start _validation_timer, not call validate immediately."""
        _load(window, tmp_path, "Show\n    Class \"Currency\"\n\n")
        window._navigate_to(0)
        immediate_validate_calls = []
        original = window._refresh_validation
        monkeypatch.setattr(
            window,
            "_refresh_validation",
            lambda: immediate_validate_calls.append(True) or original(),
        )
        # Simulate a field edit
        ed = window.rule_detail_editor
        ed._enabled_cb.setChecked(not ed._enabled_cb.isChecked())
        assert not immediate_validate_calls, \
            "Field edit must NOT call _refresh_validation() synchronously"
        assert window._validation_timer.isActive(), \
            "_validation_timer must be active after field edit"
