"""RuleListWidget — v0.6.0

Changes from v0.5.0:
  - QListWidget replaced with _DraggableListWidget (private subclass)
  - _DraggableListWidget intercepts drop events and emits move_requested(from_row, to_row)
    WITHOUT calling super().dropEvent() — so QListWidget never directly reorders items
  - RuleListWidget translates display rows → real indices and emits move_rule_requested
  - True reorder happens only in FilterDocument via MoveRuleCommand

Public API (unchanged):
  Signals:
    rule_selected(int)           — real index
    add_rule_requested()
    delete_rule_requested(int)   — real index
    copy_rule_requested(int)     — real index
    move_rule_requested(int,int) — from_real, to_real   ← NEW v0.6.0

  Methods:
    load_rules(rules)
    refresh()
    select_real_index(real_index)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton,
    QAbstractItemView,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from core.models import FilterRule


# ---------------------------------------------------------------------------
# _DraggableListWidget
# ---------------------------------------------------------------------------

class _DraggableListWidget(QListWidget):
    """QListWidget subclass that converts drag-drop into a signal.

    The built-in QListWidget InternalMove would reorder items before we
    could intercept it, so dropEvent is overridden to:
      1. Compute where the user intended to drop (from_row, to_row)
      2. Emit move_requested(from_row, to_row)
      3. Reject the drop (event.IgnoreAction) so Qt does NOT reorder items

    The actual reorder is handled externally by FilterDocument + MoveRuleCommand,
    after which load_rules() rebuilds the list from the document state.
    """

    move_requested = Signal(int, int)   # from_row, to_row (display indices)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self._drag_from_row: int = -1

    def startDrag(self, supported_actions):
        self._drag_from_row = self.currentRow()
        super().startDrag(supported_actions)

    def dropEvent(self, event):
        from_row = self._drag_from_row
        self._drag_from_row = -1

        if from_row < 0 or self.count() == 0:
            event.ignore()
            return

        target = self.indexAt(event.position().toPoint())

        if not target.isValid():
            # Dropped in empty space below all items → treat as last position
            to_row = self.count() - 1
        else:
            drop_row  = target.row()
            indicator = self.dropIndicatorPosition()
            below     = (indicator == QAbstractItemView.DropIndicatorPosition.BelowItem)

            # Compute the intended FINAL position of the dragged item.
            # pop(from_row) + insert(to_row) semantics:
            #   moving forward (from < drop): shift = -1 for AboveItem, 0 for BelowItem
            #   moving backward (from > drop): shift = 0 for AboveItem, +1 for BelowItem
            if from_row < drop_row:
                to_row = drop_row if below else drop_row - 1
            else:
                to_row = drop_row + 1 if below else drop_row

        to_row = max(0, min(to_row, self.count() - 1))

        # Reject built-in item reorder — external Command handles this
        event.setDropAction(Qt.DropAction.IgnoreAction)
        event.accept()

        if from_row != to_row:
            self.move_requested.emit(from_row, to_row)


# ---------------------------------------------------------------------------
# RuleListWidget
# ---------------------------------------------------------------------------

class RuleListWidget(QWidget):
    rule_selected         = Signal(int)       # real index into rules list
    add_rule_requested    = Signal()
    delete_rule_requested = Signal(int)       # real index
    copy_rule_requested   = Signal(int)       # real index
    move_rule_requested   = Signal(int, int)  # from_real_index, to_real_index

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules: list[FilterRule] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        btn_row = QHBoxLayout()
        self.btn_add  = QPushButton("＋ 新增")
        self.btn_del  = QPushButton("－ 刪除")
        self.btn_copy = QPushButton("複製")
        for b in (self.btn_add, self.btn_del, self.btn_copy):
            b.setFixedHeight(26)
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        self.list_widget = _DraggableListWidget()
        self.list_widget.setAlternatingRowColors(True)
        layout.addWidget(self.list_widget)

        self.btn_add.clicked.connect(self._on_add)
        self.btn_del.clicked.connect(self._on_delete)
        self.btn_copy.clicked.connect(self._on_copy)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        self.list_widget.move_requested.connect(self._on_move_requested)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_rules(self, rules: list[FilterRule]):
        self._rules = rules
        self.refresh()

    def refresh(self):
        current_row = self.list_widget.currentRow()
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        display_num = 1
        for real_idx, rule in enumerate(self._rules):
            if rule.action == "__TAIL__":
                continue
            label = self._make_label(display_num, rule)
            item  = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, real_idx)
            item.setForeground(
                QColor("#90ee90") if rule.action == "Show" else QColor("#aaaaaa")
            )
            self.list_widget.addItem(item)
            display_num += 1

        count = self.list_widget.count()
        if count > 0:
            target = max(0, min(current_row, count - 1))
            # Keep signals blocked so that restoring the selection programmatically
            # does NOT fire rule_selected — callers are responsible for reloading
            # the editor when they need it.
            self.list_widget.setCurrentRow(target)

        self.list_widget.blockSignals(False)

    def select_real_index(self, real_index: int):
        """Highlight the list row that corresponds to rules[real_index]."""
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item and item.data(Qt.ItemDataRole.UserRole) == real_index:
                self.list_widget.blockSignals(True)
                self.list_widget.setCurrentRow(row)
                self.list_widget.blockSignals(False)
                return

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_label(display_num: int, rule: FilterRule) -> str:
        if rule.conditions:
            k, v = rule.conditions[0]
            v_clean = v.strip('"').strip("'").strip()
            detail  = f"{k} {v_clean}".strip()
        elif rule.actions:
            k, v = rule.actions[0]
            detail = k
        else:
            detail = "Empty Rule"
        label = f"{rule.action} — {detail}"
        if len(label) > 52:
            label = label[:49] + "…"
        return f"[{display_num}] {label}"

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_row_changed(self, row: int):
        if row < 0:
            return
        item = self.list_widget.item(row)
        if item is None:
            return
        self.rule_selected.emit(item.data(Qt.ItemDataRole.UserRole))

    def _on_add(self):
        self.add_rule_requested.emit()

    def _on_delete(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        self.delete_rule_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    def _on_copy(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        self.copy_rule_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    def _on_move_requested(self, from_row: int, to_row: int):
        """Translate display-row indices to real indices and emit move_rule_requested.

        Since __TAIL__ is never shown, display_row == real_index for all
        visible items.  The UserRole lookup is kept for defensive correctness.
        """
        from_item = self.list_widget.item(from_row)
        to_item   = self.list_widget.item(to_row)
        if from_item is None or to_item is None:
            return
        from_real = from_item.data(Qt.ItemDataRole.UserRole)
        to_real   = to_item.data(Qt.ItemDataRole.UserRole)
        if from_real != to_real:
            self.move_rule_requested.emit(from_real, to_real)
