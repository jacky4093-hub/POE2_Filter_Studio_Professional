"""Tests for ValidationPanel — P16.2 Validation UI"""

import pytest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.validator import ValidationIssue, ValidationSeverity
from ui.validation_panel import ValidationPanel


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def _issue(sev: ValidationSeverity, field: str = "f", msg: str = "m", idx: int = -1) -> ValidationIssue:
    return ValidationIssue(sev, field, msg, rule_index=idx)


# ---------------------------------------------------------------------------
# TestValidationPanelWidget — structural
# ---------------------------------------------------------------------------

class TestValidationPanelWidget:

    def test_object_name(self, qapp):
        panel = ValidationPanel()
        assert panel.objectName() == "ValidationPanel"

    def test_has_error_chip(self, qapp):
        panel = ValidationPanel()
        assert hasattr(panel, "_error_chip")

    def test_has_warning_chip(self, qapp):
        panel = ValidationPanel()
        assert hasattr(panel, "_warning_chip")

    def test_has_info_chip(self, qapp):
        panel = ValidationPanel()
        assert hasattr(panel, "_info_chip")

    def test_has_list_widget(self, qapp):
        panel = ValidationPanel()
        assert hasattr(panel, "_list")

    def test_chips_initial_zero(self, qapp):
        panel = ValidationPanel()
        assert "0" in panel._error_chip.text()
        assert "0" in panel._warning_chip.text()
        assert "0" in panel._info_chip.text()

    def test_list_initial_empty(self, qapp):
        panel = ValidationPanel()
        assert panel._list.count() == 0

    def test_has_issue_clicked_signal(self, qapp):
        assert hasattr(ValidationPanel, "issue_clicked")

    def test_chip_object_names(self, qapp):
        panel = ValidationPanel()
        assert panel._error_chip.objectName()   == "ValidationChipError"
        assert panel._warning_chip.objectName() == "ValidationChipWarning"
        assert panel._info_chip.objectName()    == "ValidationChipInfo"

    def test_list_object_name(self, qapp):
        panel = ValidationPanel()
        assert panel._list.objectName() == "ValidationIssueList"


# ---------------------------------------------------------------------------
# TestValidationPanelCounts
# ---------------------------------------------------------------------------

class TestValidationPanelCounts:

    def test_single_error_count(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.ERROR)])
        assert "1" in panel._error_chip.text()
        assert "0" in panel._warning_chip.text()
        assert "0" in panel._info_chip.text()

    def test_single_warning_count(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.WARNING)])
        assert "0" in panel._error_chip.text()
        assert "1" in panel._warning_chip.text()
        assert "0" in panel._info_chip.text()

    def test_single_info_count(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.INFO)])
        assert "0" in panel._error_chip.text()
        assert "0" in panel._warning_chip.text()
        assert "1" in panel._info_chip.text()

    def test_mixed_counts(self, qapp):
        issues = [
            _issue(ValidationSeverity.ERROR),
            _issue(ValidationSeverity.ERROR),
            _issue(ValidationSeverity.WARNING),
            _issue(ValidationSeverity.INFO),
        ]
        panel = ValidationPanel()
        panel.refresh(issues)
        assert "2" in panel._error_chip.text()
        assert "1" in panel._warning_chip.text()
        assert "1" in panel._info_chip.text()

    def test_empty_issues_shows_zeros(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.ERROR)])
        panel.refresh([])
        assert "0" in panel._error_chip.text()
        assert "0" in panel._warning_chip.text()
        assert "0" in panel._info_chip.text()

    def test_large_error_count(self, qapp):
        issues = [_issue(ValidationSeverity.ERROR) for _ in range(10)]
        panel = ValidationPanel()
        panel.refresh(issues)
        assert "10" in panel._error_chip.text()


# ---------------------------------------------------------------------------
# TestValidationPanelIssueRows
# ---------------------------------------------------------------------------

class TestValidationPanelIssueRows:

    def test_two_issues_two_rows(self, qapp):
        panel = ValidationPanel()
        panel.refresh([
            _issue(ValidationSeverity.ERROR),
            _issue(ValidationSeverity.WARNING),
        ])
        assert panel._list.count() == 2

    def test_zero_issues_zero_rows(self, qapp):
        panel = ValidationPanel()
        panel.refresh([])
        assert panel._list.count() == 0

    def test_item_text_contains_field(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.ERROR, field="SetTextColor")])
        text = panel._list.item(0).text()
        assert "SetTextColor" in text

    def test_item_text_contains_message(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.WARNING, msg="bad range")])
        text = panel._list.item(0).text()
        assert "bad range" in text

    def test_item_text_contains_rule_index(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.ERROR, idx=5)])
        text = panel._list.item(0).text()
        assert "5" in text

    def test_item_text_minus_one_shows_dash(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.INFO, idx=-1)])
        text = panel._list.item(0).text()
        assert "—" in text

    def test_item_user_data_stores_rule_index(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.ERROR, idx=7)])
        stored = panel._list.item(0).data(Qt.ItemDataRole.UserRole)
        assert stored == 7

    def test_item_user_data_minus_one(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.INFO, idx=-1)])
        stored = panel._list.item(0).data(Qt.ItemDataRole.UserRole)
        assert stored == -1

    def test_item_order_preserved(self, qapp):
        panel = ValidationPanel()
        issues = [
            _issue(ValidationSeverity.ERROR,   field="A"),
            _issue(ValidationSeverity.WARNING, field="B"),
            _issue(ValidationSeverity.INFO,    field="C"),
        ]
        panel.refresh(issues)
        assert "A" in panel._list.item(0).text()
        assert "B" in panel._list.item(1).text()
        assert "C" in panel._list.item(2).text()

    def test_severity_prefix_error(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.ERROR)])
        assert "[E]" in panel._list.item(0).text()

    def test_severity_prefix_warning(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.WARNING)])
        assert "[W]" in panel._list.item(0).text()

    def test_severity_prefix_info(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.INFO)])
        assert "[I]" in panel._list.item(0).text()


# ---------------------------------------------------------------------------
# TestValidationPanelCleanState
# ---------------------------------------------------------------------------

class TestValidationPanelCleanState:

    def test_clear_empties_list(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.ERROR)])
        panel.clear()
        assert panel._list.count() == 0

    def test_clear_resets_all_chips_to_zero(self, qapp):
        panel = ValidationPanel()
        panel.refresh([
            _issue(ValidationSeverity.ERROR),
            _issue(ValidationSeverity.WARNING),
            _issue(ValidationSeverity.INFO),
        ])
        panel.clear()
        assert "0" in panel._error_chip.text()
        assert "0" in panel._warning_chip.text()
        assert "0" in panel._info_chip.text()

    def test_refresh_empty_list_is_clean(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.ERROR)])
        panel.refresh([])
        assert panel._list.count() == 0
        assert "0" in panel._error_chip.text()

    def test_double_clear_is_safe(self, qapp):
        panel = ValidationPanel()
        panel.clear()
        panel.clear()  # should not raise
        assert panel._list.count() == 0


# ---------------------------------------------------------------------------
# TestValidationPanelIssueClick
# ---------------------------------------------------------------------------

class TestValidationPanelIssueClick:

    def test_click_emits_rule_index(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.ERROR, idx=3)])
        received = []
        panel.issue_clicked.connect(lambda i: received.append(i))
        panel._list.itemClicked.emit(panel._list.item(0))
        assert received == [3]

    def test_click_emits_minus_one_for_no_rule(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.INFO, idx=-1)])
        received = []
        panel.issue_clicked.connect(lambda i: received.append(i))
        panel._list.itemClicked.emit(panel._list.item(0))
        assert received == [-1]

    def test_click_emits_correct_index_from_multiple(self, qapp):
        panel = ValidationPanel()
        panel.refresh([
            _issue(ValidationSeverity.ERROR,   idx=0),
            _issue(ValidationSeverity.WARNING, idx=5),
            _issue(ValidationSeverity.INFO,    idx=10),
        ])
        received = []
        panel.issue_clicked.connect(lambda i: received.append(i))
        panel._list.itemClicked.emit(panel._list.item(1))
        assert received == [5]

    def test_signal_is_int(self, qapp):
        panel = ValidationPanel()
        panel.refresh([_issue(ValidationSeverity.ERROR, idx=2)])
        received = []
        panel.issue_clicked.connect(lambda i: received.append(type(i).__name__))
        panel._list.itemClicked.emit(panel._list.item(0))
        assert received == ["int"]


# ---------------------------------------------------------------------------
# TestMainWindowValidationIntegration
# ---------------------------------------------------------------------------

class TestMainWindowValidationIntegration:
    @pytest.fixture(scope="class")
    def qapp(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication(["-platform", "offscreen"])
        return app

    @pytest.fixture
    def window(self, qapp, tmp_path):
        from core.settings_manager import SettingsManager
        from ui.main_window import MainWindow
        mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
        return MainWindow(settings_mgr=mgr)

    def test_validation_panel_attribute_exists(self, window):
        assert hasattr(window, "validation_panel")
        from ui.validation_panel import ValidationPanel
        assert isinstance(window.validation_panel, ValidationPanel)

    def test_refresh_validation_method_exists(self, window):
        assert callable(getattr(window, "_refresh_validation", None))

    def test_on_validation_issue_clicked_method_exists(self, window):
        assert callable(getattr(window, "_on_validation_issue_clicked", None))

    def test_refresh_validation_does_not_raise_on_empty_doc(self, window):
        window._refresh_validation()  # empty document → no crash

    def test_load_file_runs_validation(self, window, tmp_path):
        f = tmp_path / "t.filter"
        f.write_text(
            'Show\n    SetFontSize 99\n\nShow\n    SetTextColor 255 0 0 255\n\n',
            encoding="utf-8",
        )
        window.load_file(str(f))
        # P17.10A: load_file() defers validation; fire it now to populate the panel
        QApplication.processEvents()
        # After load, validation_panel should show at least 1 issue (font size 99)
        assert window.validation_panel._error_chip.text() is not None
        # The list should have items for the invalid font size
        assert window.validation_panel._list.count() >= 1

    def test_no_issues_shows_zero_counts(self, window, tmp_path):
        f = tmp_path / "clean.filter"
        f.write_text(
            'Show\n    SetFontSize 32\n    SetTextColor 255 200 0 255\n\n',
            encoding="utf-8",
        )
        window.load_file(str(f))
        assert "0" in window.validation_panel._error_chip.text()

    def test_clicking_issue_navigates_to_rule(self, window, tmp_path):
        f = tmp_path / "nav.filter"
        f.write_text(
            'Show\n    SetFontSize 32\n\nShow\n    SetFontSize 99\n\n',
            encoding="utf-8",
        )
        window.load_file(str(f))
        # P17.10A: load_file() defers validation; fire it now to populate the panel
        QApplication.processEvents()
        # First, find the item for rule index 1 (the invalid one)
        lw = window.validation_panel._list
        target_item = None
        for i in range(lw.count()):
            item = lw.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == 1:
                target_item = item
                break
        assert target_item is not None, "Expected an issue for rule index 1"
        # Clicking should not raise
        window._on_validation_issue_clicked(1)

    def test_invalid_rule_index_click_ignored(self, window):
        # rule_index out of range → should not raise
        window._on_validation_issue_clicked(-1)
        window._on_validation_issue_clicked(9999)
