from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QPushButton,
    QScrollArea, QGroupBox, QLabel,
)
from PySide6.QtCore import Signal, Qt

from core.models import FilterRule, BLOCK_HEADERS, KNOWN_CONDITIONS, KNOWN_ACTIONS


# ---------------------------------------------------------------------------
# Row widgets
# ---------------------------------------------------------------------------

class _KeyValueRow(QWidget):
    """A single editable key/value row with a remove button."""

    removed = Signal(object)  # emits self

    def __init__(self, keys: list[str], key: str = "", value: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(4)

        self.key_combo = QComboBox()
        self.key_combo.setEditable(True)
        self.key_combo.addItems(keys)
        self.key_combo.setCurrentText(key)
        self.key_combo.setMinimumWidth(170)
        self.key_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )

        self.value_edit = QLineEdit(value)
        self.value_edit.setPlaceholderText("值")

        btn = QPushButton("✕")
        btn.setFixedWidth(26)
        btn.setFixedHeight(24)
        btn.clicked.connect(lambda: self.removed.emit(self))

        layout.addWidget(self.key_combo)
        layout.addWidget(self.value_edit, 1)
        layout.addWidget(btn)

    def get_data(self) -> list:
        return [self.key_combo.currentText().strip(), self.value_edit.text().strip()]


# ---------------------------------------------------------------------------
# Main editor widget
# ---------------------------------------------------------------------------

class RuleEditorWidget(QWidget):
    """Right-hand panel for editing a single FilterRule."""

    rule_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rule: FilterRule | None = None
        self._cond_rows: list[_KeyValueRow] = []
        self._act_rows: list[_KeyValueRow] = []
        self._setup_ui()
        self.setEnabled(False)

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # Header group
        hdr_box = QGroupBox("規則標頭")
        hdr_form = QFormLayout(hdr_box)
        hdr_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.action_combo = QComboBox()
        self.action_combo.addItems(BLOCK_HEADERS)
        hdr_form.addRow("動作:", self.action_combo)

        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("（選填）同行備註")
        hdr_form.addRow("備註:", self.comment_edit)

        root.addWidget(hdr_box)

        # Conditions group
        cond_box = QGroupBox("篩選條件 (Conditions)")
        cond_outer = QVBoxLayout(cond_box)
        cond_outer.setSpacing(4)

        self._cond_scroll = QScrollArea()
        self._cond_scroll.setWidgetResizable(True)
        self._cond_scroll.setMaximumHeight(220)
        self._cond_container = QWidget()
        self._cond_layout = QVBoxLayout(self._cond_container)
        self._cond_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._cond_layout.setSpacing(2)
        self._cond_layout.setContentsMargins(2, 2, 2, 2)
        self._cond_scroll.setWidget(self._cond_container)
        cond_outer.addWidget(self._cond_scroll)

        btn_add_cond = QPushButton("＋ 新增條件")
        btn_add_cond.clicked.connect(lambda: self._add_cond_row())
        cond_outer.addWidget(btn_add_cond)

        root.addWidget(cond_box)

        # Actions group
        act_box = QGroupBox("顯示設定 (Actions)")
        act_outer = QVBoxLayout(act_box)
        act_outer.setSpacing(4)

        self._act_scroll = QScrollArea()
        self._act_scroll.setWidgetResizable(True)
        self._act_scroll.setMaximumHeight(220)
        self._act_container = QWidget()
        self._act_layout = QVBoxLayout(self._act_container)
        self._act_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._act_layout.setSpacing(2)
        self._act_layout.setContentsMargins(2, 2, 2, 2)
        self._act_scroll.setWidget(self._act_container)
        act_outer.addWidget(self._act_scroll)

        btn_add_act = QPushButton("＋ 新增動作")
        btn_add_act.clicked.connect(lambda: self._add_act_row())
        act_outer.addWidget(btn_add_act)

        root.addWidget(act_box)

        # Apply button
        self.btn_apply = QPushButton("套用修改 ✔")
        self.btn_apply.setFixedHeight(32)
        self.btn_apply.clicked.connect(self._apply)
        root.addWidget(self.btn_apply)

        root.addStretch()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_rule(self, rule: FilterRule):
        self._rule = rule
        self.setEnabled(True)

        # Header
        idx = BLOCK_HEADERS.index(rule.action) if rule.action in BLOCK_HEADERS else 0
        self.action_combo.setCurrentIndex(idx)
        self.comment_edit.setText(rule.inline_comment)

        # Rebuild condition rows
        self._clear_rows(self._cond_layout, self._cond_rows)
        for key, value in rule.conditions:
            self._add_cond_row(key, value)

        # Rebuild action rows
        self._clear_rows(self._act_layout, self._act_rows)
        for key, value in rule.actions:
            self._add_act_row(key, value)

    # ------------------------------------------------------------------
    # Row management helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clear_rows(layout, rows: list):
        for row in rows:
            layout.removeWidget(row)
            row.deleteLater()
        rows.clear()

    def _add_cond_row(self, key: str = "", value: str = ""):
        row = _KeyValueRow(KNOWN_CONDITIONS, key=key, value=value)
        row.removed.connect(self._remove_cond_row)
        self._cond_rows.append(row)
        self._cond_layout.addWidget(row)

    def _remove_cond_row(self, row: _KeyValueRow):
        if row in self._cond_rows:
            self._cond_rows.remove(row)
            self._cond_layout.removeWidget(row)
            row.deleteLater()

    def _add_act_row(self, key: str = "", value: str = ""):
        row = _KeyValueRow(KNOWN_ACTIONS, key=key, value=value)
        row.removed.connect(self._remove_act_row)
        self._act_rows.append(row)
        self._act_layout.addWidget(row)

    def _remove_act_row(self, row: _KeyValueRow):
        if row in self._act_rows:
            self._act_rows.remove(row)
            self._act_layout.removeWidget(row)
            row.deleteLater()

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------

    def _apply(self):
        if self._rule is None:
            return
        self._rule.action = self.action_combo.currentText()
        self._rule.inline_comment = self.comment_edit.text()
        self._rule.conditions = [r.get_data() for r in self._cond_rows]
        self._rule.actions = [r.get_data() for r in self._act_rows]
        self.rule_changed.emit()
