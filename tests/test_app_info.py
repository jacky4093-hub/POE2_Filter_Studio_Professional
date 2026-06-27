"""Tests for P17.2 Release About / Version System"""

import pytest

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


# ---------------------------------------------------------------------------
# TestAppInfoConstants
# ---------------------------------------------------------------------------

class TestAppInfoConstants:

    def test_app_name_exists(self):
        from app_info import APP_NAME
        assert APP_NAME

    def test_app_version_exists(self):
        from app_info import APP_VERSION
        assert APP_VERSION

    def test_app_author_exists(self):
        from app_info import APP_AUTHOR
        assert APP_AUTHOR

    def test_app_description_exists(self):
        from app_info import APP_DESCRIPTION
        assert APP_DESCRIPTION

    def test_app_name_is_string(self):
        from app_info import APP_NAME
        assert isinstance(APP_NAME, str)

    def test_app_version_is_string(self):
        from app_info import APP_VERSION
        assert isinstance(APP_VERSION, str)

    def test_app_version_contains_beta(self):
        from app_info import APP_VERSION
        assert "beta" in APP_VERSION.lower() or "." in APP_VERSION

    def test_app_version_format(self):
        from app_info import APP_VERSION
        # Should look like "x.y.z" or "x.y.z-tag"
        parts = APP_VERSION.split("-")[0].split(".")
        assert len(parts) >= 2

    def test_app_name_contains_poe(self):
        from app_info import APP_NAME
        assert "POE" in APP_NAME or "Filter" in APP_NAME

    def test_all_constants_non_empty(self):
        from app_info import APP_NAME, APP_VERSION, APP_AUTHOR, APP_DESCRIPTION
        for value in (APP_NAME, APP_VERSION, APP_AUTHOR, APP_DESCRIPTION):
            assert value.strip() != ""


# ---------------------------------------------------------------------------
# TestWindowTitleContainsVersion
# ---------------------------------------------------------------------------

class TestWindowTitleContainsVersion:

    @pytest.fixture
    def window(self, qapp, tmp_path):
        from core.settings_manager import SettingsManager
        from ui.main_window import MainWindow
        mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
        return MainWindow(settings_mgr=mgr)

    def test_initial_title_contains_app_name(self, window):
        from app_info import APP_NAME
        assert APP_NAME in window.windowTitle()

    def test_initial_title_contains_version(self, window):
        from app_info import APP_VERSION
        assert APP_VERSION in window.windowTitle()

    def test_dirty_title_still_has_asterisk(self, window, tmp_path):
        from core.commands import UpdateRuleCommand
        from core.models import FilterRule
        import copy
        f = tmp_path / "t.filter"
        f.write_text("Show\n    SetFontSize 32\n\n", encoding="utf-8")
        window.load_file(str(f))
        old = copy.deepcopy(window._doc.rules[0])
        new_rule = FilterRule(
            action="Show", enabled=True,
            conditions=[], actions=[["SetFontSize", "45"]],
            pre_lines=[], inline_comment="", unknown_lines=[],
        )
        cmd = UpdateRuleCommand(window._doc, 0, old, new_rule)
        window._doc.execute(cmd)
        window._refresh_status()
        assert "*" in window.windowTitle()

    def test_dirty_title_still_contains_version(self, window, tmp_path):
        from app_info import APP_VERSION
        from core.commands import AddRuleCommand
        from core.models import FilterRule
        rule = FilterRule(
            action="Show", enabled=True,
            conditions=[], actions=[],
            pre_lines=[], inline_comment="", unknown_lines=[],
        )
        window._doc.execute(AddRuleCommand(window._doc, 0, rule))
        window._refresh_status()
        assert APP_VERSION in window.windowTitle()

    def test_title_with_file_contains_version(self, window, tmp_path):
        from app_info import APP_VERSION
        f = tmp_path / "myfile.filter"
        f.write_text("Show\n    SetFontSize 32\n\n", encoding="utf-8")
        window.load_file(str(f))
        assert APP_VERSION in window.windowTitle()
        assert "myfile.filter" in window.windowTitle()

    def test_title_no_dirty_after_load(self, window, tmp_path):
        f = tmp_path / "clean.filter"
        f.write_text("Show\n    SetFontSize 32\n\n", encoding="utf-8")
        window.load_file(str(f))
        assert "*" not in window.windowTitle()


# ---------------------------------------------------------------------------
# TestAboutDialog
# ---------------------------------------------------------------------------

class TestAboutDialog:

    def test_dialog_creates(self, qapp):
        from ui.about_dialog import AboutDialog
        dlg = AboutDialog()
        assert dlg is not None

    def test_dialog_object_name(self, qapp):
        from ui.about_dialog import AboutDialog
        dlg = AboutDialog()
        assert dlg.objectName() == "AboutDialog"

    def test_dialog_shows_app_name(self, qapp):
        from ui.about_dialog import AboutDialog
        from app_info import APP_NAME
        dlg = AboutDialog()
        # Find label with app name
        from PySide6.QtWidgets import QLabel
        labels = dlg.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert any(APP_NAME in t for t in texts)

    def test_dialog_shows_version(self, qapp):
        from ui.about_dialog import AboutDialog
        from app_info import APP_VERSION
        from PySide6.QtWidgets import QLabel
        dlg = AboutDialog()
        labels = dlg.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert any(APP_VERSION in t for t in texts)

    def test_dialog_shows_description(self, qapp):
        from ui.about_dialog import AboutDialog
        from PySide6.QtWidgets import QLabel
        dlg = AboutDialog()
        labels = dlg.findChildren(QLabel)
        texts = " ".join(lbl.text() for lbl in labels)
        # Description has some content
        assert len(texts) > 10

    def test_dialog_has_close_button(self, qapp):
        from ui.about_dialog import AboutDialog
        dlg = AboutDialog()
        assert hasattr(dlg, "_close_btn")

    def test_dialog_close_btn_label(self, qapp):
        from ui.about_dialog import AboutDialog
        dlg = AboutDialog()
        assert "關閉" in dlg._close_btn.text() or "Close" in dlg._close_btn.text()

    def test_dialog_close_btn_object_name(self, qapp):
        from ui.about_dialog import AboutDialog
        dlg = AboutDialog()
        assert dlg._close_btn.objectName() == "AboutCloseBtn"

    def test_dialog_window_title_contains_app_name(self, qapp):
        from ui.about_dialog import AboutDialog
        from app_info import APP_NAME
        dlg = AboutDialog()
        assert APP_NAME in dlg.windowTitle()

    def test_dialog_close_btn_click_accepts(self, qapp):
        from ui.about_dialog import AboutDialog
        dlg = AboutDialog()
        result = []
        dlg.accepted.connect(lambda: result.append(True))
        dlg._close_btn.click()
        assert result == [True]


# ---------------------------------------------------------------------------
# TestHelpAboutAction
# ---------------------------------------------------------------------------

class TestHelpAboutAction:

    @pytest.fixture
    def window(self, qapp, tmp_path):
        from core.settings_manager import SettingsManager
        from ui.main_window import MainWindow
        mgr = SettingsManager(settings_path=str(tmp_path / "s.json"))
        return MainWindow(settings_mgr=mgr)

    def test_about_action_attribute_exists(self, window):
        assert hasattr(window, "_about_action")

    def test_about_action_is_qaction(self, window):
        from PySide6.QtGui import QAction
        assert isinstance(window._about_action, QAction)

    def test_about_action_text_contains_about(self, window):
        text = window._about_action.text()
        assert "關於" in text or "About" in text

    def test_show_about_method_exists(self, window):
        assert callable(getattr(window, "_show_about", None))

    def test_show_about_does_not_raise_without_exec(self, window, monkeypatch):
        from ui.about_dialog import AboutDialog
        shown = []
        monkeypatch.setattr(AboutDialog, "exec", lambda self: shown.append(True) or 0)
        window._show_about()
        assert shown == [True]

    def test_help_menu_in_menubar(self, window):
        mb = window.menuBar()
        menu_titles = [mb.actions()[i].text() for i in range(len(mb.actions()))]
        assert any("說明" in t or "Help" in t or "H" in t for t in menu_titles)

    def test_about_action_in_help_menu(self, window):
        mb = window.menuBar()
        # Find Help menu
        help_menu = None
        for act in mb.actions():
            if act.menu() and ("說明" in act.text() or "H" in act.text()):
                help_menu = act.menu()
                break
        assert help_menu is not None, "Help menu not found"
        action_texts = [a.text() for a in help_menu.actions()]
        assert any("關於" in t or "About" in t for t in action_texts)
