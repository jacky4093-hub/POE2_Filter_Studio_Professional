"""RuleCardBrowser — v3.0.0

QScrollArea-based card list. Drop-in replacement for RuleListWidget:
  - Same public signals (except rule_selected renamed → selected_rule_changed)
  - Same public methods (load_rules, set_category_filter, set_highlights,
    clear_highlights, select_real_index, refresh, get_section_states,
    apply_section_states)

P10 additions:
  - set_search_filter(query, options) / clear_search_filter()
  - get_visible_count() / get_total_count()
  - category filter and search filter combine with AND logic
  - matching cards get set_highlight("match"); cleared on empty query

P13.5 (Rule Actions Polish):
  - ↑ / ↓ move buttons (emit move_rule_requested)
  - Button states auto-update on selection change / load
  - Tooltips on every action button
  - Delete button styled as danger (objectName "BtnDanger")

Section collapse is not supported in the card view; get_section_states()
always returns {} and apply_section_states() is a no-op.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QScrollArea, QLabel,
)
from PySide6.QtCore import Signal, Qt

from core.models import FilterRule
from core.categorizer import Category, classify_rule
from core.rule_search import rule_matches_query
from core.sections import SectionMap
from ui.rule_card_widget import RuleCardWidget


class RuleCardBrowser(QWidget):
    # Signals — compatible with RuleListWidget except rule_selected is renamed
    selected_rule_changed = Signal(int)    # real_index (was rule_selected)
    add_rule_requested    = Signal()
    delete_rule_requested = Signal(int)    # real_index
    copy_rule_requested   = Signal(int)    # real_index
    move_rule_requested   = Signal(int, int)  # stub: no drag-UI in P3

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RuleCardBrowser")

        self._rules: list[FilterRule] = []
        self._section_map: SectionMap | None = None
        self._category_filter: Category | None = None
        self._selected_real: int = -1

        # Desired highlight state (mirrors RuleListWidget contract)
        self._highlight_matches: set[int] = set()
        self._highlight_current: int = -1

        # P10: search filter state
        self._search_query: str = ""
        self._search_options: dict = {}

        # Live card map: real_index → RuleCardWidget
        self._cards: dict[int, RuleCardWidget] = {}

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # ── Action buttons ────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(3)

        self._btn_add  = QPushButton("＋ 新增")
        self._btn_add.setObjectName("BtnAdd")
        self._btn_add.setToolTip("新增規則")

        self._btn_copy = QPushButton("複製")
        self._btn_copy.setObjectName("BtnCopy")
        self._btn_copy.setToolTip("複製目前規則")

        self._btn_up   = QPushButton("↑")
        self._btn_up.setObjectName("BtnMove")
        self._btn_up.setToolTip("上移目前規則")

        self._btn_dn   = QPushButton("↓")
        self._btn_dn.setObjectName("BtnMove")
        self._btn_dn.setToolTip("下移目前規則")

        self._btn_del  = QPushButton("刪除")
        self._btn_del.setObjectName("BtnDanger")
        self._btn_del.setToolTip("刪除目前規則")

        for btn in (self._btn_add, self._btn_copy,
                    self._btn_up, self._btn_dn, self._btn_del):
            btn.setFixedHeight(26)
            btn_row.addWidget(btn)

        root.addLayout(btn_row)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_del.clicked.connect(self._on_delete)
        self._btn_copy.clicked.connect(self._on_copy)
        self._btn_up.clicked.connect(self._on_move_up)
        self._btn_dn.clicked.connect(self._on_move_down)

        self._update_button_states()   # initial: no rule loaded

        # ── Scroll area ───────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setObjectName("RuleCardScrollArea")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._content.setObjectName("RuleCardContent")
        self._list_layout = QVBoxLayout(self._content)
        self._list_layout.setContentsMargins(4, 4, 4, 4)
        self._list_layout.setSpacing(2)

        self._scroll.setWidget(self._content)
        root.addWidget(self._scroll, stretch=1)

    # ------------------------------------------------------------------
    # Public API — matches RuleListWidget
    # ------------------------------------------------------------------

    def load_rules(self, rules: list[FilterRule], section_map: SectionMap | None = None) -> None:
        self._rules = rules
        self._section_map = section_map
        self.refresh()

    def set_category_filter(self, category: Category | None) -> None:
        """None and Category.ALL both mean "show all"."""
        if category == Category.ALL:
            category = None
        if self._category_filter == category:
            return
        self._category_filter = category
        self.refresh()

    def category_filter(self) -> Category | None:
        return self._category_filter

    def refresh(self) -> None:
        """Rebuild all card widgets from current rules + filters."""
        self._clear_cards()
        self._cards.clear()

        has_sections = bool(
            self._section_map and self._section_map.sections
        )

        any_visible = (
            self._build_with_sections()
            if has_sections
            else self._build_flat()
        )

        # If the selected rule was filtered out, clear the selection state
        # (the card won't be in _cards, so it's already visually gone).
        if self._selected_real not in self._cards:
            self._selected_real = -1

        if not any_visible:
            if not self._rules:
                msg = "尚未載入任何規則"
            elif self._search_query:
                msg = "沒有符合搜尋條件的規則"
            else:
                msg = "此分類沒有符合的規則"
            self._add_empty_label(msg)

        # Trailing spacer pushes cards to top
        self._list_layout.addStretch(1)

        self._update_button_states()

    def select_real_index(self, real_index: int) -> None:
        """Programmatically select a card by real_index."""
        if self._selected_real in self._cards:
            self._cards[self._selected_real].set_selected(False)

        self._selected_real = real_index
        card = self._cards.get(real_index)
        if card:
            card.set_selected(True)
            self._scroll.ensureWidgetVisible(card)
        self._update_button_states()

    def set_highlights(self, matches: set[int], current: int = -1) -> None:
        """Partial update: only touch cards whose highlight status changed."""
        old_matches = self._highlight_matches
        old_current = self._highlight_current

        self._highlight_matches = set(matches)
        self._highlight_current = current

        # Clear cards leaving the match set
        for idx in old_matches - matches:
            card = self._cards.get(idx)
            if card:
                card.set_highlight("none")

        # Paint cards entering the match set
        for idx in matches - old_matches:
            card = self._cards.get(idx)
            if card:
                card.set_highlight("current" if idx == current else "match")

        # Cursor movement within the existing match set (≤ 2 calls)
        if old_current != current:
            if old_current in matches and old_current in old_matches:
                card = self._cards.get(old_current)
                if card:
                    card.set_highlight("match")
            if current in old_matches:
                card = self._cards.get(current)
                if card:
                    card.set_highlight("current")

        if current >= 0:
            card = self._cards.get(current)
            if card:
                self._scroll.ensureWidgetVisible(card)

    def clear_highlights(self) -> None:
        for idx in self._highlight_matches:
            card = self._cards.get(idx)
            if card:
                card.set_highlight("none")
        self._highlight_matches = set()
        self._highlight_current = -1

    def get_section_states(self) -> dict:
        """Section collapse not supported in card view — always returns {}."""
        return {}

    def apply_section_states(self, states: dict) -> None:
        """No-op: card view has no collapsible sections."""

    # ------------------------------------------------------------------
    # P10: search filter
    # ------------------------------------------------------------------

    def set_search_filter(self, query: str, options: dict | None = None) -> None:
        """Apply a text search filter combined with the category filter."""
        self._search_query   = query or ""
        self._search_options = options or {}
        self.refresh()

    def clear_search_filter(self) -> None:
        """Remove the text search filter and refresh."""
        self._search_query   = ""
        self._search_options = {}
        self.refresh()

    def is_rule_visible(self, real_index: int) -> bool:
        """Return whether the given real_index currently has a visible card."""
        return real_index in self._cards

    def get_visible_count(self) -> int:
        """Number of cards currently shown (after both filters)."""
        return len(self._cards)

    def get_total_count(self) -> int:
        """Total number of non-tail rules, ignoring both filters."""
        return sum(1 for r in self._rules if r.action != "__TAIL__")

    # ------------------------------------------------------------------
    # Layout builders
    # ------------------------------------------------------------------

    def _build_flat(self) -> bool:
        display_num = 1
        any_visible = False
        for real_idx, rule in enumerate(self._rules):
            if not self._passes_filter(rule):
                continue
            self._list_layout.addWidget(self._make_card(real_idx, rule, display_num))
            any_visible = True
            display_num += 1
        return any_visible

    def _build_with_sections(self) -> bool:
        smap = self._section_map
        display_num = 1
        any_visible = False
        last_sec_idx: int = -999   # sentinel — triggers first header

        for real_idx, rule in enumerate(self._rules):
            if not self._passes_filter(rule):
                continue

            sec_idx = smap.rule_to_section.get(real_idx, -1) if smap else -1

            # Insert section header when section boundary crossed
            if sec_idx != last_sec_idx:
                last_sec_idx = sec_idx
                name = (
                    smap.sections[sec_idx].name
                    if sec_idx >= 0 and smap
                    else "（未分類）"
                )
                self._list_layout.addWidget(self._make_section_header(name))

            self._list_layout.addWidget(self._make_card(real_idx, rule, display_num))
            any_visible = True
            display_num += 1

        return any_visible

    # ------------------------------------------------------------------
    # Widget factories
    # ------------------------------------------------------------------

    def _make_card(self, real_idx: int, rule: FilterRule, display_num: int) -> RuleCardWidget:
        card = RuleCardWidget(real_idx, rule, display_num)

        # Restore current selection
        if real_idx == self._selected_real:
            card.set_selected(True)

        # Search highlight takes priority over legacy highlight_matches
        if self._search_query:
            card.set_highlight("match")
        elif real_idx == self._highlight_current:
            card.set_highlight("current")
        elif real_idx in self._highlight_matches:
            card.set_highlight("match")

        card.clicked.connect(self._on_card_clicked)
        self._cards[real_idx] = card
        return card

    @staticmethod
    def _make_section_header(name: str) -> QLabel:
        lbl = QLabel(name)
        lbl.setObjectName("RuleCardSectionHeader")
        lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return lbl

    def _add_empty_label(self, message: str) -> None:
        lbl = QLabel(message)
        lbl.setObjectName("RuleCardEmptyLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._list_layout.addWidget(lbl)

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------

    def _passes_filter(self, rule: FilterRule) -> bool:
        if rule.action == "__TAIL__":
            return False
        if self._category_filter is not None:
            if classify_rule(rule) != self._category_filter:
                return False
        if self._search_query:
            if not rule_matches_query(rule, self._search_query, self._search_options):
                return False
        return True

    def _clear_cards(self) -> None:
        """Remove all widgets and spacers from the card layout."""
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    # ------------------------------------------------------------------
    # Button-state helpers
    # ------------------------------------------------------------------

    def _get_non_tail_count(self) -> int:
        return sum(1 for r in self._rules if r.action != "__TAIL__")

    def _last_moveable_index(self) -> int:
        """Return real_index of the last non-tail rule, or -1."""
        for i in range(len(self._rules) - 1, -1, -1):
            if self._rules[i].action != "__TAIL__":
                return i
        return -1

    def _update_button_states(self) -> None:
        """Enable / disable action buttons based on current selection."""
        has_sel = self._selected_real >= 0
        self._btn_del.setEnabled(has_sel)
        self._btn_copy.setEnabled(has_sel)

        if not has_sel or self._get_non_tail_count() <= 1:
            self._btn_up.setEnabled(False)
            self._btn_dn.setEnabled(False)
            return

        last_idx = self._last_moveable_index()
        self._btn_up.setEnabled(self._selected_real > 0)
        self._btn_dn.setEnabled(self._selected_real < last_idx)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_card_clicked(self, real_index: int) -> None:
        if self._selected_real in self._cards:
            self._cards[self._selected_real].set_selected(False)

        self._selected_real = real_index
        card = self._cards.get(real_index)
        if card:
            card.set_selected(True)

        self.selected_rule_changed.emit(real_index)
        self._update_button_states()

    def _on_add(self) -> None:
        self.add_rule_requested.emit()

    def _on_delete(self) -> None:
        if self._selected_real >= 0:
            self.delete_rule_requested.emit(self._selected_real)

    def _on_copy(self) -> None:
        if self._selected_real >= 0:
            self.copy_rule_requested.emit(self._selected_real)

    def _on_move_up(self) -> None:
        if self._selected_real > 0:
            self.move_rule_requested.emit(self._selected_real, self._selected_real - 1)

    def _on_move_down(self) -> None:
        last = self._last_moveable_index()
        if self._selected_real >= 0 and self._selected_real < last:
            self.move_rule_requested.emit(self._selected_real, self._selected_real + 1)
