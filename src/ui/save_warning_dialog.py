"""SaveWarningDialog — P16.3 Save Warning Dialog

Shown before saving when validate_document() finds ERROR or WARNING issues.
INFO-level issues are never shown here and never block saving.

Usage (from MainWindow):
    if SaveWarningDialog.confirm(issues, parent=self):
        proceed_with_save()
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QDialogButtonBox, QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from core.validator import ValidationIssue, ValidationSeverity


_SEV_COLOR = {
    ValidationSeverity.ERROR:   "#ef4444",
    ValidationSeverity.WARNING: "#f59e0b",
}

_MAX_DISPLAY_ISSUES = 10


class SaveWarningDialog(QDialog):
    """Modal dialog listing validation issues before the user saves.

    Only ERROR and WARNING issues are displayed.
    Buttons: 取消 (reject) | 仍然儲存 (accept).
    """

    def __init__(
        self,
        issues: list[ValidationIssue],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SaveWarningDialog")
        self.setWindowTitle("儲存前確認")
        self.setMinimumWidth(520)
        self.setMinimumHeight(300)
        self._issues = issues
        self._build_ui()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 14, 16, 12)

        # ── Icon + headline ──────────────────────────────────────────
        headline_row = QHBoxLayout()
        icon_lbl = QLabel("⚠")
        icon_lbl.setObjectName("SaveWarnIcon")
        icon_lbl.setFixedWidth(32)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        headline_row.addWidget(icon_lbl)

        text_col = QVBoxLayout()
        headline = QLabel("Filter 驗證發現問題")
        headline.setObjectName("SaveWarnHeadline")
        text_col.addWidget(headline)

        n_error   = sum(1 for i in self._issues if i.severity == ValidationSeverity.ERROR)
        n_warning = sum(1 for i in self._issues if i.severity == ValidationSeverity.WARNING)
        parts = []
        if n_error:
            parts.append(f"{n_error} 個錯誤")
        if n_warning:
            parts.append(f"{n_warning} 個警告")
        summary_lbl = QLabel("、".join(parts))
        summary_lbl.setObjectName("SaveWarnSummary")
        text_col.addWidget(summary_lbl)

        # Store for test access
        self._error_count_label   = summary_lbl
        self._n_error   = n_error
        self._n_warning = n_warning

        headline_row.addLayout(text_col, stretch=1)
        layout.addLayout(headline_row)

        # ── Issue list ───────────────────────────────────────────────
        hint_lbl = QLabel(
            f"前 {min(_MAX_DISPLAY_ISSUES, len(self._issues))} 筆問題："
            if len(self._issues) > _MAX_DISPLAY_ISSUES
            else "問題清單："
        )
        hint_lbl.setObjectName("SaveWarnHint")
        layout.addWidget(hint_lbl)

        self._issue_list = QListWidget()
        self._issue_list.setObjectName("SaveWarnIssueList")
        self._issue_list.setMaximumHeight(160)
        self._issue_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        for issue in self._issues[:_MAX_DISPLAY_ISSUES]:
            prefix = "E" if issue.severity == ValidationSeverity.ERROR else "W"
            rule_str = f"規則 #{issue.rule_index}" if issue.rule_index >= 0 else "—"
            text = f"[{prefix}]  {rule_str}  [{issue.field}]  {issue.message}"
            item = QListWidgetItem(text)
            item.setForeground(QColor(_SEV_COLOR[issue.severity]))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._issue_list.addItem(item)

        if len(self._issues) > _MAX_DISPLAY_ISSUES:
            remaining = len(self._issues) - _MAX_DISPLAY_ISSUES
            overflow = QListWidgetItem(f"... 另外還有 {remaining} 個問題")
            overflow.setForeground(QColor("#5a6a88"))
            overflow.setFlags(overflow.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._issue_list.addItem(overflow)

        layout.addWidget(self._issue_list)

        # ── Sub-hint ─────────────────────────────────────────────────
        sub_hint = QLabel("儲存後的 filter 仍可正常輸出，這些問題不會阻止儲存。")
        sub_hint.setObjectName("SaveWarnSubHint")
        sub_hint.setWordWrap(True)
        layout.addWidget(sub_hint)

        # ── Buttons ──────────────────────────────────────────────────
        btn_box = QDialogButtonBox()
        btn_box.setObjectName("SaveWarnButtonBox")

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setObjectName("SaveWarnCancelBtn")
        btn_box.addButton(self._cancel_btn, QDialogButtonBox.ButtonRole.RejectRole)

        self._save_btn = QPushButton("仍然儲存")
        self._save_btn.setObjectName("SaveWarnSaveBtn")
        self._save_btn.setDefault(True)
        btn_box.addButton(self._save_btn, QDialogButtonBox.ButtonRole.AcceptRole)

        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    # ------------------------------------------------------------------
    # Convenience static method
    # ------------------------------------------------------------------

    @staticmethod
    def confirm(issues: list[ValidationIssue], parent=None) -> bool:
        """Show the dialog.  Return True if user chose '仍然儲存'."""
        dlg = SaveWarningDialog(issues, parent)
        return dlg.exec() == QDialog.DialogCode.Accepted
