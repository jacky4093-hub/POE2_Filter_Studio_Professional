"""P22 — ConditionBuilderWidget: 圖形化條件編輯器。

架構（三層）：
  ConditionRowWidget      — 顯示並編輯單一條件列
  ConditionBuilderWidget  — 容器：管理所有列、提供新增/移除操作

信號流：
  使用者修改欄位 → ConditionRowWidget.changed
                  → ConditionBuilderWidget._on_condition_changed
                  → ConditionBuilderWidget.conditions_changed(list)

Class / BaseType 沿用：
  AliasCompleter（P21.4）— 中文 autocomplete popup
  RuleEditorAliasService（P21.5）— editingFinished 時解析中文 → 英文
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from core.condition_builder import (
    ConditionBuilderService, ConditionDef, ConditionValue, FieldType,
)


# ---------------------------------------------------------------------------
# ConditionRowWidget
# ---------------------------------------------------------------------------

class ConditionRowWidget(QWidget):
    """顯示並編輯單一條件的橫向列 widget。

    layout: [label(68px)] [op_combo(52px)] [value_widget(stretch)] [remove_btn]
    STRING 條件無 op_combo。
    """

    changed          = Signal()
    remove_requested = Signal()

    _OP_NUMERIC = [">=", "<=", "=", ">", "<"]
    _OP_ENUM    = [">=", "<=", "="]

    _RARITY_PAIRS: list[tuple[str, str]] = [
        ("Normal", "普通"),
        ("Magic",  "魔法"),
        ("Rare",   "稀有"),
        ("Unique", "傳說"),
    ]

    def __init__(
        self,
        cv:        ConditionValue,
        cdef:      ConditionDef,
        alias_svc  = None,
        parent:    QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._cdef            = cdef
        self._alias_svc       = alias_svc
        self._syncing         = False
        self._alias_completer = None

        # Value sub-widgets (at most one is set)
        self._value_combo:  QComboBox | None  = None
        self._spin:         QSpinBox  | None  = None
        self._string_edit:  QLineEdit | None  = None
        self._op_combo:     QComboBox | None  = None

        self._setup_ui(cv)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _setup_ui(self, cv: ConditionValue) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        # Label
        lbl = QLabel(self._cdef.label)
        lbl.setFixedWidth(68)
        lbl.setObjectName("ConditionLabel")
        layout.addWidget(lbl)

        # Op combo (omitted for STRING)
        if self._cdef.field_type != FieldType.STRING:
            ops = (self._OP_ENUM
                   if self._cdef.field_type == FieldType.ENUM
                   else self._OP_NUMERIC)
            self._op_combo = QComboBox()
            self._op_combo.setObjectName("ConditionOpCombo")
            self._op_combo.addItems(ops)
            self._op_combo.setFixedWidth(52)
            idx = ops.index(cv.op) if cv.op in ops else 0
            self._op_combo.setCurrentIndex(idx)
            self._op_combo.currentTextChanged.connect(self._emit_changed)
            layout.addWidget(self._op_combo)

        # Value widget
        val_w = self._make_value_widget(cv)
        layout.addWidget(val_w, stretch=1)

        # Remove button
        rm = QPushButton("×")
        rm.setObjectName("ConditionRemoveBtn")
        rm.setFixedSize(22, 22)
        rm.setToolTip("移除此條件")
        rm.clicked.connect(self.remove_requested)
        layout.addWidget(rm)

    def _make_value_widget(self, cv: ConditionValue) -> QWidget:
        ft = self._cdef.field_type

        if ft == FieldType.ENUM:
            self._value_combo = QComboBox()
            self._value_combo.setObjectName("ConditionValueCombo")
            for en, zh in self._RARITY_PAIRS:
                self._value_combo.addItem(f"{zh}（{en}）", userData=en)
            # Pre-select matching entry
            for i, (en, _) in enumerate(self._RARITY_PAIRS):
                if en == cv.value:
                    self._value_combo.setCurrentIndex(i)
                    break
            self._value_combo.currentIndexChanged.connect(self._emit_changed)
            return self._value_combo

        if ft == FieldType.NUMERIC:
            self._spin = QSpinBox()
            self._spin.setObjectName("ConditionSpinBox")
            self._spin.setRange(self._cdef.min_val, self._cdef.max_val)
            try:
                self._spin.setValue(
                    int(cv.value) if cv.value.strip() else 0
                )
            except (ValueError, TypeError):
                self._spin.setValue(0)
            self._spin.valueChanged.connect(self._emit_changed)
            return self._spin

        # STRING
        self._string_edit = QLineEdit()
        self._string_edit.setObjectName("ConditionStringEdit")
        self._string_edit.setText(cv.value)
        ph = ('"Currency" "Gems" …'
              if self._cdef.key == "Class"
              else '"Divine Orb" …')
        self._string_edit.setPlaceholderText(ph)
        self._string_edit.editingFinished.connect(self._on_string_editing_finished)

        # P21 AliasCompleter（可選）
        try:
            from widgets.alias_completer import AliasCompleter
            self._alias_completer = AliasCompleter(
                self._string_edit, parent=self
            )
            self._alias_completer.completed.connect(self._on_string_completed)
        except Exception:
            pass

        return self._string_edit

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_value(self) -> ConditionValue:
        """讀取目前 UI 狀態為 ConditionValue。"""
        op = self._op_combo.currentText() if self._op_combo else ""
        ft = self._cdef.field_type

        if ft == FieldType.ENUM:
            val = (self._value_combo.currentData() or "") if self._value_combo else ""
            return ConditionValue(key=self._cdef.key, op=op, value=val)

        if ft == FieldType.NUMERIC:
            val = str(self._spin.value()) if self._spin else "0"
            return ConditionValue(key=self._cdef.key, op=op, value=val)

        # STRING
        val = self._string_edit.text() if self._string_edit else ""
        return ConditionValue(key=self._cdef.key, op="", value=val)

    def set_value(self, cv: ConditionValue) -> None:
        """從 ConditionValue 更新 UI（不發射 changed）。"""
        self._syncing = True
        try:
            if self._op_combo and cv.op:
                ops = [self._op_combo.itemText(i)
                       for i in range(self._op_combo.count())]
                if cv.op in ops:
                    self._op_combo.setCurrentText(cv.op)

            ft = self._cdef.field_type
            if ft == FieldType.ENUM and self._value_combo:
                for i, (en, _) in enumerate(self._RARITY_PAIRS):
                    if en == cv.value:
                        self._value_combo.setCurrentIndex(i)
                        break
            elif ft == FieldType.NUMERIC and self._spin:
                try:
                    self._spin.setValue(int(cv.value))
                except (ValueError, TypeError):
                    pass
            elif self._string_edit:
                self._string_edit.setText(cv.value)
        finally:
            self._syncing = False

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _emit_changed(self, *_args) -> None:
        if not self._syncing:
            self.changed.emit()

    def _on_string_editing_finished(self) -> None:
        """editingFinished: 解析中文 alias → 英文（透過 RuleEditorAliasService）。"""
        if self._alias_svc and self._string_edit:
            text = self._string_edit.text()
            try:
                resolved = self._alias_svc.resolve_filter_value(
                    text, self._cdef.key
                )
                if resolved != text:
                    self._string_edit.blockSignals(True)
                    self._string_edit.setText(resolved)
                    self._string_edit.blockSignals(False)
            except Exception:
                pass
        self._emit_changed()

    def _on_string_completed(self, en_name: str) -> None:
        """AliasCompleter 選取後加引號並回填欄位。"""
        if not self._string_edit:
            return
        quoted = f'"{en_name}"'
        self._string_edit.blockSignals(True)
        self._string_edit.setText(quoted)
        self._string_edit.blockSignals(False)
        self._emit_changed()


# ---------------------------------------------------------------------------
# ConditionBuilderWidget
# ---------------------------------------------------------------------------

class ConditionBuilderWidget(QWidget):
    """圖形化條件編輯器容器。

    用法：
        w = ConditionBuilderWidget()
        w.set_conditions(rule.conditions)
        w.conditions_changed.connect(lambda conds: ...)

    conditions_changed 發射的清單格式與 rule.conditions 完全相容：
        [[key, value_str], ...]
    """

    conditions_changed = Signal(list)

    def __init__(
        self,
        alias_svc  = None,
        parent:    QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ConditionBuilderWidget")

        self._svc       = ConditionBuilderService()
        self._alias_svc = alias_svc

        if self._alias_svc is None:
            try:
                from core.rule_editor_alias import RuleEditorAliasService
                self._alias_svc = RuleEditorAliasService()
            except Exception:
                pass

        self._rows:                list[ConditionRowWidget] = []
        self._existing_conditions: list                     = []

        self._setup_ui()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        # Scrollable rows area
        scroll = QScrollArea()
        scroll.setObjectName("ConditionBuilderScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._rows_container = QWidget()
        self._rows_container.setObjectName("ConditionRowsContainer")
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(2)
        self._rows_layout.addStretch(1)   # 永遠在最後

        scroll.setWidget(self._rows_container)
        root.addWidget(scroll, stretch=1)

        # Add condition bar
        add_bar = QHBoxLayout()
        add_bar.setSpacing(4)

        self._add_key_combo = QComboBox()
        self._add_key_combo.setObjectName("ConditionAddCombo")
        for key in self._svc.available_keys():
            cdef = self._svc.get_def(key)
            label = f"{cdef.label}（{key}）" if cdef else key
            self._add_key_combo.addItem(label, userData=key)

        add_btn = QPushButton("新增條件")
        add_btn.setObjectName("ConditionAddBtn")
        add_btn.clicked.connect(self._on_add_condition)

        add_bar.addWidget(self._add_key_combo, stretch=1)
        add_bar.addWidget(add_btn)
        root.addLayout(add_bar)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_conditions(self, conditions: list) -> None:
        """從 rule.conditions 格式清單載入並顯示條件。"""
        self._existing_conditions = list(conditions)
        cvs = self._svc.load_from_rule(conditions)
        self._rebuild_rows(cvs)

    def get_conditions(self) -> list:
        """回傳目前條件，格式相容 rule.conditions。"""
        cvs = [row.get_value() for row in self._rows]
        return self._svc.save_to_rule(cvs, self._existing_conditions)

    def row_count(self) -> int:
        """回傳目前顯示的條件列數量（測試用）。"""
        return len(self._rows)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _rebuild_rows(self, cvs: list[ConditionValue]) -> None:
        """清空舊列並重新建立。"""
        for row in self._rows:
            try:
                row.changed.disconnect()
                row.remove_requested.disconnect()
            except RuntimeError:
                pass
            self._rows_layout.removeWidget(row)
            row.setParent(None)
            row.deleteLater()
        self._rows.clear()

        for cv in cvs:
            self._add_row(cv)

    def _add_row(self, cv: ConditionValue) -> None:
        cdef = self._svc.get_def(cv.key)
        if cdef is None:
            return
        row = ConditionRowWidget(
            cv, cdef,
            alias_svc=self._alias_svc,
            parent=self._rows_container,
        )
        row.changed.connect(self._on_condition_changed)
        row.remove_requested.connect(lambda r=row: self._on_remove_row(r))

        insert_pos = max(0, self._rows_layout.count() - 1)
        self._rows_layout.insertWidget(insert_pos, row)
        self._rows.append(row)

    def _on_add_condition(self) -> None:
        key = self._add_key_combo.currentData()
        cdef = self._svc.get_def(key) if key else None
        if cdef is None:
            return

        if cdef.field_type == FieldType.ENUM:
            cv = ConditionValue(key=key, op=">=",
                                value=cdef.choices[0] if cdef.choices else "")
        elif cdef.field_type == FieldType.NUMERIC:
            cv = ConditionValue(key=key, op=">=", value="0")
        else:
            cv = ConditionValue(key=key, op="", value="")

        self._add_row(cv)
        self._on_condition_changed()

    def _on_remove_row(self, row: ConditionRowWidget) -> None:
        if row not in self._rows:
            return
        try:
            row.changed.disconnect()
            row.remove_requested.disconnect()
        except RuntimeError:
            pass
        self._rows.remove(row)
        self._rows_layout.removeWidget(row)
        row.setParent(None)
        row.deleteLater()
        self._on_condition_changed()

    def _on_condition_changed(self) -> None:
        self.conditions_changed.emit(self.get_conditions())

    def update_condition(self, cv: ConditionValue) -> None:
        """P22.2: 更新單一條件列的值（不發射 conditions_changed）。

        用於 Rule Editor 文字欄位 → Widget 的單向同步。
        若 key 對應的列已存在 → 更新值；
        若不存在且 cv 非空 → 新增一列；
        若不存在且 cv 為空 → 不動作。
        """
        for row in self._rows:
            if row._cdef.key == cv.key:
                row.set_value(cv)
                return
        if not cv.is_empty():
            self._add_row(cv)
