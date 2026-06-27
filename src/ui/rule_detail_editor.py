"""RuleDetailEditor — v2.3.0

Right-side form editor for a single FilterRule.

Design contract:
  - set_rule(rule, index) populates all fields WITHOUT emitting rule_changed.
  - Any subsequent user interaction emits rule_changed(index, updated_rule).
  - updated_rule is built from the current field values on top of a deep-copy
    of the last-loaded rule, so all unmanaged fields (pre_lines, inline_comment,
    unknown_lines, and unrecognised conditions/actions) are preserved.
  - flush_pending() is a no-op (no debounce timer).

Signal guard: _loading=True during set_rule() blocks _on_any_field_changed.
QLineEdit uses editingFinished (fires on Enter/focus-loss, not on setText).
QCheckBox / QComboBox use state/text-change signals guarded by _loading.
"""

from __future__ import annotations

import copy

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFormLayout,
    QLabel, QCheckBox, QComboBox, QLineEdit, QPlainTextEdit,
    QStackedWidget,
)
from PySide6.QtCore import Signal, Qt

from core.models import FilterRule


_ACTIONS = ["Show", "Hide", "Continue"]


# ---------------------------------------------------------------------------
# RuleDetailEditor
# ---------------------------------------------------------------------------

class RuleDetailEditor(QWidget):
    """Form editor for one FilterRule.  Emits rule_changed(index, updated_rule)."""

    rule_changed = Signal(int, object)   # (index: int, rule: FilterRule)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RuleDetailEditor")

        self._rule: FilterRule | None = None
        self._index: int = -1
        self._loading: bool = False   # guards against spurious rule_changed during set_rule

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

        # ── Page 0: empty ─────────────────────────────────────────────
        self._empty_page = QWidget()
        ep_layout = QVBoxLayout(self._empty_page)
        empty_lbl = QLabel("選擇規則以編輯")
        empty_lbl.setObjectName("RuleDetailEmptyLabel")
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ep_layout.addStretch()
        ep_layout.addWidget(empty_lbl)
        ep_layout.addStretch()
        self._stacked.addWidget(self._empty_page)

        # ── Page 1: form (scrollable) ─────────────────────────────────
        scroll = QScrollArea()
        scroll.setObjectName("RuleDetailScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("RuleDetailContent")
        self._editor_page = scroll

        vlayout = QVBoxLayout(content)
        vlayout.setContentsMargins(10, 10, 10, 10)
        vlayout.setSpacing(8)

        self._build_sections(vlayout)
        vlayout.addStretch()

        scroll.setWidget(content)
        self._stacked.addWidget(scroll)

    def _build_sections(self, vlayout: QVBoxLayout) -> None:
        # ── 基本設定 ──────────────────────────────────────────────────
        vlayout.addWidget(self._section_hdr("基本設定"))
        basic = QFormLayout()
        basic.setSpacing(6)
        basic.setContentsMargins(0, 0, 0, 0)

        self._enabled_cb = QCheckBox()
        self._enabled_cb.setObjectName("RuleDetailEnabled")
        basic.addRow("啟用", self._enabled_cb)

        self._action_combo = QComboBox()
        self._action_combo.setObjectName("RuleDetailAction")
        self._action_combo.addItems(_ACTIONS)
        basic.addRow("動作", self._action_combo)

        vlayout.addLayout(basic)

        # ── 條件 ─────────────────────────────────────────────────────
        vlayout.addWidget(self._section_hdr("條件"))
        cond = QFormLayout()
        cond.setSpacing(6)
        cond.setContentsMargins(0, 0, 0, 0)

        self._class_edit = QLineEdit()
        self._class_edit.setObjectName("RuleDetailClass")
        self._class_edit.setPlaceholderText('"Currency" "Gems" …')
        cond.addRow("Class", self._class_edit)

        self._basetype_edit = QLineEdit()
        self._basetype_edit.setObjectName("RuleDetailBaseType")
        self._basetype_edit.setPlaceholderText('"Divine Orb" …')
        cond.addRow("BaseType", self._basetype_edit)

        vlayout.addLayout(cond)

        # ── 外觀 ─────────────────────────────────────────────────────
        vlayout.addWidget(self._section_hdr("外觀"))
        appear = QFormLayout()
        appear.setSpacing(6)
        appear.setContentsMargins(0, 0, 0, 0)

        self._fontsize_edit = QLineEdit()
        self._fontsize_edit.setObjectName("RuleDetailFontSize")
        self._fontsize_edit.setPlaceholderText("36")
        appear.addRow("SetFontSize", self._fontsize_edit)

        self._textcolor_edit = QLineEdit()
        self._textcolor_edit.setObjectName("RuleDetailTextColor")
        self._textcolor_edit.setPlaceholderText("255 200 0 255")
        appear.addRow("SetTextColor", self._textcolor_edit)

        self._bordercolor_edit = QLineEdit()
        self._bordercolor_edit.setObjectName("RuleDetailBorderColor")
        self._bordercolor_edit.setPlaceholderText("0 0 0 0")
        appear.addRow("SetBorderColor", self._bordercolor_edit)

        self._bgcolor_edit = QLineEdit()
        self._bgcolor_edit.setObjectName("RuleDetailBgColor")
        self._bgcolor_edit.setPlaceholderText("0 0 0 180")
        appear.addRow("SetBackgroundColor", self._bgcolor_edit)

        vlayout.addLayout(appear)

        # ── 音效 ─────────────────────────────────────────────────────
        vlayout.addWidget(self._section_hdr("音效"))
        audio = QFormLayout()
        audio.setSpacing(6)
        audio.setContentsMargins(0, 0, 0, 0)

        self._alert_edit = QLineEdit()
        self._alert_edit.setObjectName("RuleDetailAlertSound")
        self._alert_edit.setPlaceholderText("1 300")
        audio.addRow("PlayAlertSound", self._alert_edit)

        vlayout.addLayout(audio)

        # ── 小地圖 ───────────────────────────────────────────────────
        vlayout.addWidget(self._section_hdr("小地圖"))
        minimap = QFormLayout()
        minimap.setSpacing(6)
        minimap.setContentsMargins(0, 0, 0, 0)

        self._minimap_edit = QLineEdit()
        self._minimap_edit.setObjectName("RuleDetailMinimapIcon")
        self._minimap_edit.setPlaceholderText("1 Red Circle")
        minimap.addRow("MinimapIcon", self._minimap_edit)

        vlayout.addLayout(minimap)

        # ── 規則預覽（唯讀）──────────────────────────────────────────
        vlayout.addWidget(self._section_hdr("規則預覽（唯讀）"))
        self._preview_text = QPlainTextEdit()
        self._preview_text.setObjectName("RuleDetailPreview")
        self._preview_text.setReadOnly(True)
        self._preview_text.setMaximumHeight(130)
        vlayout.addWidget(self._preview_text)

        # ── Wire up signals ───────────────────────────────────────────
        self._enabled_cb.stateChanged.connect(self._on_any_field_changed)
        self._action_combo.currentTextChanged.connect(self._on_any_field_changed)

        for edit in (
            self._class_edit, self._basetype_edit,
            self._fontsize_edit, self._textcolor_edit,
            self._bordercolor_edit, self._bgcolor_edit,
            self._alert_edit, self._minimap_edit,
        ):
            edit.editingFinished.connect(self._on_any_field_changed)

    @staticmethod
    def _section_hdr(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("RuleDetailSectionHeader")
        return lbl

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

        # Basic
        self._enabled_cb.setChecked(rule.enabled)
        action_idx = _ACTIONS.index(rule.action) if rule.action in _ACTIONS else 0
        self._action_combo.setCurrentIndex(action_idx)

        # Conditions
        self._class_edit.setText(self._get_from_list(rule.conditions, "Class"))
        self._basetype_edit.setText(self._get_from_list(rule.conditions, "BaseType"))

        # Actions
        self._fontsize_edit.setText(self._get_from_list(rule.actions, "SetFontSize"))
        self._textcolor_edit.setText(self._get_from_list(rule.actions, "SetTextColor"))
        self._bordercolor_edit.setText(self._get_from_list(rule.actions, "SetBorderColor"))
        self._bgcolor_edit.setText(self._get_from_list(rule.actions, "SetBackgroundColor"))
        self._alert_edit.setText(self._get_from_list(rule.actions, "PlayAlertSound"))
        self._minimap_edit.setText(self._get_from_list(rule.actions, "MinimapIcon"))

    def _build_rule_from_fields(self) -> FilterRule:
        """Create an updated FilterRule from current field values.

        Starts from a deep-copy of self._rule so that pre_lines, inline_comment,
        unknown_lines, and all unmanaged conditions/actions are preserved.
        """
        rule = copy.deepcopy(self._rule)

        # Basic
        rule.enabled = self._enabled_cb.isChecked()
        if self._action_combo.currentText() in _ACTIONS:
            rule.action = self._action_combo.currentText()

        # Conditions (only managed keys; others are untouched)
        rule.conditions = self._update_in_list(
            rule.conditions, "Class", self._class_edit.text()
        )
        rule.conditions = self._update_in_list(
            rule.conditions, "BaseType", self._basetype_edit.text()
        )

        # Actions
        rule.actions = self._update_in_list(
            rule.actions, "SetFontSize", self._fontsize_edit.text()
        )
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

    def _update_preview(self) -> None:
        """Regenerate the plain-text rule preview from self._rule."""
        if self._rule is None:
            self._preview_text.setPlainText("")
            return

        rule = self._rule
        prefix = "" if rule.enabled else "#"
        lines = [f"{prefix}{rule.action}"]

        for key, value in rule.conditions:
            lines.append(f"    {prefix}{key} {value}")
        for key, value in rule.actions:
            lines.append(f"    {prefix}{key} {value}")

        self._preview_text.setPlainText("\n".join(lines))

    # ------------------------------------------------------------------
    # Slot
    # ------------------------------------------------------------------

    def _on_any_field_changed(self, *_) -> None:
        """Called whenever a managed field is changed by the user."""
        if self._loading:
            return
        if self._rule is None or self._index < 0:
            return

        updated_rule = self._build_rule_from_fields()
        self._rule = updated_rule      # keep local copy in sync for subsequent edits
        self._update_preview()
        self.rule_changed.emit(self._index, updated_rule)
