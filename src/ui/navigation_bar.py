"""NavigationBarV4 — P18.1 V4 Shell

Top navigation bar replacing the old NavBarPlaceholder + QToolBar.

Layout (left → right):
  ⚡ "POE2 Filter Studio V4"  |  [Open][New][Import][Save][Save As][Export]
  ··· stretch ···  [SearchBar]  [ValidationChip]  [⚙]
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Signal, Qt


class NavigationBarV4(QWidget):
    """V4 integrated top navigation bar.

    Signals emitted for each file-operation button; caller connects them to
    existing MainWindow slots so no business logic lives here.
    """

    new_requested           = Signal()
    open_requested          = Signal()
    import_backup_requested = Signal()
    save_requested          = Signal()
    save_as_requested       = Signal()
    export_requested        = Signal()
    settings_requested      = Signal()

    def __init__(self, search_bar=None, parent: QWidget | None = None):
        """
        Args:
            search_bar: Optional SearchBar widget to embed in the right section.
                        The caller owns the widget; this class only reparents it
                        into the layout.
        """
        super().__init__(parent)
        self.setObjectName("NavigationBarV4")
        self._search_bar = search_bar
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(0)

        # ── Left: Logo + Brand title ───────────────────────────────────
        logo_lbl = QLabel("⚡")
        logo_lbl.setObjectName("NavLogoIcon")
        layout.addWidget(logo_lbl)

        layout.addSpacing(6)

        brand_lbl = QLabel("POE2 Filter Studio V4")
        brand_lbl.setObjectName("NavBrandTitle")
        layout.addWidget(brand_lbl)

        layout.addSpacing(16)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setObjectName("NavSeparator")
        layout.addWidget(sep)

        layout.addSpacing(12)

        # ── Center: File-operation buttons ────────────────────────────
        btn_defs = [
            ("開啟 Filter",  self.open_requested),
            ("新建 Filter",  self.new_requested),
            ("匯入備份",     self.import_backup_requested),
            ("儲存",         self.save_requested),
            ("另存新檔",     self.save_as_requested),
            ("匯出 Filter",  self.export_requested),
        ]
        for label, sig in btn_defs:
            btn = QPushButton(label)
            btn.setObjectName("NavBtnFile")
            btn.clicked.connect(sig)
            layout.addWidget(btn)
            layout.addSpacing(4)

        # Flexible gap pushes right-side items to the right
        layout.addStretch(1)

        # ── Right: Navigation SearchBar ───────────────────────────────
        if self._search_bar is not None:
            self._search_bar.setFixedWidth(210)
            layout.addWidget(self._search_bar)
            layout.addSpacing(10)

        # ── Validation chip ───────────────────────────────────────────
        self._validation_chip = QLabel("–")
        self._validation_chip.setObjectName("NavValidationChip")
        self._validation_chip.setProperty("validationState", "idle")
        self._validation_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._validation_chip)

        layout.addSpacing(8)

        # ── Settings button ───────────────────────────────────────────
        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("NavSettingsBtn")
        settings_btn.setFixedSize(32, 32)
        settings_btn.setToolTip("偏好設定")
        settings_btn.clicked.connect(self.settings_requested)
        layout.addWidget(settings_btn)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_validation_status(self, passed: bool, summary: str) -> None:
        """Update the validation chip text and colour state.

        Args:
            passed:  True if no errors (warnings are OK).
            summary: Short human-readable text, e.g. "語法檢查：通過".
        """
        prefix = "✓" if passed else "⚠"
        state  = "pass" if passed else "fail"
        self._validation_chip.setText(f"{prefix}  {summary}")
        self._validation_chip.setProperty("validationState", state)
        # Trigger Qt dynamic-property re-evaluation so QSS selector updates
        style = self._validation_chip.style()
        style.unpolish(self._validation_chip)
        style.polish(self._validation_chip)
