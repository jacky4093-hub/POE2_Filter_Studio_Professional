"""ValidationPanel — P16.2 Validation UI

Displays issues produced by core.validator.validate_document().
Lives at the bottom of the main editor shell, above the status bar.

Public API:
    refresh(issues)  — repopulate from a list[ValidationIssue]
    clear()          — reset to clean / no-issue state

Signal:
    issue_clicked(rule_index: int) — fired when user clicks a row.
        Callers should ignore rule_index == -1 (issue not tied to a rule).
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from core.validator import ValidationIssue, ValidationSeverity


_SEV_META: dict[ValidationSeverity, tuple[str, str]] = {
    ValidationSeverity.ERROR:   ("E", "#ef4444"),
    ValidationSeverity.WARNING: ("W", "#f59e0b"),
    ValidationSeverity.INFO:    ("I", "#60a5fa"),
}


class ValidationPanel(QWidget):
    """Compact bottom panel showing filter validation issues."""

    issue_clicked = Signal(int)

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

    def refresh(self, issues: list[ValidationIssue]) -> None:
        """Repopulate the panel from a list of ValidationIssue objects."""
        self._list.clear()

        n_error   = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        n_warning = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
        n_info    = sum(1 for i in issues if i.severity == ValidationSeverity.INFO)

        self._error_chip.setText(f"E {n_error}")
        self._warning_chip.setText(f"W {n_warning}")
        self._info_chip.setText(f"I {n_info}")

        for issue in issues:
            prefix, color = _SEV_META[issue.severity]
            rule_str = f"規則 #{issue.rule_index}" if issue.rule_index >= 0 else "—"
            text = f"[{prefix}]  {rule_str}  [{issue.field}]  {issue.message}"
            item = QListWidgetItem(text)
            item.setForeground(QColor(color))
            item.setData(Qt.ItemDataRole.UserRole, issue.rule_index)
            self._list.addItem(item)

    def clear(self) -> None:
        """Reset to empty / no-issue state."""
        self._list.clear()
        self._error_chip.setText("E 0")
        self._warning_chip.setText("W 0")
        self._info_chip.setText("I 0")

    # ------------------------------------------------------------------
    # Internal slot
    # ------------------------------------------------------------------

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        rule_index = item.data(Qt.ItemDataRole.UserRole)
        if rule_index is not None:
            self.issue_clicked.emit(int(rule_index))
