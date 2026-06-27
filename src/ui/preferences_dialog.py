"""PreferencesDialog — v2.8.0

Formal settings window for POE2 Filter Studio.
Manages:
  - Startup restore preference
  - Recent files list (with clear)
  - Displays last_open_file and settings.json path

Public API
----------
    dlg = PreferencesDialog(settings_mgr, parent)
    dlg.set_settings_manager(mgr)   # inject / replace manager
    dlg.load_from_settings()        # populate UI from current settings
    dlg.apply_to_settings()         # write UI → settings (and save)

Signals
-------
    settings_applied   emitted on both Apply and OK (before close)
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.settings_manager import SettingsManager


class PreferencesDialog(QDialog):
    """Settings dialog — OK / Cancel / Apply pattern."""

    settings_applied = Signal()

    def __init__(
        self,
        settings_mgr: SettingsManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("偏好設定")
        self.setMinimumWidth(520)
        self.setObjectName("PreferencesDialog")

        self._mgr: SettingsManager | None = None
        self._pending_clear_recent: bool = False

        self._build_ui()

        if settings_mgr is not None:
            self.set_settings_manager(settings_mgr)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_settings_manager(self, mgr: SettingsManager) -> None:
        """Inject (or replace) the settings manager and reload the UI."""
        self._mgr = mgr
        self.load_from_settings()

    def load_from_settings(self) -> None:
        """Populate every control from the current settings state."""
        if self._mgr is None:
            return
        self._cb_restore.setChecked(self._mgr.get_restore_last_file_on_startup())
        last = self._mgr.get_last_open_file()
        self._lbl_last_open_file.setText(last if last else "（無）")
        self._lbl_settings_path.setText(str(self._mgr._path))
        self._pending_clear_recent = False
        self._btn_clear.setEnabled(True)
        self._rebuild_recent_list()

    def apply_to_settings(self) -> None:
        """Write the current UI state to the settings manager and persist."""
        if self._mgr is None:
            return
        self._mgr.set_restore_last_file_on_startup(self._cb_restore.isChecked())
        if self._pending_clear_recent:
            self._mgr.clear_recent_files()
            self._pending_clear_recent = False
        self._mgr.save()

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def accept(self) -> None:  # OK button
        self.apply_to_settings()
        self.settings_applied.emit()
        super().accept()

    def _on_apply(self) -> None:
        self.apply_to_settings()
        self.settings_applied.emit()

    def _on_clear_recent(self) -> None:
        self._pending_clear_recent = True
        self._recent_list.clear()
        self._btn_clear.setEnabled(False)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 16)

        # ── General section ──────────────────────────────────────────
        layout.addWidget(self._make_section_title("一般"))

        self._cb_restore = QCheckBox("啟動時恢復上次開啟的 Filter")
        self._cb_restore.setObjectName("PrefCheckBox")
        layout.addWidget(self._cb_restore)

        layout.addLayout(self._make_label_row(
            "上次開啟：",
            "_lbl_last_open_file",
            "（無）",
        ))
        layout.addLayout(self._make_label_row(
            "設定檔：",
            "_lbl_settings_path",
            "（未知）",
        ))

        layout.addWidget(self._make_separator())

        # ── Recent Files section ─────────────────────────────────────
        layout.addWidget(self._make_section_title("最近開啟"))

        self._recent_list = QListWidget()
        self._recent_list.setObjectName("PrefRecentList")
        self._recent_list.setFixedHeight(140)
        layout.addWidget(self._recent_list)

        self._btn_clear = QPushButton("清除最近檔案")
        self._btn_clear.setObjectName("PrefClearButton")
        self._btn_clear.clicked.connect(self._on_clear_recent)
        layout.addWidget(self._btn_clear, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addStretch()

        # ── OK / Cancel / Apply ──────────────────────────────────────
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply,
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        apply_btn = self._button_box.button(QDialogButtonBox.StandardButton.Apply)
        apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(self._button_box)

    def _make_section_title(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("PrefSectionTitle")
        return lbl

    def _make_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("PrefSeparator")
        return sep

    def _make_label_row(
        self, key_text: str, attr_name: str, placeholder: str
    ) -> QHBoxLayout:
        row = QHBoxLayout()
        key = QLabel(key_text)
        key.setObjectName("PrefLabel")
        val = QLabel(placeholder)
        val.setObjectName("PrefPathLabel")
        val.setWordWrap(True)
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        setattr(self, attr_name, val)
        row.addWidget(key)
        row.addWidget(val, stretch=1)
        return row

    def _rebuild_recent_list(self) -> None:
        self._recent_list.clear()
        if self._pending_clear_recent or self._mgr is None:
            return
        for path in self._mgr.recent_files():
            self._recent_list.addItem(path)
