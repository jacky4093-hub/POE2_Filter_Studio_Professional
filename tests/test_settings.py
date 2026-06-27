"""Tests for WorkspaceSettings and related v0.9.0 features.

Categories:
    A. Pure-logic helpers in settings_service (_to_bool, _norm, _to_int)
    B. WorkspaceSettings with a temporary QSettings store (in-memory / tmp dir)
    C. SearchBar Escape key (requires offscreen Qt)
    D. MainWindow recent-files menu (headless, offscreen Qt)
"""
import os
import sys
import tempfile
import pytest

# ---------------------------------------------------------------------------
# Qt fixture — one QApplication for the entire test session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


# ---------------------------------------------------------------------------
# Helper: isolated WorkspaceSettings backed by a temp INI file
# ---------------------------------------------------------------------------

@pytest.fixture()
def settings(tmp_path):
    """Return a WorkspaceSettings instance writing to a temp directory."""
    from PySide6.QtCore import QSettings
    from services.settings_service import WorkspaceSettings

    ini_path = str(tmp_path / "test_settings.ini")

    ws = WorkspaceSettings.__new__(WorkspaceSettings)
    ws._qs = QSettings(ini_path, QSettings.Format.IniFormat)
    return ws


# ===========================================================================
# A. Pure-logic helper tests (no Qt required)
# ===========================================================================

class TestToBool:
    def test_bool_true(self):
        from services.settings_service import _to_bool
        assert _to_bool(True, False) is True

    def test_bool_false(self):
        from services.settings_service import _to_bool
        assert _to_bool(False, True) is False

    def test_string_true(self):
        from services.settings_service import _to_bool
        assert _to_bool("true", False) is True

    def test_string_false(self):
        from services.settings_service import _to_bool
        assert _to_bool("false", True) is False

    def test_string_zero(self):
        from services.settings_service import _to_bool
        assert _to_bool("0", True) is False

    def test_none_uses_default(self):
        from services.settings_service import _to_bool
        assert _to_bool(None, True) is True
        assert _to_bool(None, False) is False


class TestNorm:
    def test_backslash_to_forward(self):
        from services.settings_service import _norm
        assert _norm(r"C:\Users\foo\bar.filter") == "c:/users/foo/bar.filter"

    def test_already_forward(self):
        from services.settings_service import _norm
        assert _norm("C:/foo/bar.filter") == "c:/foo/bar.filter"

    def test_case_fold(self):
        from services.settings_service import _norm
        assert _norm("C:/FOO/Bar.Filter") == "c:/foo/bar.filter"


# ===========================================================================
# B. WorkspaceSettings behaviour
# ===========================================================================

class TestRecentFiles:
    def test_empty_on_first_use(self, settings):
        assert settings.recent_files() == []

    def test_add_single(self, settings):
        settings.add_recent_file("/a/b.filter")
        assert settings.recent_files() == ["/a/b.filter"]

    def test_add_multiple_order(self, settings):
        settings.add_recent_file("/a.filter")
        settings.add_recent_file("/b.filter")
        settings.add_recent_file("/c.filter")
        assert settings.recent_files() == ["/c.filter", "/b.filter", "/a.filter"]

    def test_dedup_moves_to_front(self, settings):
        settings.add_recent_file("/a.filter")
        settings.add_recent_file("/b.filter")
        settings.add_recent_file("/a.filter")   # duplicate → moves to front
        result = settings.recent_files()
        assert result[0] == "/a.filter"
        assert result.count("/a.filter") == 1

    def test_dedup_case_insensitive_windows_paths(self, settings):
        settings.add_recent_file(r"C:\Foo\Bar.filter")
        settings.add_recent_file(r"C:\foo\bar.filter")   # same path, different case
        assert len(settings.recent_files()) == 1

    def test_cap_at_10(self, settings):
        for i in range(12):
            settings.add_recent_file(f"/file{i}.filter")
        result = settings.recent_files()
        assert len(result) == 10
        # Most recent 10 should be files 11 → 2 (file0 and file1 dropped)
        assert result[0] == "/file11.filter"
        assert "/file0.filter" not in result
        assert "/file1.filter" not in result

    def test_clear_recent_files(self, settings):
        settings.add_recent_file("/a.filter")
        settings.add_recent_file("/b.filter")
        settings.clear_recent_files()
        assert settings.recent_files() == []

    def test_roundtrip_persists(self, tmp_path):
        """Data survives constructing a second WorkspaceSettings on the same file."""
        from PySide6.QtCore import QSettings
        from services.settings_service import WorkspaceSettings

        ini_path = str(tmp_path / "persist.ini")

        ws1 = WorkspaceSettings.__new__(WorkspaceSettings)
        ws1._qs = QSettings(ini_path, QSettings.Format.IniFormat)
        ws1.add_recent_file("/keep.filter")
        ws1._qs.sync()

        ws2 = WorkspaceSettings.__new__(WorkspaceSettings)
        ws2._qs = QSettings(ini_path, QSettings.Format.IniFormat)
        assert ws2.recent_files() == ["/keep.filter"]


class TestSectionStates:
    def test_defaults_when_never_saved(self, settings):
        states = settings.restore_section_states()
        assert states == {"conditions": True, "appearance": True, "audio": False}

    def test_roundtrip_all_true(self, settings):
        settings.save_section_states({"conditions": True, "appearance": True, "audio": True})
        assert settings.restore_section_states() == {
            "conditions": True, "appearance": True, "audio": True
        }

    def test_roundtrip_mixed(self, settings):
        settings.save_section_states({"conditions": False, "appearance": True, "audio": False})
        states = settings.restore_section_states()
        assert states["conditions"] is False
        assert states["appearance"] is True
        assert states["audio"] is False

    def test_partial_save_uses_defaults_for_missing(self, settings):
        # Only save "conditions"; "appearance" and "audio" should fall back to defaults
        settings.save_section_states({"conditions": False})
        states = settings.restore_section_states()
        assert states["conditions"] is False
        assert states["appearance"] is True   # default
        assert states["audio"] is False       # default


class TestSplitterSizes:
    """Use mock splitters to avoid Qt headless-mode size normalisation."""

    def _mock_splitter(self, sizes: list[int]):
        from unittest.mock import MagicMock
        sp = MagicMock()
        sp.sizes.return_value = sizes
        sp.count.return_value = len(sizes)
        return sp

    def test_roundtrip(self, settings):
        sp = self._mock_splitter([200, 600, 200])
        settings.save_splitter(sp)

        sp2 = self._mock_splitter([100, 100, 100])
        settings.restore_splitter(sp2)

        sp2.setSizes.assert_called_once_with([200, 600, 200])

    def test_restore_wrong_pane_count_is_noop(self, settings):
        sp = self._mock_splitter([240, 720, 260])
        settings.save_splitter(sp)

        # Splitter with 2 panes — count mismatch, setSizes must NOT be called
        sp2 = self._mock_splitter([100, 100])
        settings.restore_splitter(sp2)
        sp2.setSizes.assert_not_called()

    def test_restore_when_nothing_saved_is_noop(self, settings):
        sp = self._mock_splitter([100, 200, 300])
        settings.restore_splitter(sp)   # nothing saved — setSizes must NOT be called
        sp.setSizes.assert_not_called()

    def test_malformed_sizes_string_is_noop(self, settings):
        # Manually write a corrupt value
        settings._qs.beginGroup("Splitter")
        settings._qs.setValue("sizes", "abc,def,ghi")
        settings._qs.endGroup()

        sp = self._mock_splitter([100, 100, 100])
        settings.restore_splitter(sp)
        sp.setSizes.assert_not_called()


# ===========================================================================
# C. SearchBar Escape key
# ===========================================================================

class TestSearchBarEscape:
    def test_escape_clears_text_and_emits_signal(self, qapp):
        from PySide6.QtCore import QCoreApplication
        from widgets.search_bar import SearchBar

        bar = SearchBar()
        received: list[str] = []
        bar.search_changed.connect(received.append)

        # Type something
        bar._input.setText("Currency")
        received.clear()

        # Trigger the Escape shortcut
        bar._input.setFocus()
        # Directly invoke the internal slot (simulates shortcut activation)
        bar._on_escape()

        # Process pending events so signals are delivered
        QCoreApplication.processEvents()

        assert bar.current_text() == ""
        assert "" in received

    def test_escape_when_already_empty_does_not_crash(self, qapp):
        from PySide6.QtCore import QCoreApplication
        from widgets.search_bar import SearchBar

        bar = SearchBar()
        bar._on_escape()
        QCoreApplication.processEvents()
        assert bar.current_text() == ""


# ===========================================================================
# D. MainWindow recent-files menu (headless)
# ===========================================================================

class TestMainWindowRecentMenu:
    @pytest.fixture()
    def window(self, qapp, settings, tmp_path):
        from ui.main_window import MainWindow
        from core.settings_manager import SettingsManager
        mgr = SettingsManager(settings_path=str(tmp_path / "sm.json"))
        w = MainWindow(settings, settings_mgr=mgr)
        yield w
        w.close()

    def test_empty_recent_menu_shows_placeholder(self, window):
        actions = [a for a in window._recent_menu.actions() if not a.isSeparator()]
        assert len(actions) == 1
        assert not actions[0].isEnabled()

    def test_recent_menu_rebuilt_after_load(self, window, settings, tmp_path):
        # Create a real temp filter file so load_file() succeeds
        f = tmp_path / "test.filter"
        f.write_text("Show\n", encoding="utf-8")
        path = str(f)

        # Recent files now managed by SettingsManager, not WorkspaceSettings
        window._settings_mgr.add_recent_file(path)
        window._rebuild_recent_menu()

        texts = [a.text() for a in window._recent_menu.actions() if not a.isSeparator()]
        assert any("test.filter" in t for t in texts)
        # Clear action should also be present
        assert any("清除" in t for t in texts)

    def test_open_recent_missing_file_shows_warning(self, window, qapp):
        from PySide6.QtCore import QCoreApplication
        from unittest.mock import patch

        nonexistent = "/nonexistent/path/file.filter"
        warned: list[str] = []

        with patch("PySide6.QtWidgets.QMessageBox.warning",
                   side_effect=lambda *a, **kw: warned.append(a[2])):
            window._open_recent(nonexistent)

        QCoreApplication.processEvents()
        assert len(warned) == 1
        assert "不存在" in warned[0] or nonexistent in warned[0]

    def test_clear_recent_empties_menu(self, window, settings):
        settings.add_recent_file("/some/file.filter")
        window._rebuild_recent_menu()
        window._clear_recent_files()

        actions = [a for a in window._recent_menu.actions() if not a.isSeparator()]
        assert len(actions) == 1
        assert not actions[0].isEnabled()
