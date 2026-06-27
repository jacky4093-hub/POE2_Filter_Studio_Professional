import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from core.settings_manager import SettingsManager
from ui.main_window import MainWindow
from controllers.recent_files_controller import RecentFilesController


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.fixture
def fresh(qapp, tmp_path):
    mgr = SettingsManager(settings_path=str(tmp_path / "settings.json"))
    window = MainWindow(settings_mgr=mgr)
    return window, mgr


class TestRecentFilesController:
    def test_refresh_views_syncs_menu_and_welcome(self, fresh, tmp_path):
        window, mgr = fresh
        p = tmp_path / "recent.filter"
        p.write_text("Show\n", encoding="utf-8")
        mgr.add_recent_file(str(p))

        controller = RecentFilesController(window, mgr)
        controller.refresh_views()

        menu_actions = [a.text() for a in window._recent_menu.actions() if not a.isSeparator()]
        assert any("recent.filter" in label for label in menu_actions)
        welcome_buttons = window.welcome_screen.findChildren(QPushButton, "WelcomeRecentItem")
        assert len(welcome_buttons) == 1

    def test_clear_recent_clears_settings_and_refreshes_ui(self, fresh, tmp_path):
        window, mgr = fresh
        p = tmp_path / "clear.filter"
        p.write_text("Show\n", encoding="utf-8")
        mgr.add_recent_file(str(p))
        controller = RecentFilesController(window, mgr)

        controller.clear_recent()

        assert mgr.recent_files() == []
        actions = [a.text() for a in window._recent_menu.actions() if not a.isSeparator()]
        assert actions == ["（無最近開啟檔案）"]

    def test_record_opened_and_saved_add_recent(self, fresh, tmp_path):
        window, mgr = fresh
        opened = tmp_path / "opened.filter"
        opened.write_text("Show\n", encoding="utf-8")
        saved = tmp_path / "saved.filter"

        controller = RecentFilesController(window, mgr)
        controller.record_opened(str(opened))
        controller.record_saved(str(saved))

        assert str(opened) in mgr.recent_files()
        assert str(saved) in mgr.recent_files()

    def test_open_recent_delegates_to_load_file(self, fresh, tmp_path, monkeypatch):
        window, mgr = fresh
        p = tmp_path / "delegate.filter"
        p.write_text("Show\n", encoding="utf-8")
        called = {}

        def fake_load(path, *, silent=False):
            called["path"] = path
            called["silent"] = silent
            return True

        monkeypatch.setattr(window, "load_file", fake_load)
        controller = RecentFilesController(window, mgr)

        controller.open_recent(str(p))

        assert called == {"path": str(p), "silent": False}
