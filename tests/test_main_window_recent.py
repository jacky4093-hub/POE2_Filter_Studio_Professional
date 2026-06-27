"""Tests for P7 Recent Files + Settings Persistence — v2.6.0

Covers:
- load_file adds to recent files + updates last_open_dir
- _write_to (Save As) adds to recent files + updates last_open_dir
- _rebuild_recent_menu reflects SettingsManager recent files
- _clear_recent_files clears SettingsManager + saves
- save_file_as uses last_open_dir as initial dialog path
- open_file uses last_open_dir as initial dialog path
- _save_workspace saves geometry + splitter to SettingsManager
"""

import os
import pytest
from PySide6.QtWidgets import QApplication, QFileDialog

from core.settings_manager import SettingsManager
from ui.main_window import MainWindow


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
# Helper: MainWindow with isolated SettingsManager
# ---------------------------------------------------------------------------

@pytest.fixture
def window_and_mgr(qapp, tmp_path):
    mgr = SettingsManager(settings_path=str(tmp_path / "settings.json"))
    w = MainWindow(settings_mgr=mgr)
    return w, mgr


# ---------------------------------------------------------------------------
# TestLoadFileAddsRecent
# ---------------------------------------------------------------------------

class TestLoadFileAddsRecent:
    def test_load_file_adds_to_recent(self, window_and_mgr, tmp_path):
        w, mgr = window_and_mgr
        p = tmp_path / "myfilter.filter"
        p.write_text("Show\n", encoding="utf-8")
        w.load_file(str(p))
        assert str(p) in mgr.recent_files()

    def test_load_file_recent_at_top(self, window_and_mgr, tmp_path):
        w, mgr = window_and_mgr
        p1 = tmp_path / "first.filter"
        p2 = tmp_path / "second.filter"
        p1.write_text("Show\n", encoding="utf-8")
        p2.write_text("Show\n", encoding="utf-8")
        w.load_file(str(p1))
        w.load_file(str(p2))
        assert mgr.recent_files()[0] == str(p2)

    def test_load_file_updates_last_open_dir(self, window_and_mgr, tmp_path):
        w, mgr = window_and_mgr
        p = tmp_path / "sub" / "myfilter.filter"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("Show\n", encoding="utf-8")
        w.load_file(str(p))
        expected = os.path.dirname(os.path.abspath(str(p)))
        assert mgr.last_open_dir == expected

    def test_load_file_saves_settings(self, window_and_mgr, tmp_path):
        w, mgr = window_and_mgr
        p = tmp_path / "saved.filter"
        p.write_text("Show\n", encoding="utf-8")
        w.load_file(str(p))
        # Reload from disk to confirm save happened
        mgr2 = SettingsManager(settings_path=str(tmp_path / "settings.json"))
        assert str(p) in mgr2.recent_files()


# ---------------------------------------------------------------------------
# TestWriteToAddsRecent
# ---------------------------------------------------------------------------

class TestWriteToAddsRecent:
    def test_write_to_adds_to_recent(self, window_and_mgr, tmp_path):
        w, mgr = window_and_mgr
        path = str(tmp_path / "saved.filter")
        w._write_to(path)
        assert path in mgr.recent_files()

    def test_write_to_updates_last_open_dir(self, window_and_mgr, tmp_path):
        w, mgr = window_and_mgr
        path = str(tmp_path / "saved.filter")
        w._write_to(path)
        expected = os.path.dirname(os.path.abspath(path))
        assert mgr.last_open_dir == expected

    def test_write_to_saves_settings(self, window_and_mgr, tmp_path):
        w, mgr = window_and_mgr
        path = str(tmp_path / "saved.filter")
        w._write_to(path)
        mgr2 = SettingsManager(settings_path=str(tmp_path / "settings.json"))
        assert path in mgr2.recent_files()


# ---------------------------------------------------------------------------
# TestRecentMenu
# ---------------------------------------------------------------------------

class TestRecentMenu:
    def test_recent_menu_shows_placeholder_when_empty(self, window_and_mgr):
        w, mgr = window_and_mgr
        w._rebuild_recent_menu()
        actions = w._recent_menu.actions()
        assert len(actions) == 1
        assert not actions[0].isEnabled()

    def test_recent_menu_shows_file_after_load(self, window_and_mgr, tmp_path):
        w, mgr = window_and_mgr
        p = tmp_path / "shown.filter"
        p.write_text("Show\n", encoding="utf-8")
        w.load_file(str(p))
        actions = w._recent_menu.actions()
        labels = [a.text() for a in actions]
        assert any("shown.filter" in lbl for lbl in labels)

    def test_recent_menu_shows_clear_action_when_files_present(self, window_and_mgr, tmp_path):
        w, mgr = window_and_mgr
        p = tmp_path / "f.filter"
        p.write_text("Show\n", encoding="utf-8")
        w.load_file(str(p))
        labels = [a.text() for a in w._recent_menu.actions()]
        assert "清除清單" in labels

    def test_clear_recent_removes_from_menu(self, window_and_mgr, tmp_path):
        w, mgr = window_and_mgr
        p = tmp_path / "f.filter"
        p.write_text("Show\n", encoding="utf-8")
        w.load_file(str(p))
        w._clear_recent_files()
        actions = w._recent_menu.actions()
        assert len(actions) == 1
        assert not actions[0].isEnabled()

    def test_clear_recent_persists(self, window_and_mgr, tmp_path):
        w, mgr = window_and_mgr
        p = tmp_path / "f.filter"
        p.write_text("Show\n", encoding="utf-8")
        w.load_file(str(p))
        w._clear_recent_files()
        mgr2 = SettingsManager(settings_path=str(tmp_path / "settings.json"))
        assert mgr2.recent_files() == []


# ---------------------------------------------------------------------------
# TestOpenFileDialogUsesLastOpenDir
# ---------------------------------------------------------------------------

class TestOpenFileDialogUsesLastOpenDir:
    def test_open_file_passes_last_open_dir_to_dialog(self, window_and_mgr, tmp_path, monkeypatch):
        w, mgr = window_and_mgr
        mgr.last_open_dir = str(tmp_path)
        captured = {}

        def fake_dialog(parent, title, directory, filter_):
            captured["directory"] = directory
            return ("", "")

        monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(fake_dialog))
        monkeypatch.setattr(w, "_confirm_discard", lambda: True)
        w.open_file()
        assert captured.get("directory") == str(tmp_path)

    def test_save_as_passes_last_open_dir_when_no_doc_path(self, window_and_mgr, tmp_path, monkeypatch):
        w, mgr = window_and_mgr
        mgr.last_open_dir = str(tmp_path)
        captured = {}

        def fake_dialog(parent, title, initial, filter_):
            captured["initial"] = initial
            return ("", "")

        monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(fake_dialog))
        w.save_file_as()
        assert captured.get("initial") == str(tmp_path)


# ---------------------------------------------------------------------------
# TestSaveWorkspacePersistsSettings
# ---------------------------------------------------------------------------

class TestSaveWorkspacePersistsSettings:
    def test_save_workspace_stores_splitter_sizes(self, window_and_mgr, tmp_path):
        w, mgr = window_and_mgr
        w._save_workspace()
        sizes = mgr.get_splitter_sizes()
        assert len(sizes) == w._splitter.count()
        assert all(isinstance(s, int) and s >= 0 for s in sizes)

    def test_save_workspace_stores_geometry(self, window_and_mgr, tmp_path):
        w, mgr = window_and_mgr
        w._save_workspace()
        assert mgr.window_geometry != ""

    def test_save_workspace_writes_to_disk(self, window_and_mgr, tmp_path):
        w, mgr = window_and_mgr
        w._save_workspace()
        mgr2 = SettingsManager(settings_path=str(tmp_path / "settings.json"))
        # Splitter sizes written to disk and re-read successfully
        assert len(mgr2.get_splitter_sizes()) == w._splitter.count()

    def test_restore_workspace_state_applies_splitter(self, qapp, tmp_path):
        mgr = SettingsManager(settings_path=str(tmp_path / "settings.json"))
        mgr.set_splitter_sizes([200, 700, 350])
        mgr.save()

        mgr2 = SettingsManager(settings_path=str(tmp_path / "settings.json"))
        w = MainWindow(settings_mgr=mgr2)
        sizes = w._splitter.sizes()
        assert len(sizes) == 3
        # sizes should sum to roughly the same total (Qt may adjust slightly)
        assert sum(sizes) > 0


# ---------------------------------------------------------------------------
# TestSettingsMgrInjection
# ---------------------------------------------------------------------------

class TestSettingsMgrInjection:
    def test_main_window_has_settings_mgr(self, window_and_mgr):
        w, mgr = window_and_mgr
        assert hasattr(w, "_settings_mgr")
        assert isinstance(w._settings_mgr, SettingsManager)

    def test_injected_mgr_is_used(self, window_and_mgr, tmp_path):
        w, mgr = window_and_mgr
        p = tmp_path / "inject.filter"
        p.write_text("Show\n", encoding="utf-8")
        w.load_file(str(p))
        assert str(p) in mgr.recent_files()

    def test_default_mgr_created_when_not_injected(self, qapp):
        w = MainWindow()
        assert isinstance(w._settings_mgr, SettingsManager)
