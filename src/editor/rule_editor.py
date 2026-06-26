"""Schema-driven Rule Editor — v0.3.0

Public API (unchanged from v0.2):
  load_rule(rule: FilterRule)
  rule_changed  Signal()

Sections:
  General    — Show/Hide action + inline comment
  Conditions — dynamic add/remove rows (schema-typed widgets)
  Appearance — dynamic add/remove rows  (color, font, minimap, effect)
  Audio      — dynamic add/remove rows  (alert sounds, drop sound)

Unknown conditions/actions not in the schema are preserved via
UnknownPropertyWidget so they round-trip correctly.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QPushButton,
    QScrollArea, QGroupBox, QMenu, QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction

from core.models import FilterRule, BLOCK_HEADERS
from core.filter_schema import (
    CONDITION_SCHEMA, ACTION_SCHEMA,
    SECTION_APPEARANCE, SECTION_AUDIO, SECTION_CONDITIONS,
    get_field_def,
)
from editor.property_widgets import make_property_widget, BasePropertyWidget


# ---------------------------------------------------------------------------
# PropertyRow — one key + its typed widget + remove button
# ---------------------------------------------------------------------------

class _PropertyRow(QWidget):
    removed = Signal(object)  # emits self

    def __init__(self, key: str, raw_value: str, parent=None):
        super().__init__(parent)
        self.key = key

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(6)

        # Label (fixed width for alignment)
        fd = get_field_def(key)
        display = fd.display_name if fd else key
        lbl = QLabel(display)
        lbl.setFixedWidth(100)
        lbl.setToolTip(key)

        self.prop_widget = make_property_widget(fd)
        self.prop_widget.set_raw_value(raw_value)
        self.prop_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        btn_rm = QPushButton("✕")
        btn_rm.setFixedSize(24, 24)
        btn_rm.clicked.connect(lambda: self.removed.emit(self))

        layout.addWidget(lbl)
        layout.addWidget(self.prop_widget, 1)
        layout.addWidget(btn_rm)

    def get_data(self) -> list:
        return [self.key, self.prop_widget.get_raw_value()]


# ---------------------------------------------------------------------------
# _SectionPanel — a scrollable GroupBox with dynamic property rows
# ---------------------------------------------------------------------------

class _SectionPanel(QGroupBox):
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        outer = QVBoxLayout(self)
        outer.setSpacing(4)
        outer.setContentsMargins(6, 6, 6, 6)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.setSpacing(2)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._scroll.setWidget(self._container)

        outer.addWidget(self._scroll)
        self._rows: list[_PropertyRow] = []

    def set_max_height(self, h: int):
        self._scroll.setMaximumHeight(h)

    def clear(self):
        for row in self._rows:
            self._layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()

    def add_row(self, key: str, value: str):
        row = _PropertyRow(key, value)
        row.removed.connect(self._on_remove)
        self._rows.append(row)
        self._layout.addWidget(row)

    def _on_remove(self, row: _PropertyRow):
        if row in self._rows:
            self._rows.remove(row)
            self._layout.removeWidget(row)
            row.deleteLater()

    def collect(self) -> list:
        return [row.get_data() for row in self._rows]

    def used_keys(self) -> set[str]:
        return {row.key for row in self._rows}


# ---------------------------------------------------------------------------
# RuleEditorWidget
# ---------------------------------------------------------------------------

class RuleEditorWidget(QWidget):
    rule_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rule: FilterRule | None = None
        self._setup_ui()
        self.setEnabled(False)

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ── General ──────────────────────────────────────────────────
        gen_box = QGroupBox("General")
        gen_form = QFormLayout(gen_box)
        gen_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.action_combo = QComboBox()
        self.action_combo.addItems(BLOCK_HEADERS)
        gen_form.addRow("動作:", self.action_combo)

        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("（選填）同行備註")
        gen_form.addRow("備註:", self.comment_edit)

        root.addWidget(gen_box)

        # ── Conditions ───────────────────────────────────────────────
        self._cond_panel = _SectionPanel("Conditions 篩選條件")
        self._cond_panel.set_max_height(240)
        root.addWidget(self._cond_panel)

        btn_add_cond = QPushButton("＋ 新增條件")
        btn_add_cond.clicked.connect(self._show_add_condition_menu)
        root.addWidget(btn_add_cond)
        self._btn_add_cond = btn_add_cond

        # ── Appearance ───────────────────────────────────────────────
        self._app_panel = _SectionPanel("Appearance 顯示設定")
        self._app_panel.set_max_height(240)
        root.addWidget(self._app_panel)

        btn_add_app = QPushButton("＋ 新增顯示設定")
        btn_add_app.clicked.connect(self._show_add_appearance_menu)
        root.addWidget(btn_add_app)
        self._btn_add_app = btn_add_app

        # ── Audio ────────────────────────────────────────────────────
        self._audio_panel = _SectionPanel("Audio 音效設定")
        self._audio_panel.set_max_height(160)
        root.addWidget(self._audio_panel)

        btn_add_audio = QPushButton("＋ 新增音效設定")
        btn_add_audio.clicked.connect(self._show_add_audio_menu)
        root.addWidget(btn_add_audio)

        # ── Apply ────────────────────────────────────────────────────
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

        # General
        idx = BLOCK_HEADERS.index(rule.action) if rule.action in BLOCK_HEADERS else 0
        self.action_combo.setCurrentIndex(idx)
        self.comment_edit.setText(rule.inline_comment)

        # Conditions
        self._cond_panel.clear()
        for key, value in rule.conditions:
            self._cond_panel.add_row(key, value)

        # Actions → split into Appearance and Audio
        self._app_panel.clear()
        self._audio_panel.clear()
        for key, value in rule.actions:
            fd = get_field_def(key)
            if fd and fd.section == SECTION_AUDIO:
                self._audio_panel.add_row(key, value)
            else:
                # Appearance OR unknown action — both go into Appearance panel
                self._app_panel.add_row(key, value)

    # ------------------------------------------------------------------
    # "Add" menus — show only items not already used
    # ------------------------------------------------------------------

    def _show_add_condition_menu(self):
        used = self._cond_panel.used_keys()
        menu = QMenu(self)
        for key, fd in CONDITION_SCHEMA.items():
            if key not in used:
                act = QAction(f"{fd.display_name}  ({key})", self)
                act.triggered.connect(lambda _=False, k=key: self._cond_panel.add_row(k, ""))
                menu.addAction(act)
        if menu.isEmpty():
            act = QAction("（所有條件已新增）", self)
            act.setEnabled(False)
            menu.addAction(act)
        menu.exec(self._btn_add_cond.mapToGlobal(
            self._btn_add_cond.rect().bottomLeft()
        ))

    def _show_add_appearance_menu(self):
        used = self._app_panel.used_keys()
        menu = QMenu(self)
        for key, fd in ACTION_SCHEMA.items():
            if fd.section == SECTION_APPEARANCE and key not in used:
                act = QAction(f"{fd.display_name}  ({key})", self)
                act.triggered.connect(lambda _=False, k=key: self._app_panel.add_row(k, ""))
                menu.addAction(act)
        if menu.isEmpty():
            act = QAction("（所有顯示設定已新增）", self)
            act.setEnabled(False)
            menu.addAction(act)
        menu.exec(self._btn_add_app.mapToGlobal(
            self._btn_add_app.rect().bottomLeft()
        ))

    def _show_add_audio_menu(self):
        used = self._audio_panel.used_keys()
        menu = QMenu(self)
        for key, fd in ACTION_SCHEMA.items():
            if fd.section == SECTION_AUDIO and key not in used:
                act = QAction(f"{fd.display_name}  ({key})", self)
                act.triggered.connect(lambda _=False, k=key: self._audio_panel.add_row(k, ""))
                menu.addAction(act)
        if menu.isEmpty():
            act = QAction("（所有音效設定已新增）", self)
            act.setEnabled(False)
            menu.addAction(act)
        menu.exec(self.sender().parent().mapToGlobal(
            self.sender().rect().bottomLeft()
        ) if self.sender() else self.mapToGlobal(self.rect().center()))

    # ------------------------------------------------------------------
    # Apply — write back to FilterRule (same contract as v0.2)
    # ------------------------------------------------------------------

    def _apply(self):
        if self._rule is None:
            return
        self._rule.action = self.action_combo.currentText()
        self._rule.inline_comment = self.comment_edit.text()
        self._rule.conditions = self._cond_panel.collect()
        self._rule.actions = (
            self._app_panel.collect() + self._audio_panel.collect()
        )
        self.rule_changed.emit()
