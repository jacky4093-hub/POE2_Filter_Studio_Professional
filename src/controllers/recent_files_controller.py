import os
from typing import Protocol

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

from core.settings_manager import SettingsManager


class _WindowProtocol(Protocol):
    _recent_menu: object
    _confirm_discard: object
    _clear_recent_files: object
    load_file: object
    welcome_screen: object


class RecentFilesController:
    def __init__(self, window: _WindowProtocol, settings_mgr: SettingsManager) -> None:
        self._window = window
        self._settings_mgr = settings_mgr

    def refresh_views(self) -> None:
        self._refresh_recent_menu()
        self._refresh_welcome_screen()

    def record_opened(self, path: str) -> None:
        self._settings_mgr.add_recent_file(path)
        self._settings_mgr.save()
        self.refresh_views()

    def record_saved(self, path: str) -> None:
        self._settings_mgr.add_recent_file(path)
        self._settings_mgr.save()
        self.refresh_views()

    def clear_recent(self) -> None:
        self._settings_mgr.clear_recent_files()
        self._settings_mgr.save()
        self.refresh_views()

    def open_recent(self, path: str) -> None:
        if not os.path.isfile(path):
            QMessageBox.warning(
                self._window,
                "找不到檔案",
                f"檔案不存在或已被移動：\n{path}",
            )
            return
        if not self._window._confirm_discard():
            return
        self._window.load_file(path)

    def _refresh_recent_menu(self) -> None:
        recent_menu = getattr(self._window, "_recent_menu", None)
        if recent_menu is None:
            return

        recent_menu.clear()
        paths = self._settings_mgr.recent_files()
        if not paths:
            placeholder = QAction("（無最近開啟檔案）", self._window)
            placeholder.setEnabled(False)
            recent_menu.addAction(placeholder)
        else:
            for path in paths:
                label = os.path.basename(path)
                action = QAction(label, self._window)
                action.setToolTip(path)
                action.triggered.connect(lambda _=False, p=path: self.open_recent(p))
                recent_menu.addAction(action)
            recent_menu.addSeparator()
            clear_action = QAction("清除清單", self._window)
            clear_action.triggered.connect(self._window._clear_recent_files)
            recent_menu.addAction(clear_action)

    def _refresh_welcome_screen(self) -> None:
        welcome_screen = getattr(self._window, "welcome_screen", None)
        if welcome_screen is None:
            return
        welcome_screen.set_recent_files(self._settings_mgr.recent_files())
