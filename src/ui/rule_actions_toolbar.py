"""RuleActionsToolbar — v2.4.0

Compact horizontal toolbar with 5 rule-management buttons.
Placed between CategorySidebarWidget and RuleCardBrowser in the left column.

Enable/disable contract
-----------------------
- "新增" is always enabled (no selection required).
- "刪除", "複製", "上移", "下移" are disabled until a rule is selected.
- "上移" is also disabled when the rule is at index 0.
- "下移" is also disabled when the rule is the last movable rule.

Usage
-----
    toolbar = RuleActionsToolbar()
    toolbar.new_requested.connect(...)
    toolbar.delete_requested.connect(...)
    toolbar.duplicate_requested.connect(...)
    toolbar.move_up_requested.connect(...)
    toolbar.move_down_requested.connect(...)

    # Call whenever selection or list length changes:
    toolbar.update_state(selected_index=2, total_movable=5)
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QStyle
from PySide6.QtCore import Signal


class RuleActionsToolbar(QWidget):
    """Five-button rule-management toolbar."""

    new_requested       = Signal()
    delete_requested    = Signal()
    duplicate_requested = Signal()
    move_up_requested   = Signal()
    move_down_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RuleActionsToolbar")
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_state(self, selected_index: int, total_movable: int) -> None:
        """Enable/disable buttons based on current selection.

        Args:
            selected_index:  real_index of the currently selected rule,
                             or -1 when nothing is selected.
            total_movable:   count of non-__TAIL__ rules in the document
                             (i.e., FilterDocument.visible_count).
        """
        has_sel = 0 <= selected_index < total_movable
        self._btn_delete.setEnabled(has_sel)
        self._btn_duplicate.setEnabled(has_sel)
        self._btn_move_up.setEnabled(has_sel and selected_index > 0)
        self._btn_move_down.setEnabled(has_sel and selected_index < total_movable - 1)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(4)

        st = self.style()

        self._btn_new = self._make_btn(
            "新增",
            st.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder),
        )
        self._btn_delete = self._make_btn(
            "刪除",
            st.standardIcon(QStyle.StandardPixmap.SP_TrashIcon),
        )
        self._btn_duplicate = self._make_btn(
            "複製",
            st.standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon),
        )
        self._btn_move_up = self._make_btn(
            "上移",
            st.standardIcon(QStyle.StandardPixmap.SP_ArrowUp),
        )
        self._btn_move_down = self._make_btn(
            "下移",
            st.standardIcon(QStyle.StandardPixmap.SP_ArrowDown),
        )

        for btn in (
            self._btn_new, self._btn_delete, self._btn_duplicate,
            self._btn_move_up, self._btn_move_down,
        ):
            layout.addWidget(btn)

        # Initial state: all selection-dependent buttons are disabled
        self.update_state(-1, 0)

        # Wire
        self._btn_new.clicked.connect(self.new_requested)
        self._btn_delete.clicked.connect(self.delete_requested)
        self._btn_duplicate.clicked.connect(self.duplicate_requested)
        self._btn_move_up.clicked.connect(self.move_up_requested)
        self._btn_move_down.clicked.connect(self.move_down_requested)

    @staticmethod
    def _make_btn(text: str, icon) -> QPushButton:
        btn = QPushButton(icon, text)
        btn.setObjectName("RuleActionButton")
        btn.setFixedHeight(28)
        return btn
