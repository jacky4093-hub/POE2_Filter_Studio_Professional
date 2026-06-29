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
import math

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFormLayout,
    QGroupBox, QLabel, QCheckBox, QComboBox, QLineEdit, QPlainTextEdit,
    QSpinBox, QStackedWidget, QColorDialog, QPushButton, QButtonGroup,
)
from PySide6.QtCore import Signal, Qt, QEvent, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF

from core.models import FilterRule
from widgets.visual_effect_picker import VisualEffectPicker
from widgets.minimap_icon_grid import MinimapIconGrid
from widgets.color_swatch_picker import ColorSwatchPicker


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


def _effect_parse(text: str) -> tuple[str, bool] | None:
    """Parse PlayEffect text into (color, is_temp), or None if invalid."""
    parts = text.strip().split()
    if not parts:
        return None
    color = parts[0]
    if color not in _MM_COLORS:
        return None
    is_temp = len(parts) >= 2 and parts[1].lower() == "temp"
    return color, is_temp


# RGB triples for each POE2 minimap colour name
_MM_PREVIEW_COLORS: dict[str, tuple[int, int, int]] = {
    "Red":    (220,  60,  60),
    "Green":  ( 60, 200,  60),
    "Blue":   ( 60, 120, 220),
    "Brown":  (150,  90,  40),
    "White":  (230, 230, 230),
    "Yellow": (220, 200,  40),
    "Cyan":   ( 40, 200, 200),
    "Grey":   (140, 140, 140),
    "Orange": (220, 140,  40),
    "Pink":   (220, 120, 170),
    "Purple": (150,  60, 200),
}


class MinimapPreviewWidget(QWidget):
    """Renders a POE2-style minimap icon: shape + colour + size.

    Call set_icon(size, color, shape) to display an icon, or clear() for
    the empty-state placeholder.  All drawing is done in paintEvent so
    there are no external image assets required.
    """

    # POE2 size-0 is the *largest* icon on the minimap
    _RADII: dict[str, float] = {"0": 15.0, "1": 12.0, "2": 9.0}
    _DEFAULT_RADIUS = 12.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MinimapPreviewWidget")
        self.setFixedSize(54, 54)
        self._size:  str = ""
        self._color: str = ""
        self._shape: str = ""

    def set_icon(self, size: str, color: str, shape: str) -> None:
        self._size  = size
        self._color = color
        self._shape = shape
        self.update()

    def clear(self) -> None:
        self._size  = ""
        self._color = ""
        self._shape = ""
        self.update()

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())
        cx, cy = w / 2.0, h / 2.0

        painter.fillRect(self.rect(), QColor(7, 9, 15))

        if not self._size:
            # Empty-state: dashed circle placeholder
            pen = QPen(QColor(40, 60, 100, 160))
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(cx - 13, cy - 13, 26, 26))
            painter.end()
            return

        r     = self._RADII.get(self._size, self._DEFAULT_RADIUS)
        rgb   = _MM_PREVIEW_COLORS.get(self._color, (180, 180, 180))
        fill  = QColor(*rgb)
        edge  = QColor(
            min(rgb[0] + 60, 255),
            min(rgb[1] + 60, 255),
            min(rgb[2] + 60, 255),
        )

        painter.setPen(QPen(edge, 1.2))
        painter.setBrush(fill)
        self._draw_shape(painter, cx, cy, r, self._shape.lower())
        painter.end()

    @staticmethod
    def _draw_shape(
        painter: QPainter,
        cx: float, cy: float, r: float,
        shape: str,
    ) -> None:
        if shape == "circle":
            painter.drawEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))

        elif shape == "square":
            painter.drawRect(QRectF(cx - r, cy - r, 2 * r, 2 * r))

        elif shape == "diamond":
            painter.drawPolygon(QPolygonF([
                QPointF(cx,     cy - r),
                QPointF(cx + r, cy),
                QPointF(cx,     cy + r),
                QPointF(cx - r, cy),
            ]))

        elif shape == "triangle":
            hr = r * math.sqrt(3) / 2
            painter.drawPolygon(QPolygonF([
                QPointF(cx,      cy - r),
                QPointF(cx + hr, cy + r / 2),
                QPointF(cx - hr, cy + r / 2),
            ]))

        elif shape == "star":
            outer, inner = r, r * 0.42
            pts = [
                QPointF(
                    cx + (outer if i % 2 == 0 else inner) * math.cos(math.pi * i / 5 - math.pi / 2),
                    cy + (outer if i % 2 == 0 else inner) * math.sin(math.pi * i / 5 - math.pi / 2),
                )
                for i in range(10)
            ]
            painter.drawPolygon(QPolygonF(pts))

        elif shape == "cross":
            arm = r * 0.38
            painter.drawRect(QRectF(cx - arm, cy - r,   2 * arm, 2 * r))
            painter.drawRect(QRectF(cx - r,   cy - arm, 2 * r,   2 * arm))

        elif shape == "hexagon":
            pts = [
                QPointF(
                    cx + r * math.cos(math.pi * i / 3 - math.pi / 6),
                    cy + r * math.sin(math.pi * i / 3 - math.pi / 6),
                )
                for i in range(6)
            ]
            painter.drawPolygon(QPolygonF(pts))

        elif shape == "pentagon":
            pts = [
                QPointF(
                    cx + r * math.cos(2 * math.pi * i / 5 - math.pi / 2),
                    cy + r * math.sin(2 * math.pi * i / 5 - math.pi / 2),
                )
                for i in range(5)
            ]
            painter.drawPolygon(QPolygonF(pts))

        elif shape == "moon":
            # Crescent via path subtraction
            full = QPainterPath()
            full.addEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))
            cut = QPainterPath()
            cut.addEllipse(QRectF(cx - r * 0.1, cy - r, 2 * r * 0.88, 2 * r * 0.88))
            painter.drawPath(full.subtracted(cut))

        elif shape == "kite":
            painter.drawPolygon(QPolygonF([
                QPointF(cx,           cy - r),
                QPointF(cx + r * 0.7, cy),
                QPointF(cx,           cy + r * 0.5),
                QPointF(cx - r * 0.7, cy),
            ]))

        elif shape == "raindrop":
            path = QPainterPath()
            path.moveTo(cx, cy + r)
            path.quadTo(cx + r * 0.85, cy,        cx,            cy - r * 0.5)
            path.quadTo(cx - r * 0.85, cy,        cx,            cy + r)
            painter.drawPath(path)

        elif shape == "upsidedownhouse":
            painter.drawPolygon(QPolygonF([
                QPointF(cx - r,       cy - r * 0.25),
                QPointF(cx + r,       cy - r * 0.25),
                QPointF(cx + r * 0.7, cy + r * 0.4),
                QPointF(cx,           cy + r),
                QPointF(cx - r * 0.7, cy + r * 0.4),
            ]))

        else:
            # Unknown shape → circle fallback
            painter.drawEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))


class RuleDetailEditor(QWidget):
    """Form editor for one FilterRule.  Emits rule_changed(index, updated_rule)."""

    rule_changed = Signal(int, object)   # (index: int, rule: FilterRule)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RuleDetailEditor")

        self._rule: FilterRule | None = None
        self._index: int = -1
        self._loading: bool = False   # guards spurious rule_changed during set_rule
        self._mm_syncing: bool = False      # re-entrance guard for minimap sync
        self._alert_syncing: bool = False   # re-entrance guard for alert sound sync
        self._effect_syncing: bool = False  # re-entrance guard for PlayEffect sync

        # P21.5 — 中文 Alias 整合服務（可選，失敗不影響編輯器）
        self._alias_svc = None
        try:
            from core.rule_editor_alias import RuleEditorAliasService
            self._alias_svc = RuleEditorAliasService()
        except Exception:
            pass

        # P22.2 — 圖形化條件建立器（可選，失敗不影響編輯器）
        self._cond_builder = None

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
            self._update_raw_filter()
            self._update_title()
        finally:
            self._loading = False
        self._tab_bar_widget.setVisible(True)
        self._tab1_btn.setChecked(True)   # always reset to Rule Editor tab
        self._stacked.setCurrentWidget(self._editor_page)

    def clear(self) -> None:
        """Return to the empty-state page."""
        self._rule = None
        self._index = -1
        self._preview_text.setPlainText("")
        self._raw_filter_text.setPlainText("")
        self._tab_bar_widget.setVisible(False)
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

        # Tab bar is added first; pages are referenced by the button lambdas
        # at call-time (not definition-time), so order is safe.
        self._tab_bar_widget = self._build_tab_bar()
        self._tab_bar_widget.setVisible(False)
        root.addWidget(self._tab_bar_widget)

        root.addWidget(self._stacked, stretch=1)

        self._build_empty_page()
        self._build_editor_page()
        self._build_raw_filter_page()

    # ── Tab bar (shown when a rule is loaded) ─────────────────────────

    def _build_tab_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("RuleDetailTabBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 6, 8, 0)
        layout.setSpacing(4)

        self._tab1_btn = QPushButton("規則編輯")
        self._tab1_btn.setObjectName("RuleDetailTabBtn")
        self._tab1_btn.setCheckable(True)

        self._tab2_btn = QPushButton("原始內容")
        self._tab2_btn.setObjectName("RuleDetailTabBtn")
        self._tab2_btn.setCheckable(True)

        self._tab_btn_group = QButtonGroup(bar)
        self._tab_btn_group.setExclusive(True)
        self._tab_btn_group.addButton(self._tab1_btn)
        self._tab_btn_group.addButton(self._tab2_btn)

        # Set initial state without firing signals (pages don't exist yet)
        self._tab1_btn.blockSignals(True)
        self._tab1_btn.setChecked(True)
        self._tab1_btn.blockSignals(False)

        layout.addWidget(self._tab1_btn)
        layout.addWidget(self._tab2_btn)
        layout.addStretch()

        # Connections: page attributes resolved at call-time, not here
        self._tab1_btn.toggled.connect(
            lambda checked: self._stacked.setCurrentWidget(self._editor_page)
            if checked else None
        )
        self._tab2_btn.toggled.connect(
            lambda checked: self._stacked.setCurrentWidget(self._raw_filter_page)
            if checked else None
        )

        return bar

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
        vlayout.setContentsMargins(12, 4, 12, 12)
        vlayout.setSpacing(8)

        self._build_title_bar(vlayout)
        self._build_basic_card(vlayout)
        self._build_condition_card(vlayout)
        self._build_condition_builder_card(vlayout)   # P22.2
        self._build_appearance_card(vlayout)
        self._build_effect_card(vlayout)    # P19.4A.1: separated from 音效
        self._build_minimap_card(vlayout)
        self._build_audio_card(vlayout)
        vlayout.addStretch()

        self._build_preview_card()  # hidden widget for test compatibility (P19.3B)
        scroll.setWidget(content)
        self._stacked.addWidget(scroll)

    # ── Page 2: Raw Filter (read-only) ───────────────────────────────

    def _build_raw_filter_page(self) -> None:
        page = QWidget()
        page.setObjectName("RuleDetailRawPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(0)

        self._raw_filter_text = QPlainTextEdit()
        self._raw_filter_text.setObjectName("RuleDetailRawFilter")
        self._raw_filter_text.setReadOnly(True)
        self._raw_filter_text.setPlaceholderText("（尚未選取規則）")
        layout.addWidget(self._raw_filter_text)

        self._raw_filter_page = page
        self._stacked.addWidget(page)

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
        form.setSpacing(8)
        form.setContentsMargins(10, 6, 10, 10)
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

        # P21.5 — 中文別名補全（可選）
        self._class_completer = None
        self._basetype_completer = None
        try:
            from widgets.alias_completer import AliasCompleter
            self._class_completer = AliasCompleter(self._class_edit, parent=self)
            self._basetype_completer = AliasCompleter(self._basetype_edit, parent=self)
            self._basetype_completer.completed.connect(self._on_basetype_completed)
            self._class_completer.completed.connect(self._on_class_completed)
        except Exception:
            pass

        # 中文解析在 _on_any_field_changed 前執行（訊號連接順序即執行順序）
        self._class_edit.editingFinished.connect(self._resolve_class_alias)
        self._basetype_edit.editingFinished.connect(self._resolve_basetype_alias)
        self._class_edit.editingFinished.connect(self._on_any_field_changed)
        self._basetype_edit.editingFinished.connect(self._on_any_field_changed)

    # ------------------------------------------------------------------
    # P22.2 — ConditionBuilderWidget 整合
    # ------------------------------------------------------------------

    def _build_condition_builder_card(self, vlayout: QVBoxLayout) -> None:
        """P22.2: 在「條件」卡片下方插入圖形化條件建立器。"""
        box = QGroupBox("基本條件")
        box.setObjectName("ConditionBuilderCard")
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(6, 4, 6, 6)
        box_layout.setSpacing(0)

        try:
            from ui.condition_builder_widget import ConditionBuilderWidget
            self._cond_builder = ConditionBuilderWidget(
                alias_svc=self._alias_svc, parent=box
            )
            self._cond_builder.setMinimumHeight(180)
            self._cond_builder.setMaximumHeight(300)
            box_layout.addWidget(self._cond_builder)
            self._cond_builder.conditions_changed.connect(self._on_cond_builder_changed)
        except Exception:
            self._cond_builder = None

        vlayout.addWidget(box)

    def _on_cond_builder_changed(self, new_conditions: list) -> None:
        """P22.2: Widget 條件改變 → 同步 Class/BaseType 文字欄位 → 觸發 rule update。"""
        if self._loading or self._rule is None:
            return
        # 同步 Class / BaseType 文字欄位（backward compat，靜默設定）
        class_val    = self._get_from_list(new_conditions, "Class")
        basetype_val = self._get_from_list(new_conditions, "BaseType")
        self._class_edit.blockSignals(True)
        self._basetype_edit.blockSignals(True)
        self._class_edit.setText(class_val)
        self._basetype_edit.setText(basetype_val)
        self._class_edit.blockSignals(False)
        self._basetype_edit.blockSignals(False)
        if self._alias_svc is not None:
            self._class_edit.setToolTip(
                self._alias_svc.tooltip_class(class_val) or ""
            )
            self._basetype_edit.setToolTip(
                self._alias_svc.tooltip_basetype(basetype_val) or ""
            )
        self._on_any_field_changed()

    # ------------------------------------------------------------------
    # P21.5 — 中文 Alias 解析（條件欄位）
    # ------------------------------------------------------------------

    def _resolve_basetype_alias(self) -> None:
        """editingFinished 時將 BaseType 欄位的中文輸入解析為英文。"""
        if self._alias_svc is None:
            return
        text = self._basetype_edit.text()
        resolved = self._alias_svc.resolve_filter_value(text, "BaseType")
        if resolved != text:
            self._basetype_edit.blockSignals(True)
            self._basetype_edit.setText(resolved)
            self._basetype_edit.blockSignals(False)
        tt = self._alias_svc.tooltip_basetype(self._basetype_edit.text())
        self._basetype_edit.setToolTip(tt or "")
        # P22.2: 同步文字欄位 → ConditionBuilderWidget
        if self._cond_builder is not None:
            from core.condition_builder import ConditionValue
            self._cond_builder.update_condition(
                ConditionValue(key="BaseType", op="", value=self._basetype_edit.text())
            )

    def _resolve_class_alias(self) -> None:
        """editingFinished 時將 Class 欄位的中文輸入解析為英文。"""
        if self._alias_svc is None:
            return
        text = self._class_edit.text()
        resolved = self._alias_svc.resolve_filter_value(text, "Class")
        if resolved != text:
            self._class_edit.blockSignals(True)
            self._class_edit.setText(resolved)
            self._class_edit.blockSignals(False)
        tt = self._alias_svc.tooltip_class(self._class_edit.text())
        self._class_edit.setToolTip(tt or "")
        # P22.2: 同步文字欄位 → ConditionBuilderWidget
        if self._cond_builder is not None:
            from core.condition_builder import ConditionValue
            self._cond_builder.update_condition(
                ConditionValue(key="Class", op="", value=self._class_edit.text())
            )

    def _on_basetype_completed(self, en_name: str) -> None:
        """AliasCompleter 選取後，將英文物品名稱格式化為 filter 引號格式。"""
        quoted = f'"{en_name}"'
        self._basetype_edit.blockSignals(True)
        self._basetype_edit.setText(quoted)
        self._basetype_edit.blockSignals(False)
        if self._alias_svc is not None:
            tt = self._alias_svc.tooltip_basetype(quoted)
            self._basetype_edit.setToolTip(tt or "")
        # P22.2: 同步 → ConditionBuilderWidget
        if self._cond_builder is not None:
            from core.condition_builder import ConditionValue
            self._cond_builder.update_condition(
                ConditionValue(key="BaseType", op="", value=quoted)
            )

    def _on_class_completed(self, en_name: str) -> None:
        """AliasCompleter 選取後，將英文分類名稱格式化為 filter 引號格式。"""
        quoted = f'"{en_name}"'
        self._class_edit.blockSignals(True)
        self._class_edit.setText(quoted)
        self._class_edit.blockSignals(False)
        if self._alias_svc is not None:
            tt = self._alias_svc.tooltip_class(quoted)
            self._class_edit.setToolTip(tt or "")
        # P22.2: 同步 → ConditionBuilderWidget
        if self._cond_builder is not None:
            from core.condition_builder import ConditionValue
            self._cond_builder.update_condition(
                ConditionValue(key="Class", op="", value=quoted)
            )

    def _build_appearance_card(self, vlayout: QVBoxLayout) -> None:
        box, form = self._make_card("外觀")

        # SetFontSize → QSpinBox (0 = "—" / not set)
        self._fontsize_spin = QSpinBox()
        self._fontsize_spin.setObjectName("RuleDetailFontSize")
        self._fontsize_spin.setRange(0, 60)
        self._fontsize_spin.setSpecialValueText("—")
        form.addRow("字體大小", self._fontsize_spin)

        # ── 3 colour pickers (P19.3C: compact single row) ──────────────
        # Full ColorSwatchPicker objects kept for backward-compat attr aliases
        # (_edit, _swatch, _btn). _edit and _btn are hidden so each picker
        # collapses to swatch-only display inside the compact row.
        self._textcolor_picker = ColorSwatchPicker(
            "RuleDetailTextColor", "255 200 0 255", "ColorPickTextBtn"
        )
        self._textcolor_edit   = self._textcolor_picker._edit
        self._textcolor_swatch = self._textcolor_picker._swatch
        self._textcolor_btn    = self._textcolor_picker._btn
        self._textcolor_picker._edit.hide()
        self._textcolor_picker._btn.hide()
        self._textcolor_swatch.setToolTip("點選文字顏色預覽塊開啟選色器")
        self._textcolor_swatch.installEventFilter(self)
        self._textcolor_btn.clicked.connect(
            lambda: self._on_swatch_clicked("SetTextColor", self._textcolor_edit)
        )

        self._bordercolor_picker = ColorSwatchPicker(
            "RuleDetailBorderColor", "0 0 0 0", "ColorPickBorderBtn"
        )
        self._bordercolor_edit   = self._bordercolor_picker._edit
        self._bordercolor_swatch = self._bordercolor_picker._swatch
        self._bordercolor_btn    = self._bordercolor_picker._btn
        self._bordercolor_picker._edit.hide()
        self._bordercolor_picker._btn.hide()
        self._bordercolor_swatch.setToolTip("點選邊框顏色預覽塊開啟選色器")
        self._bordercolor_swatch.installEventFilter(self)
        self._bordercolor_btn.clicked.connect(
            lambda: self._on_swatch_clicked("SetBorderColor", self._bordercolor_edit)
        )

        self._bgcolor_picker = ColorSwatchPicker(
            "RuleDetailBgColor", "0 0 0 180", "ColorPickBgBtn"
        )
        self._bgcolor_edit   = self._bgcolor_picker._edit
        self._bgcolor_swatch = self._bgcolor_picker._swatch
        self._bgcolor_btn    = self._bgcolor_picker._btn
        self._bgcolor_picker._edit.hide()
        self._bgcolor_picker._btn.hide()
        self._bgcolor_swatch.setToolTip("點選背景顏色預覽塊開啟選色器")
        self._bgcolor_swatch.installEventFilter(self)
        self._bgcolor_btn.clicked.connect(
            lambda: self._on_swatch_clicked("SetBackgroundColor", self._bgcolor_edit)
        )

        # Compact single row: label (above) + swatch (below) × 3 colours
        color_row_w = QWidget()
        color_row = QHBoxLayout(color_row_w)
        color_row.setContentsMargins(0, 2, 0, 2)
        color_row.setSpacing(14)
        for label_text, picker in (
            ("文字顏色", self._textcolor_picker),
            ("背景顏色", self._bgcolor_picker),
            ("邊框顏色", self._bordercolor_picker),
        ):
            cell_w = QWidget()
            cell = QVBoxLayout(cell_w)
            cell.setContentsMargins(0, 0, 0, 0)
            cell.setSpacing(3)
            lbl = QLabel(label_text)
            lbl.setObjectName("RuleDetailColorLabel")
            cell.addWidget(lbl)
            cell.addWidget(picker)
            color_row.addWidget(cell_w)
        color_row.addStretch()
        form.addRow(color_row_w)

        vlayout.addWidget(box)

        self._fontsize_spin.valueChanged.connect(self._on_any_field_changed)
        for edit in (self._textcolor_edit, self._bordercolor_edit, self._bgcolor_edit):
            edit.textChanged.connect(self._update_color_swatches)
            edit.editingFinished.connect(self._on_any_field_changed)

    # ------------------------------------------------------------------
    # Minimap picker sync
    # ------------------------------------------------------------------

    def _mm_sync_to_grid(self) -> None:
        """Parse minimap text and update MinimapIconGrid; no-op if invalid."""
        if self._mm_syncing:
            return
        parsed = _mm_parse(self._minimap_edit.text())
        if parsed is None:
            return
        self._mm_syncing = True
        try:
            size, color, shape = parsed
            self._minimap_grid.set_value(int(size), color, shape)
        finally:
            self._mm_syncing = False

    def _mm_sync_from_grid(self) -> None:
        """Write MinimapIconGrid values back to minimap text and emit rule_changed."""
        if self._mm_syncing or self._rule is None:
            return
        self._mm_syncing = True
        try:
            size, color, shape = self._minimap_grid.value()
            self._minimap_edit.setText(f"{size} {color} {shape}")
        finally:
            self._mm_syncing = False
        # setText triggers textChanged → _update_mm_preview automatically.
        # editingFinished is NOT triggered by setText, so call the slot manually.
        self._on_any_field_changed()

    def _update_mm_preview(self) -> None:
        """Refresh the MinimapPreviewWidget from current minimap text."""
        parsed = _mm_parse(self._minimap_edit.text())
        if parsed is None:
            self._mm_preview.clear()
        else:
            size, color, shape = parsed
            self._mm_preview.set_icon(size, color, shape)

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

    def _update_alert_preview(self) -> None:
        """Refresh the PlayAlertSound preview label from current text."""
        parsed = _alert_parse(self._alert_edit.text())
        if parsed is None:
            self._alert_preview_lbl.setText("（未設定）")
            self._alert_preview_lbl.setStyleSheet(
                "color: #3d4f6b; background: transparent;"
            )
        else:
            sid, vol = parsed
            self._alert_preview_lbl.setText(f"♪  音效 #{sid}   音量 {vol}")
            self._alert_preview_lbl.setStyleSheet(
                "color: #7e8eaf; background: transparent; font-weight: bold;"
            )

    # ------------------------------------------------------------------
    # PlayEffect sync
    # ------------------------------------------------------------------

    def _effect_sync_to_controls(self) -> None:
        """Parse PlayEffect text and update controls; no-op if invalid."""
        if self._effect_syncing:
            return
        parsed = _effect_parse(self._effect_edit.text())
        if parsed is None:
            return
        self._effect_syncing = True
        try:
            color, is_temp = parsed
            self._effect_picker.set_value(color)
            self._effect_temp_cb.setChecked(is_temp)
        finally:
            self._effect_syncing = False

    def _effect_sync_from_controls(self) -> None:
        """Write control values to PlayEffect text and emit rule_changed."""
        if self._effect_syncing or self._rule is None:
            return
        self._effect_syncing = True
        try:
            color = self._effect_picker.value()
            if color:
                temp_suffix = " Temp" if self._effect_temp_cb.isChecked() else ""
                self._effect_edit.setText(f"{color}{temp_suffix}")
            else:
                self._effect_edit.setText("")
        finally:
            self._effect_syncing = False
        self._on_any_field_changed()

    def _update_effect_preview(self) -> None:
        """Refresh the PlayEffect preview label from current text."""
        parsed = _effect_parse(self._effect_edit.text())
        if parsed is None:
            self._effect_preview_lbl.setText("（未設定）")
            self._effect_preview_lbl.setStyleSheet(
                "color: #3d4f6b; background: #07090f;"
                "border: 1px dashed #1c2845; border-radius: 3px;"
            )
        else:
            color, is_temp = parsed
            rgb = _MM_PREVIEW_COLORS.get(color, (180, 180, 180))
            r, g, b = rgb
            badge = "  (Temp)" if is_temp else ""
            self._effect_preview_lbl.setText(f"♦  {color}{badge}")
            self._effect_preview_lbl.setStyleSheet(
                f"background: rgba({r},{g},{b},160);"
                "color: white; font-weight: bold;"
                "border-radius: 3px; padding: 0 8px;"
            )

    def _build_audio_card(self, vlayout: QVBoxLayout) -> None:
        """音效 Card — PlayAlertSound only (P19.4A.1: separated from PlayEffect)."""
        box, form = self._make_card("音效")

        self._alert_edit = QLineEdit()
        self._alert_edit.setObjectName("RuleDetailAlertSound")
        self._alert_edit.setPlaceholderText("1 300")
        form.addRow("PlayAlertSound", self._alert_edit)

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

        self._alert_preview_lbl = QLabel("（未設定）")
        self._alert_preview_lbl.setObjectName("AlertSoundPreviewLabel")
        form.addRow("預覽", self._alert_preview_lbl)

        self._alert_hint = QLabel("格式：音效ID 音量（例：1 300）")
        self._alert_hint.setObjectName("RuleDetailHintLabel")
        form.addRow("", self._alert_hint)

        vlayout.addWidget(box)

        self._alert_edit.textChanged.connect(self._alert_sync_to_spins)
        self._alert_edit.textChanged.connect(self._update_alert_preview)
        self._alert_edit.editingFinished.connect(self._on_any_field_changed)
        self._alert_id_spin.valueChanged.connect(self._alert_sync_from_spins)
        self._alert_vol_spin.valueChanged.connect(self._alert_sync_from_spins)

    def _build_effect_card(self, vlayout: QVBoxLayout) -> None:
        """光柱效果 Card — PlayEffect only (P19.4A.1: separated from 音效)."""
        box, form = self._make_card("光柱效果")

        self._effect_edit = QLineEdit()
        self._effect_edit.setObjectName("RuleDetailPlayEffect")
        self._effect_edit.setPlaceholderText("Red")
        form.addRow("PlayEffect", self._effect_edit)

        self._effect_picker = VisualEffectPicker()
        form.addRow("顏色選擇", self._effect_picker)

        self._effect_temp_cb = QCheckBox("臨時(Temp)")
        self._effect_temp_cb.setObjectName("EffectTempCheck")
        self._effect_temp_cb.setToolTip("加入 Temp 關鍵字（物品拾取前效果消失）")
        form.addRow("", self._effect_temp_cb)

        self._effect_preview_lbl = QLabel("（未設定）")
        self._effect_preview_lbl.setObjectName("EffectPreviewLabel")
        self._effect_preview_lbl.setFixedHeight(26)
        self._effect_preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form.addRow("預覽", self._effect_preview_lbl)

        self._effect_hint = QLabel("格式：顏色 [Temp]（例：Red Temp）")
        self._effect_hint.setObjectName("RuleDetailHintLabel")
        form.addRow("", self._effect_hint)

        vlayout.addWidget(box)

        self._effect_edit.textChanged.connect(self._effect_sync_to_controls)
        self._effect_edit.textChanged.connect(self._update_effect_preview)
        self._effect_edit.editingFinished.connect(self._on_any_field_changed)
        self._effect_picker.effect_changed.connect(self._effect_sync_from_controls)
        self._effect_temp_cb.stateChanged.connect(self._effect_sync_from_controls)

    def _build_minimap_card(self, vlayout: QVBoxLayout) -> None:
        box, form = self._make_card("小地圖")

        # Text input (manual entry preserved)
        self._minimap_edit = QLineEdit()
        self._minimap_edit.setObjectName("RuleDetailMinimapIcon")
        self._minimap_edit.setPlaceholderText("1 Red Circle")
        form.addRow("MinimapIcon", self._minimap_edit)

        # Visual icon grid: Size / Color / Shape
        self._minimap_grid = MinimapIconGrid()
        form.addRow("圖示選擇", self._minimap_grid)

        # Visual icon preview
        self._mm_preview = MinimapPreviewWidget()
        form.addRow("預覽", self._mm_preview)

        # Format hint
        self._minimap_hint = QLabel("格式：大小 顏色 形狀（例：1 Red Circle）")
        self._minimap_hint.setObjectName("RuleDetailHintLabel")
        form.addRow("", self._minimap_hint)

        vlayout.addWidget(box)

        # Connections
        self._minimap_edit.textChanged.connect(self._mm_sync_to_grid)
        self._minimap_edit.textChanged.connect(self._update_mm_preview)
        self._minimap_edit.editingFinished.connect(self._on_any_field_changed)
        self._minimap_grid.icon_changed.connect(self._mm_sync_from_grid)

    def _build_preview_card(self) -> None:
        # P19.3B: 語法預覽移至 PreviewPanel。保留 _preview_text 供測試使用。
        self._preview_text = QPlainTextEdit(self)
        self._preview_text.setObjectName("RuleDetailPreview")
        self._preview_text.setReadOnly(True)
        self._preview_text.hide()

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

        class_val    = self._get_from_list(rule.conditions, "Class")
        basetype_val = self._get_from_list(rule.conditions, "BaseType")
        self._class_edit.setText(class_val)
        self._basetype_edit.setText(basetype_val)
        # P21.5 — Tooltip 顯示中文名稱
        if self._alias_svc is not None:
            self._class_edit.setToolTip(self._alias_svc.tooltip_class(class_val) or "")
            self._basetype_edit.setToolTip(self._alias_svc.tooltip_basetype(basetype_val) or "")
        # P22.2 — 圖形化條件建立器
        if self._cond_builder is not None:
            self._cond_builder.set_conditions(rule.conditions)

        fs_raw = self._get_from_list(rule.actions, "SetFontSize")
        try:
            self._fontsize_spin.setValue(int(fs_raw.strip()) if fs_raw.strip() else 0)
        except ValueError:
            self._fontsize_spin.setValue(0)

        self._textcolor_edit.setText(self._get_from_list(rule.actions, "SetTextColor"))
        self._bordercolor_edit.setText(self._get_from_list(rule.actions, "SetBorderColor"))
        self._bgcolor_edit.setText(self._get_from_list(rule.actions, "SetBackgroundColor"))
        self._alert_edit.setText(self._get_from_list(rule.actions, "PlayAlertSound"))
        self._effect_edit.setText(self._get_from_list(rule.actions, "PlayEffect"))
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

        # P22.2: ConditionBuilderWidget 可用時，由 widget 管理所有已知條件
        if self._cond_builder is not None:
            rule.conditions = self._cond_builder.get_conditions()
        else:
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
            rule.actions, "PlayEffect", self._effect_edit.text()
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
                "background: transparent; border: 1.5px solid #1e2435; border-radius: 5px;"
            )
            return
        try:
            vals = [max(0, min(255, int(p))) for p in color_text.strip().split()[:4]]
            while len(vals) < 4:
                vals.append(255)
            r, g, b, a = vals
            swatch.setStyleSheet(
                f"background: rgba({r},{g},{b},{a});"
                "border: 1.5px solid #334155; border-radius: 5px;"
            )
        except (ValueError, TypeError):
            swatch.setStyleSheet(
                "background: transparent;"
                "border: 1.5px dashed #ef4444; border-radius: 5px;"
            )

    def _render_rule_text(self) -> str:
        if self._rule is None:
            return ""
        rule = self._rule
        prefix = "" if rule.enabled else "# "
        lines = [f"{prefix}{rule.action}"]
        for key, value in rule.conditions:
            lines.append(f"    {key} {value}")
        for key, value in rule.actions:
            lines.append(f"    {key} {value}")
        for ul in rule.unknown_lines:
            lines.append(f"    {ul}")
        return "\n".join(lines)

    def _update_preview(self) -> None:
        self._preview_text.setPlainText(self._render_rule_text())

    def _update_raw_filter(self) -> None:
        self._raw_filter_text.setPlainText(self._render_rule_text())

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
        self._update_raw_filter()
        self._update_title()
        self.rule_changed.emit(self._index, updated_rule)
