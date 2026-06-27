"""Tests for SaveWarningDialog and _check_save_issues — P16.3 Save Warning"""

import pytest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from core.validator import ValidationIssue, ValidationSeverity
from ui.save_warning_dialog import SaveWarningDialog, _MAX_DISPLAY_ISSUES


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def _err(field="f", msg="m", idx=0) -> ValidationIssue:
    return ValidationIssue(ValidationSeverity.ERROR, field, msg, rule_index=idx)


def _warn(field="f", msg="m", idx=0) -> ValidationIssue:
    return ValidationIssue(ValidationSeverity.WARNING, field, msg, rule_index=idx)


def _info(field="f", msg="m", idx=0) -> ValidationIssue:
    return ValidationIssue(ValidationSeverity.INFO, field, msg, rule_index=idx)


# ---------------------------------------------------------------------------
# TestSaveWarningDialogStructure
# ---------------------------------------------------------------------------

class TestSaveWarningDialogStructure:

    def test_object_name(self, qapp):
        dlg = SaveWarningDialog([_err()])
        assert dlg.objectName() == "SaveWarningDialog"

    def test_window_title(self, qapp):
        dlg = SaveWarningDialog([_err()])
        assert "儲存" in dlg.windowTitle()

    def test_has_issue_list(self, qapp):
        dlg = SaveWarningDialog([_err()])
        assert hasattr(dlg, "_issue_list")

    def test_has_cancel_button(self, qapp):
        dlg = SaveWarningDialog([_err()])
        assert hasattr(dlg, "_cancel_btn")

    def test_has_save_button(self, qapp):
        dlg = SaveWarningDialog([_err()])
        assert hasattr(dlg, "_save_btn")

    def test_cancel_button_object_name(self, qapp):
        dlg = SaveWarningDialog([_err()])
        assert dlg._cancel_btn.objectName() == "SaveWarnCancelBtn"

    def test_save_button_object_name(self, qapp):
        dlg = SaveWarningDialog([_err()])
        assert dlg._save_btn.objectName() == "SaveWarnSaveBtn"

    def test_issue_list_object_name(self, qapp):
        dlg = SaveWarningDialog([_err()])
        assert dlg._issue_list.objectName() == "SaveWarnIssueList"

    def test_save_button_is_default(self, qapp):
        dlg = SaveWarningDialog([_err()])
        assert dlg._save_btn.isDefault()

    def test_is_qdialog(self, qapp):
        dlg = SaveWarningDialog([_err()])
        assert isinstance(dlg, QDialog)


# ---------------------------------------------------------------------------
# TestSaveWarningDialogCounts
# ---------------------------------------------------------------------------

class TestSaveWarningDialogCounts:

    def test_single_error_shows_one_error(self, qapp):
        dlg = SaveWarningDialog([_err()])
        assert dlg._n_error == 1
        assert dlg._n_warning == 0

    def test_single_warning_shows_one_warning(self, qapp):
        dlg = SaveWarningDialog([_warn()])
        assert dlg._n_error == 0
        assert dlg._n_warning == 1

    def test_mixed_counts(self, qapp):
        issues = [_err(), _err(), _warn()]
        dlg = SaveWarningDialog(issues)
        assert dlg._n_error == 2
        assert dlg._n_warning == 1

    def test_summary_label_contains_error_count(self, qapp):
        dlg = SaveWarningDialog([_err(), _err()])
        assert "2" in dlg._error_count_label.text()

    def test_summary_label_contains_warning_count(self, qapp):
        dlg = SaveWarningDialog([_warn(), _warn(), _warn()])
        assert "3" in dlg._error_count_label.text()

    def test_zero_warning_from_pure_errors(self, qapp):
        dlg = SaveWarningDialog([_err()])
        assert dlg._n_warning == 0


# ---------------------------------------------------------------------------
# TestSaveWarningDialogIssueList
# ---------------------------------------------------------------------------

class TestSaveWarningDialogIssueList:

    def test_one_issue_one_row(self, qapp):
        dlg = SaveWarningDialog([_err()])
        assert dlg._issue_list.count() == 1

    def test_five_issues_five_rows(self, qapp):
        dlg = SaveWarningDialog([_err() for _ in range(5)])
        assert dlg._issue_list.count() == 5

    def test_item_text_contains_field(self, qapp):
        dlg = SaveWarningDialog([_err(field="SetTextColor")])
        assert "SetTextColor" in dlg._issue_list.item(0).text()

    def test_item_text_contains_message(self, qapp):
        dlg = SaveWarningDialog([_err(msg="color out of range")])
        assert "color out of range" in dlg._issue_list.item(0).text()

    def test_item_text_contains_rule_index(self, qapp):
        dlg = SaveWarningDialog([_err(idx=4)])
        assert "4" in dlg._issue_list.item(0).text()

    def test_error_prefix(self, qapp):
        dlg = SaveWarningDialog([_err()])
        assert "[E]" in dlg._issue_list.item(0).text()

    def test_warning_prefix(self, qapp):
        dlg = SaveWarningDialog([_warn()])
        assert "[W]" in dlg._issue_list.item(0).text()

    def test_max_ten_issues_displayed(self, qapp):
        issues = [_err() for _ in range(15)]
        dlg = SaveWarningDialog(issues)
        # List has 10 issue rows + 1 overflow row
        assert dlg._issue_list.count() == _MAX_DISPLAY_ISSUES + 1

    def test_exactly_ten_issues_no_overflow(self, qapp):
        issues = [_err() for _ in range(_MAX_DISPLAY_ISSUES)]
        dlg = SaveWarningDialog(issues)
        assert dlg._issue_list.count() == _MAX_DISPLAY_ISSUES

    def test_overflow_row_text_mentions_count(self, qapp):
        issues = [_err() for _ in range(13)]
        dlg = SaveWarningDialog(issues)
        overflow_item = dlg._issue_list.item(_MAX_DISPLAY_ISSUES)
        assert "3" in overflow_item.text()

    def test_rule_index_minus_one_shows_dash(self, qapp):
        dlg = SaveWarningDialog([_err(idx=-1)])
        assert "—" in dlg._issue_list.item(0).text()


# ---------------------------------------------------------------------------
# TestSaveWarningDialogButtons
# ---------------------------------------------------------------------------

class TestSaveWarningDialogButtons:

    def test_save_btn_click_accepts(self, qapp):
        dlg = SaveWarningDialog([_err()])
        result = []

        def on_accepted():
            result.append("accepted")
        dlg.accepted.connect(on_accepted)
        dlg._save_btn.click()
        assert result == ["accepted"]

    def test_cancel_btn_click_rejects(self, qapp):
        dlg = SaveWarningDialog([_err()])
        result = []

        def on_rejected():
            result.append("rejected")
        dlg.rejected.connect(on_rejected)
        dlg._cancel_btn.click()
        assert result == ["rejected"]


# ---------------------------------------------------------------------------
# TestCheckSaveIssues — unit tests via monkeypatching SaveWarningDialog.confirm
# ---------------------------------------------------------------------------

class TestCheckSaveIssues:

    @pytest.fixture
    def window(self, qapp, tmp_path):
        from core.settings_manager import SettingsManager
        from ui.main_window import MainWindow
        mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
        return MainWindow(settings_mgr=mgr)

    def _load_clean_file(self, window, tmp_path) -> str:
        f = tmp_path / "clean.filter"
        f.write_text(
            "Show\n    SetFontSize 32\n    SetTextColor 255 200 0 255\n\n",
            encoding="utf-8",
        )
        window.load_file(str(f))
        return str(f)

    def _load_invalid_file(self, window, tmp_path) -> str:
        f = tmp_path / "bad.filter"
        f.write_text(
            "Show\n    SetFontSize 99\n\n",   # SetFontSize 99 → WARNING
            encoding="utf-8",
        )
        window.load_file(str(f))
        return str(f)

    def _load_info_only_file(self, window, tmp_path) -> str:
        f = tmp_path / "info.filter"
        # Empty Show → INFO (no conditions/actions); no ERROR/WARNING
        f.write_text("Show\n\n", encoding="utf-8")
        window.load_file(str(f))
        return str(f)

    # -- _check_save_issues returns True/False ----------------------------

    def test_no_issues_returns_true(self, window, tmp_path):
        self._load_clean_file(window, tmp_path)
        assert window._check_save_issues() is True

    def test_info_only_returns_true(self, window, tmp_path):
        self._load_info_only_file(window, tmp_path)
        # INFO issues never block saving
        assert window._check_save_issues() is True

    def test_warning_calls_dialog(self, window, tmp_path, monkeypatch):
        self._load_invalid_file(window, tmp_path)
        called = []
        monkeypatch.setattr(
            "ui.save_warning_dialog.SaveWarningDialog.confirm",
            lambda issues, parent=None: called.append(issues) or True,
        )
        result = window._check_save_issues()
        assert called, "confirm() should have been called"
        assert result is True

    def test_error_calls_dialog(self, window, tmp_path, monkeypatch):
        f = tmp_path / "err.filter"
        f.write_text("Show\n    SetTextColor 999 0 0 255\n\n", encoding="utf-8")
        window.load_file(str(f))
        called = []
        monkeypatch.setattr(
            "ui.save_warning_dialog.SaveWarningDialog.confirm",
            lambda issues, parent=None: called.append(issues) or True,
        )
        result = window._check_save_issues()
        assert called
        assert result is True

    def test_cancel_returns_false(self, window, tmp_path, monkeypatch):
        self._load_invalid_file(window, tmp_path)
        monkeypatch.setattr(
            "ui.save_warning_dialog.SaveWarningDialog.confirm",
            lambda issues, parent=None: False,
        )
        assert window._check_save_issues() is False

    def test_save_anyway_returns_true(self, window, tmp_path, monkeypatch):
        self._load_invalid_file(window, tmp_path)
        monkeypatch.setattr(
            "ui.save_warning_dialog.SaveWarningDialog.confirm",
            lambda issues, parent=None: True,
        )
        assert window._check_save_issues() is True

    # -- save_file integration -------------------------------------------

    def test_save_file_skips_write_on_cancel(self, window, tmp_path, monkeypatch):
        path = self._load_invalid_file(window, tmp_path)
        monkeypatch.setattr(
            "ui.save_warning_dialog.SaveWarningDialog.confirm",
            lambda issues, parent=None: False,
        )
        write_calls = []
        original_write = window._file_mgr.save_as

        def mock_save(text, p):
            write_calls.append(p)
            return original_write(text, p)

        monkeypatch.setattr(window._file_mgr, "save_as", mock_save)
        window.save_file()
        assert write_calls == [], "File should NOT be written when user cancels"

    def test_save_file_writes_on_save_anyway(self, window, tmp_path, monkeypatch):
        path = self._load_invalid_file(window, tmp_path)
        monkeypatch.setattr(
            "ui.save_warning_dialog.SaveWarningDialog.confirm",
            lambda issues, parent=None: True,
        )
        write_calls = []
        original_write = window._file_mgr.save_as

        def mock_save(text, p):
            write_calls.append(p)
            return original_write(text, p)

        monkeypatch.setattr(window._file_mgr, "save_as", mock_save)
        window.save_file()
        assert len(write_calls) == 1, "File SHOULD be written when user says Save Anyway"

    def test_clean_file_saves_without_dialog(self, window, tmp_path, monkeypatch):
        path = self._load_clean_file(window, tmp_path)
        dialog_calls = []
        monkeypatch.setattr(
            "ui.save_warning_dialog.SaveWarningDialog.confirm",
            lambda issues, parent=None: dialog_calls.append(issues) or True,
        )
        write_calls = []
        original_write = window._file_mgr.save_as

        def mock_save(text, p):
            write_calls.append(p)
            return original_write(text, p)

        monkeypatch.setattr(window._file_mgr, "save_as", mock_save)
        window.save_file()
        assert dialog_calls == [], "Dialog must NOT appear for a clean file"
        assert len(write_calls) == 1

    def test_info_only_saves_without_dialog(self, window, tmp_path, monkeypatch):
        self._load_info_only_file(window, tmp_path)
        dialog_calls = []
        monkeypatch.setattr(
            "ui.save_warning_dialog.SaveWarningDialog.confirm",
            lambda issues, parent=None: dialog_calls.append(issues) or True,
        )
        write_calls = []
        original_write = window._file_mgr.save_as

        def mock_save(text, p):
            write_calls.append(p)
            return original_write(text, p)

        monkeypatch.setattr(window._file_mgr, "save_as", mock_save)
        window.save_file()
        assert dialog_calls == [], "INFO issues must NOT trigger dialog"
        assert len(write_calls) == 1
