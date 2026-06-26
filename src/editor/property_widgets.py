"""Schema-driven property editor widgets — v0.4.0

Architecture
------------
  FieldType  ──Registry──▶  Widget Class  ──from_field_def()──▶  Instance

Registry: _REGISTRY maps FieldType → Widget Class (not factory function).
Each widget class registers itself with @register(FieldType.X).
Each widget class has a from_field_def(fd, parent) classmethod that
extracts FieldDef metadata (placeholder, tooltip, min/max, options) and
returns a fully configured instance.

UnknownPropertyWidget is always the last fallback:
  - field_def is None           → UnknownPropertyWidget
  - field_type not in registry  → UnknownPropertyWidget
  - any exception during create → UnknownPropertyWidget

Public API (unchanged from v0.3.0):
  get_raw_value() -> str
  set_raw_value(str)
  value_changed  Signal

New in v0.4.0:
  validate()           -> ValidationResult
  reset_to_default()   (reserved stub — does nothing yet)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox, QLineEdit,
    QSpinBox, QSizePolicy, QFrame, QLabel, QCheckBox,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

if TYPE_CHECKING:
    from core.filter_schema import FieldDef, FieldType as _FieldType


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------

class Severity(Enum):
    INFO    = "info"
    WARNING = "warning"
    ERROR   = "error"


@dataclass
class ValidationResult:
    valid:    bool
    message:  str      = ""
    severity: Severity = Severity.INFO

    @staticmethod
    def ok() -> "ValidationResult":
        return ValidationResult(valid=True)

    @staticmethod
    def error(msg: str) -> "ValidationResult":
        return ValidationResult(valid=False, message=msg, severity=Severity.ERROR)

    @staticmethod
    def warning(msg: str) -> "ValidationResult":
        return ValidationResult(valid=True, message=msg, severity=Severity.WARNING)

    @staticmethod
    def info(msg: str) -> "ValidationResult":
        return ValidationResult(valid=True, message=msg, severity=Severity.INFO)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

from core.filter_schema import FieldType

_REGISTRY: dict[FieldType, type["BasePropertyWidget"]] = {}


def register(*field_types: FieldType):
    """Class decorator: register a widget class for one or more FieldTypes.

    Usage:
        @register(FieldType.STRING)
        class StringPropertyWidget(BasePropertyWidget): ...
    """
    def decorator(cls: type["BasePropertyWidget"]) -> type["BasePropertyWidget"]:
        for ft in field_types:
            _REGISTRY[ft] = cls
        return cls
    return decorator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _combo(items: list[str], width: int = 0) -> QComboBox:
    c = QComboBox()
    c.addItems(items)
    if width:
        c.setFixedWidth(width)
    return c


def _spin(min_v: int, max_v: int, width: int = 60) -> QSpinBox:
    s = QSpinBox()
    s.setRange(min_v, max_v)
    s.setFixedWidth(width)
    return s


def _swatch() -> QFrame:
    f = QFrame()
    f.setFixedSize(22, 22)
    f.setFrameShape(QFrame.Shape.Box)
    return f


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BasePropertyWidget(QWidget):
    value_changed = Signal()

    # ── required overrides ────────────────────────────────────────────────

    def get_raw_value(self) -> str:
        raise NotImplementedError

    def set_raw_value(self, s: str) -> None:
        raise NotImplementedError

    # ── validation ────────────────────────────────────────────────────────

    def validate(self) -> ValidationResult:
        """Return ValidationResult describing whether the current value is valid.

        Subclasses override this.  The default is always valid so that
        widgets that do not implement explicit validation never block data.
        """
        return ValidationResult.ok()

    # ── reserved stub ─────────────────────────────────────────────────────

    def reset_to_default(self) -> None:
        """Reset widget to its schema-defined default value.
        Reserved for future use — currently a no-op.
        """

    # ── factory classmethod ───────────────────────────────────────────────

    @classmethod
    def from_field_def(cls, fd: "FieldDef", parent: QWidget | None = None) -> "BasePropertyWidget":
        """Create and configure an instance from a FieldDef.
        Subclasses override to extract options / min / max / placeholder / tooltip.
        The default just instantiates with no extra args.
        """
        w = cls(parent)
        if fd.tooltip:
            w.setToolTip(fd.tooltip)
        return w

    # ── internal helpers ─────────────────────────────────────────────────

    def _block(self, widget: QWidget, callback) -> None:
        widget.blockSignals(True)
        callback()
        widget.blockSignals(False)


# ---------------------------------------------------------------------------
# StringPropertyWidget
# ---------------------------------------------------------------------------

@register(FieldType.STRING)
class StringPropertyWidget(BasePropertyWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText('例: "Currency" "Gems"')
        layout.addWidget(self.edit)
        self.edit.textChanged.connect(lambda _: self.value_changed.emit())

    @classmethod
    def from_field_def(cls, fd, parent=None):
        w = cls(parent)
        if fd.placeholder:
            w.edit.setPlaceholderText(fd.placeholder)
        if fd.tooltip:
            w.setToolTip(fd.tooltip)
        return w

    def get_raw_value(self) -> str:
        return self.edit.text().strip()

    def set_raw_value(self, s: str) -> None:
        self._block(self.edit, lambda: self.edit.setText(s))

    def validate(self) -> ValidationResult:
        return ValidationResult.ok()


# ---------------------------------------------------------------------------
# EnumPropertyWidget
# ---------------------------------------------------------------------------

@register(FieldType.ENUM)
class EnumPropertyWidget(BasePropertyWidget):
    def __init__(self, options: list[str], parent=None):
        super().__init__(parent)
        self._original_options = list(options)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.combo = _combo(options)
        self.combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.combo)
        self.combo.currentTextChanged.connect(lambda _: self.value_changed.emit())

    @classmethod
    def from_field_def(cls, fd, parent=None):
        w = cls(fd.options or [], parent)
        if fd.tooltip:
            w.setToolTip(fd.tooltip)
        return w

    def get_raw_value(self) -> str:
        return self.combo.currentText()

    def set_raw_value(self, s: str) -> None:
        s = s.strip()
        idx = self.combo.findText(s, Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self._block(self.combo, lambda: self.combo.setCurrentIndex(idx))
        else:
            # Unknown value: add temporarily so it is not lost
            self.combo.addItem(s)
            self._block(self.combo, lambda: self.combo.setCurrentText(s))

    def validate(self) -> ValidationResult:
        v = self.combo.currentText()
        if v not in self._original_options:
            return ValidationResult.warning(f"「{v}」不在已知選項中")
        return ValidationResult.ok()


# ---------------------------------------------------------------------------
# BoolPropertyWidget
# ---------------------------------------------------------------------------

from core.filter_schema import BOOL_OPTIONS

@register(FieldType.BOOL)
class BoolPropertyWidget(BasePropertyWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.combo = _combo(BOOL_OPTIONS)
        self.combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.combo)
        self.combo.currentTextChanged.connect(lambda _: self.value_changed.emit())

    def get_raw_value(self) -> str:
        return self.combo.currentText()

    def set_raw_value(self, s: str) -> None:
        idx = self.combo.findText(s.strip(), Qt.MatchFlag.MatchFixedString)
        self._block(self.combo, lambda: self.combo.setCurrentIndex(max(0, idx)))

    def validate(self) -> ValidationResult:
        if self.combo.currentText() not in BOOL_OPTIONS:
            return ValidationResult.error("必須為 True 或 False")
        return ValidationResult.ok()


# ---------------------------------------------------------------------------
# IntOpPropertyWidget  (AreaLevel >= 68)
# ---------------------------------------------------------------------------

from core.filter_schema import OPERATORS

@register(FieldType.INT_OP)
class IntOpPropertyWidget(BasePropertyWidget):
    def __init__(self, min_val: int = 0, max_val: int = 100, parent=None):
        super().__init__(parent)
        self._min = min_val
        self._max = max_val
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.op_combo = _combo(OPERATORS, width=52)
        self.spin     = _spin(min_val, max_val, width=70)
        layout.addWidget(self.op_combo)
        layout.addWidget(self.spin)
        layout.addStretch()
        self.op_combo.currentTextChanged.connect(lambda _: self.value_changed.emit())
        self.spin.valueChanged.connect(lambda _: self.value_changed.emit())

    @classmethod
    def from_field_def(cls, fd, parent=None):
        w = cls(fd.min_val, fd.max_val, parent)
        if fd.tooltip:
            w.setToolTip(fd.tooltip)
        return w

    def get_raw_value(self) -> str:
        return f"{self.op_combo.currentText()} {self.spin.value()}"

    def set_raw_value(self, s: str) -> None:
        parts = s.strip().split()
        op, val = ">=", self.spin.minimum()
        if len(parts) == 2 and parts[0] in OPERATORS:
            op = parts[0]
            try: val = int(parts[1])
            except ValueError: pass
        elif len(parts) == 1:
            try:
                val = int(parts[0])
                op  = ">="
            except ValueError: pass
        self._block(self.op_combo, lambda: self.op_combo.setCurrentText(op))
        self._block(self.spin, lambda: self.spin.setValue(
            max(self.spin.minimum(), min(self.spin.maximum(), val))
        ))

    def validate(self) -> ValidationResult:
        return ValidationResult.ok()  # SpinBox enforces range


# ---------------------------------------------------------------------------
# IntPropertyWidget  (SetFontSize 18)
# ---------------------------------------------------------------------------

@register(FieldType.INT)
class IntPropertyWidget(BasePropertyWidget):
    def __init__(self, min_val: int = 0, max_val: int = 100, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.spin = _spin(min_val, max_val, width=80)
        layout.addWidget(self.spin)
        layout.addStretch()
        self.spin.valueChanged.connect(lambda _: self.value_changed.emit())

    @classmethod
    def from_field_def(cls, fd, parent=None):
        w = cls(fd.min_val, fd.max_val, parent)
        if fd.tooltip:
            w.setToolTip(fd.tooltip)
        return w

    def get_raw_value(self) -> str:
        return str(self.spin.value())

    def set_raw_value(self, s: str) -> None:
        try:
            v = int(s.strip())
        except ValueError:
            v = self.spin.minimum()
        self._block(self.spin, lambda: self.spin.setValue(
            max(self.spin.minimum(), min(self.spin.maximum(), v))
        ))

    def validate(self) -> ValidationResult:
        return ValidationResult.ok()


# ---------------------------------------------------------------------------
# ColorPropertyWidget  (SetTextColor R G B A)
# ---------------------------------------------------------------------------

@register(FieldType.COLOR)
class ColorPropertyWidget(BasePropertyWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        self.r = _spin(0, 255, 48)
        self.g = _spin(0, 255, 48)
        self.b = _spin(0, 255, 48)
        self.a = _spin(0, 255, 48)
        self.a.setValue(255)
        self._sw = _swatch()
        for sp in (self.r, self.g, self.b, self.a):
            layout.addWidget(sp)
        layout.addWidget(self._sw)
        layout.addStretch()
        for sp in (self.r, self.g, self.b, self.a):
            sp.valueChanged.connect(self._on_changed)
        self._refresh_swatch()

    def _on_changed(self):
        self._refresh_swatch()
        self.value_changed.emit()

    def _refresh_swatch(self):
        r, g, b, a = self.r.value(), self.g.value(), self.b.value(), self.a.value()
        self._sw.setStyleSheet(
            f"background-color: rgba({r},{g},{b},{a}); border: 1px solid #555;"
        )

    def get_raw_value(self) -> str:
        return f"{self.r.value()} {self.g.value()} {self.b.value()} {self.a.value()}"

    def set_raw_value(self, s: str) -> None:
        parts = s.strip().split()
        vals: list[int] = []
        for p in parts[:4]:
            try: vals.append(int(p))
            except ValueError: vals.append(0)
        while len(vals) < 4:
            vals.append(255)
        for sp, v in zip((self.r, self.g, self.b, self.a), vals):
            self._block(sp, lambda _sp=sp, _v=v: _sp.setValue(
                max(_sp.minimum(), min(_sp.maximum(), _v))
            ))
        self._refresh_swatch()

    def validate(self) -> ValidationResult:
        return ValidationResult.ok()  # SpinBox enforces 0–255


# ---------------------------------------------------------------------------
# SoundIdPropertyWidget  (PlayAlertSound ID Volume)
# ---------------------------------------------------------------------------

@register(FieldType.SOUND_ID)
class SoundIdPropertyWidget(BasePropertyWidget):
    def __init__(self, max_id: int = 16, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.id_spin  = _spin(1, max_id, 60)
        self.vol_spin = _spin(0, 300, 60)
        self.vol_spin.setValue(300)
        layout.addWidget(QLabel("ID:"))
        layout.addWidget(self.id_spin)
        layout.addWidget(QLabel("音量:"))
        layout.addWidget(self.vol_spin)
        layout.addStretch()
        self.id_spin.valueChanged.connect(lambda _: self.value_changed.emit())
        self.vol_spin.valueChanged.connect(lambda _: self.value_changed.emit())

    @classmethod
    def from_field_def(cls, fd, parent=None):
        w = cls(fd.max_val, parent)
        if fd.tooltip:
            w.setToolTip(fd.tooltip)
        return w

    def get_raw_value(self) -> str:
        return f"{self.id_spin.value()} {self.vol_spin.value()}"

    def set_raw_value(self, s: str) -> None:
        parts = s.strip().split()
        id_v, vol_v = 1, 300
        if len(parts) >= 1:
            try: id_v = int(parts[0])
            except ValueError: pass
        if len(parts) >= 2:
            try: vol_v = int(parts[1])
            except ValueError: pass
        self._block(self.id_spin,  lambda: self.id_spin.setValue(
            max(1, min(self.id_spin.maximum(), id_v))))
        self._block(self.vol_spin, lambda: self.vol_spin.setValue(
            max(0, min(300, vol_v))))

    def validate(self) -> ValidationResult:
        return ValidationResult.ok()


# ---------------------------------------------------------------------------
# CustomSoundPropertyWidget  (CustomAlertSound "file" Volume)
# ---------------------------------------------------------------------------

@register(FieldType.CUSTOM_SND)
class CustomSoundPropertyWidget(BasePropertyWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText('"sound.mp3"')
        self.vol_spin  = _spin(0, 300, 60)
        self.vol_spin.setValue(300)
        layout.addWidget(self.path_edit, 1)
        layout.addWidget(QLabel("音量:"))
        layout.addWidget(self.vol_spin)
        self.path_edit.textChanged.connect(lambda _: self.value_changed.emit())
        self.vol_spin.valueChanged.connect(lambda _: self.value_changed.emit())

    @classmethod
    def from_field_def(cls, fd, parent=None):
        w = cls(parent)
        if fd.placeholder:
            w.path_edit.setPlaceholderText(fd.placeholder)
        if fd.tooltip:
            w.setToolTip(fd.tooltip)
        return w

    def get_raw_value(self) -> str:
        path = self.path_edit.text().strip()
        return f"{path} {self.vol_spin.value()}" if path else ""

    def set_raw_value(self, s: str) -> None:
        s = s.strip()
        parts = s.rsplit(None, 1)
        path, vol = s, 300
        if len(parts) == 2:
            try:
                vol  = int(parts[1])
                path = parts[0]
            except ValueError:
                path = s
        self._block(self.path_edit, lambda: self.path_edit.setText(path))
        self._block(self.vol_spin,  lambda: self.vol_spin.setValue(max(0, min(300, vol))))

    def validate(self) -> ValidationResult:
        if not self.path_edit.text().strip():
            return ValidationResult.warning("請指定音效檔案路徑")
        return ValidationResult.ok()


# ---------------------------------------------------------------------------
# MinimapIconPropertyWidget  (MinimapIcon Size Color Shape)
# ---------------------------------------------------------------------------

from core.filter_schema import MINIMAP_SIZES, SOUND_COLORS, BEAM_SHAPES

@register(FieldType.MINIMAP)
class MinimapIconPropertyWidget(BasePropertyWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.size_combo  = _combo(MINIMAP_SIZES, 44)
        self.color_combo = _combo(SOUND_COLORS,  80)
        self.shape_combo = _combo(BEAM_SHAPES,   80)
        layout.addWidget(QLabel("大小:"))
        layout.addWidget(self.size_combo)
        layout.addWidget(QLabel("顏色:"))
        layout.addWidget(self.color_combo)
        layout.addWidget(QLabel("形狀:"))
        layout.addWidget(self.shape_combo)
        layout.addStretch()
        for c in (self.size_combo, self.color_combo, self.shape_combo):
            c.currentTextChanged.connect(lambda _: self.value_changed.emit())

    def get_raw_value(self) -> str:
        return (f"{self.size_combo.currentText()} "
                f"{self.color_combo.currentText()} "
                f"{self.shape_combo.currentText()}")

    def set_raw_value(self, s: str) -> None:
        parts = s.strip().split()
        size  = parts[0] if len(parts) > 0 else "0"
        color = parts[1] if len(parts) > 1 else "White"
        shape = parts[2] if len(parts) > 2 else "Circle"

        def _set(combo, val):
            idx = combo.findText(val, Qt.MatchFlag.MatchFixedString)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        self._block(self.size_combo,  lambda: _set(self.size_combo,  size))
        self._block(self.color_combo, lambda: _set(self.color_combo, color))
        self._block(self.shape_combo, lambda: _set(self.shape_combo, shape))

    def validate(self) -> ValidationResult:
        return ValidationResult.ok()


# ---------------------------------------------------------------------------
# PlayEffectPropertyWidget  (PlayEffect Color [Temp])
# ---------------------------------------------------------------------------

from core.filter_schema import EFFECT_COLORS

@register(FieldType.PLAY_EFFECT)
class PlayEffectPropertyWidget(BasePropertyWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.color_combo = _combo(EFFECT_COLORS, 80)
        self.temp_check  = QCheckBox("暫時")
        layout.addWidget(QLabel("顏色:"))
        layout.addWidget(self.color_combo)
        layout.addWidget(self.temp_check)
        layout.addStretch()
        self.color_combo.currentTextChanged.connect(lambda _: self.value_changed.emit())
        self.temp_check.stateChanged.connect(lambda _: self.value_changed.emit())

    def get_raw_value(self) -> str:
        val = self.color_combo.currentText()
        if self.temp_check.isChecked():
            val += " Temp"
        return val

    def set_raw_value(self, s: str) -> None:
        parts = s.strip().split()
        color = parts[0] if parts else "White"
        temp  = len(parts) > 1 and parts[1].lower() == "temp"
        idx   = self.color_combo.findText(color, Qt.MatchFlag.MatchFixedString)
        self._block(self.color_combo,
                    lambda: self.color_combo.setCurrentIndex(max(0, idx)))
        self._block(self.temp_check,
                    lambda: self.temp_check.setChecked(temp))

    def validate(self) -> ValidationResult:
        return ValidationResult.ok()


# ---------------------------------------------------------------------------
# UnknownPropertyWidget  — permanent last fallback
# ---------------------------------------------------------------------------

class UnknownPropertyWidget(BasePropertyWidget):
    """Used for any key/FieldType not in the registry.
    Always preserves the raw string without modification.
    Never raises — guaranteed safe fallback.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("原始值（未知指令）")
        layout.addWidget(self.edit)
        self.edit.textChanged.connect(lambda _: self.value_changed.emit())

    def get_raw_value(self) -> str:
        return self.edit.text()

    def set_raw_value(self, s: str) -> None:
        self._block(self.edit, lambda: self.edit.setText(s))

    def validate(self) -> ValidationResult:
        return ValidationResult.ok()

    def reset_to_default(self) -> None:
        pass  # nothing meaningful to reset to


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

def make_property_widget(
    field_def: "FieldDef | None",
    parent: QWidget | None = None,
) -> BasePropertyWidget:
    """Create the appropriate property widget for *field_def*.

    Falls back to UnknownPropertyWidget in every failure case:
      • field_def is None
      • field_type not in _REGISTRY
      • any exception during widget construction
    """
    if field_def is None:
        return UnknownPropertyWidget(parent)

    cls = _REGISTRY.get(field_def.field_type)
    if cls is None:
        return UnknownPropertyWidget(parent)

    try:
        return cls.from_field_def(field_def, parent)
    except Exception:
        return UnknownPropertyWidget(parent)
