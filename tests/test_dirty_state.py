"""Tests for P17.1 Dirty State Protection

Covers:
  - FilterDocument dirty lifecycle (is_dirty / mark_dirty / clear_dirty)
  - Dirty triggers: edit, undo, redo, quick fix
  - Dirty cleared: save, new file, load file
  - MainWindow title bar * indicator
  - closeEvent: Save / Discard / Cancel
  - _confirm_discard: Save / Discard / Cancel for new_file / open_file
  - load_file with dirty state
  - new_file with dirty state
"""

import pytest

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QCloseEvent

from core.models import FilterRule
from core.document import FilterDocument
from core.commands import UpdateRuleCommand


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def _make_rule(font_size: str = "32") -> FilterRule:
    return FilterRule(
        action="Show",
        enabled=True,
        conditions=[],
        actions=[["SetFontSize", font_size]],
        pre_lines=[],
        inline_comment="",
        unknown_lines=[],
    )


@pytest.fixture
def window(qapp, tmp_path):
    from core.settings_manager import SettingsManager
    from ui.main_window import MainWindow
    mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
    return MainWindow(settings_mgr=mgr)


def _write_filter(tmp_path, name: str = "t.filter", text: str = "") -> str:
    if not text:
        text = "Show\n    SetFontSize 32\n\n"
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    return str(f)


# ---------------------------------------------------------------------------
# TestFilterDocumentDirtyLifecycle
# (Unit tests — no UI needed)
# ---------------------------------------------------------------------------

class TestFilterDocumentDirtyLifecycle:

    def test_initial_not_dirty(self):
        doc = FilterDocument()
        assert doc.dirty is False

    def test_dirty_property(self):
        doc = FilterDocument()
        doc.mark_dirty()
        assert doc.dirty is True

    def test_mark_dirty(self):
        doc = FilterDocument()
        doc.mark_dirty()
        assert doc.dirty is True

    def test_clear_dirty(self):
        doc = FilterDocument()
        doc.mark_dirty()
        doc.clear_dirty()
        assert doc.dirty is False

    def test_execute_marks_dirty(self):
        doc = FilterDocument()
        doc.load_from_text("Show\n    SetFontSize 32\n\n")
        assert doc.dirty is False
        rule = _make_rule("45")
        import copy
        old = copy.deepcopy(doc.rules[0])
        cmd = UpdateRuleCommand(doc, 0, old, rule)
        doc.execute(cmd)
        assert doc.dirty is True

    def test_undo_marks_dirty(self):
        doc = FilterDocument()
        doc.load_from_text("Show\n    SetFontSize 32\n\n")
        import copy
        old = copy.deepcopy(doc.rules[0])
        cmd = UpdateRuleCommand(doc, 0, old, _make_rule("45"))
        doc.execute(cmd)
        doc.clear_dirty()          # reset to verify undo re-sets it
        doc.undo()
        assert doc.dirty is True

    def test_redo_marks_dirty(self):
        doc = FilterDocument()
        doc.load_from_text("Show\n    SetFontSize 32\n\n")
        import copy
        old = copy.deepcopy(doc.rules[0])
        cmd = UpdateRuleCommand(doc, 0, old, _make_rule("45"))
        doc.execute(cmd)
        doc.undo()
        doc.clear_dirty()
        doc.redo()
        assert doc.dirty is True

    def test_load_from_text_clears_dirty(self):
        doc = FilterDocument()
        doc.mark_dirty()
        doc.load_from_text("Show\n    SetFontSize 32\n\n")
        assert doc.dirty is False

    def test_load_from_text_resets_undo_stack(self):
        doc = FilterDocument()
        doc.load_from_text("Show\n    SetFontSize 32\n\n")
        import copy
        old = copy.deepcopy(doc.rules[0])
        doc.execute(UpdateRuleCommand(doc, 0, old, _make_rule("45")))
        doc.load_from_text("Show\n    SetFontSize 32\n\n")
        assert not doc.can_undo()


# ---------------------------------------------------------------------------
# TestTitleBarDirtyIndicator
# ---------------------------------------------------------------------------

class TestTitleBarDirtyIndicator:

    def test_title_clean_has_no_asterisk(self, window, tmp_path):
        path = _write_filter(tmp_path)
        window.load_file(path)
        assert "*" not in window.windowTitle()

    def test_title_dirty_has_asterisk(self, window, tmp_path):
        from core.commands import UpdateRuleCommand
        import copy
        path = _write_filter(tmp_path)
        window.load_file(path)
        rule = window._doc.rules[0]
        old = copy.deepcopy(rule)
        cmd = UpdateRuleCommand(window._doc, 0, old, _make_rule("45"))
        window._doc.execute(cmd)
        window._refresh_status()
        assert "*" in window.windowTitle()

    def test_title_clean_after_save(self, window, tmp_path, monkeypatch):
        from core.commands import UpdateRuleCommand
        import copy
        path = _write_filter(tmp_path)
        window.load_file(path)
        old = copy.deepcopy(window._doc.rules[0])
        cmd = UpdateRuleCommand(window._doc, 0, old, _make_rule("45"))
        window._doc.execute(cmd)
        window._refresh_status()
        assert "*" in window.windowTitle()
        # Monkeypatch dialog to avoid validation warning dialog
        monkeypatch.setattr(
            "ui.save_warning_dialog.SaveWarningDialog.confirm",
            lambda *a, **kw: True,
        )
        window.save_file()
        assert "*" not in window.windowTitle()


# ---------------------------------------------------------------------------
# TestDirtyAfterOperations — MainWindow level
# ---------------------------------------------------------------------------

class TestDirtyAfterOperations:

    def test_dirty_after_rule_edit(self, window, tmp_path):
        from core.commands import UpdateRuleCommand
        import copy
        path = _write_filter(tmp_path)
        window.load_file(path)
        assert window._doc.dirty is False
        old = copy.deepcopy(window._doc.rules[0])
        cmd = UpdateRuleCommand(window._doc, 0, old, _make_rule("45"))
        window._doc.execute(cmd)
        assert window._doc.dirty is True

    def test_clean_after_load_file(self, window, tmp_path):
        path = _write_filter(tmp_path)
        window.load_file(path)
        assert window._doc.dirty is False

    def test_clean_after_save(self, window, tmp_path, monkeypatch):
        from core.commands import UpdateRuleCommand
        import copy
        monkeypatch.setattr(
            "ui.save_warning_dialog.SaveWarningDialog.confirm",
            lambda *a, **kw: True,
        )
        path = _write_filter(tmp_path)
        window.load_file(path)
        old = copy.deepcopy(window._doc.rules[0])
        cmd = UpdateRuleCommand(window._doc, 0, old, _make_rule("45"))
        window._doc.execute(cmd)
        assert window._doc.dirty is True
        window.save_file()
        assert window._doc.dirty is False

    def test_dirty_after_undo(self, window, tmp_path):
        from core.commands import UpdateRuleCommand
        import copy
        path = _write_filter(tmp_path)
        window.load_file(path)
        old = copy.deepcopy(window._doc.rules[0])
        cmd = UpdateRuleCommand(window._doc, 0, old, _make_rule("45"))
        window._doc.execute(cmd)
        window._doc.clear_dirty()
        window._on_undo()
        assert window._doc.dirty is True

    def test_dirty_after_redo(self, window, tmp_path):
        from core.commands import UpdateRuleCommand
        import copy
        path = _write_filter(tmp_path)
        window.load_file(path)
        old = copy.deepcopy(window._doc.rules[0])
        cmd = UpdateRuleCommand(window._doc, 0, old, _make_rule("45"))
        window._doc.execute(cmd)
        window._on_undo()
        window._doc.clear_dirty()
        window._on_redo()
        assert window._doc.dirty is True

    def test_dirty_after_quick_fix(self, window, tmp_path):
        from core.quick_fix import QuickFix
        path = _write_filter(tmp_path, text="Show\n    SetFontSize 99\n\n")
        window.load_file(path)
        window._doc.clear_dirty()
        fix = QuickFix("修正為 45", "SetFontSize", "45")
        window._on_quick_fix_requested(0, fix)
        assert window._doc.dirty is True

    def test_clean_after_new_file(self, window, tmp_path, monkeypatch):
        from core.commands import UpdateRuleCommand
        import copy
        path = _write_filter(tmp_path)
        window.load_file(path)
        old = copy.deepcopy(window._doc.rules[0])
        cmd = UpdateRuleCommand(window._doc, 0, old, _make_rule("45"))
        window._doc.execute(cmd)
        assert window._doc.dirty is True
        # Monkeypatch _confirm_discard to return True (discard)
        monkeypatch.setattr(window, "_confirm_discard", lambda: True)
        window.new_file()
        assert window._doc.dirty is False


# ---------------------------------------------------------------------------
# TestCloseEvent
# ---------------------------------------------------------------------------

class TestCloseEvent:

    def _make_close_event(self):
        return QCloseEvent()

    def test_close_clean_no_dialog(self, window, tmp_path, monkeypatch):
        path = _write_filter(tmp_path)
        window.load_file(path)
        assert window._doc.dirty is False
        dialog_calls = []
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: dialog_calls.append(True) or QMessageBox.StandardButton.Cancel,
        )
        ev = self._make_close_event()
        window.closeEvent(ev)
        assert dialog_calls == [], "No dialog should appear when not dirty"
        assert ev.isAccepted()

    def test_close_cancel_ignores_event(self, window, tmp_path, monkeypatch):
        from core.commands import UpdateRuleCommand
        import copy
        path = _write_filter(tmp_path)
        window.load_file(path)
        old = copy.deepcopy(window._doc.rules[0])
        cmd = UpdateRuleCommand(window._doc, 0, old, _make_rule("45"))
        window._doc.execute(cmd)
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Cancel,
        )
        ev = self._make_close_event()
        window.closeEvent(ev)
        assert not ev.isAccepted()

    def test_close_discard_accepts_event(self, window, tmp_path, monkeypatch):
        from core.commands import UpdateRuleCommand
        import copy
        path = _write_filter(tmp_path)
        window.load_file(path)
        old = copy.deepcopy(window._doc.rules[0])
        cmd = UpdateRuleCommand(window._doc, 0, old, _make_rule("45"))
        window._doc.execute(cmd)
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Discard,
        )
        ev = self._make_close_event()
        window.closeEvent(ev)
        assert ev.isAccepted()

    def test_close_save_accepts_when_save_succeeds(self, window, tmp_path, monkeypatch):
        from core.commands import UpdateRuleCommand
        import copy
        path = _write_filter(tmp_path)
        window.load_file(path)
        old = copy.deepcopy(window._doc.rules[0])
        cmd = UpdateRuleCommand(window._doc, 0, old, _make_rule("45"))
        window._doc.execute(cmd)
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Save,
        )
        # Bypass validation dialog
        monkeypatch.setattr(
            "ui.save_warning_dialog.SaveWarningDialog.confirm",
            lambda *a, **kw: True,
        )
        ev = self._make_close_event()
        window.closeEvent(ev)
        assert ev.isAccepted()
        assert window._doc.dirty is False

    def test_close_save_ignores_when_no_path_cancelled(self, window, tmp_path, monkeypatch):
        """If user picks Save but then cancels the Save As dialog, close is aborted."""
        from core.commands import UpdateRuleCommand
        import copy
        # New doc with no file path
        window.new_file()
        # Force dirty
        rule = _make_rule("99")
        from core.commands import AddRuleCommand
        cmd = AddRuleCommand(window._doc, 0, rule)
        window._doc.execute(cmd)
        assert window._doc.dirty is True
        # QMessageBox → Save
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Save,
        )
        # Save As dialog cancelled (returns empty path)
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *a, **kw: ("", ""),
        )
        ev = self._make_close_event()
        window.closeEvent(ev)
        assert not ev.isAccepted(), "Should stay open when Save As is cancelled"


# ---------------------------------------------------------------------------
# TestConfirmDiscard — new_file and open_file paths
# ---------------------------------------------------------------------------

class TestConfirmDiscard:

    def _make_dirty(self, window, tmp_path):
        """Load a file then make it dirty via execute()."""
        from core.commands import UpdateRuleCommand
        import copy
        path = _write_filter(tmp_path)
        window.load_file(path)
        old = copy.deepcopy(window._doc.rules[0])
        cmd = UpdateRuleCommand(window._doc, 0, old, _make_rule("45"))
        window._doc.execute(cmd)
        return path

    def test_confirm_discard_clean_returns_true(self, window):
        assert window._confirm_discard() is True

    def test_confirm_discard_dirty_cancel_returns_false(self, window, tmp_path, monkeypatch):
        self._make_dirty(window, tmp_path)
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Cancel,
        )
        assert window._confirm_discard() is False

    def test_confirm_discard_dirty_discard_returns_true(self, window, tmp_path, monkeypatch):
        self._make_dirty(window, tmp_path)
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Discard,
        )
        assert window._confirm_discard() is True

    def test_confirm_discard_dirty_save_returns_true_on_success(
        self, window, tmp_path, monkeypatch
    ):
        self._make_dirty(window, tmp_path)
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Save,
        )
        monkeypatch.setattr(
            "ui.save_warning_dialog.SaveWarningDialog.confirm",
            lambda *a, **kw: True,
        )
        result = window._confirm_discard()
        assert result is True
        assert window._doc.dirty is False

    def test_confirm_discard_dialog_has_three_buttons(
        self, window, tmp_path, monkeypatch
    ):
        self._make_dirty(window, tmp_path)
        captured_buttons = []

        def fake_question(parent, title, text, buttons, default=None):
            captured_buttons.append(int(buttons))
            return QMessageBox.StandardButton.Cancel

        monkeypatch.setattr(QMessageBox, "question", fake_question)
        window._confirm_discard()
        expected = int(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        assert captured_buttons[0] == expected

    # -- new_file path --------------------------------------------------

    def test_new_file_dirty_cancel_aborts(self, window, tmp_path, monkeypatch):
        path = self._make_dirty(window, tmp_path)
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Cancel,
        )
        old_doc = window._doc
        window.new_file()
        assert window._doc is old_doc, "Document should NOT change on Cancel"

    def test_new_file_dirty_discard_proceeds(self, window, tmp_path, monkeypatch):
        self._make_dirty(window, tmp_path)
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Discard,
        )
        window.new_file()
        assert window._doc.dirty is False
        assert len(window._doc.rules) == 0

    def test_new_file_dirty_save_then_proceeds(self, window, tmp_path, monkeypatch):
        self._make_dirty(window, tmp_path)
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Save,
        )
        monkeypatch.setattr(
            "ui.save_warning_dialog.SaveWarningDialog.confirm",
            lambda *a, **kw: True,
        )
        window.new_file()
        # After Save + new_file, doc should be blank and clean
        assert window._doc.dirty is False
        assert len(window._doc.rules) == 0

    # -- open_file / load_file path ------------------------------------

    def test_load_file_dirty_discard_proceeds(self, window, tmp_path, monkeypatch):
        self._make_dirty(window, tmp_path)
        new_path = _write_filter(tmp_path, name="new.filter",
                                  text="Show\n    SetFontSize 20\n\n")
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Discard,
        )
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getOpenFileName",
            lambda *a, **kw: (new_path, ""),
        )
        window.open_file()
        # New file should be loaded
        vals = {str(k): str(v) for k, v in window._doc.rules[0].actions}
        assert vals["SetFontSize"] == "20"
        assert window._doc.dirty is False

    def test_load_file_dirty_cancel_aborts(self, window, tmp_path, monkeypatch):
        path = self._make_dirty(window, tmp_path)
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Cancel,
        )
        old_path = window._doc.file_path
        window.open_file()   # internally calls _confirm_discard → Cancel
        assert window._doc.file_path == old_path, "File path should not change"

    def test_load_clean_proceeds_without_dialog(self, window, tmp_path, monkeypatch):
        path = _write_filter(tmp_path)
        window.load_file(path)
        assert window._doc.dirty is False
        dialog_calls = []
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: dialog_calls.append(True) or QMessageBox.StandardButton.Cancel,
        )
        new_path = _write_filter(tmp_path, name="new.filter")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getOpenFileName",
            lambda *a, **kw: (new_path, ""),
        )
        window.open_file()
        assert dialog_calls == [], "No dirty dialog when doc is clean"
