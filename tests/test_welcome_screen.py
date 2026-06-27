"""Tests for WelcomeScreen — v2.7.0

Covers:
- Title / subtitle labels present
- open_requested signal from Open button
- new_requested signal from New button
- recent_file_requested(path) signal
- empty state placeholder when no recent files
- missing file shown as disabled
- max 10 items rendered
- set_recent_files can be called multiple times
"""

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from ui.welcome_screen import WelcomeScreen


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
# Helpers
# ---------------------------------------------------------------------------

def _ws(qapp) -> WelcomeScreen:
    return WelcomeScreen()


def _collect(ws: WelcomeScreen, signal_name: str) -> list:
    received: list = []
    sig = getattr(ws, signal_name)
    if signal_name == "recent_file_requested":
        sig.connect(lambda p: received.append(p))
    else:
        sig.connect(lambda: received.append(True))
    return received


# ---------------------------------------------------------------------------
# TestLayout
# ---------------------------------------------------------------------------

class TestLayout:
    def test_has_welcome_title(self, qapp):
        ws = _ws(qapp)
        titles = ws.findChildren(QLabel, "WelcomeTitle")
        assert titles
        assert "POE2" in titles[0].text()

    def test_has_subtitle(self, qapp):
        ws = _ws(qapp)
        subs = ws.findChildren(QLabel, "WelcomeSubtitle")
        assert subs

    def test_has_open_button(self, qapp):
        ws = _ws(qapp)
        btns = ws.findChildren(QPushButton, "WelcomePrimaryButton")
        assert btns

    def test_has_new_button(self, qapp):
        ws = _ws(qapp)
        btns = ws.findChildren(QPushButton, "WelcomeSecondaryButton")
        assert btns


# ---------------------------------------------------------------------------
# TestSignals
# ---------------------------------------------------------------------------

class TestSignals:
    def test_open_button_emits_open_requested(self, qapp):
        ws = _ws(qapp)
        received = _collect(ws, "open_requested")
        ws.findChildren(QPushButton, "WelcomePrimaryButton")[0].click()
        assert received

    def test_new_button_emits_new_requested(self, qapp):
        ws = _ws(qapp)
        received = _collect(ws, "new_requested")
        ws.findChildren(QPushButton, "WelcomeSecondaryButton")[0].click()
        assert received

    def test_recent_file_click_emits_signal(self, qapp, tmp_path):
        ws = _ws(qapp)
        p = tmp_path / "click.filter"
        p.write_text("Show\n", encoding="utf-8")
        ws.set_recent_files([str(p)])
        received = _collect(ws, "recent_file_requested")
        btns = ws.findChildren(QPushButton, "WelcomeRecentItem")
        assert btns
        btns[0].click()
        assert received
        assert received[0] == str(p)

    def test_missing_file_click_does_not_emit(self, qapp):
        ws = _ws(qapp)
        ws.set_recent_files(["/nonexistent/missing.filter"])
        received = _collect(ws, "recent_file_requested")
        btns = ws.findChildren(QPushButton, "WelcomeRecentItem")
        assert btns
        btns[0].click()
        assert received == []


# ---------------------------------------------------------------------------
# TestRecentFilesDisplay
# ---------------------------------------------------------------------------

class TestRecentFilesDisplay:
    def test_empty_shows_placeholder_label(self, qapp):
        ws = _ws(qapp)
        ws.set_recent_files([])
        labels = ws.findChildren(QLabel, "WelcomeEmptyState")
        assert labels

    def test_empty_no_recent_item_buttons(self, qapp):
        ws = _ws(qapp)
        ws.set_recent_files([])
        btns = ws.findChildren(QPushButton, "WelcomeRecentItem")
        assert btns == []

    def test_file_shows_as_button(self, qapp, tmp_path):
        ws = _ws(qapp)
        p = tmp_path / "myfilter.filter"
        p.write_text("Show\n", encoding="utf-8")
        ws.set_recent_files([str(p)])
        btns = ws.findChildren(QPushButton, "WelcomeRecentItem")
        assert btns
        assert "myfilter.filter" in btns[0].text()

    def test_existing_file_enabled(self, qapp, tmp_path):
        ws = _ws(qapp)
        p = tmp_path / "exists.filter"
        p.write_text("Show\n", encoding="utf-8")
        ws.set_recent_files([str(p)])
        btns = ws.findChildren(QPushButton, "WelcomeRecentItem")
        assert btns[0].isEnabled()

    def test_missing_file_disabled(self, qapp):
        ws = _ws(qapp)
        ws.set_recent_files(["/totally/nonexistent/path.filter"])
        btns = ws.findChildren(QPushButton, "WelcomeRecentItem")
        assert btns
        assert not btns[0].isEnabled()

    def test_max_10_files_rendered(self, qapp, tmp_path):
        ws = _ws(qapp)
        paths = []
        for i in range(15):
            p = tmp_path / f"f{i}.filter"
            p.write_text("Show\n", encoding="utf-8")
            paths.append(str(p))
        ws.set_recent_files(paths)
        btns = ws.findChildren(QPushButton, "WelcomeRecentItem")
        assert len(btns) == 10

    def test_set_recent_files_clears_previous(self, qapp, tmp_path):
        ws = _ws(qapp)
        p1 = tmp_path / "first.filter"
        p1.write_text("Show\n", encoding="utf-8")
        ws.set_recent_files([str(p1)])
        assert len(ws.findChildren(QPushButton, "WelcomeRecentItem")) == 1

        p2 = tmp_path / "second.filter"
        p2.write_text("Show\n", encoding="utf-8")
        ws.set_recent_files([str(p1), str(p2)])
        assert len(ws.findChildren(QPushButton, "WelcomeRecentItem")) == 2

    def test_call_empty_after_files_shows_placeholder(self, qapp, tmp_path):
        ws = _ws(qapp)
        p = tmp_path / "f.filter"
        p.write_text("Show\n", encoding="utf-8")
        ws.set_recent_files([str(p)])
        ws.set_recent_files([])
        labels = ws.findChildren(QLabel, "WelcomeEmptyState")
        assert labels
        btns = ws.findChildren(QPushButton, "WelcomeRecentItem")
        assert btns == []

    def test_mixed_existing_and_missing(self, qapp, tmp_path):
        ws = _ws(qapp)
        p_exists = tmp_path / "good.filter"
        p_exists.write_text("Show\n", encoding="utf-8")
        ws.set_recent_files([str(p_exists), "/bad/missing.filter"])
        btns = ws.findChildren(QPushButton, "WelcomeRecentItem")
        assert len(btns) == 2
        enabled_count = sum(1 for b in btns if b.isEnabled())
        assert enabled_count == 1
