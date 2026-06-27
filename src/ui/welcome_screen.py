"""WelcomeScreen — v2.7.0

Displayed when no filter file is open.  Shows quick-action buttons and
a recent-files list.  Emits signals only; never opens dialogs itself.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class WelcomeScreen(QWidget):
    """Welcome / start page shown at startup when no file is loaded."""

    open_requested = Signal()
    new_requested = Signal()
    recent_file_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("WelcomeScreen")
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("WelcomeCard")
        card.setFixedWidth(480)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 48, 40, 48)
        card_layout.setSpacing(0)

        # Title + subtitle
        title = QLabel("POE2 Filter Studio")
        title.setObjectName("WelcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Path of Exile 2 濾鏡編輯器")
        subtitle.setObjectName("WelcomeSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(title)
        card_layout.addSpacing(4)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(28)

        # Action buttons
        btn_open = QPushButton("開啟 Filter 檔案…")
        btn_open.setObjectName("WelcomePrimaryButton")
        btn_open.clicked.connect(self.open_requested.emit)

        btn_new = QPushButton("新建 Filter")
        btn_new.setObjectName("WelcomeSecondaryButton")
        btn_new.clicked.connect(self.new_requested.emit)

        card_layout.addWidget(btn_open)
        card_layout.addSpacing(8)
        card_layout.addWidget(btn_new)
        card_layout.addSpacing(32)

        # Recent files header
        recent_header = QLabel("最近開啟")
        recent_header.setObjectName("WelcomeRecentHeader")

        card_layout.addWidget(recent_header)
        card_layout.addSpacing(6)

        # Recent files container (populated by set_recent_files)
        self._recent_container = QWidget()
        self._recent_container.setObjectName("WelcomeRecentContainer")
        self._recent_layout = QVBoxLayout(self._recent_container)
        self._recent_layout.setContentsMargins(0, 0, 0, 0)
        self._recent_layout.setSpacing(2)
        self._recent_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        card_layout.addWidget(self._recent_container)

        outer.addWidget(card)

        # Populate with empty state by default
        self.set_recent_files([])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_recent_files(self, paths: list[str]) -> None:
        """Rebuild the recent-files list from *paths* (max 10 shown).

        Missing files are shown as disabled items so users can see their
        history even if paths have moved.
        """
        # Remove all existing widgets immediately
        while self._recent_layout.count():
            item = self._recent_layout.takeAt(0)
            if w := item.widget():
                w.setParent(None)

        if not paths:
            lbl = QLabel("沒有最近開啟的檔案")
            lbl.setObjectName("WelcomeEmptyState")
            self._recent_layout.addWidget(lbl)
            return

        for path in paths[:10]:
            exists = os.path.isfile(path)
            btn = QPushButton(os.path.basename(path))
            btn.setObjectName("WelcomeRecentItem")
            btn.setToolTip(path if exists else f"（檔案不存在）{path}")
            btn.setEnabled(exists)
            btn.setProperty("fileMissing", not exists)
            if exists:
                btn.clicked.connect(lambda _, p=path: self.recent_file_requested.emit(p))
            self._recent_layout.addWidget(btn)
