"""Tests for P6 Save System — main_window integration — v2.5.0

Covers:
- dirty flag after rule changes
- clean after save
- window title with * marker
- close dialog when dirty (3-button)
- window title after load
"""

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from core.models import FilterRule
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
# TestDirtyAfterRuleChange
# ---------------------------------------------------------------------------

class TestDirtyAfterRuleChange:
    def test_initially_not_dirty(self, qapp):
        w = MainWindow()
        assert w._doc.dirty is False

    def test_add_rule_marks_dirty(self, qapp):
        w = MainWindow()
        w._on_add_rule()
        assert w._doc.dirty is True

    def test_delete_rule_marks_dirty(self, qapp):
        w = MainWindow()
        w._on_add_rule()
        w._doc._dirty = False   # reset so we can verify delete alone
        idx = w._selected_index
        # Bypass confirmation dialog for test
        from core.commands import DeleteRuleCommand
        from core.document import FilterDocument
        if 0 <= idx < len(w._doc.rules):
            cmd = DeleteRuleCommand(w._doc, idx)
            w._doc.execute(cmd)
            w._reload_rule_list()
            w._clear_rule_ui()
            w._refresh_status()
            w._refresh_undo_actions()
        assert w._doc.dirty is True

    def test_duplicate_rule_marks_dirty(self, qapp):
        w = MainWindow()
        w._on_add_rule()
        w._doc._dirty = False
        w._on_toolbar_duplicate()
        assert w._doc.dirty is True

    def test_move_rule_marks_dirty(self, qapp):
        w = MainWindow()
        w._on_add_rule()
        w._on_add_rule()   # second rule at index 1
        w._doc._dirty = False
        w._on_toolbar_move_up()
        # MoveRuleCommand is noop if only 1 movable rule, check after adding 2
        assert w._doc.dirty is True

    def test_undo_marks_dirty(self, qapp):
        w = MainWindow()
        w._on_add_rule()
        w._doc._dirty = False   # pretend saved
        w._on_undo()
        assert w._doc.dirty is True

    def test_redo_marks_dirty(self, qapp):
        w = MainWindow()
        w._on_add_rule()
        w._on_undo()
        w._doc._dirty = False
        w._on_redo()
        assert w._doc.dirty is True


# ---------------------------------------------------------------------------
# TestSaveClearsDirty
# ---------------------------------------------------------------------------

class TestSaveClearsDirty:
    def test_write_to_clears_dirty(self, qapp, tmp_path):
        w = MainWindow()
        w._on_add_rule()
        assert w._doc.dirty is True
        path = str(tmp_path / "test.filter")
        w._write_to(path)
        assert w._doc.dirty is False

    def test_write_to_creates_file(self, qapp, tmp_path):
        w = MainWindow()
        path = str(tmp_path / "output.filter")
        w._write_to(path)
        import os
        assert os.path.exists(path)

    def test_save_updates_file_mgr_path(self, qapp, tmp_path):
        w = MainWindow()
        path = str(tmp_path / "test.filter")
        w._write_to(path)
        assert w._file_mgr.current_path == path

    def test_file_mgr_not_dirty_after_save(self, qapp, tmp_path):
        w = MainWindow()
        w._file_mgr.mark_dirty()
        path = str(tmp_path / "test.filter")
        w._write_to(path)
        assert w._file_mgr.is_dirty is False


# ---------------------------------------------------------------------------
# TestWindowTitle
# ---------------------------------------------------------------------------

class TestWindowTitle:
    def test_initial_title(self, qapp):
        w = MainWindow()
        assert w.windowTitle() == "POE2 Filter Studio"

    def test_title_no_star_when_clean(self, qapp):
        w = MainWindow()
        assert "*" not in w.windowTitle()

    def test_title_has_star_when_dirty(self, qapp):
        w = MainWindow()
        w._on_add_rule()
        assert "*" in w.windowTitle()

    def test_title_includes_filename_after_save(self, qapp, tmp_path):
        w = MainWindow()
        path = str(tmp_path / "myfilter.filter")
        w._write_to(path)
        assert "myfilter.filter" in w.windowTitle()

    def test_title_no_star_after_save(self, qapp, tmp_path):
        w = MainWindow()
        w._on_add_rule()
        path = str(tmp_path / "test.filter")
        w._write_to(path)
        assert "*" not in w.windowTitle()

    def test_title_star_removed_after_save(self, qapp, tmp_path):
        """Verify * appears then disappears on dirty→save cycle."""
        w = MainWindow()
        w._on_add_rule()
        assert "*" in w.windowTitle()
        path = str(tmp_path / "cycle.filter")
        w._write_to(path)
        assert "*" not in w.windowTitle()

    def test_title_after_load(self, qapp, tmp_path):
        p = tmp_path / "loaded.filter"
        p.write_text("Show\n", encoding="utf-8")
        w = MainWindow()
        w.load_file(str(p))
        assert "loaded.filter" in w.windowTitle()
        assert "*" not in w.windowTitle()


# ---------------------------------------------------------------------------
# TestUpdateTitle
# ---------------------------------------------------------------------------

class TestUpdateTitle:
    def test_update_title_no_path_clean(self, qapp):
        w = MainWindow()
        w._update_title()
        assert w.windowTitle() == "POE2 Filter Studio"

    def test_update_title_no_path_dirty(self, qapp):
        w = MainWindow()
        w._doc._dirty = True
        w._update_title()
        title = w.windowTitle()
        assert title.startswith("* ")
        assert "POE2 Filter Studio" in title

    def test_update_title_with_path_clean(self, qapp, tmp_path):
        w = MainWindow()
        path = str(tmp_path / "clean.filter")
        w._doc._file_path = path
        w._doc._dirty = False
        w._update_title()
        assert "clean.filter" in w.windowTitle()
        assert "*" not in w.windowTitle()

    def test_update_title_with_path_dirty(self, qapp, tmp_path):
        w = MainWindow()
        path = str(tmp_path / "dirty.filter")
        w._doc._file_path = path
        w._doc._dirty = True
        w._update_title()
        title = w.windowTitle()
        assert title.startswith("* ")
        assert "dirty.filter" in title


# ---------------------------------------------------------------------------
# TestCloseEvent
# ---------------------------------------------------------------------------

class TestCloseEvent:
    def test_close_clean_accepts(self, qapp):
        from PySide6.QtGui import QCloseEvent
        w = MainWindow()
        assert w._doc.dirty is False
        event = QCloseEvent()
        w.closeEvent(event)
        assert event.isAccepted()

    def test_close_dirty_cancel_ignores(self, qapp, monkeypatch):
        from PySide6.QtGui import QCloseEvent
        w = MainWindow()
        w._on_add_rule()
        assert w._doc.dirty is True

        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Cancel,
        )
        event = QCloseEvent()
        w.closeEvent(event)
        assert not event.isAccepted()

    def test_close_dirty_discard_accepts(self, qapp, monkeypatch):
        from PySide6.QtGui import QCloseEvent
        w = MainWindow()
        w._on_add_rule()

        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Discard,
        )
        event = QCloseEvent()
        w.closeEvent(event)
        assert event.isAccepted()

    def test_close_dirty_save_then_accept(self, qapp, monkeypatch, tmp_path):
        from PySide6.QtGui import QCloseEvent
        w = MainWindow()
        w._on_add_rule()
        path = str(tmp_path / "close_save.filter")

        # "Save" button chosen → triggers save_file() → needs a path
        # We set the path first so save_file() won't open SaveAs dialog
        w._doc._file_path = path
        w._file_mgr._current_path = path

        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Save,
        )
        event = QCloseEvent()
        w.closeEvent(event)
        # After saving, dirty clears → closeEvent accepts
        assert event.isAccepted()

    def test_close_dialog_shown_when_dirty(self, qapp, monkeypatch):
        """Verify dialog is actually shown when doc is dirty."""
        from PySide6.QtGui import QCloseEvent
        w = MainWindow()
        w._on_add_rule()

        calls = []
        original = QMessageBox.question
        def tracking_question(*args, **kwargs):
            calls.append(True)
            return QMessageBox.StandardButton.Cancel
        monkeypatch.setattr(QMessageBox, "question", tracking_question)

        event = QCloseEvent()
        w.closeEvent(event)
        assert calls, "QMessageBox.question should be called when doc is dirty"

    def test_close_no_dialog_when_clean(self, qapp, monkeypatch):
        """No dialog when doc is clean."""
        from PySide6.QtGui import QCloseEvent
        w = MainWindow()
        assert not w._doc.dirty

        calls = []
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: calls.append(True) or QMessageBox.StandardButton.Cancel,
        )
        event = QCloseEvent()
        w.closeEvent(event)
        assert not calls, "No dialog should appear when doc is clean"


# ---------------------------------------------------------------------------
# TestFileMgrIntegration
# ---------------------------------------------------------------------------

class TestFileMgrIntegration:
    def test_main_window_has_file_mgr(self, qapp):
        from core.file_manager import FilterFileManager
        w = MainWindow()
        assert hasattr(w, "_file_mgr")
        assert isinstance(w._file_mgr, FilterFileManager)

    def test_load_file_updates_file_mgr_path(self, qapp, tmp_path):
        p = tmp_path / "mgr.filter"
        p.write_text("Show\n", encoding="utf-8")
        w = MainWindow()
        w.load_file(str(p))
        assert w._file_mgr.current_path == str(p)

    def test_load_file_clears_file_mgr_dirty(self, qapp, tmp_path):
        p = tmp_path / "mgr.filter"
        p.write_text("Show\n", encoding="utf-8")
        w = MainWindow()
        w._file_mgr.mark_dirty()
        w.load_file(str(p))
        assert w._file_mgr.is_dirty is False
