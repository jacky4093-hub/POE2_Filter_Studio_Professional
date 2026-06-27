"""RuleDetailEditor — v7.0.0  (P13.8 Alert Sound Picker)

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
  - Colour fields gain a live colour-swatch preview label.
  - PlayAlertSound and MinimapIcon fields show a one-line format hint.

P13.6 colour picker:
  - Clicking a colour swatch opens QColorDialog (with alpha channel).
  - On accept: R G B A written back to the field + rule_changed emitted.
  - On cancel: field and emit are both unchanged.
  - _choose_color() is the testable hook for monkeypatching in tests.
  - Manual text entry still works; invalid values show dashed-red swatch.

P13.7 minimap icon picker:
  - Three QComboBox dropdowns (size / color / shape) beside the text field.
  - Changing a dropdown writes "{size} {color} {shape}" back to the text field
    and triggers rule_changed.
  - Typing valid text syncs the dropdowns; invalid text leaves them unchanged.
  - _mm_parse() is the module-level pure validator (testable without GUI).

P13.8 alert sound picker:
  - Two QSpinBox controls (Sound ID 0–16, Volume 0–300) beside the text field.
  - Changing either spin writes "{id} {vol}" back to the text field and triggers
    rule_changed.  If either value is 0 the field is cleared instead.
  - Typing valid text syncs the spinboxes; empty/invalid text resets both to 0.
  - _alert_parse() is the module-level pure validator (testable without GUI).
"""

from __future__ import annotations

import copy

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFormLayout,
    QGroupBox, QLabel, QCheckBox, QComboBox, QLineEdit, QPlainTextEdit,
    QSpinBox, QStackedWidget, QColorDialog,
)
from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtGui import QColor

from core.models import FilterRule


_ACTIONS = ["Show", "Hide", "Continue"]

# Default colours used when the text field is empty or invalid
_COLOR_DEFAULTS: dict[str, tuple[int, int, int, int]] = {
    "SetTextColor":       (255, 255, 255, 255),
    "SetBorderColor":     (0,   0,   0,   255),
    "SetBackgroundColor": (0,   0,   0,   180),
}

# MinimapIcon picker options
_MM_SIZES  = ["0", "1", "2"]
_MM_COLORS = [
    "Red", "Green", "Blue", "Brown", "White", "Yellow",
    "Cyan", "Grey", "Orange", "Pink", "Purple",
]
_MM_SHAPES = [
    "Circle", "Diamond", "Hexagon", "Square", "Star",
    "Triangle", "Cross", "Moon", "Raindrop", "Kite",
    "Pentagon", "UpsideDownHouse",
]


def _mm_parse(text: str) -> tuple[str, str, str] | None:
    """Parse MinimapIcon text into (size, color, shape), or None if invalid."""
    parts = text.strip().split()
    if len(parts) < 3:
        return None
    size, color, shape = parts[0], parts[1], parts[2]
    if size not in _MM_SIZES or color not in _MM_COLORS or shape not in _MM_SHAPES:
        return None
    return size, color, shape


def _alert_parse(text: str) -> tuple[int, int] | None:
    """Parse PlayAlertSound text into (sound_id, volume), or None if invalid."""
    parts = text.strip().split()
    if len(parts) < 2:
        return None
    try:
        sound_id = int(parts[0])
        volume   = int(parts[1])
    except ValueError:
        return None
    if not (0 <= sound_id <= 16):
        return None
    if not (0 <= volume <= 300):
        return None
    return sound_id, volume


class RuleDetailEditor(QWidget):
    """Form editor for one FilterRule.  Emits rule_changed(index, updated_rule)."""

    rule_changed = Signal(int, object)   # (index: int, rule: FilterRule)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RuleDetailEditor")

        self._rule: FilterRule | None = None
        self._index: int = -1
        self._loading: bool = False   # guards spurious rule_changed during set_rule
        self._mm_syncing: bool = False     # re-entrance guard for minimap sync
        self._alert_syncing: bool = False  # re-entrance guard for alert sound sync

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
        """Return (container_widget, QLineEdit, swatch_QLabel) for a colour field.

        The swatch is clickable: it has a PointingHand cursor and emits mouse
        press events that eventFilter() converts into a _on_swatch_clicked call.
        The tooltip (per-field text) is set by the caller after this returns.
        """
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
        swatch.setCursor(Qt.CursorShape.PointingHandCursor)
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

        # Colour fields: QLineEdit + clickable swatch
        tc_row, self._textcolor_edit, self._textcolor_swatch = self._make_color_row(
            "RuleDetailTextColor", "255 200 0 255"
        )
        self._textcolor_swatch.setToolTip("點選文字顏色")
        self._textcolor_swatch.installEventFilter(self)
        form.addRow("SetTextColor", tc_row)

        bc_row, self._bordercolor_edit, self._bordercolor_swatch = self._make_color_row(
            "RuleDetailBorderColor", "0 0 0 0"
        )
        self._bordercolor_swatch.setToolTip("點選邊框顏色")
        self._bordercolor_swatch.installEventFilter(self)
        form.addRow("SetBorderColor", bc_row)

        bg_row, self._bgcolor_edit, self._bgcolor_swatch = self._make_color_row(
            "RuleDetailBgColor", "0 0 0 180"
        )
        self._bgcolor_swatch.setToolTip("點選背景顏色")
        self._bgcolor_swatch.installEventFilter(self)
        form.addRow("SetBackgroundColor", bg_row)

        vlayout.addWidget(box)

        self._fontsize_spin.valueChanged.connect(self._on_any_field_changed)
        for edit in (self._textcolor_edit, self._bordercolor_edit, self._bgcolor_edit):
            edit.textChanged.connect(self._update_color_swatches)
            edit.editingFinished.connect(self._on_any_field_changed)

    # ------------------------------------------------------------------
    # Minimap picker sync
    # ------------------------------------------------------------------

    def _mm_sync_to_dropdowns(self) -> None:
        """Parse minimap text and update dropdowns; no-op if invalid."""
        if self._mm_syncing:
            return
        parsed = _mm_parse(self._minimap_edit.text())
        if parsed is None:
            return
        self._mm_syncing = True
        try:
            size, color, shape = parsed
            self._mm_size.setCurrentText(size)
            self._mm_color.setCurrentText(color)
            self._mm_shape.setCurrentText(shape)
        finally:
            self._mm_syncing = False

    def _mm_sync_from_dropdowns(self) -> None:
        """Write dropdown values back to minimap text and emit rule_changed."""
        if self._mm_syncing or self._rule is None:
            return
        self._mm_syncing = True
        try:
            size  = self._mm_size.currentText()
            color = self._mm_color.currentText()
            shape = self._mm_shape.currentText()
            self._minimap_edit.setText(f"{size} {color} {shape}")
        finally:
            self._mm_syncing = False
        # setText does not trigger editingFinished, so call the slot manually
        self._on_any_field_changed()

    # ------------------------------------------------------------------
    # Alert sound picker sync
    # ------------------------------------------------------------------

    def _alert_sync_to_spins(self) -> None:
        """Parse alert text and update spinboxes; reset to 0 if empty/invalid."""
        if self._alert_syncing:
            return
        text = self._alert_edit.text()
        parsed = _alert_parse(text) if text.strip() else None
        self._alert_syncing = True
        try:
            if parsed is not None:
                self._alert_id_spin.setValue(parsed[0])
                self._alert_vol_spin.setValue(parsed[1])
            else:
                self._alert_id_spin.setValue(0)
                self._alert_vol_spin.setValue(0)
        finally:
            self._alert_syncing = False

    def _alert_sync_from_spins(self) -> None:
        """Write spinbox values to alert text and emit rule_changed.
        Either value == 0 → clear text (treat as not set)."""
        if self._alert_syncing or self._rule is None:
            return
        self._alert_syncing = True
        try:
            sid = self._alert_id_spin.value()
            vol = self._alert_vol_spin.value()
            if sid == 0 or vol == 0:
                self._alert_edit.setText("")
            else:
                self._alert_edit.setText(f"{sid} {vol}")
        finally:
            self._alert_syncing = False
        # setText does not trigger editingFinished, so call the slot manually
        self._on_any_field_changed()

    def _build_audio_card(self, vlayout: QVBoxLayout) -> None:
        box, form = self._make_card("音效")

        # Text input (manual entry preserved)
        self._alert_edit = QLineEdit()
        self._alert_edit.setObjectName("RuleDetailAlertSound")
        self._alert_edit.setPlaceholderText("1 300")
        form.addRow("PlayAlertSound", self._alert_edit)

        # Quick-pick spinboxes: Sound ID / Volume
        picker = QWidget()
        picker_layout = QHBoxLayout(picker)
        picker_layout.setContentsMargins(0, 0, 0, 0)
        picker_layout.setSpacing(4)

        self._alert_id_spin = QSpinBox()
        self._alert_id_spin.setObjectName("AlertSoundIdSpin")
        self._alert_id_spin.setRange(0, 16)
        self._alert_id_spin.setSpecialValueText("—")
        self._alert_id_spin.setToolTip("音效 ID（0 = 不設定，範圍 0–16）")

        vol_lbl = QLabel("音量")
        self._alert_vol_spin = QSpinBox()
        self._alert_vol_spin.setObjectName("AlertVolumeSpin")
        self._alert_vol_spin.setRange(0, 300)
        self._alert_vol_spin.setSpecialValueText("—")
        self._alert_vol_spin.setToolTip("音量（0 = 不設定，範圍 0–300）")

        picker_layout.addWidget(self._alert_id_spin)
        picker_layout.addWidget(vol_lbl)
        picker_layout.addWidget(self._alert_vol_spin)
        picker_layout.addStretch()
        form.addRow("快速選擇", picker)

        # Format hint
        self._alert_hint = QLabel("格式：音效ID 音量（例：1 300）")
        self._alert_hint.setObjectName("RuleDetailHintLabel")
        form.addRow("", self._alert_hint)

        vlayout.addWidget(box)

        # Connections
        self._alert_edit.textChanged.connect(self._alert_sync_to_spins)
        self._alert_edit.editingFinished.connect(self._on_any_field_changed)
        self._alert_id_spin.valueChanged.connect(self._alert_sync_from_spins)
        self._alert_vol_spin.valueChanged.connect(self._alert_sync_from_spins)

    def _build_minimap_card(self, vlayout: QVBoxLayout) -> None:
        box, form = self._make_card("小地圖")

        # Text input (manual entry preserved)
        self._minimap_edit = QLineEdit()
        self._minimap_edit.setObjectName("RuleDetailMinimapIcon")
        self._minimap_edit.setPlaceholderText("1 Red Circle")
        form.addRow("MinimapIcon", self._minimap_edit)

        # Quick-pick dropdowns: Size / Color / Shape
        picker = QWidget()
        picker_layout = QHBoxLayout(picker)
        picker_layout.setContentsMargins(0, 0, 0, 0)
        picker_layout.setSpacing(4)

        self._mm_size = QComboBox()
        self._mm_size.setObjectName("MinimapSizeCombo")
        self._mm_size.addItems(_MM_SIZES)
        self._mm_size.setToolTip("大小")

        self._mm_color = QComboBox()
        self._mm_color.setObjectName("MinimapColorCombo")
        self._mm_color.addItems(_MM_COLORS)
        self._mm_color.setToolTip("顏色")

        self._mm_shape = QComboBox()
        self._mm_shape.setObjectName("MinimapShapeCombo")
        self._mm_shape.addItems(_MM_SHAPES)
        self._mm_shape.setToolTip("形狀")

        picker_layout.addWidget(self._mm_size)
        picker_layout.addWidget(self._mm_color, stretch=1)
        picker_layout.addWidget(self._mm_shape, stretch=1)
        form.addRow("快速選擇", picker)

        # Format hint
        self._minimap_hint = QLabel("格式：大小 顏色 形狀（例：1 Red Circle）")
        self._minimap_hint.setObjectName("RuleDetailHintLabel")
        form.addRow("", self._minimap_hint)

        vlayout.addWidget(box)

        # Connections
        self._minimap_edit.textChanged.connect(self._mm_sync_to_dropdowns)
        self._minimap_edit.editingFinished.connect(self._on_any_field_changed)
        for combo in (self._mm_size, self._mm_color, self._mm_shape):
            combo.currentTextChanged.connect(self._mm_sync_from_dropdowns)

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

    # ------------------------------------------------------------------
    # Colour picker — event filter + dialog hook
    # ------------------------------------------------------------------

    def eventFilter(self, watched, event) -> bool:
        """Route swatch mouse-press events to _on_swatch_clicked."""
        if event.type() == QEvent.Type.MouseButtonPress:
            if watched is self._textcolor_swatch:
                self._on_swatch_clicked("SetTextColor", self._textcolor_edit)
                return True
            if watched is self._bordercolor_swatch:
                self._on_swatch_clicked("SetBorderColor", self._bordercolor_edit)
                return True
            if watched is self._bgcolor_swatch:
                self._on_swatch_clicked("SetBackgroundColor", self._bgcolor_edit)
                return True
        return super().eventFilter(watched, event)

    def _on_swatch_clicked(self, field_key: str, edit: QLineEdit) -> None:
        """Open colour picker; on accept write RGBA back to *edit* and emit."""
        color = self._choose_color(field_key, edit.text())
        if not color.isValid():
            return  # user cancelled — no change, no emit
        r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()
        edit.setText(f"{r} {g} {b} {a}")
        # setText → textChanged → _update_color_swatches (swatch live update)
        # editingFinished is NOT triggered by setText, so call the slot manually
        self._on_any_field_changed()

    def _choose_color(self, field_key: str, current_text: str) -> QColor:
        """Open QColorDialog and return the chosen QColor (invalid if cancelled).

        Extracted as its own method so tests can monkeypatch it without
        opening a real GUI dialog.
        """
        initial = self._parse_rgba_to_qcolor(current_text, field_key)
        return QColorDialog.getColor(
            initial,
            self,
            "選擇顏色",
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )

    def _parse_rgba_to_qcolor(self, text: str, field_key: str) -> QColor:
        """Parse 'R G B [A]' text into QColor; fall back to field default."""
        default = _COLOR_DEFAULTS.get(field_key, (255, 255, 255, 255))
        if text.strip():
            try:
                vals = [max(0, min(255, int(p))) for p in text.strip().split()[:4]]
                while len(vals) < 4:
                    vals.append(255)
                r, g, b, a = vals
                return QColor(r, g, b, a)
            except (ValueError, TypeError):
                pass
        r, g, b, a = default
        return QColor(r, g, b, a)

    # ------------------------------------------------------------------
    # Colour swatch live preview
    # ------------------------------------------------------------------

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
