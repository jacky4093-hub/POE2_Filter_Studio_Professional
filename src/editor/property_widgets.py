"""Schema-driven property editor widgets.

Each widget class handles one FieldType.  The unified interface is:
  get_raw_value() -> str   — serialise to the string stored in FilterRule
  set_raw_value(str)       — deserialise from FilterRule string
  value_changed signal     — emitted whenever the user changes anything

None of these widgets know about FilterRule, FilterDocument, or the schema
name of the field — they only know their own type.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox, QLineEdit,
    QSpinBox, QSizePolicy, QFrame,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from core.filter_schema import (
    OPERATORS, RARITY_OPTIONS, BOOL_OPTIONS,
    SOUND_COLORS, BEAM_SHAPES, MINIMAP_SIZES, EFFECT_COLORS,
)


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


def _swatch(parent: QWidget | None = None) -> QFrame:
    """A small coloured square that acts as a live preview swatch."""
    f = QFrame(parent)
    f.setFixedSize(22, 22)
    f.setFrameShape(QFrame.Shape.Box)
    return f


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BasePropertyWidget(QWidget):
    value_changed = Signal()

    def get_raw_value(self) -> str:
        raise NotImplementedError

    def set_raw_value(self, s: str):
        raise NotImplementedError

    def _block(self, widget, callback):
        """Block signals, run callback, unblock."""
        widget.blockSignals(True)
        callback()
        widget.blockSignals(False)


# ---------------------------------------------------------------------------
# StringPropertyWidget  — free-text LineEdit
# ---------------------------------------------------------------------------

class StringPropertyWidget(BasePropertyWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText('例: "Currency" "Gems"')
        layout.addWidget(self.edit)
        self.edit.textChanged.connect(lambda _: self.value_changed.emit())

    def get_raw_value(self) -> str:
        return self.edit.text().strip()

    def set_raw_value(self, s: str):
        self._block(self.edit, lambda: self.edit.setText(s))


# ---------------------------------------------------------------------------
# EnumPropertyWidget  — fixed QComboBox
# ---------------------------------------------------------------------------

class EnumPropertyWidget(BasePropertyWidget):
    def __init__(self, options: list[str], parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.combo = _combo(options)
        self.combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.combo)
        self.combo.currentTextChanged.connect(lambda _: self.value_changed.emit())

    def get_raw_value(self) -> str:
        return self.combo.currentText()

    def set_raw_value(self, s: str):
        s = s.strip()
        idx = self.combo.findText(s, Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self._block(self.combo, lambda: self.combo.setCurrentIndex(idx))
        else:
            # Unknown value: add it temporarily so it's not lost
            self.combo.addItem(s)
            self._block(self.combo, lambda: self.combo.setCurrentText(s))


# ---------------------------------------------------------------------------
# BoolPropertyWidget  — True / False combo
# ---------------------------------------------------------------------------

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

    def set_raw_value(self, s: str):
        s = s.strip()
        idx = self.combo.findText(s, Qt.MatchFlag.MatchFixedString)
        self._block(self.combo, lambda: self.combo.setCurrentIndex(max(0, idx)))


# ---------------------------------------------------------------------------
# IntOpPropertyWidget  — operator combo + SpinBox  (AreaLevel >= 68)
# ---------------------------------------------------------------------------

class IntOpPropertyWidget(BasePropertyWidget):
    def __init__(self, min_val: int = 0, max_val: int = 100, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.op_combo = _combo(OPERATORS, width=52)
        self.spin = _spin(min_val, max_val, width=70)

        layout.addWidget(self.op_combo)
        layout.addWidget(self.spin)
        layout.addStretch()

        self.op_combo.currentTextChanged.connect(lambda _: self.value_changed.emit())
        self.spin.valueChanged.connect(lambda _: self.value_changed.emit())

    def get_raw_value(self) -> str:
        return f"{self.op_combo.currentText()} {self.spin.value()}"

    def set_raw_value(self, s: str):
        parts = s.strip().split()
        op, val = ">=", self.spin.minimum()
        if len(parts) == 2 and parts[0] in OPERATORS:
            op, val_str = parts[0], parts[1]
            try:
                val = int(val_str)
            except ValueError:
                pass
        elif len(parts) == 1:
            try:
                val = int(parts[0])
                op = ">="
            except ValueError:
                pass

        self._block(self.op_combo, lambda: self.op_combo.setCurrentText(op))
        self._block(self.spin, lambda: self.spin.setValue(
            max(self.spin.minimum(), min(self.spin.maximum(), val))
        ))


# ---------------------------------------------------------------------------
# IntPropertyWidget  — plain SpinBox  (SetFontSize 18)
# ---------------------------------------------------------------------------

class IntPropertyWidget(BasePropertyWidget):
    def __init__(self, min_val: int = 0, max_val: int = 100, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.spin = _spin(min_val, max_val, width=80)
        layout.addWidget(self.spin)
        layout.addStretch()
        self.spin.valueChanged.connect(lambda _: self.value_changed.emit())

    def get_raw_value(self) -> str:
        return str(self.spin.value())

    def set_raw_value(self, s: str):
        try:
            v = int(s.strip())
        except ValueError:
            v = self.spin.minimum()
        self._block(self.spin, lambda: self.spin.setValue(
            max(self.spin.minimum(), min(self.spin.maximum(), v))
        ))


# ---------------------------------------------------------------------------
# ColorPropertyWidget  — 4 × SpinBox (R G B A) + colour swatch
# ---------------------------------------------------------------------------

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

        self._swatch = _swatch()

        for label, spin in [("R", self.r), ("G", self.g), ("B", self.b), ("A", self.a)]:
            layout.addWidget(spin)
        layout.addWidget(self._swatch)
        layout.addStretch()

        for spin in (self.r, self.g, self.b, self.a):
            spin.valueChanged.connect(self._on_changed)

        self._update_swatch()

    def _on_changed(self):
        self._update_swatch()
        self.value_changed.emit()

    def _update_swatch(self):
        c = QColor(self.r.value(), self.g.value(), self.b.value(), self.a.value())
        self._swatch.setStyleSheet(
            f"background-color: rgba({c.red()},{c.green()},{c.blue()},{c.alpha()});"
            "border: 1px solid #555;"
        )

    def get_raw_value(self) -> str:
        return f"{self.r.value()} {self.g.value()} {self.b.value()} {self.a.value()}"

    def set_raw_value(self, s: str):
        parts = s.strip().split()
        vals = []
        for p in parts[:4]:
            try:
                vals.append(int(p))
            except ValueError:
                vals.append(0)
        while len(vals) < 4:
            vals.append(255)

        for spin, v in zip((self.r, self.g, self.b, self.a), vals):
            self._block(spin, lambda sp=spin, vv=v: sp.setValue(
                max(sp.minimum(), min(sp.maximum(), vv))
            ))
        self._update_swatch()


# ---------------------------------------------------------------------------
# SoundIdPropertyWidget  — SpinBox ID + SpinBox Volume
# ---------------------------------------------------------------------------

class SoundIdPropertyWidget(BasePropertyWidget):
    def __init__(self, max_id: int = 16, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.id_spin  = _spin(1, max_id, 60)
        self.vol_spin = _spin(0, 300, 60)
        self.vol_spin.setValue(300)

        from PySide6.QtWidgets import QLabel
        layout.addWidget(QLabel("ID:"))
        layout.addWidget(self.id_spin)
        layout.addWidget(QLabel("音量:"))
        layout.addWidget(self.vol_spin)
        layout.addStretch()

        self.id_spin.valueChanged.connect(lambda _: self.value_changed.emit())
        self.vol_spin.valueChanged.connect(lambda _: self.value_changed.emit())

    def get_raw_value(self) -> str:
        return f"{self.id_spin.value()} {self.vol_spin.value()}"

    def set_raw_value(self, s: str):
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


# ---------------------------------------------------------------------------
# CustomSoundPropertyWidget  — LineEdit filename + SpinBox Volume
# ---------------------------------------------------------------------------

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

        from PySide6.QtWidgets import QLabel
        layout.addWidget(self.path_edit, 1)
        layout.addWidget(QLabel("音量:"))
        layout.addWidget(self.vol_spin)

        self.path_edit.textChanged.connect(lambda _: self.value_changed.emit())
        self.vol_spin.valueChanged.connect(lambda _: self.value_changed.emit())

    def get_raw_value(self) -> str:
        path = self.path_edit.text().strip()
        return f"{path} {self.vol_spin.value()}" if path else ""

    def set_raw_value(self, s: str):
        s = s.strip()
        # last token is volume if it's a number
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


# ---------------------------------------------------------------------------
# MinimapIconPropertyWidget  — Size + Color + Shape
# ---------------------------------------------------------------------------

class MinimapIconPropertyWidget(BasePropertyWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        from PySide6.QtWidgets import QLabel
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

    def set_raw_value(self, s: str):
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


# ---------------------------------------------------------------------------
# PlayEffectPropertyWidget  — Color + optional "Temp"
# ---------------------------------------------------------------------------

class PlayEffectPropertyWidget(BasePropertyWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        from PySide6.QtWidgets import QLabel, QCheckBox
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

    def set_raw_value(self, s: str):
        parts = s.strip().split()
        color = parts[0] if parts else "White"
        temp  = len(parts) > 1 and parts[1].lower() == "temp"

        idx = self.color_combo.findText(color, Qt.MatchFlag.MatchFixedString)
        self._block(self.color_combo,
                    lambda: self.color_combo.setCurrentIndex(max(0, idx)))
        self._block(self.temp_check,
                    lambda: self.temp_check.setChecked(temp))


# ---------------------------------------------------------------------------
# UnknownPropertyWidget  — plain LineEdit for unrecognised keys
# ---------------------------------------------------------------------------

class UnknownPropertyWidget(BasePropertyWidget):
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

    def set_raw_value(self, s: str):
        self._block(self.edit, lambda: self.edit.setText(s))


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

from core.filter_schema import FieldDef, FieldType


def make_property_widget(field_def: FieldDef | None,
                         parent: QWidget | None = None) -> BasePropertyWidget:
    """Create the right property widget for *field_def*.
    Falls back to UnknownPropertyWidget if field_def is None."""
    if field_def is None:
        return UnknownPropertyWidget(parent)

    ft = field_def.field_type
    if ft == FieldType.STRING:
        return StringPropertyWidget(parent)
    if ft == FieldType.ENUM:
        return EnumPropertyWidget(field_def.options or [], parent)
    if ft == FieldType.BOOL:
        return BoolPropertyWidget(parent)
    if ft == FieldType.INT_OP:
        return IntOpPropertyWidget(field_def.min_val, field_def.max_val, parent)
    if ft == FieldType.INT:
        return IntPropertyWidget(field_def.min_val, field_def.max_val, parent)
    if ft == FieldType.COLOR:
        return ColorPropertyWidget(parent)
    if ft in (FieldType.SOUND_ID,):
        return SoundIdPropertyWidget(field_def.max_val, parent)
    if ft == FieldType.CUSTOM_SND:
        return CustomSoundPropertyWidget(parent)
    if ft == FieldType.MINIMAP:
        return MinimapIconPropertyWidget(parent)
    if ft == FieldType.PLAY_EFFECT:
        return PlayEffectPropertyWidget(parent)

    return UnknownPropertyWidget(parent)
