"""Tests for P9 Preferences integration in MainWindow

Covers:
- Edit menu has '偏好設定' action with Ctrl+, shortcut
- open_preferences() creates a PreferencesDialog
- _on_preferences_applied() syncs restore_action checkbox
- _on_preferences_applied() rebuilds recent menu
- _on_preferences_applied() updates welcome screen recent files
- Full signal flow: PreferencesDialog.settings_applied → main_window
"""

import pytest
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QPushButton

from core.settings_manager import SettingsManager
from ui.main_window import MainWindow
from ui.preferences_dialog import PreferencesDialog


# ---------------------------------------------------------------------------
# Session-scoped QApplication
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

@pytest.fixture
def fresh(qapp, tmp_path):
    """Isolated MainWindow + SettingsManager."""
    mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
    w = MainWindow(settings_mgr=mgr)
    return w, mgr


def _pref_action(window: MainWindow):
    """Return (pref_action, edit_menu, menu_bar) keeping all parents alive.

    Returning parent objects prevents PySide6/Shiboken from GC-ing the C++
    wrappers before the caller is done with them.
    """
    mb = window.menuBar()
    for bar_act in mb.actions():
        em = bar_act.menu()
        if em is None or "編輯" not in bar_act.text():
            continue
        for a in em.actions():
            if "偏好設定" in a.text():
                return a, em, mb
    return None, None, None


# ---------------------------------------------------------------------------
# TestPreferencesMenuEntry
# ---------------------------------------------------------------------------

class TestPreferencesMenuEntry:
    def test_edit_menu_has_preferences_action(self, fresh):
        w, _ = fresh
        action, em, mb = _pref_action(w)
        assert action is not None

    def test_preferences_action_has_ctrl_comma_shortcut(self, fresh):
        w, _ = fresh
        action, em, mb = _pref_action(w)
        assert action is not None
        assert action.shortcut() == QKeySequence("Ctrl+,")

    def test_preferences_action_is_enabled(self, fresh):
        w, _ = fresh
        action, em, mb = _pref_action(w)
        assert action is not None
        assert action.isEnabled()


# ---------------------------------------------------------------------------
# TestOnPreferencesApplied
# ---------------------------------------------------------------------------

class TestOnPreferencesApplied:
    def test_applied_syncs_restore_action_to_true(self, fresh):
        w, mgr = fresh
        mgr.set_restore_last_file_on_startup(True)
        w._on_preferences_applied()
        assert w._restore_action.isChecked() is True

    def test_applied_syncs_restore_action_to_false(self, qapp, tmp_path):
        mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
        mgr.set_restore_last_file_on_startup(True)
        w = MainWindow(settings_mgr=mgr)
        # Now the setting changes to False
        mgr.set_restore_last_file_on_startup(False)
        w._on_preferences_applied()
        assert w._restore_action.isChecked() is False

    def test_applied_rebuilds_recent_menu(self, fresh, tmp_path):
        """After apply, the File menu 最近開啟 submenu should have the new file."""
        w, mgr = fresh
        mgr.add_recent_file("/applied_rebuild.filter")
        w._on_preferences_applied()
        # Find '最近開啟' menu under File
        file_menu = None
        for action in w.menuBar().actions():
            if "檔案" in action.text() or "File" in action.text():
                file_menu = action.menu()
                break
        assert file_menu is not None
        recent_menu = None
        for act in file_menu.actions():
            if act.menu() and ("最近" in act.text()):
                recent_menu = act.menu()
                break
        assert recent_menu is not None
        texts = [a.text() for a in recent_menu.actions()]
        assert any("applied_rebuild.filter" in t for t in texts)

    def test_applied_updates_welcome_screen(self, fresh, tmp_path):
        """After apply, welcome_screen shows the updated recent list."""
        w, mgr = fresh
        p = tmp_path / "ws_pref.filter"
        p.write_text("Show\n", encoding="utf-8")
        mgr.add_recent_file(str(p))
        w._on_preferences_applied()
        btns = w.welcome_screen.findChildren(QPushButton, "WelcomeRecentItem")
        labels = [b.text() for b in btns]
        assert any("ws_pref.filter" in lbl for lbl in labels)

    def test_applied_does_not_change_current_page(self, fresh, tmp_path):
        """Applying preferences must not switch the stacked widget."""
        w, mgr = fresh
        # Navigate to editor first
        p = tmp_path / "ed.filter"
        p.write_text("Show\n", encoding="utf-8")
        w.load_file(str(p))
        assert w._main_stack.currentIndex() == 1

        mgr.add_recent_file("/new.filter")
        w._on_preferences_applied()
        # Must still be on editor page
        assert w._main_stack.currentIndex() == 1


# ---------------------------------------------------------------------------
# TestPreferencesDialogSignalFlow
# ---------------------------------------------------------------------------

class TestPreferencesDialogSignalFlow:
    def test_dialog_apply_triggers_on_preferences_applied(self, fresh):
        """When PreferencesDialog emits settings_applied, main_window reacts."""
        w, mgr = fresh
        dlg = PreferencesDialog(mgr, w)
        dlg.settings_applied.connect(w._on_preferences_applied)

        # Set the checkbox directly — dialog state drives apply, not mgr
        dlg._cb_restore.setChecked(True)
        dlg._on_apply()   # writes True to mgr → emits settings_applied → syncs restore_action

        assert w._restore_action.isChecked() is True

    def test_dialog_ok_triggers_on_preferences_applied(self, fresh):
        w, mgr = fresh
        dlg = PreferencesDialog(mgr, w)
        dlg.settings_applied.connect(w._on_preferences_applied)

        dlg._cb_restore.setChecked(True)
        dlg.accept()

        assert w._restore_action.isChecked() is True

    def test_dialog_cancel_does_not_trigger_on_preferences_applied(self, fresh):
        """Reject should NOT call _on_preferences_applied."""
        w, mgr = fresh
        # Start with restore = False
        mgr.set_restore_last_file_on_startup(False)
        w._restore_action.setChecked(False)

        dlg = PreferencesDialog(mgr, w)
        dlg.settings_applied.connect(w._on_preferences_applied)
        dlg._cb_restore.setChecked(True)  # change UI but cancel
        dlg.reject()

        # restore_action must still be False (no apply happened)
        assert w._restore_action.isChecked() is False

    def test_clear_recent_via_dialog_updates_welcome_screen(self, fresh, tmp_path):
        """Clear in dialog + apply removes items from welcome screen."""
        w, mgr = fresh
        p = tmp_path / "to_clear.filter"
        p.write_text("Show\n", encoding="utf-8")
        mgr.add_recent_file(str(p))

        dlg = PreferencesDialog(mgr, w)
        dlg.settings_applied.connect(w._on_preferences_applied)
        dlg._on_clear_recent()
        dlg._on_apply()

        btns = w.welcome_screen.findChildren(QPushButton, "WelcomeRecentItem")
        assert btns == []
