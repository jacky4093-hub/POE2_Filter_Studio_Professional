"""RuleDetailEditor — v4.0.0  (P13.4 Editor Input Polish)

Design contract (unchanged from v2.3.0):
  - set_rule(rule, index) populates all fields WITHOUT emitting rule_changed.
  - Any subsequent user interaction emits rule_changed(index, updated_rule).
  - updated_rule is built from current field values on top of a deep-copy of
    the last-loaded rule, so all unmanaged fields (pre_lines, inline_comment,
    unknown_lines, unrecognised conditions/actions) are preserved.
  - flush_pending() is a no-op.

P13.1 visual improvements:
  - Title bar showing rule index + action (updated live).
  - Sections wrapped in QGroupBox cards instead of plain headers.
  - Richer empty-state placeholder with icon + hint text.
  - Preview section inside its own card with monospace display.

P13.4 input polish:
  - SetFontSize replaced with QSpinBox (range 0–60; 0 = not set → "—").
  - Colour fields (SetTextColor / SetBorderColor / SetBackgroundColor) retain
    text input but gain a live colour-swatch preview label beside them.
    Invalid colour strings show a dashed-red swatch; empty → transparent.
  - PlayAlertSound and MinimapIcon fields show a one-line format hint.
"""

from __future__ import annotations

import copy

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFormLayout,
    QGroupBox, QLabel, QCheckBox, QComboBox, QLineEdit, QPlainTextEdit,
    QSpinBox, QStackedWidget,
)
from PySide6.QtCore import Signal, Qt

from core.models import FilterRule


_ACTIONS = ["Show", "Hide", "Continue"]


class RuleDetailEditor(QWidget):
    """Form editor for one FilterRule.  Emits rule_changed(index, updated_rule)."""

    rule_changed = Signal(int, object)   # (index: int, rule: FilterRule)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RuleDetailEditor")

        self._rule: FilterRule | None = None
        self._index: int = -1
        self._loading: bool = False   # guards spurious rule_changed during set_rule

        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_rule(self, rule: FilterRule, index: int = -1) -> None:
        """Load rule into form.  Never emits rule_changed."""
        self._rule = copy.deepcopy(rule)
        self._index = index
        self._loading = True
        try:
            self._populate_fields()
            self._update_preview()
            self._update_title()
        finally:
            self._loading = False
        self._stacked.setCurrentWidget(self._editor_page)

    def clear(self) -> None:
        """Return to the empty-state page."""
        self._rule = None
        self._index = -1
        self._preview_text.setPlainText("")
        self._stacked.setCurrentWidget(self._empty_page)

    def flush_pending(self) -> None:
        """No-op: this editor commits changes immediately on editingFinished."""

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._stacked = QStackedWidget()
        root.addWidget(self._stacked)

        self._build_empty_page()
        self._build_editor_page()

    # ── Page 0: empty state ──────────────────────────────────────────

    def _build_empty_page(self) -> None:
        self._empty_page = QWidget()
        self._empty_page.setObjectName("RuleDetailEmptyPage")

        layout = QVBoxLayout(self._empty_page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel("⚙")
        icon_lbl.setObjectName("RuleDetailEmptyIcon")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        msg_lbl = QLabel("尚未選取規則")
        msg_lbl.setObjectName("RuleDetailEmptyLabel")
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        hint_lbl = QLabel("從左側規則列表點選一條規則開始編輯")
        hint_lbl.setObjectName("RuleDetailEmptyHint")
        hint_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch(2)
        layout.addWidget(icon_lbl)
        layout.addSpacing(8)
        layout.addWidget(msg_lbl)
        layout.addSpacing(4)
        layout.addWidget(hint_lbl)
        layout.addStretch(3)

        self._stacked.addWidget(self._empty_page)

    # ── Page 1: editor (scrollable) ───────────────────────────────────

    def _build_editor_page(self) -> None:
        scroll = QScrollArea()
        scroll.setObjectName("RuleDetailScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._editor_page = scroll   # tests compare identity with this attribute

        content = QWidget()
        content.setObjectName("RuleDetailContent")

        vlayout = QVBoxLayout(content)
        vlayout.setContentsMargins(10, 0, 10, 10)
        vlayout.setSpacing(6)

        self._build_title_bar(vlayout)
        self._build_basic_card(vlayout)
        self._build_condition_card(vlayout)
        self._build_appearance_card(vlayout)
        self._build_audio_card(vlayout)
        self._build_minimap_card(vlayout)
        self._build_preview_card(vlayout)
        vlayout.addStretch()

        scroll.setWidget(content)
        self._stacked.addWidget(scroll)

    def _build_title_bar(self, vlayout: QVBoxLayout) -> None:
        title_bar = QWidget()
        title_bar.setObjectName("RuleEditorTitleBar")
        bar_layout = QHBoxLayout(title_bar)
        bar_layout.setContentsMargins(0, 8, 0, 8)
        bar_layout.setSpacing(8)

        self._title_lbl = QLabel("規則")
        self._title_lbl.setObjectName("RuleEditorTitle")
        bar_layout.addWidget(self._title_lbl, stretch=1)

        vlayout.addWidget(title_bar)

    def _make_card(self, title: str) -> tuple[QGroupBox, QFormLayout]:
        box = QGroupBox(title)
        box.setObjectName("RuleEditorCard")
        form = QFormLayout(box)
        form.setSpacing(6)
        form.setContentsMargins(8, 4, 8, 8)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        return box, form

    def _build_basic_card(self, vlayout: QVBoxLayout) -> None:
        box, form = self._make_card("基本設定")

        self._enabled_cb = QCheckBox()
        self._enabled_cb.setObjectName("RuleDetailEnabled")
        form.addRow("啟用", self._enabled_cb)

        self._action_combo = QComboBox()
        self._action_combo.setObjectName("RuleDetailAction")
        self._action_combo.addItems(_ACTIONS)
        form.addRow("動作", self._action_combo)

        vlayout.addWidget(box)

        self._enabled_cb.stateChanged.connect(self._on_any_field_changed)
        self._action_combo.currentTextChanged.connect(self._on_any_field_changed)

    def _build_condition_card(self, vlayout: QVBoxLayout) -> None:
        box, form = self._make_card("條件")

        self._class_edit = QLineEdit()
        self._class_edit.setObjectName("RuleDetailClass")
        self._class_edit.setPlaceholderText('"Currency" "Gems" …')
        form.addRow("Class", self._class_edit)

        self._basetype_edit = QLineEdit()
        self._basetype_edit.setObjectName("RuleDetailBaseType")
        self._basetype_edit.setPlaceholderText('"Divine Orb" …')
        form.addRow("BaseType", self._basetype_edit)

        vlayout.addWidget(box)

        self._class_edit.editingFinished.connect(self._on_any_field_changed)
        self._basetype_edit.editingFinished.connect(self._on_any_field_changed)

    def _make_color_row(self, obj_name: str, placeholder: str) -> tuple:
        """Return (container_widget, QLineEdit, swatch_QLabel) for a colour field."""
        container = QWidget()
        hlayout = QHBoxLayout(container)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setSpacing(4)

        edit = QLineEdit()
        edit.setObjectName(obj_name)
        edit.setPlaceholderText(placeholder)
        hlayout.addWidget(edit, stretch=1)

        swatch = QLabel()
        swatch.setObjectName("ColorSwatch")
        swatch.setFixedSize(20, 18)
        swatch.setToolTip("色彩預覽")
        self._update_one_swatch(swatch, "")
        hlayout.addWidget(swatch)

        return container, edit, swatch

    def _build_appearance_card(self, vlayout: QVBoxLayout) -> None:
        box, form = self._make_card("外觀")

        # SetFontSize → QSpinBox (0 = "—" / not set)
        self._fontsize_spin = QSpinBox()
        self._fontsize_spin.setObjectName("RuleDetailFontSize")
        self._fontsize_spin.setRange(0, 60)
        self._fontsize_spin.setSpecialValueText("—")
        form.addRow("SetFontSize", self._fontsize_spin)

        # Colour fields: QLineEdit + live swatch
        tc_row, self._textcolor_edit, self._textcolor_swatch = self._make_color_row(
            "RuleDetailTextColor", "255 200 0 255"
        )
        form.addRow("SetTextColor", tc_row)

        bc_row, self._bordercolor_edit, self._bordercolor_swatch = self._make_color_row(
            "RuleDetailBorderColor", "0 0 0 0"
        )
        form.addRow("SetBorderColor", bc_row)

        bg_row, self._bgcolor_edit, self._bgcolor_swatch = self._make_color_row(
            "RuleDetailBgColor", "0 0 0 180"
        )
        form.addRow("SetBackgroundColor", bg_row)

        vlayout.addWidget(box)

        self._fontsize_spin.valueChanged.connect(self._on_any_field_changed)
        for edit in (self._textcolor_edit, self._bordercolor_edit, self._bgcolor_edit):
            edit.textChanged.connect(self._update_color_swatches)
            edit.editingFinished.connect(self._on_any_field_changed)

    def _build_audio_card(self, vlayout: QVBoxLayout) -> None:
        box, form = self._make_card("音效")

        self._alert_edit = QLineEdit()
        self._alert_edit.setObjectName("RuleDetailAlertSound")
        self._alert_edit.setPlaceholderText("1 300")
        form.addRow("PlayAlertSound", self._alert_edit)

        self._alert_hint = QLabel("格式：音效ID 音量（例：1 300）")
        self._alert_hint.setObjectName("RuleDetailHintLabel")
        form.addRow("", self._alert_hint)

        vlayout.addWidget(box)

        self._alert_edit.editingFinished.connect(self._on_any_field_changed)

    def _build_minimap_card(self, vlayout: QVBoxLayout) -> None:
        box, form = self._make_card("小地圖")

        self._minimap_edit = QLineEdit()
        self._minimap_edit.setObjectName("RuleDetailMinimapIcon")
        self._minimap_edit.setPlaceholderText("1 Red Circle")
        form.addRow("MinimapIcon", self._minimap_edit)

        self._minimap_hint = QLabel("格式：大小 顏色 形狀（例：1 Red Circle）")
        self._minimap_hint.setObjectName("RuleDetailHintLabel")
        form.addRow("", self._minimap_hint)

        vlayout.addWidget(box)

        self._minimap_edit.editingFinished.connect(self._on_any_field_changed)

    def _build_preview_card(self, vlayout: QVBoxLayout) -> None:
        box = QGroupBox("規則預覽（唯讀）")
        box.setObjectName("RuleEditorCard")
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(8, 4, 8, 8)
        box_layout.setSpacing(4)

        self._preview_text = QPlainTextEdit()
        self._preview_text.setObjectName("RuleDetailPreview")
        self._preview_text.setReadOnly(True)
        self._preview_text.setMaximumHeight(130)
        box_layout.addWidget(self._preview_text)

        vlayout.addWidget(box)

    # ------------------------------------------------------------------
    # Field helpers — pure, no side effects
    # ------------------------------------------------------------------

    @staticmethod
    def _get_from_list(items: list, key: str) -> str:
        """Return raw value string for the first matching key, or ''."""
        key_lower = key.lower()
        for item in items:
            if len(item) >= 2 and str(item[0]).lower() == key_lower:
                return str(item[1])
        return ""

    @staticmethod
    def _update_in_list(items: list, key: str, value: str) -> list:
        """Return a new list with *key* updated to *value* (or removed if empty).

        Preserves the position of the first occurrence; removes duplicates;
        appends a new entry if the key did not exist before.
        All other entries are preserved unchanged (unknown fields included).
        """
        key_lower = key.lower()
        result: list = []
        found = False
        for item in items:
            if len(item) >= 2 and str(item[0]).lower() == key_lower:
                if not found and value.strip():
                    result.append([key, value.strip()])
                    found = True
                # drop duplicates / empty entry
            else:
                result.append(list(item))
        if not found and value.strip():
            result.append([key, value.strip()])
        return result

    # ------------------------------------------------------------------
    # Populate / build rule
    # ------------------------------------------------------------------

    def _populate_fields(self) -> None:
        rule = self._rule
        assert rule is not None

        self._enabled_cb.setChecked(rule.enabled)
        action_idx = _ACTIONS.index(rule.action) if rule.action in _ACTIONS else 0
        self._action_combo.setCurrentIndex(action_idx)

        self._class_edit.setText(self._get_from_list(rule.conditions, "Class"))
        self._basetype_edit.setText(self._get_from_list(rule.conditions, "BaseType"))

        fs_raw = self._get_from_list(rule.actions, "SetFontSize")
        try:
            self._fontsize_spin.setValue(int(fs_raw.strip()) if fs_raw.strip() else 0)
        except ValueError:
            self._fontsize_spin.setValue(0)

        self._textcolor_edit.setText(self._get_from_list(rule.actions, "SetTextColor"))
        self._bordercolor_edit.setText(self._get_from_list(rule.actions, "SetBorderColor"))
        self._bgcolor_edit.setText(self._get_from_list(rule.actions, "SetBackgroundColor"))
        self._alert_edit.setText(self._get_from_list(rule.actions, "PlayAlertSound"))
        self._minimap_edit.setText(self._get_from_list(rule.actions, "MinimapIcon"))

    def _build_rule_from_fields(self) -> FilterRule:
        """Create an updated FilterRule from current field values.

        Starts from a deep-copy of self._rule so pre_lines, inline_comment,
        unknown_lines, and all unmanaged conditions/actions are preserved.
        """
        rule = copy.deepcopy(self._rule)

        rule.enabled = self._enabled_cb.isChecked()
        if self._action_combo.currentText() in _ACTIONS:
            rule.action = self._action_combo.currentText()

        rule.conditions = self._update_in_list(
            rule.conditions, "Class", self._class_edit.text()
        )
        rule.conditions = self._update_in_list(
            rule.conditions, "BaseType", self._basetype_edit.text()
        )

        fs_str = str(self._fontsize_spin.value()) if self._fontsize_spin.value() > 0 else ""
        rule.actions = self._update_in_list(rule.actions, "SetFontSize", fs_str)

        rule.actions = self._update_in_list(
            rule.actions, "SetTextColor", self._textcolor_edit.text()
        )
        rule.actions = self._update_in_list(
            rule.actions, "SetBorderColor", self._bordercolor_edit.text()
        )
        rule.actions = self._update_in_list(
            rule.actions, "SetBackgroundColor", self._bgcolor_edit.text()
        )
        rule.actions = self._update_in_list(
            rule.actions, "PlayAlertSound", self._alert_edit.text()
        )
        rule.actions = self._update_in_list(
            rule.actions, "MinimapIcon", self._minimap_edit.text()
        )

        return rule

    def _update_color_swatches(self) -> None:
        """Refresh all three colour swatches from current field text."""
        self._update_one_swatch(self._textcolor_swatch, self._textcolor_edit.text())
        self._update_one_swatch(self._bordercolor_swatch, self._bordercolor_edit.text())
        self._update_one_swatch(self._bgcolor_swatch, self._bgcolor_edit.text())

    @staticmethod
    def _update_one_swatch(swatch: QLabel, color_text: str) -> None:
        """Parse 'R G B [A]' text and apply background colour to *swatch*."""
        if not color_text.strip():
            swatch.setStyleSheet(
                "background: transparent; border: 1px solid #1e2435; border-radius: 2px;"
            )
            return
        try:
            vals = [max(0, min(255, int(p))) for p in color_text.strip().split()[:4]]
            while len(vals) < 4:
                vals.append(255)
            r, g, b, a = vals
            swatch.setStyleSheet(
                f"background: rgba({r},{g},{b},{a});"
                "border: 1px solid #334155; border-radius: 2px;"
            )
        except (ValueError, TypeError):
            swatch.setStyleSheet(
                "background: transparent;"
                "border: 1px dashed #ef4444; border-radius: 2px;"
            )

    def _update_preview(self) -> None:
        if self._rule is None:
            self._preview_text.setPlainText("")
            return

        rule = self._rule
        prefix = "" if rule.enabled else "# "
        lines = [f"{prefix}{rule.action}"]
        for key, value in rule.conditions:
            lines.append(f"    {key} {value}")
        for key, value in rule.actions:
            lines.append(f"    {key} {value}")
        for ul in rule.unknown_lines:
            lines.append(f"    {ul}")

        self._preview_text.setPlainText("\n".join(lines))

    def _update_title(self) -> None:
        if self._rule is None or not hasattr(self, "_title_lbl"):
            return
        n = self._index + 1 if self._index >= 0 else "?"
        action = self._rule.action
        disabled = "  ✕ 停用" if not self._rule.enabled else ""
        self._title_lbl.setText(f"規則 #{n}  —  {action}{disabled}")

    # ------------------------------------------------------------------
    # Slot
    # ------------------------------------------------------------------

    def _on_any_field_changed(self, *_) -> None:
        if self._loading:
            return
        if self._rule is None or self._index < 0:
            return

        updated_rule = self._build_rule_from_fields()
        self._rule = updated_rule
        self._update_preview()
        self._update_title()
        self.rule_changed.emit(self._index, updated_rule)
