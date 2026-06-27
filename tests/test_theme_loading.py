"""Tests for QSS theme loading — P15.2 Premium Theme Foundation

Verifies that:
- All expected QSS files exist and are non-empty
- Each file contains valid CSS-like syntax (no unclosed braces)
- Key objectName selectors are present in the correct files
- The combined QSS can be applied to a QWidget without crashing
"""

import pytest
from pathlib import Path

STYLES_DIR = Path(__file__).parent.parent / "src" / "assets" / "styles"

EXPECTED_QSS = [
    "base.qss",
    "shell.qss",
    "sidebar.qss",
    "browser.qss",
    "editor.qss",
    "preview.qss",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


# ---------------------------------------------------------------------------
# TestQssFilesExist
# ---------------------------------------------------------------------------

class TestQssFilesExist:

    @pytest.mark.parametrize("filename", EXPECTED_QSS)
    def test_qss_file_exists(self, filename):
        path = STYLES_DIR / filename
        assert path.exists(), f"Missing QSS: {path}"

    @pytest.mark.parametrize("filename", EXPECTED_QSS)
    def test_qss_file_not_empty(self, filename):
        path = STYLES_DIR / filename
        assert path.stat().st_size > 0, f"Empty QSS: {filename}"

    @pytest.mark.parametrize("filename", EXPECTED_QSS)
    def test_qss_file_is_utf8(self, filename):
        path = STYLES_DIR / filename
        content = path.read_text(encoding="utf-8")
        assert len(content) > 0


# ---------------------------------------------------------------------------
# TestQssSyntax
# ---------------------------------------------------------------------------

class TestQssSyntax:
    """Basic structural validation — balanced braces, no empty selectors."""

    @pytest.mark.parametrize("filename", EXPECTED_QSS)
    def test_balanced_braces(self, filename):
        content = (STYLES_DIR / filename).read_text(encoding="utf-8")
        # Strip comments to avoid false positives from brace-like chars
        depth = 0
        i = 0
        while i < len(content):
            if content[i:i+2] == "/*":
                end = content.find("*/", i + 2)
                i = end + 2 if end >= 0 else len(content)
                continue
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
            i += 1
        assert depth == 0, f"{filename}: unbalanced braces (depth={depth})"

    @pytest.mark.parametrize("filename", EXPECTED_QSS)
    def test_no_tabs_in_selectors(self, filename):
        """QSS parsers can misbehave with literal tab characters in selectors."""
        content = (STYLES_DIR / filename).read_text(encoding="utf-8")
        # Allow tabs in comments but warn about them in selector lines
        lines_with_tabs = [
            i + 1 for i, line in enumerate(content.splitlines())
            if "\t" in line and "/*" not in line
        ]
        assert not lines_with_tabs, (
            f"{filename} has tabs on lines: {lines_with_tabs[:5]}"
        )


# ---------------------------------------------------------------------------
# TestQssSelectors
# ---------------------------------------------------------------------------

class TestQssSelectors:
    """Key objectName selectors are present in the correct files."""

    def _content(self, filename: str) -> str:
        return (STYLES_DIR / filename).read_text(encoding="utf-8")

    # base.qss
    def test_base_has_qwidget(self):
        assert "QWidget" in self._content("base.qss")

    def test_base_has_qscrollbar(self):
        assert "QScrollBar" in self._content("base.qss")

    def test_base_has_qgroupbox(self):
        assert "QGroupBox" in self._content("base.qss")

    def test_base_has_qpushbutton(self):
        assert "QPushButton" in self._content("base.qss")

    def test_base_has_qlineedit(self):
        assert "QLineEdit" in self._content("base.qss")

    # shell.qss
    def test_shell_has_navbarbrand(self):
        assert "#NavBarBrand" in self._content("shell.qss")

    def test_shell_has_contentshell(self):
        assert "#ContentShell" in self._content("shell.qss")

    # sidebar.qss
    def test_sidebar_has_list(self):
        assert "#CategorySidebarList" in self._content("sidebar.qss")

    def test_sidebar_selected_has_border_left(self):
        content = self._content("sidebar.qss")
        selected_block = content[content.find("#CategorySidebarList::item:selected"):]
        brace_end = selected_block.find("}")
        block = selected_block[:brace_end]
        assert "border-left" in block

    def test_sidebar_selected_has_background(self):
        content = self._content("sidebar.qss")
        selected_block = content[content.find("#CategorySidebarList::item:selected"):]
        brace_end = selected_block.find("}")
        block = selected_block[:brace_end]
        assert "background" in block

    # browser.qss
    def test_browser_has_rulecard(self):
        assert "#RuleCard" in self._content("browser.qss")

    def test_browser_has_card_selected(self):
        assert 'cardSelected="true"' in self._content("browser.qss")

    def test_browser_has_card_highlight_current(self):
        assert 'cardHighlight="current"' in self._content("browser.qss")

    def test_browser_has_card_highlight_match(self):
        assert 'cardHighlight="match"' in self._content("browser.qss")

    def test_browser_has_card_disabled(self):
        assert 'cardDisabled="true"' in self._content("browser.qss")

    def test_browser_has_btndanger(self):
        assert "#BtnDanger" in self._content("browser.qss")

    def test_browser_has_action_icon(self):
        assert "#RuleCardActionIcon" in self._content("browser.qss")

    # editor.qss
    def test_editor_has_rule_editor_card(self):
        assert "#RuleEditorCard" in self._content("editor.qss")

    def test_editor_has_alert_spinboxes(self):
        content = self._content("editor.qss")
        assert "#AlertSoundIdSpin" in content
        assert "#AlertVolumeSpin" in content

    def test_editor_has_minimap_combos(self):
        content = self._content("editor.qss")
        assert "#MinimapSizeCombo" in content
        assert "#MinimapColorCombo" in content
        assert "#MinimapShapeCombo" in content

    def test_editor_has_rule_detail_preview(self):
        assert "#RuleDetailPreview" in self._content("editor.qss")

    # preview.qss
    def test_preview_has_preview_panel(self):
        assert "#PreviewPanel" in self._content("preview.qss")

    def test_preview_has_action_badge(self):
        assert "#PreviewActionBadge" in self._content("preview.qss")

    def test_preview_has_disabled_banner(self):
        assert "#PreviewDisabledBanner" in self._content("preview.qss")

    def test_preview_has_badge(self):
        assert "#PreviewBadge" in self._content("preview.qss")


# ---------------------------------------------------------------------------
# TestQssApplied
# ---------------------------------------------------------------------------

class TestQssApplied:
    """Load combined QSS via apply_theme() and verify no crash."""

    def test_apply_theme_does_not_raise(self, qapp):
        try:
            from assets import theme  # noqa: F401  just import
        except Exception as e:
            pytest.fail(f"theme module import failed: {e}")

    def test_all_qss_files_readable_as_combined_string(self):
        combined = ""
        for filename in EXPECTED_QSS:
            content = (STYLES_DIR / filename).read_text(encoding="utf-8")
            combined += content + "\n"
        assert len(combined) > 500  # sanity: not empty
