"""RuleCardBrowser — v5.0.0  (P17.7/P17.8 Performance)

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

P14.0 (Rule Creation Wizard):
  - ＋ 新增 button now opens RuleCreationDialog instead of inserting a blank rule
  - On confirm: emits add_rule_from_wizard(FilterRule) then add_rule_requested()
  - On cancel: nothing is emitted (no rule inserted)
  - add_rule_from_wizard carries the template; add_rule_requested keeps backward compat

P17.7/P17.8 Performance:
  - _rebuild_card_pool(): creates all card widgets once per load_rules() call
  - refresh(): show/hide existing cards instead of destroy/recreate — O(N×setVisible)
  - pool_insert_card(), pool_remove_card(), pool_swap_cards(): incremental mutations
    without full pool rebuild — Add/Delete/Copy/Move run in O(1) widget ops + O(N) renumber
  - _renumber_all_cards(): O(N) setText() calls (not widget creation)

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
from ui.rule_creation_dialog import RuleCreationDialog


class RuleCardBrowser(QWidget):
    # Signals — compatible with RuleListWidget except rule_selected is renamed
    selected_rule_changed    = Signal(int)       # real_index (was rule_selected)
    add_rule_requested       = Signal()          # backward-compat; fires after wizard confirms
    add_rule_from_wizard     = Signal(object)    # carries FilterRule template on wizard confirm
    delete_rule_requested    = Signal(int)       # real_index
    copy_rule_requested      = Signal(int)       # real_index
    move_rule_requested      = Signal(int, int)  # stub: no drag-UI in P3

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

        # Live card map: real_index → RuleCardWidget (persists across refresh() calls)
        self._cards: dict[int, RuleCardWidget] = {}

        # P17.7: persistent pool state
        # list of (section_idx, QLabel) for show/hide in refresh()
        self._section_headers: list[tuple[int, QLabel]] = []
        # persistent empty-state label (show/hide instead of create/destroy)
        self._empty_lbl: QLabel | None = None

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
        self._rebuild_card_pool()
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

    def update_single_card(self, real_index: int, rule: FilterRule) -> bool:
        """Update only the card at *real_index* in-place without rebuilding all cards.

        Calls RuleCardWidget.update_rule() which refreshes label text/visibility
        without destroying the widget — avoids Qt widget allocation on every edit.

        Returns True on success, False when the card doesn't exist.
        """
        card = self._cards.get(real_index)
        if card is None:
            return False
        card.update_rule(rule)
        return True

    def refresh(self) -> None:
        """Show/hide existing cards/headers based on current filters.

        P17.7: O(N×setVisible) instead of O(N×widget_creation).
        No widget allocation — only visibility toggling.
        Also re-applies highlight state for visible cards so that
        quick-filter and nav-search highlights stay consistent.
        """
        if not self._cards and not self._empty_lbl:
            # Pool not yet built (called before load_rules)
            return

        any_visible = False
        visible_sections: set[int] = set()
        has_sections = bool(self._section_map and self._section_map.sections)
        has_query = bool(self._search_query)

        for real_idx, card in self._cards.items():
            if real_idx >= len(self._rules):
                card.hide()
                continue
            rule = self._rules[real_idx]
            show = self._passes_filter(rule)
            card.setVisible(show)

            if show:
                any_visible = True
                if has_sections and self._section_map:
                    sec_idx = self._section_map.rule_to_section.get(real_idx, -1)
                    visible_sections.add(sec_idx)

                # Re-apply highlight: quick filter > nav current > nav match > none
                if has_query:
                    target_hl = "match"
                elif real_idx == self._highlight_current:
                    target_hl = "current"
                elif real_idx in self._highlight_matches:
                    target_hl = "match"
                else:
                    target_hl = "none"

                current_hl = card.property("cardHighlight") or "none"
                if current_hl != target_hl:
                    card.set_highlight(target_hl)

        # Show section headers only when they have at least one visible card
        for sec_idx, header in self._section_headers:
            header.setVisible(sec_idx in visible_sections)

        # Update empty state label
        if self._empty_lbl is not None:
            if not any_visible:
                if not self._rules or all(r.action == "__TAIL__" for r in self._rules):
                    self._empty_lbl.setText("尚未載入任何規則")
                elif self._search_query:
                    self._empty_lbl.setText("沒有符合搜尋條件的規則")
                else:
                    self._empty_lbl.setText("此分類沒有符合的規則")
                self._empty_lbl.show()
            else:
                self._empty_lbl.hide()

        # Clear selection if the selected card is now hidden by filter
        if (self._selected_real in self._cards
                and self._cards[self._selected_real].isHidden()):
            self._selected_real = -1

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
        card = self._cards.get(real_index)
        return card is not None and not card.isHidden()

    def get_visible_count(self) -> int:
        """Number of cards currently shown (after both filters)."""
        return sum(1 for card in self._cards.values() if not card.isHidden())

    def get_total_count(self) -> int:
        """Total number of non-tail rules, ignoring both filters."""
        return sum(1 for r in self._rules if r.action != "__TAIL__")

    # ------------------------------------------------------------------
    # P17.7: Pool construction and incremental mutation methods
    # ------------------------------------------------------------------

    def _rebuild_card_pool(self) -> None:
        """Destroy all existing widgets and build a fresh pool for all rules.

        Called only by load_rules() (file open / undo-redo).  Subsequent
        filter changes use refresh() (show/hide only — no widget allocation).
        """
        self._clear_all_layout_items()
        self._cards.clear()
        self._section_headers.clear()

        has_sections = bool(self._section_map and self._section_map.sections)
        last_sec_idx: int = -999
        display_num = 1

        for real_idx, rule in enumerate(self._rules):
            if rule.action == "__TAIL__":
                continue

            if has_sections and self._section_map:
                sec_idx = self._section_map.rule_to_section.get(real_idx, -1)
                if sec_idx != last_sec_idx:
                    last_sec_idx = sec_idx
                    name = (
                        self._section_map.sections[sec_idx].name
                        if sec_idx >= 0
                        else "（未分類）"
                    )
                    header = self._make_section_header(name)
                    header.hide()
                    self._section_headers.append((sec_idx, header))
                    self._list_layout.addWidget(header)

            card = self._make_card(real_idx, rule, display_num)
            card.hide()  # refresh() will show based on filters
            self._list_layout.addWidget(card)
            display_num += 1

        # Persistent empty-state label (show/hide instead of create/destroy)
        self._empty_lbl = QLabel()
        self._empty_lbl.setObjectName("RuleCardEmptyLabel")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._list_layout.addWidget(self._empty_lbl)
        self._empty_lbl.hide()

        # Trailing spacer pushes cards to top
        self._list_layout.addStretch(1)

    def pool_insert_card(self, insert_at: int, rule: FilterRule,
                         new_rules: list[FilterRule]) -> None:
        """Insert one new card at insert_at without rebuilding the full pool.

        Shifts all existing cards at real_index >= insert_at by +1,
        inserts the new card widget at the correct layout position,
        then renumbers all cards.  O(1) widget creation + O(N) setText.
        """
        self._rules = new_rules

        # Shift cards with real_index >= insert_at
        new_cards: dict[int, RuleCardWidget] = {}
        for ri in sorted(self._cards.keys()):
            card = self._cards[ri]
            if ri >= insert_at:
                card._real_index = ri + 1
                new_cards[ri + 1] = card
            else:
                new_cards[ri] = card

        # Find layout insertion position: just before the card now at insert_at+1
        next_card = new_cards.get(insert_at + 1)
        if next_card is not None:
            layout_pos = self._list_layout.indexOf(next_card)
        elif self._empty_lbl is not None:
            layout_pos = self._list_layout.indexOf(self._empty_lbl)
        else:
            layout_pos = max(0, self._list_layout.count() - 1)

        # Create and insert the new card
        new_card = self._make_card(insert_at, rule, insert_at + 1)
        new_card.setVisible(self._passes_filter(rule))
        if layout_pos >= 0:
            self._list_layout.insertWidget(layout_pos, new_card)
        else:
            self._list_layout.addWidget(new_card)

        new_cards[insert_at] = new_card
        self._cards = new_cards

        # Selection tracking: inserted rule shifts selected index
        if self._selected_real >= insert_at:
            self._selected_real += 1

        self._renumber_all_cards()
        self._update_empty_state()
        self._update_button_states()

    def pool_remove_card(self, remove_at: int, new_rules: list[FilterRule]) -> None:
        """Remove one card at remove_at from the pool without a full rebuild.

        Shifts all cards at real_index > remove_at by -1.
        O(1) widget destruction + O(N) setText.
        """
        self._rules = new_rules

        card = self._cards.pop(remove_at, None)
        if card is not None:
            card.hide()
            card.setParent(None)
            card.deleteLater()

        # Shift cards with real_index > remove_at
        new_cards: dict[int, RuleCardWidget] = {}
        for ri in sorted(self._cards.keys()):
            c = self._cards[ri]
            if ri > remove_at:
                c._real_index = ri - 1
                new_cards[ri - 1] = c
            else:
                new_cards[ri] = c
        self._cards = new_cards

        # Update selection
        if self._selected_real == remove_at:
            self._selected_real = -1
        elif self._selected_real > remove_at:
            self._selected_real -= 1

        self._renumber_all_cards()
        self._update_empty_state()
        self._update_button_states()

    def pool_swap_cards(self, idx_a: int, idx_b: int,
                        new_rules: list[FilterRule]) -> None:
        """Swap two cards in the layout pool (for move-up/down).

        Repositions the widgets in QVBoxLayout and swaps their entries in
        _cards / _real_index.  O(1) layout op + O(2) renumber.
        """
        self._rules = new_rules

        card_a = self._cards.get(idx_a)
        card_b = self._cards.get(idx_b)
        if card_a is None or card_b is None:
            return

        pos_a = self._list_layout.indexOf(card_a)
        pos_b = self._list_layout.indexOf(card_b)
        if pos_a < 0 or pos_b < 0:
            return

        # Ensure pos_a < pos_b for consistent handling
        if pos_a > pos_b:
            pos_a, pos_b = pos_b, pos_a
            card_a, card_b = card_b, card_a
            idx_a, idx_b = idx_b, idx_a

        # Move card_b (the one at the higher position) to before card_a
        self._list_layout.removeWidget(card_b)
        self._list_layout.insertWidget(pos_a, card_b)

        # Update _cards and _real_index
        self._cards[idx_a] = card_b
        self._cards[idx_b] = card_a
        card_a._real_index = idx_b
        card_b._real_index = idx_a

        # Update the two affected display_nums only
        card_a.update_display_num(self._card_display_num(idx_b))
        card_b.update_display_num(self._card_display_num(idx_a))

        self._update_button_states()

    def _card_display_num(self, real_index: int) -> int:
        """Return sequential display number for real_index (1-based, counting non-TAIL)."""
        return sum(1 for ri in sorted(self._cards.keys()) if ri <= real_index)

    def _renumber_all_cards(self) -> None:
        """Update display_num labels for all cards in ascending real_index order."""
        for num, ri in enumerate(sorted(self._cards.keys()), start=1):
            self._cards[ri].update_display_num(num)

    def _update_empty_state(self) -> None:
        """Show or hide the empty-state label based on current card visibility."""
        if self._empty_lbl is None:
            return
        any_visible = any(not c.isHidden() for c in self._cards.values())
        if not any_visible:
            if not self._rules or all(r.action == "__TAIL__" for r in self._rules):
                self._empty_lbl.setText("尚未載入任何規則")
            elif self._search_query:
                self._empty_lbl.setText("沒有符合搜尋條件的規則")
            else:
                self._empty_lbl.setText("此分類沒有符合的規則")
            self._empty_lbl.show()
        else:
            self._empty_lbl.hide()

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

    def _clear_all_layout_items(self) -> None:
        """Remove all widgets and spacers from the card layout."""
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self._empty_lbl = None

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
        has_sel = (
            self._selected_real >= 0
            and self._selected_real in self._cards
            and not self._cards[self._selected_real].isHidden()
        )
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
        rule = RuleCreationDialog.get_rule(self)
        if rule is not None:
            self.add_rule_from_wizard.emit(rule)
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
