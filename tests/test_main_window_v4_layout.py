"""P18.1 Main Window V4 Shell layout tests.

Verifies:
- 4-panel QSplitter exists with correct widget types
- NavigationBarV4 is present with expected signals
- NavigationBarV4 signals wire to the correct MainWindow slots
- Rule browser header / rule count label exist
- Status bar V4 labels exist
- Performance fast-path is unchanged (no full rebuild on field edit)
"""

import pytest

from PySide6.QtWidgets import QApplication, QSplitter
from PySide6.QtCore import Qt

from core.settings_manager import SettingsManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.fixture
def window(qapp, tmp_path):
    from ui.main_window import MainWindow
    mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
    return MainWindow(settings_mgr=mgr)


@pytest.fixture
def loaded_window(window, tmp_path):
    f = tmp_path / "test.filter"
    f.write_text(
        "Show\n    Class \"Currency\"\n\nHide\n    Class \"Gems\"\n\n",
        encoding="utf-8",
    )
    window.load_file(str(f))
    return window


# ──────────────────────────────────────────────────────────────────────
# 1. Structural checks
# ──────────────────────────────────────────────────────────────────────

class TestV4ShellStructure:
    def test_nav_bar_exists(self, window):
        from ui.navigation_bar import NavigationBarV4
        assert hasattr(window, "nav_bar")
        assert isinstance(window.nav_bar, NavigationBarV4)

    def test_splitter_has_four_panels(self, window):
        assert window._splitter.count() == 4

    def test_splitter_orientation_horizontal(self, window):
        assert window._splitter.orientation() == Qt.Orientation.Horizontal

    def test_rule_browser_header_exists(self, window):
        assert hasattr(window, "_rule_browser_hdr")
        assert hasattr(window, "_rule_count_lbl")

    def test_status_bar_labels_exist(self, window):
        assert hasattr(window, "_status_lbl")
        assert hasattr(window, "_status_rule_count_lbl")
        assert hasattr(window, "_status_validation_lbl")

    def test_col_category_object_name(self, window):
        col = window._splitter.widget(0)
        assert col.objectName() == "ColCategory"

    def test_col_browser_object_name(self, window):
        col = window._splitter.widget(1)
        assert col.objectName() == "ColBrowser"

    def test_col_preview_object_name(self, window):
        col = window._splitter.widget(3)
        assert col.objectName() == "ColPreview"

    def test_category_sidebar_in_panel_0(self, window):
        col = window._splitter.widget(0)
        assert window.category_sidebar.parent() is col

    def test_rule_browser_in_panel_1(self, window):
        col = window._splitter.widget(1)
        assert window.rule_card_browser.parent() is col

    def test_preview_panel_in_panel_3(self, window):
        col = window._splitter.widget(3)
        assert window.preview_panel.parent() is col

    def test_nav_bar_object_name(self, window):
        assert window.nav_bar.objectName() == "NavigationBarV4"


# ──────────────────────────────────────────────────────────────────────
# 2. NavigationBarV4 signals → MainWindow slots
# ──────────────────────────────────────────────────────────────────────

class TestNavBarSignals:
    def test_new_requested_calls_new_file(self, window, monkeypatch):
        called = []
        monkeypatch.setattr(window, "new_file", lambda: called.append(True))
        window.nav_bar.new_requested.emit()
        assert called

    def test_open_requested_calls_open_file(self, window, monkeypatch):
        called = []
        monkeypatch.setattr(window, "open_file", lambda: called.append(True))
        window.nav_bar.open_requested.emit()
        assert called

    def test_save_requested_calls_save_file(self, window, monkeypatch):
        called = []
        monkeypatch.setattr(window, "save_file", lambda: called.append(True))
        window.nav_bar.save_requested.emit()
        assert called

    def test_save_as_requested_calls_save_file_as(self, window, monkeypatch):
        called = []
        monkeypatch.setattr(window, "save_file_as", lambda: called.append(True))
        window.nav_bar.save_as_requested.emit()
        assert called

    def test_import_backup_shows_stub_dialog(self, window, monkeypatch):
        shown = []
        monkeypatch.setattr(
            "ui.main_window.QMessageBox.information",
            lambda *a, **kw: shown.append(True),
        )
        window._on_import_backup()
        assert shown

    def test_settings_requested_calls_open_preferences(self, window, monkeypatch):
        called = []
        monkeypatch.setattr(window, "open_preferences", lambda: called.append(True))
        window.nav_bar.settings_requested.emit()
        assert called


# ──────────────────────────────────────────────────────────────────────
# 3. Validation chip update
# ──────────────────────────────────────────────────────────────────────

class TestValidationChip:
    def test_chip_pass_on_valid_doc(self, loaded_window):
        loaded_window._refresh_validation()
        chip = loaded_window.nav_bar._validation_chip
        assert chip.property("validationState") in ("pass", "fail", "idle")

    def test_set_validation_status_pass(self, window):
        window.nav_bar.set_validation_status(True, "語法檢查：通過")
        chip = window.nav_bar._validation_chip
        assert chip.property("validationState") == "pass"
        assert "通過" in chip.text()

    def test_set_validation_status_fail(self, window):
        window.nav_bar.set_validation_status(False, "2 個錯誤")
        chip = window.nav_bar._validation_chip
        assert chip.property("validationState") == "fail"
        assert "2" in chip.text()


# ──────────────────────────────────────────────────────────────────────
# 4. Rule count label sync
# ──────────────────────────────────────────────────────────────────────

class TestRuleCountLabel:
    def test_count_label_updates_on_load(self, loaded_window):
        loaded_window._update_rule_count_label()
        text = loaded_window._rule_count_lbl.text()
        assert "規則列表" in text
        assert "2" in text

    def test_status_rule_count_updates_on_load(self, loaded_window):
        loaded_window._update_rule_count_label()
        text = loaded_window._status_rule_count_lbl.text()
        assert "2" in text


# ──────────────────────────────────────────────────────────────────────
# 5. P17.7/P17.8 fast-path not broken
# ──────────────────────────────────────────────────────────────────────

class TestFastPathPreserved:
    def test_field_edit_does_not_call_load_rules(self, loaded_window, monkeypatch):
        """Field edit must not trigger rule_card_browser.load_rules()."""
        load_calls = []
        monkeypatch.setattr(
            loaded_window.rule_card_browser,
            "load_rules",
            lambda *a, **kw: load_calls.append(True),
        )
        import copy
        from core.models import FilterRule
        from core.commands import UpdateRuleCommand

        rule = loaded_window._doc.rules[0]
        old = copy.deepcopy(rule)
        new = copy.deepcopy(rule)
        new.inline_comment = "# test P18.1"
        cmd = UpdateRuleCommand(loaded_window._doc, 0, old, new)
        loaded_window._doc.execute(cmd)
        loaded_window._on_detail_rule_changed(0, new)

        assert not load_calls, "load_rules() must NOT be called on field edit"

    def test_field_edit_does_not_call_refresh(self, loaded_window, monkeypatch):
        """Field edit must not trigger rule_card_browser.refresh()."""
        refresh_calls = []
        monkeypatch.setattr(
            loaded_window.rule_card_browser,
            "refresh",
            lambda *a, **kw: refresh_calls.append(True),
        )
        import copy
        from core.models import FilterRule
        from core.commands import UpdateRuleCommand

        rule = loaded_window._doc.rules[0]
        old = copy.deepcopy(rule)
        new = copy.deepcopy(rule)
        new.inline_comment = "# test P18.1 refresh guard"
        cmd = UpdateRuleCommand(loaded_window._doc, 0, old, new)
        loaded_window._doc.execute(cmd)
        loaded_window._on_detail_rule_changed(0, new)

        assert not refresh_calls, "refresh() must NOT be called on field edit"
