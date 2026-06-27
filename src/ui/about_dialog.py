"""AboutDialog — P17.2 Release / Version System

Displays application name, version, author, and description.
Opened from Help → About.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QDialogButtonBox, QPushButton,
)
from PySide6.QtCore import Qt

from app_info import APP_NAME, APP_VERSION, APP_AUTHOR, APP_DESCRIPTION


class AboutDialog(QDialog):
    """Simple About dialog with app metadata."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("AboutDialog")
        self.setWindowTitle(f"關於 {APP_NAME}")
        self.setMinimumWidth(380)
        self.setMinimumHeight(200)
        self._build_ui()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 20, 24, 16)

        # App name
        name_lbl = QLabel(APP_NAME)
        name_lbl.setObjectName("AboutAppName")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_lbl)

        # Version
        ver_lbl = QLabel(f"版本 {APP_VERSION}")
        ver_lbl.setObjectName("AboutVersion")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver_lbl)

        # Separator line
        sep = QLabel()
        sep.setObjectName("AboutSeparator")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # Description
        desc_lbl = QLabel(APP_DESCRIPTION)
        desc_lbl.setObjectName("AboutDescription")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        # Author
        author_lbl = QLabel(f"© {APP_AUTHOR}")
        author_lbl.setObjectName("AboutAuthor")
        author_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(author_lbl)

        layout.addStretch()

        # Close button
        btn_box = QDialogButtonBox()
        self._close_btn = QPushButton("關閉")
        self._close_btn.setObjectName("AboutCloseBtn")
        self._close_btn.setDefault(True)
        btn_box.addButton(self._close_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)
