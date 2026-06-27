"""Tests for P8 Startup Restore + Welcome Screen — v2.7.0

Covers:
- startup with no file → welcome screen (stack index 0)
- load_file → editor shown (stack index 1)
- new_file → editor shown (stack index 1)
- new_file resets document
- new_file respects confirm-discard
- restore_last_file_on_startup = True → loads last file on startup
- last_open_file missing → welcome shown, no crash
- restore = False → welcome shown even when last file exists
- _restore_action checkbox wires to setting
- load_file updates last_open_file in settings
- _write_to updates last_open_file in settings
- welcome_screen connected to open_file / new_file / load_file
"""

import os
import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from core.settings_manager import SettingsManager
from ui.main_window import MainWindow
from ui.welcome_screen import WelcomeScreen


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
    """Isolated MainWindow + SettingsManager. No startup restore."""
    mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
    w = MainWindow(settings_mgr=mgr)
    return w, mgr


# ---------------------------------------------------------------------------
# TestStartupShowsWelcome
# ---------------------------------------------------------------------------

class TestStartupShowsWelcome:
    def test_default_shows_welcome(self, fresh):
        w, _ = fresh
        assert w._main_stack.currentIndex() == 0

    def test_has_welcome_screen_widget(self, fresh):
        w, _ = fresh
        assert hasattr(w, "welcome_screen")
        assert isinstance(w.welcome_screen, WelcomeScreen)

    def test_has_main_stack(self, fresh):
        w, _ = fresh
        from PySide6.QtWidgets import QStackedWidget
        assert isinstance(w._main_stack, QStackedWidget)
        assert w._main_stack.count() == 2

    def test_welcome_is_page_zero(self, fresh):
        w, _ = fresh
        assert w._main_stack.widget(0) is w.welcome_screen


# ---------------------------------------------------------------------------
# TestLoadFileShowsEditor
# ---------------------------------------------------------------------------

class TestLoadFileShowsEditor:
    def test_load_switches_to_editor(self, fresh, tmp_path):
        w, _ = fresh
        p = tmp_path / "f.filter"
        p.write_text("Show\n", encoding="utf-8")
        w.load_file(str(p))
        assert w._main_stack.currentIndex() == 1

    def test_load_invalid_file_stays_welcome(self, fresh):
        w, _ = fresh
        w.load_file("/nonexistent/missing.filter")
        assert w._main_stack.currentIndex() == 0


# ---------------------------------------------------------------------------
# TestNewFile
# ---------------------------------------------------------------------------

class TestNewFile:
    def test_new_file_switches_to_editor(self, fresh):
        w, _ = fresh
        w.new_file()
        assert w._main_stack.currentIndex() == 1

    def test_new_file_empty_doc(self, fresh):
        w, _ = fresh
        w.new_file()
        assert w._doc.visible_count == 0

    def test_new_file_not_dirty(self, fresh):
        w, _ = fresh
        w.new_file()
        assert w._doc.dirty is False

    def test_new_file_no_filepath(self, fresh):
        w, _ = fresh
        w.new_file()
        assert w._doc.file_path == ""

    def test_new_file_clears_file_mgr(self, fresh):
        w, _ = fresh
        w.new_file()
        assert w._file_mgr.current_path == ""

    def test_new_file_title_clean(self, fresh):
        w, _ = fresh
        w.new_file()
        assert "POE2 Filter Studio" in w.windowTitle()
        assert "*" not in w.windowTitle()

    def test_new_file_resets_doc_after_add_rule(self, fresh):
        w, _ = fresh
        w.new_file()                 # go to editor
        w._on_add_rule()             # add a rule
        assert w._doc.visible_count == 1
        # new_file on a dirty doc requires confirm-discard
        # We monkeypatch to avoid the dialog — test the reset directly
        w._doc._dirty = False        # pretend saved
        w.new_file()
        assert w._doc.visible_count == 0

    def test_new_file_confirm_discard_cancel_keeps_dirty(self, fresh, monkeypatch):
        w, _ = fresh
        w.new_file()                 # go to editor
        w._on_add_rule()
        assert w._doc.dirty is True

        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.No,
        )
        w.new_file()
        assert w._doc.dirty is True  # not reset

    def test_new_file_confirm_discard_yes_proceeds(self, fresh, monkeypatch):
        w, _ = fresh
        w.new_file()
        w._on_add_rule()
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Yes,
        )
        w.new_file()
        assert w._doc.visible_count == 0
        assert w._main_stack.currentIndex() == 1


# ---------------------------------------------------------------------------
# TestStartupRestore
# ---------------------------------------------------------------------------

class TestStartupRestore:
    def test_restore_enabled_loads_last_file(self, qapp, tmp_path):
        p = tmp_path / "last.filter"
        p.write_text("Show\n", encoding="utf-8")

        mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
        mgr.set_restore_last_file_on_startup(True)
        mgr.set_last_open_file(str(p))
        mgr.save()

        mgr2 = SettingsManager(settings_path=str(tmp_path / "s.json"))
        w = MainWindow(settings_mgr=mgr2)
        assert w._main_stack.currentIndex() == 1
        assert os.path.basename(p) in w._doc.file_path

    def test_restore_disabled_shows_welcome(self, qapp, tmp_path):
        p = tmp_path / "last.filter"
        p.write_text("Show\n", encoding="utf-8")

        mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
        mgr.set_restore_last_file_on_startup(False)
        mgr.set_last_open_file(str(p))
        mgr.save()

        mgr2 = SettingsManager(settings_path=str(tmp_path / "s.json"))
        w = MainWindow(settings_mgr=mgr2)
        assert w._main_stack.currentIndex() == 0

    def test_restore_missing_file_shows_welcome(self, qapp, tmp_path):
        mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
        mgr.set_restore_last_file_on_startup(True)
        mgr.set_last_open_file("/totally/nonexistent/file.filter")
        mgr.save()

        mgr2 = SettingsManager(settings_path=str(tmp_path / "s.json"))
        w = MainWindow(settings_mgr=mgr2)
        assert w._main_stack.currentIndex() == 0  # welcome, no crash

    def test_restore_no_last_file_shows_welcome(self, qapp, tmp_path):
        mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
        mgr.set_restore_last_file_on_startup(True)
        # No last_open_file set
        mgr.save()

        mgr2 = SettingsManager(settings_path=str(tmp_path / "s.json"))
        w = MainWindow(settings_mgr=mgr2)
        assert w._main_stack.currentIndex() == 0

    def test_restore_missing_file_no_qmessagebox(self, qapp, tmp_path, monkeypatch):
        """QMessageBox.critical must NOT appear when startup restore fails."""
        mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
        mgr.set_restore_last_file_on_startup(True)
        mgr.set_last_open_file("/totally/nonexistent/startup.filter")
        mgr.save()

        shown: list = []
        monkeypatch.setattr(
            QMessageBox, "critical",
            staticmethod(lambda *a, **kw: shown.append(True)),
        )

        mgr2 = SettingsManager(settings_path=str(tmp_path / "s.json"))
        w = MainWindow(settings_mgr=mgr2)

        assert shown == [], "QMessageBox.critical must not appear on startup restore failure"
        assert w._main_stack.currentIndex() == 0

    def test_restore_failure_preserves_last_open_file_setting(self, qapp, tmp_path):
        """last_open_file must not be wiped when restore fails."""
        missing = "/totally/nonexistent/preserved.filter"
        mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
        mgr.set_restore_last_file_on_startup(True)
        mgr.set_last_open_file(missing)
        mgr.save()

        mgr2 = SettingsManager(settings_path=str(tmp_path / "s.json"))
        MainWindow(settings_mgr=mgr2)

        # Reload from disk — path must still be there
        mgr3 = SettingsManager(settings_path=str(tmp_path / "s.json"))
        assert mgr3.get_last_open_file() == missing

    def test_silent_load_file_returns_false_on_missing(self, fresh):
        """load_file(silent=True) returns False and shows no dialog."""
        w, _ = fresh
        result = w.load_file("/nonexistent/path.filter", silent=True)
        assert result is False

    def test_silent_load_file_returns_true_on_success(self, fresh, tmp_path):
        """load_file(silent=True) returns True when file loads correctly."""
        w, _ = fresh
        p = tmp_path / "ok.filter"
        p.write_text("Show\n", encoding="utf-8")
        result = w.load_file(str(p), silent=True)
        assert result is True

    def test_normal_load_file_shows_qmessagebox_on_error(self, fresh, monkeypatch):
        """load_file() (silent=False, default) still shows error dialog."""
        w, _ = fresh
        shown: list = []
        monkeypatch.setattr(
            QMessageBox, "critical",
            staticmethod(lambda *a, **kw: shown.append(True)),
        )
        w.load_file("/nonexistent/path.filter")
        assert shown, "Normal load_file must show QMessageBox on error"


# ---------------------------------------------------------------------------
# TestRestoreCheckboxAction
# ---------------------------------------------------------------------------

class TestRestoreCheckboxAction:
    def test_restore_action_is_checkable(self, fresh):
        w, _ = fresh
        assert w._restore_action.isCheckable()

    def test_restore_action_initial_state_matches_setting(self, qapp, tmp_path):
        mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
        mgr.set_restore_last_file_on_startup(True)
        w = MainWindow(settings_mgr=mgr)
        assert w._restore_action.isChecked() is True

    def test_toggle_on_updates_setting(self, fresh):
        w, mgr = fresh
        assert mgr.get_restore_last_file_on_startup() is False
        w._restore_action.setChecked(True)
        assert mgr.get_restore_last_file_on_startup() is True

    def test_toggle_off_updates_setting(self, qapp, tmp_path):
        mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
        mgr.set_restore_last_file_on_startup(True)
        w = MainWindow(settings_mgr=mgr)
        w._restore_action.setChecked(False)
        assert mgr.get_restore_last_file_on_startup() is False

    def test_toggle_persisted_to_disk(self, fresh, tmp_path):
        w, mgr = fresh
        w._restore_action.setChecked(True)
        # Reload from disk
        mgr2 = SettingsManager(settings_path=str(tmp_path / "s.json"))
        assert mgr2.get_restore_last_file_on_startup() is True


# ---------------------------------------------------------------------------
# TestLastOpenFileTracking
# ---------------------------------------------------------------------------

class TestLastOpenFileTracking:
    def test_load_file_sets_last_open_file(self, fresh, tmp_path):
        w, mgr = fresh
        p = tmp_path / "track.filter"
        p.write_text("Show\n", encoding="utf-8")
        w.load_file(str(p))
        assert mgr.get_last_open_file() == str(p)

    def test_write_to_sets_last_open_file(self, fresh, tmp_path):
        w, mgr = fresh
        path = str(tmp_path / "saved.filter")
        w._write_to(path)
        assert mgr.get_last_open_file() == path

    def test_last_open_file_persisted_after_load(self, fresh, tmp_path):
        w, mgr = fresh
        p = tmp_path / "persist.filter"
        p.write_text("Show\n", encoding="utf-8")
        w.load_file(str(p))
        mgr2 = SettingsManager(settings_path=str(tmp_path / "s.json"))
        assert mgr2.get_last_open_file() == str(p)


# ---------------------------------------------------------------------------
# TestWelcomeSignalWiring
# ---------------------------------------------------------------------------

class TestWelcomeSignalWiring:
    def test_welcome_recent_file_triggers_load(self, fresh, tmp_path):
        """welcome_screen.recent_file_requested → load_file → editor shown."""
        w, _ = fresh
        p = tmp_path / "ws.filter"
        p.write_text("Show\n", encoding="utf-8")
        w.welcome_screen.recent_file_requested.emit(str(p))
        assert w._main_stack.currentIndex() == 1

    def test_welcome_new_triggers_new_file(self, fresh):
        """welcome_screen.new_requested → new_file → editor shown."""
        w, _ = fresh
        w.welcome_screen.new_requested.emit()
        assert w._main_stack.currentIndex() == 1

    def test_show_welcome_updates_recent_list(self, fresh, tmp_path):
        """_show_welcome() passes current recent files to WelcomeScreen."""
        from PySide6.QtWidgets import QPushButton
        w, mgr = fresh
        p = tmp_path / "recent.filter"
        p.write_text("Show\n", encoding="utf-8")
        mgr.add_recent_file(str(p))
        w._show_welcome()
        btns = w.welcome_screen.findChildren(QPushButton, "WelcomeRecentItem")
        labels = [b.text() for b in btns]
        assert any("recent.filter" in lbl for lbl in labels)
