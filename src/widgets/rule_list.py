"""RuleListWidget — v1.0.0

Changes from v0.8.0:
  - Internal widget changed from QListWidget to QTreeWidget
  - Rules without sections are shown as flat top-level items (backward-compat)
  - Rules with sections are grouped under collapsible SectionItems
  - set_highlights() auto-expands sections that contain a search match
  - Section collapse state tracked in _section_expanded {name: bool}
  - get_section_states() / apply_section_states() for settings persistence

Public API (signals unchanged):
  Signals:
    rule_selected(int)           — real index
    add_rule_requested()
    delete_rule_requested(int)   — real index
    copy_rule_requested(int)     — real index
    move_rule_requested(int,int) — from_real, to_real (within-section only)

  Methods:
    load_rules(rules, section_map=None)
    refresh()
    select_real_index(real_index)
    set_highlights(matches: set[int], current: int = -1)
    clear_highlights()
    get_section_states() -> dict[int, bool]    NEW v1.0.0 (key=first_rule_index)
    apply_section_states(states: dict[int, bool])  NEW v1.0.0
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QPushButton,
    QAbstractItemView,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QFont

from core.models import FilterRule


# ---------------------------------------------------------------------------
# Roles and colours
# ---------------------------------------------------------------------------

# Stores first_rule_index on section items; None on rule items
SECTION_ROLE = Qt.ItemDataRole.UserRole + 1

_HIGHLIGHT_CURRENT = QColor("#5a4200")   # amber — cursor match
_HIGHLIGHT_OTHER   = QColor("#2d2000")   # dark amber — other matches

_COLOUR_SHOW     = QColor("#90ee90")
_COLOUR_OTHER    = QColor("#aaaaaa")
_COLOUR_SECTION  = QColor("#ccaa55")
_COLOUR_UNGROUP  = QColor("#888888")


# ---------------------------------------------------------------------------
# _DraggableTreeWidget
# ---------------------------------------------------------------------------

class _DraggableTreeWidget(QTreeWidget):
    """QTreeWidget that converts within-section drag-drop to a signal.

    Cross-section drops are silently rejected to preserve section boundaries.
    Actual reorder is handled externally via MoveRuleCommand.
    """

    move_requested = Signal(int, int)   # from_real_idx, to_real_idx

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._drag_from_item: QTreeWidgetItem | None = None

    def startDrag(self, supported_actions):
        self._drag_from_item = self.currentItem()
        super().startDrag(supported_actions)

    def dropEvent(self, event):
        from_item = self._drag_from_item
        self._drag_from_item = None

        if from_item is None:
            event.ignore()
            return

        # Reject drags of section header items
        if from_item.data(0, SECTION_ROLE) is not None:
            event.ignore()
            return

        from_real = from_item.data(0, Qt.ItemDataRole.UserRole)
        if from_real is None or from_real < 0:
            event.ignore()
            return

        # Determine drop target item
        target_item = self.itemAt(event.position().toPoint())

        if target_item is None:
            # Dropped in empty space — move to last item within from_item's parent
            from_parent = from_item.parent()
            if from_parent is None:
                # Flat mode: move to last top-level item
                count = self.topLevelItemCount()
                if count == 0:
                    event.ignore()
                    return
                to_item = self.topLevelItem(count - 1)
            else:
                count = from_parent.childCount()
                to_item = from_parent.child(count - 1)
        elif target_item.data(0, SECTION_ROLE) is not None:
            # Dropped on a section header — reject cross-section
            event.ignore()
            return
        else:
            # Dropped on a rule item — check same parent
            from_parent = from_item.parent()
            to_parent   = target_item.parent()
            if from_parent != to_parent:
                # Cross-section drop — reject
                event.ignore()
                return
            to_item = target_item

        if to_item is None:
            event.ignore()
            return

        to_real = to_item.data(0, Qt.ItemDataRole.UserRole)
        if to_real is None or to_real < 0:
            event.ignore()
            return

        # Reject built-in item reorder — Command handles the actual move
        event.setDropAction(Qt.DropAction.IgnoreAction)
        event.accept()

        if from_real != to_real:
            self.move_requested.emit(from_real, to_real)


# ---------------------------------------------------------------------------
# RuleListWidget
# ---------------------------------------------------------------------------

class RuleListWidget(QWidget):
    rule_selected         = Signal(int)
    add_rule_requested    = Signal()
    delete_rule_requested = Signal(int)
    copy_rule_requested   = Signal(int)
    move_rule_requested   = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules: list[FilterRule] = []
        self._section_map = None           # SectionMap or None
        self._highlight_indices: set[int] = set()
        self._current_highlight: int      = -1
        # Collapse state keyed by section NAME for in-session stability
        self._section_expanded: dict[str, bool] = {}
        # O(1) lookup: real_index -> QTreeWidgetItem (rebuilt on every refresh)
        self._real_to_item: dict[int, QTreeWidgetItem] = {}
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

        self.list_widget = _DraggableTreeWidget()
        self.list_widget.setHeaderHidden(True)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setAnimated(False)   # faster rebuild
        layout.addWidget(self.list_widget)

        self.btn_add.clicked.connect(self._on_add)
        self.btn_del.clicked.connect(self._on_delete)
        self.btn_copy.clicked.connect(self._on_copy)
        self.list_widget.currentItemChanged.connect(self._on_item_changed)
        self.list_widget.move_requested.connect(self._on_move_requested)
        self.list_widget.itemCollapsed.connect(
            lambda item: self._on_section_toggled(item, False)
        )
        self.list_widget.itemExpanded.connect(
            lambda item: self._on_section_toggled(item, True)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_rules(self, rules: list[FilterRule], section_map=None):
        self._rules = rules
        self._section_map = section_map
        self.refresh()

    def refresh(self):
        current_real = self._get_current_real_index()
        self._real_to_item.clear()

        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        has_sections = (
            self._section_map is not None
            and bool(self._section_map.sections)
        )

        if has_sections:
            self._build_tree_with_sections(current_real)
        else:
            self._build_flat_list(current_real)

        self.list_widget.blockSignals(False)

    def select_real_index(self, real_index: int) -> None:
        item = self._real_to_item.get(real_index)
        if item:
            self.list_widget.blockSignals(True)
            self.list_widget.setCurrentItem(item)
            self.list_widget.scrollToItem(item)
            self.list_widget.blockSignals(False)

    def set_highlights(self, matches: set[int], current: int = -1) -> None:
        self._highlight_indices = matches
        self._current_highlight = current
        # Auto-expand sections that contain a match BEFORE refresh
        if matches and self._section_map and self._section_map.sections:
            self._mark_sections_expanded_for(matches)
        self.refresh()

    def clear_highlights(self) -> None:
        self._highlight_indices = set()
        self._current_highlight = -1
        self.refresh()

    def get_section_states(self) -> dict[int, bool]:
        """Return {first_rule_index: expanded} for all known sections.

        Converts from the in-memory name-keyed dict to the index-keyed
        format expected by WorkspaceSettings.
        """
        if not self._section_map:
            return {}
        result: dict[int, bool] = {}
        for sec in self._section_map.sections:
            result[sec.first_rule_index] = self._section_expanded.get(sec.name, True)
        return result

    def apply_section_states(self, states: dict[int, bool]) -> None:
        """Restore collapse states from {first_rule_index: expanded}.

        Converts index keys back to name keys via the current section_map.
        """
        if not self._section_map or not states:
            return
        for sec in self._section_map.sections:
            if sec.first_rule_index in states:
                self._section_expanded[sec.name] = states[sec.first_rule_index]
        # Reflect in the live tree without a full refresh
        for i in range(self.list_widget.topLevelItemCount()):
            top = self.list_widget.topLevelItem(i)
            fid = top.data(0, SECTION_ROLE)
            if fid is None:
                continue
            for sec in self._section_map.sections:
                if sec.first_rule_index == fid:
                    expanded = self._section_expanded.get(sec.name, True)
                    self.list_widget.blockSignals(True)
                    top.setExpanded(expanded)
                    self.list_widget.blockSignals(False)
                    break

    # ------------------------------------------------------------------
    # Tree builders
    # ------------------------------------------------------------------

    def _build_flat_list(self, current_real: int) -> None:
        item_to_select: QTreeWidgetItem | None = None
        display_num = 1

        for real_idx, rule in enumerate(self._rules):
            if rule.action == "__TAIL__":
                continue
            item = self._make_rule_item(None, real_idx, rule, display_num)
            if real_idx == current_real:
                item_to_select = item
            display_num += 1

        if item_to_select:
            self.list_widget.setCurrentItem(item_to_select)

    def _build_tree_with_sections(self, current_real: int) -> None:
        smap = self._section_map
        item_to_select: QTreeWidgetItem | None = None
        section_items: dict[int, QTreeWidgetItem] = {}   # section_idx → item

        # ── Phase 1: create all top-level containers ───────────────────
        unsec_item: QTreeWidgetItem | None = None
        if smap.unsectioned_indices:
            expanded = self._section_expanded.get("(未分類)", True)
            unsec_item = QTreeWidgetItem(["(未分類)"])
            unsec_item.setData(0, Qt.ItemDataRole.UserRole, -1)
            unsec_item.setFlags(
                unsec_item.flags()
                & ~Qt.ItemFlag.ItemIsSelectable
                & ~Qt.ItemFlag.ItemIsDragEnabled
            )
            unsec_item.setForeground(0, _COLOUR_UNGROUP)
            self.list_widget.addTopLevelItem(unsec_item)
            unsec_item.setExpanded(expanded)

        font = self._section_font()
        for sec_idx, section in enumerate(smap.sections):
            expanded = self._section_expanded.get(section.name, True)
            arrow = "▼" if expanded else "▶"
            label = f"{arrow}  {section.name}  ({section.rule_count})"
            sec_item = QTreeWidgetItem([label])
            sec_item.setData(0, Qt.ItemDataRole.UserRole, -1)
            sec_item.setData(0, SECTION_ROLE, section.first_rule_index)
            sec_item.setFlags(
                sec_item.flags()
                & ~Qt.ItemFlag.ItemIsSelectable
                & ~Qt.ItemFlag.ItemIsDragEnabled
            )
            sec_item.setForeground(0, _COLOUR_SECTION)
            sec_item.setFont(0, font)
            self.list_widget.addTopLevelItem(sec_item)
            sec_item.setExpanded(expanded)
            section_items[sec_idx] = sec_item

        # ── Phase 2: add rule items as children (document order) ───────
        display_num = 1
        for real_idx, rule in enumerate(self._rules):
            if rule.action == "__TAIL__":
                continue

            sec_idx = smap.rule_to_section.get(real_idx, -1)
            parent = (
                unsec_item if sec_idx < 0
                else section_items.get(sec_idx)
            )
            if parent is None:
                continue

            child = self._make_rule_item(parent, real_idx, rule, display_num)
            if real_idx == current_real:
                item_to_select = child
            display_num += 1

        # ── Phase 3: select ────────────────────────────────────────────
        if item_to_select:
            self.list_widget.setCurrentItem(item_to_select)
            self.list_widget.scrollToItem(item_to_select)

    def _make_rule_item(
        self,
        parent: QTreeWidgetItem | None,
        real_idx: int,
        rule: FilterRule,
        display_num: int,
    ) -> QTreeWidgetItem:
        label = RuleListWidget._make_label(display_num, rule)
        item = QTreeWidgetItem([label])
        item.setData(0, Qt.ItemDataRole.UserRole, real_idx)

        item.setForeground(
            0, _COLOUR_SHOW if rule.action == "Show" else _COLOUR_OTHER
        )
        if real_idx == self._current_highlight:
            item.setBackground(0, _HIGHLIGHT_CURRENT)
        elif real_idx in self._highlight_indices:
            item.setBackground(0, _HIGHLIGHT_OTHER)

        if parent is None:
            self.list_widget.addTopLevelItem(item)
        else:
            parent.addChild(item)

        self._real_to_item[real_idx] = item
        return item

    def _make_section_item_label(self, section_name: str, rule_count: int) -> str:
        expanded = self._section_expanded.get(section_name, True)
        arrow = "▼" if expanded else "▶"
        return f"{arrow}  {section_name}  ({rule_count})"

    # ------------------------------------------------------------------
    # Search-highlight helpers
    # ------------------------------------------------------------------

    def _mark_sections_expanded_for(self, real_indices: set[int]) -> None:
        """Ensure sections containing any matched index are expanded."""
        smap = self._section_map
        if not smap:
            return
        for real_idx in real_indices:
            sec_idx = smap.rule_to_section.get(real_idx, -1)
            if sec_idx >= 0:
                sec = smap.sections[sec_idx]
                self._section_expanded[sec.name] = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_current_real_index(self) -> int:
        item = self.list_widget.currentItem()
        if item is None:
            return -1
        val = item.data(0, Qt.ItemDataRole.UserRole)
        if val is None or val < 0:
            return -1
        return val

    @staticmethod
    def _section_font() -> QFont:
        f = QFont()
        f.setBold(True)
        return f

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

    def _on_item_changed(self, current: QTreeWidgetItem, previous):
        if current is None:
            return
        # Skip section header items
        if current.data(0, SECTION_ROLE) is not None:
            return
        val = current.data(0, Qt.ItemDataRole.UserRole)
        if val is None or val < 0:
            return
        self.rule_selected.emit(val)

    def _on_section_toggled(self, item: QTreeWidgetItem, expanded: bool) -> None:
        fid = item.data(0, SECTION_ROLE)
        if fid is None or not self._section_map:
            return
        for sec in self._section_map.sections:
            if sec.first_rule_index == fid:
                self._section_expanded[sec.name] = expanded
                # Update arrow in label
                arrow = "▼" if expanded else "▶"
                item.setText(0, f"{arrow}  {sec.name}  ({sec.rule_count})")
                break

    def _on_add(self):
        self.add_rule_requested.emit()

    def _on_delete(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        if item.data(0, SECTION_ROLE) is not None:
            return   # can't delete a section header
        val = item.data(0, Qt.ItemDataRole.UserRole)
        if val is None or val < 0:
            return
        self.delete_rule_requested.emit(val)

    def _on_copy(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        if item.data(0, SECTION_ROLE) is not None:
            return
        val = item.data(0, Qt.ItemDataRole.UserRole)
        if val is None or val < 0:
            return
        self.copy_rule_requested.emit(val)

    def _on_move_requested(self, from_real: int, to_real: int):
        if from_real != to_real:
            self.move_rule_requested.emit(from_real, to_real)
