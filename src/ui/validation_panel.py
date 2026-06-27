"""ValidationPanel — P16.2 / P16.4 Validation UI

Displays issues produced by core.validator.validate_document().
Lives at the bottom of the main editor shell, above the status bar.

Public API:
    refresh(issues, quick_fixes=None)  — repopulate from issue list;
        optional quick_fixes[i] is list[QuickFix] for issues[i].
    clear()                            — reset to clean / no-issue state

Signals:
    issue_clicked(rule_index: int)    — row clicked → navigate to rule.
        Callers should ignore rule_index == -1.
    fix_requested(rule_index: int, fix: QuickFix)
        — Fix button clicked; MainWindow applies the fix via undo command.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from core.validator import ValidationIssue, ValidationSeverity

if TYPE_CHECKING:
    from core.quick_fix import QuickFix


_SEV_META: dict[ValidationSeverity, tuple[str, str]] = {
    ValidationSeverity.ERROR:   ("E", "#ef4444"),
    ValidationSeverity.WARNING: ("W", "#f59e0b"),
    ValidationSeverity.INFO:    ("I", "#60a5fa"),
}


class ValidationPanel(QWidget):
    """Compact bottom panel showing filter validation issues."""

    issue_clicked  = Signal(int)
    fix_requested  = Signal(int, object)   # (rule_index, QuickFix)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ValidationPanel")
        self.setFixedHeight(110)
        self._build_ui()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 2, 4, 2)
        v.setSpacing(2)

        # Header: title label + severity count chips
        header = QWidget()
        header.setObjectName("ValidationPanelHeader")
        h = QHBoxLayout(header)
        h.setContentsMargins(2, 0, 2, 0)
        h.setSpacing(8)

        title = QLabel("驗證問題")
        title.setObjectName("ValidationPanelTitle")
        h.addWidget(title)

        self._error_chip   = QLabel("E 0")
        self._warning_chip = QLabel("W 0")
        self._info_chip    = QLabel("I 0")
        for chip, obj_name in [
            (self._error_chip,   "ValidationChipError"),
            (self._warning_chip, "ValidationChipWarning"),
            (self._info_chip,    "ValidationChipInfo"),
        ]:
            chip.setObjectName(obj_name)
            chip.setFixedHeight(18)
            h.addWidget(chip)

        h.addStretch()
        v.addWidget(header)

        # Issue list
        self._list = QListWidget()
        self._list.setObjectName("ValidationIssueList")
        self._list.itemClicked.connect(self._on_item_clicked)
        v.addWidget(self._list, stretch=1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(
        self,
        issues: list[ValidationIssue],
        quick_fixes: list[list[QuickFix]] | None = None,
    ) -> None:
        """Repopulate the panel from a list of ValidationIssue objects.

        ``quick_fixes[i]`` is a list of available QuickFix objects for
        ``issues[i]``.  Pass ``None`` (default) to show no Fix buttons.
        """
        self._list.clear()

        n_error   = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        n_warning = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
        n_info    = sum(1 for i in issues if i.severity == ValidationSeverity.INFO)

        self._error_chip.setText(f"E {n_error}")
        self._warning_chip.setText(f"W {n_warning}")
        self._info_chip.setText(f"I {n_info}")

        for idx, issue in enumerate(issues):
            prefix, color = _SEV_META[issue.severity]
            rule_str = f"規則 #{issue.rule_index}" if issue.rule_index >= 0 else "—"
            text = f"[{prefix}]  {rule_str}  [{issue.field}]  {issue.message}"

            item = QListWidgetItem(text)
            item.setForeground(QColor(color))
            item.setData(Qt.ItemDataRole.UserRole, issue.rule_index)
            self._list.addItem(item)

            fixes = (quick_fixes[idx] if quick_fixes is not None and idx < len(quick_fixes) else [])
            if fixes:
                row = self._make_fix_row(text, color, issue.rule_index, fixes[0])
                item.setSizeHint(row.sizeHint())
                self._list.setItemWidget(item, row)

    def clear(self) -> None:
        """Reset to empty / no-issue state."""
        self._list.clear()
        self._error_chip.setText("E 0")
        self._warning_chip.setText("W 0")
        self._info_chip.setText("I 0")

    # ------------------------------------------------------------------
    # Row widget factory
    # ------------------------------------------------------------------

    def _make_fix_row(
        self,
        text: str,
        color: str,
        rule_index: int,
        fix: QuickFix,
    ) -> QWidget:
        """Build a row widget: [text label  ][Fix button]."""
        row = QWidget()
        row.setObjectName("ValidationFixRow")
        h = QHBoxLayout(row)
        h.setContentsMargins(4, 1, 4, 1)
        h.setSpacing(6)

        lbl = QLabel(text)
        lbl.setObjectName("ValidationFixRowLabel")
        lbl.setStyleSheet(
            f"color: {color}; font-size: 11px;"
            "font-family: Consolas, 'Cascadia Code', 'Courier New', monospace;"
        )
        h.addWidget(lbl, stretch=1)

        btn = QPushButton(fix.label)
        btn.setObjectName("ValidationFixBtn")
        btn.setFixedHeight(20)
        btn.setFixedWidth(110)
        btn.clicked.connect(
            lambda _, ri=rule_index, f=fix: self.fix_requested.emit(ri, f)
        )
        h.addWidget(btn)
        return row

    # ------------------------------------------------------------------
    # Internal slot
    # ------------------------------------------------------------------

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        rule_index = item.data(Qt.ItemDataRole.UserRole)
        if rule_index is not None:
            self.issue_clicked.emit(int(rule_index))
