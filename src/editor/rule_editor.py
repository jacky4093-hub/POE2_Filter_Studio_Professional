"""Schema-driven Rule Editor — v0.4.0

Public API (unchanged since v0.2):
  load_rule(rule: FilterRule)
  rule_changed  Signal()

Sections (now collapsible):
  General    — Show/Hide action + inline comment
  Conditions — dynamic add/remove rows (schema-typed widgets)
  Appearance — dynamic add/remove rows (color, font, minimap, effect)
  Audio      — dynamic add/remove rows (alert sounds, drop sound)

Unknown conditions/actions not in the schema are preserved via
UnknownPropertyWidget so they round-trip correctly.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QPushButton,
    QGroupBox, QMenu, QLabel, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction

from core.models import FilterRule, BLOCK_HEADERS
from core.filter_schema import (
    CONDITION_SCHEMA, ACTION_SCHEMA,
    SECTION_APPEARANCE, SECTION_AUDIO,
    get_field_def,
)
from editor.property_widgets import make_property_widget, BasePropertyWidget
from editor.collapsible_section import CollapsibleSection


# ---------------------------------------------------------------------------
# _PropertyRow — one label + typed widget + remove button
# ---------------------------------------------------------------------------

class _PropertyRow(QWidget):
    removed = Signal(object)  # emits self

    def __init__(self, key: str, raw_value: str, parent=None):
        super().__init__(parent)
        self.key = key

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(6)

        fd = get_field_def(key)
        display = fd.display_name if fd else key
        lbl = QLabel(display)
        lbl.setFixedWidth(100)
        lbl.setToolTip(key)  # always show the raw key on hover

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
# _SectionPanel — thin wrapper that composes CollapsibleSection
#                 and manages a list of _PropertyRow objects
# ---------------------------------------------------------------------------

class _SectionPanel(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._section = CollapsibleSection(title, self)
        layout.addWidget(self._section)
        self._rows: list[_PropertyRow] = []

    # ── delegate visual control ────────────────────────────────────────

    def set_max_height(self, h: int) -> None:
        self._section.set_max_content_height(h)

    def expand(self)  -> None: self._section.expand()
    def collapse(self)-> None: self._section.collapse()

    def save_state(self)         -> dict: return self._section.save_state()
    def restore_state(self, s: dict)    : self._section.restore_state(s)

    # ── row management ─────────────────────────────────────────────────

    def clear(self) -> None:
        for row in self._rows:
            self._section.remove_widget(row)
            row.deleteLater()
        self._rows.clear()
        self._section.set_count(0)

    def add_row(self, key: str, value: str) -> None:
        row = _PropertyRow(key, value)
        row.removed.connect(self._on_remove)
        self._rows.append(row)
        self._section.add_widget(row)
        self._section.set_count(len(self._rows))

    def _on_remove(self, row: _PropertyRow) -> None:
        if row in self._rows:
            self._rows.remove(row)
            self._section.remove_widget(row)
            row.deleteLater()
            self._section.set_count(len(self._rows))

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

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

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
        self._cond_panel.expand()
        root.addWidget(self._cond_panel)

        self._btn_add_cond = QPushButton("＋ 新增條件")
        self._btn_add_cond.clicked.connect(self._show_add_condition_menu)
        root.addWidget(self._btn_add_cond)

        # ── Appearance ───────────────────────────────────────────────
        self._app_panel = _SectionPanel("Appearance 顯示設定")
        self._app_panel.set_max_height(240)
        self._app_panel.expand()
        root.addWidget(self._app_panel)

        self._btn_add_app = QPushButton("＋ 新增顯示設定")
        self._btn_add_app.clicked.connect(self._show_add_appearance_menu)
        root.addWidget(self._btn_add_app)

        # ── Audio ────────────────────────────────────────────────────
        self._audio_panel = _SectionPanel("Audio 音效設定")
        self._audio_panel.set_max_height(160)
        self._audio_panel.collapse()  # collapsed by default to save space
        root.addWidget(self._audio_panel)

        self._btn_add_audio = QPushButton("＋ 新增音效設定")
        self._btn_add_audio.clicked.connect(self._show_add_audio_menu)
        root.addWidget(self._btn_add_audio)

        # ── Apply ────────────────────────────────────────────────────
        self.btn_apply = QPushButton("套用修改 ✔")
        self.btn_apply.setFixedHeight(32)
        self.btn_apply.clicked.connect(self._apply)
        root.addWidget(self.btn_apply)

        root.addStretch()

    # ------------------------------------------------------------------
    # Public API (unchanged)
    # ------------------------------------------------------------------

    def load_rule(self, rule: FilterRule) -> None:
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

        # Actions — split into Appearance vs Audio
        self._app_panel.clear()
        self._audio_panel.clear()
        for key, value in rule.actions:
            fd = get_field_def(key)
            if fd and fd.section == SECTION_AUDIO:
                self._audio_panel.add_row(key, value)
            else:
                self._app_panel.add_row(key, value)

        # Auto-expand Audio if it has content
        if self._audio_panel.used_keys():
            self._audio_panel.expand()

    # ------------------------------------------------------------------
    # "Add" popup menus
    # ------------------------------------------------------------------

    def _show_add_condition_menu(self) -> None:
        used = self._cond_panel.used_keys()
        menu = QMenu(self)
        for key, fd in CONDITION_SCHEMA.items():
            if key not in used:
                act = QAction(f"{fd.display_name}  ({key})", self)
                act.triggered.connect(
                    lambda _=False, k=key: self._cond_panel.add_row(k, "")
                )
                menu.addAction(act)
        if menu.isEmpty():
            a = QAction("（所有條件已新增）", self)
            a.setEnabled(False)
            menu.addAction(a)
        menu.exec(self._btn_add_cond.mapToGlobal(
            self._btn_add_cond.rect().bottomLeft()
        ))

    def _show_add_appearance_menu(self) -> None:
        used = self._app_panel.used_keys()
        menu = QMenu(self)
        for key, fd in ACTION_SCHEMA.items():
            if fd.section == SECTION_APPEARANCE and key not in used:
                act = QAction(f"{fd.display_name}  ({key})", self)
                act.triggered.connect(
                    lambda _=False, k=key: self._app_panel.add_row(k, "")
                )
                menu.addAction(act)
        if menu.isEmpty():
            a = QAction("（所有顯示設定已新增）", self)
            a.setEnabled(False)
            menu.addAction(a)
        menu.exec(self._btn_add_app.mapToGlobal(
            self._btn_add_app.rect().bottomLeft()
        ))

    def _show_add_audio_menu(self) -> None:
        used = self._audio_panel.used_keys()
        menu = QMenu(self)
        for key, fd in ACTION_SCHEMA.items():
            if fd.section == SECTION_AUDIO and key not in used:
                act = QAction(f"{fd.display_name}  ({key})", self)
                act.triggered.connect(
                    lambda _=False, k=key: self._audio_panel.add_row(k, "")
                )
                menu.addAction(act)
        if menu.isEmpty():
            a = QAction("（所有音效設定已新增）", self)
            a.setEnabled(False)
            menu.addAction(a)
        menu.exec(self._btn_add_audio.mapToGlobal(
            self._btn_add_audio.rect().bottomLeft()
        ))

    # ------------------------------------------------------------------
    # Apply — write back to FilterRule
    # ------------------------------------------------------------------

    def _apply(self) -> None:
        if self._rule is None:
            return
        self._rule.action         = self.action_combo.currentText()
        self._rule.inline_comment = self.comment_edit.text()
        self._rule.conditions     = self._cond_panel.collect()
        self._rule.actions        = (
            self._app_panel.collect() + self._audio_panel.collect()
        )
        self.rule_changed.emit()
