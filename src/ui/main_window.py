import copy
import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QFileDialog, QMessageBox, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut

from core.document import FilterDocument
from core.models import FilterRule
from core.commands import (
    AddRuleCommand, DeleteRuleCommand,
    DuplicateRuleCommand, UpdateRuleCommand,
    MoveRuleCommand,
)
from core.search import search_rules, SearchQuery
from core.sections import build_section_map, SectionMap
from services.settings_service import WorkspaceSettings
from widgets.rule_list import RuleListWidget
from widgets.search_bar import SearchBar
from editor.rule_editor import RuleEditorWidget
from ui.preview_panel import PreviewPanel


class MainWindow(QMainWindow):
    def __init__(self, settings: WorkspaceSettings | None = None):
        super().__init__()
        self._doc = FilterDocument()
        self._selected_index: int = -1
        self._editing_snapshot: FilterRule | None = None
        self._settings = settings or WorkspaceSettings()
        self._section_map: SectionMap | None = None

        # Search state
        self._search_results: list[int] = []
        self._search_cursor:  int       = -1

        self.setWindowTitle("POE2 Filter Studio")
        self.resize(1250, 720)

        self._build_ui()
        self._build_menus()
        self._build_toolbar()
        self._build_shortcuts()

        # Restore workspace state (geometry, splitter, section states)
        self._settings.restore_geometry(self)
        self._settings.restore_splitter(self._splitter)
        self._restore_section_states()

        self._refresh_status()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("ContentShell")
        self.setCentralWidget(central)
        v = QVBoxLayout(central)
        v.setContentsMargins(4, 4, 4, 2)
        v.setSpacing(2)

        # v2 shell — NavBar placeholder (brand + existing search bar)
        nav_bar = QWidget()
        nav_bar.setObjectName("NavBarPlaceholder")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(8, 4, 8, 4)
        nav_layout.setSpacing(12)

        brand_lbl = QLabel("POE2 Filter Studio")
        brand_lbl.setObjectName("NavBarBrand")
        nav_layout.addWidget(brand_lbl)

        self.search_bar = SearchBar()
        nav_layout.addWidget(self.search_bar, stretch=1)

        v.addWidget(nav_bar)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # v2 shell — Category sidebar placeholder (P2 will replace)
        category_placeholder = QWidget()
        category_placeholder.setObjectName("CategoryPlaceholder")
        category_placeholder.setMinimumWidth(140)
        category_placeholder.setMaximumWidth(200)
        cat_layout = QVBoxLayout(category_placeholder)
        cat_layout.setContentsMargins(8, 12, 8, 8)
        cat_layout.setSpacing(6)
        cat_title = QLabel("分類")
        cat_title.setObjectName("CategoryPlaceholderTitle")
        cat_hint = QLabel("（即將推出）")
        cat_hint.setObjectName("CategoryPlaceholderHint")
        cat_layout.addWidget(cat_title)
        cat_layout.addWidget(cat_hint)
        cat_layout.addStretch()

        self.rule_list = RuleListWidget()
        self.rule_list.setMinimumWidth(200)
        self.rule_list.setMaximumWidth(340)

        self.rule_editor = RuleEditorWidget()

        self.preview_panel = PreviewPanel()
        self.preview_panel.setMinimumWidth(180)
        self.preview_panel.setMaximumWidth(340)

        self._splitter.addWidget(category_placeholder)
        self._splitter.addWidget(self.rule_list)
        self._splitter.addWidget(self.rule_editor)
        self._splitter.addWidget(self.preview_panel)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 3)
        self._splitter.setStretchFactor(3, 1)
        self._splitter.setSizes([160, 240, 560, 260])
        v.addWidget(self._splitter, stretch=1)

        # v2 shell — bottom status placeholder (replaces QStatusBar content area)
        status_shell = QWidget()
        status_shell.setObjectName("StatusBarPlaceholder")
        status_layout = QHBoxLayout(status_shell)
        status_layout.setContentsMargins(8, 0, 8, 0)
        self._status_lbl = QLabel()
        status_layout.addWidget(self._status_lbl)
        status_layout.addStretch()
        v.addWidget(status_shell)

        self.rule_list.rule_selected.connect(self._on_rule_selected)
        self.rule_list.add_rule_requested.connect(self._on_add_rule)
        self.rule_list.delete_rule_requested.connect(self._on_delete_rule)
        self.rule_list.copy_rule_requested.connect(self._on_copy_rule)
        self.rule_list.move_rule_requested.connect(self._on_move_rule)
        self.rule_editor.rule_changed.connect(self._on_rule_changed)

        self.search_bar.search_changed.connect(self._on_search_changed)
        self.search_bar.next_requested.connect(self._on_search_next)
        self.search_bar.prev_requested.connect(self._on_search_prev)

    def _build_menus(self):
        mb = self.menuBar()

        fm = mb.addMenu("檔案(&F)")

        a = QAction("開啟(&O)…", self)
        a.setShortcut(QKeySequence.StandardKey.Open)
        a.triggered.connect(self.open_file)
        fm.addAction(a)

        self._recent_menu = fm.addMenu("最近開啟(&R)")
        self._rebuild_recent_menu()

        a = QAction("儲存(&S)", self)
        a.setShortcut(QKeySequence.StandardKey.Save)
        a.triggered.connect(self.save_file)
        fm.addAction(a)

        a = QAction("另存新檔(&A)…", self)
        a.setShortcut(QKeySequence("Ctrl+Shift+S"))
        a.triggered.connect(self.save_file_as)
        fm.addAction(a)

        fm.addSeparator()

        a = QAction("結束(&X)", self)
        a.setShortcut(QKeySequence("Alt+F4"))
        a.triggered.connect(self.close)
        fm.addAction(a)

        em = mb.addMenu("編輯(&E)")

        self._undo_action = QAction("復原(&U)", self)
        self._undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        self._undo_action.setEnabled(False)
        self._undo_action.triggered.connect(self._on_undo)
        em.addAction(self._undo_action)

        self._redo_action = QAction("取消復原(&R)", self)
        self._redo_action.setShortcut(QKeySequence("Ctrl+Y"))
        self._redo_action.setEnabled(False)
        self._redo_action.triggered.connect(self._on_redo)
        em.addAction(self._redo_action)

        em.addSeparator()

        a = QAction("搜尋(&F)…", self)
        a.setShortcut(QKeySequence("Ctrl+F"))
        a.triggered.connect(self.search_bar.focus_input)
        em.addAction(a)

    def _build_toolbar(self):
        tb = self.addToolBar("工具列")
        tb.setMovable(False)

        a = QAction("開啟", self)
        a.triggered.connect(self.open_file)
        tb.addAction(a)

        a = QAction("儲存", self)
        a.triggered.connect(self.save_file)
        tb.addAction(a)

        tb.addSeparator()

        a = QAction("新增規則", self)
        a.triggered.connect(self._on_add_rule)
        tb.addAction(a)

        tb.addSeparator()

        self._tb_undo = QAction("復原", self)
        self._tb_undo.setEnabled(False)
        self._tb_undo.triggered.connect(self._on_undo)
        tb.addAction(self._tb_undo)

        self._tb_redo = QAction("取消復原", self)
        self._tb_redo.setEnabled(False)
        self._tb_redo.triggered.connect(self._on_redo)
        tb.addAction(self._tb_redo)

    def _build_shortcuts(self):
        QShortcut(QKeySequence("F3"),       self).activated.connect(self._on_search_next)
        QShortcut(QKeySequence("Shift+F3"), self).activated.connect(self._on_search_prev)

    # ------------------------------------------------------------------
    # Settings helpers
    # ------------------------------------------------------------------

    def _restore_section_states(self) -> None:
        states = self._settings.restore_section_states()
        if states.get("conditions", True):
            self.rule_editor._cond_panel.expand()
        else:
            self.rule_editor._cond_panel.collapse()
        if states.get("appearance", True):
            self.rule_editor._app_panel.expand()
        else:
            self.rule_editor._app_panel.collapse()
        if states.get("audio", False):
            self.rule_editor._audio_panel.expand()
        else:
            self.rule_editor._audio_panel.collapse()

    def _save_workspace(self) -> None:
        self._settings.save_geometry(self)
        self._settings.save_splitter(self._splitter)
        self._settings.save_section_states({
            "conditions": self.rule_editor._cond_panel.save_state()["expanded"],
            "appearance": self.rule_editor._app_panel.save_state()["expanded"],
            "audio":      self.rule_editor._audio_panel.save_state()["expanded"],
        })
        if self._doc.file_path:
            self._settings.save_section_collapse_states(
                self._doc.file_path,
                self.rule_list.get_section_states(),
            )

    # ------------------------------------------------------------------
    # Recent Files menu
    # ------------------------------------------------------------------

    def _rebuild_recent_menu(self) -> None:
        self._recent_menu.clear()
        paths = self._settings.recent_files()
        if not paths:
            placeholder = QAction("（無最近開啟檔案）", self)
            placeholder.setEnabled(False)
            self._recent_menu.addAction(placeholder)
        else:
            for path in paths:
                label = os.path.basename(path)
                a = QAction(label, self)
                a.setToolTip(path)
                a.triggered.connect(lambda _=False, p=path: self._open_recent(p))
                self._recent_menu.addAction(a)
            self._recent_menu.addSeparator()
            clear_action = QAction("清除清單", self)
            clear_action.triggered.connect(self._clear_recent_files)
            self._recent_menu.addAction(clear_action)

    def _open_recent(self, path: str) -> None:
        if not os.path.isfile(path):
            QMessageBox.warning(
                self, "找不到檔案",
                f"檔案不存在或已被移動：\n{path}",
            )
            return
        if not self._confirm_discard():
            return
        self.load_file(path)

    def _clear_recent_files(self) -> None:
        self._settings.clear_recent_files()
        self._rebuild_recent_menu()

    # ------------------------------------------------------------------
    # UI synchronization helpers
    # ------------------------------------------------------------------

    def _load_rule_to_ui(self, real_index: int) -> None:
        if 0 <= real_index < len(self._doc.rules):
            rule = self._doc.rules[real_index]
            self._selected_index   = real_index
            self._editing_snapshot = copy.deepcopy(rule)
            self.rule_editor.load_rule(rule)
            self.preview_panel.show_rule(rule)
        else:
            self._clear_rule_ui()

    def _clear_rule_ui(self) -> None:
        self._selected_index   = -1
        self._editing_snapshot = None
        self.rule_editor.setEnabled(False)
        self.preview_panel.show_empty()

    def _navigate_to(self, real_index: int) -> None:
        self.rule_list.select_real_index(real_index)
        self._load_rule_to_ui(real_index)

    def _reload_rule_list(self) -> None:
        """Rebuild section_map and reload RuleListWidget. Call after every mutation."""
        self._section_map = build_section_map(self._doc.rules)
        self.rule_list.load_rules(self._doc.rules, self._section_map)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def open_file(self):
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "開啟 Filter 檔案", "",
            "Filter 檔案 (*.filter *.txt *.filter.backup);;所有檔案 (*.*)"
        )
        if path:
            self.load_file(path)

    def load_file(self, path: str):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as e:
            QMessageBox.critical(self, "錯誤", f"無法開啟檔案：\n{e}")
            return

        self._doc.load_from_text(text, path)
        self._section_map = build_section_map(self._doc.rules)
        self.rule_list.load_rules(self._doc.rules, self._section_map)
        self._clear_rule_ui()
        self.search_bar.clear()
        self._search_results = []
        self._search_cursor  = -1

        # Restore per-file section collapse states
        saved = self._settings.restore_section_collapse_states(path)
        if saved:
            self.rule_list.apply_section_states(saved)

        self._refresh_status()
        self._refresh_undo_actions()
        self.setWindowTitle(f"POE2 Filter Studio — {os.path.basename(path)}")

        self._settings.add_recent_file(path)
        self._rebuild_recent_menu()

    def save_file(self):
        if not self._doc.file_path:
            self.save_file_as()
        else:
            self._write_to(self._doc.file_path)

    def save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "另存 Filter 檔案", self._doc.file_path or "",
            "Filter 檔案 (*.filter);;所有檔案 (*.*)"
        )
        if path:
            self._write_to(path)

    def _write_to(self, path: str):
        try:
            text = self._doc.export_text()
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
        except OSError as e:
            QMessageBox.critical(self, "錯誤", f"無法儲存檔案：\n{e}")
            return
        self._doc.set_file_path(path)
        self._doc.clear_dirty()
        self._refresh_status()
        self.setWindowTitle(f"POE2 Filter Studio — {os.path.basename(path)}")

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    def _on_undo(self):
        # Commit any in-progress edit first so it appears as its own undo step.
        self.rule_editor.flush_pending()
        last_cmd = self._doc.peek_undo_command()
        self._doc.undo()
        if isinstance(last_cmd, MoveRuleCommand) and not last_cmd.is_noop:
            self._selected_index = last_cmd.from_index
        self._refresh_after_undo_redo()

    def _on_redo(self):
        # Commit any in-progress edit first so the redo target is unambiguous.
        self.rule_editor.flush_pending()
        last_cmd = self._doc.peek_redo_command()
        self._doc.redo()
        if isinstance(last_cmd, MoveRuleCommand) and not last_cmd.is_noop:
            self._selected_index = last_cmd.to_index
        self._refresh_after_undo_redo()

    def _refresh_after_undo_redo(self):
        self._reload_rule_list()
        if 0 <= self._selected_index < len(self._doc.rules):
            self.rule_list.select_real_index(self._selected_index)
            self._load_rule_to_ui(self._selected_index)
        else:
            self._clear_rule_ui()
        self._refresh_search()
        self._refresh_status()
        self._refresh_undo_actions()

    def _refresh_undo_actions(self):
        can_u = self._doc.can_undo()
        can_r = self._doc.can_redo()
        self._undo_action.setEnabled(can_u)
        self._redo_action.setEnabled(can_r)
        self._tb_undo.setEnabled(can_u)
        self._tb_redo.setEnabled(can_r)

    # ------------------------------------------------------------------
    # Rule operations
    # ------------------------------------------------------------------

    def _on_rule_selected(self, real_index: int):
        # Flush any pending debounced edit on the CURRENT rule before switching.
        # Must come before _load_rule_to_ui() so _selected_index still points
        # at the old rule when _on_rule_changed() executes.
        self.rule_editor.flush_pending()
        self._load_rule_to_ui(real_index)

    def _on_rule_changed(self):
        idx = self._selected_index
        if not (0 <= idx < len(self._doc.rules)):
            return

        old_rule = self._editing_snapshot
        if old_rule is None:
            old_rule = copy.deepcopy(self._doc.rules[idx])

        new_rule = copy.deepcopy(self._doc.rules[idx])
        cmd = UpdateRuleCommand(self._doc, idx, old_rule, new_rule)
        self._doc.execute(cmd)

        self._editing_snapshot = copy.deepcopy(self._doc.rules[idx])
        self.preview_panel.show_rule(self._doc.rules[idx])

        # UpdateRuleCommand doesn't change pre_lines → section_map unchanged
        # _refresh_search calls rule_list.refresh() via clear/set_highlights
        self._refresh_search()
        self._refresh_status()
        self._refresh_undo_actions()

    def _on_add_rule(self):
        new_rule = FilterRule(action="Show", pre_lines=[""])
        insert_at = (
            self._selected_index + 1
            if 0 <= self._selected_index < len(self._doc.rules)
            else self._doc.tail_insert_pos()
        )
        cmd = AddRuleCommand(self._doc, insert_at, new_rule)
        self._doc.execute(cmd)

        self._reload_rule_list()
        self.rule_list.select_real_index(insert_at)
        self._load_rule_to_ui(insert_at)
        self._refresh_search()
        self._refresh_status()
        self._refresh_undo_actions()

    def _on_delete_rule(self, real_index: int):
        if not (0 <= real_index < len(self._doc.rules)):
            return
        reply = QMessageBox.question(
            self, "確認刪除", "確定要刪除這條規則嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        cmd = DeleteRuleCommand(self._doc, real_index)
        self._doc.execute(cmd)

        self._reload_rule_list()
        self._clear_rule_ui()
        self._refresh_search()
        self._refresh_status()
        self._refresh_undo_actions()

    def _on_move_rule(self, from_real: int, to_real: int):
        cmd = MoveRuleCommand(self._doc, from_real, to_real)
        if cmd.is_noop:
            return
        self._doc.execute(cmd)

        self._reload_rule_list()
        self.rule_list.select_real_index(cmd.to_index)
        self._load_rule_to_ui(cmd.to_index)
        self._refresh_search()
        self._refresh_status()
        self._refresh_undo_actions()

    def _on_copy_rule(self, real_index: int):
        if not (0 <= real_index < len(self._doc.rules)):
            return
        cmd = DuplicateRuleCommand(self._doc, real_index)
        self._doc.execute(cmd)
        new_index = cmd.new_index

        self._reload_rule_list()
        self.rule_list.select_real_index(new_index)
        self._load_rule_to_ui(new_index)
        self._refresh_search()
        self._refresh_status()
        self._refresh_undo_actions()

    # ------------------------------------------------------------------
    # Search — handlers
    # ------------------------------------------------------------------

    def _on_search_changed(self, text: str) -> None:
        if not text.strip():
            self._search_results = []
            self._search_cursor  = -1
            self.rule_list.clear_highlights()
            self.search_bar.clear_count()
            return

        results = search_rules(self._doc.rules, SearchQuery(text=text))
        self._search_results = results
        self._search_cursor  = 0

        if not results:
            self.rule_list.set_highlights(set(), -1)
            self.search_bar.set_count(0, 0)
            return

        current_real = results[0]
        self.rule_list.set_highlights(set(results), current_real)
        self.search_bar.set_count(len(results), 1)
        self._navigate_to(current_real)

    def _on_search_next(self) -> None:
        if not self._search_results:
            return
        self._search_cursor = (self._search_cursor + 1) % len(self._search_results)
        self._go_to_cursor()

    def _on_search_prev(self) -> None:
        if not self._search_results:
            return
        self._search_cursor = (self._search_cursor - 1) % len(self._search_results)
        self._go_to_cursor()

    def _go_to_cursor(self) -> None:
        current_real = self._search_results[self._search_cursor]
        self.rule_list.set_highlights(set(self._search_results), current_real)
        self.search_bar.set_count(len(self._search_results), self._search_cursor + 1)
        self._navigate_to(current_real)

    def _refresh_search(self) -> None:
        text = self.search_bar.current_text()
        if not text.strip():
            self.rule_list.clear_highlights()
            self.search_bar.clear_count()
            self._search_results = []
            self._search_cursor  = -1
            return

        results = search_rules(self._doc.rules, SearchQuery(text=text))
        old_real = (
            self._search_results[self._search_cursor]
            if 0 <= self._search_cursor < len(self._search_results) else -1
        )
        self._search_results = results

        if not results:
            self._search_cursor = -1
            self.rule_list.set_highlights(set(), -1)
            self.search_bar.set_count(0, 0)
            return

        self._search_cursor = (
            results.index(old_real) if old_real in results else 0
        )
        current_real = results[self._search_cursor]
        self.rule_list.set_highlights(set(results), current_real)
        self.search_bar.set_count(len(results), self._search_cursor + 1)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _refresh_status(self):
        name  = os.path.basename(self._doc.file_path) if self._doc.file_path else "（未開啟）"
        dirty = " [已修改]" if self._doc.dirty else ""
        count = self._doc.visible_count
        self._status_lbl.setText(f"{name}{dirty}  ·  {count} 條規則")

    def _confirm_discard(self) -> bool:
        if not self._doc.dirty:
            return True
        reply = QMessageBox.question(
            self, "未儲存的修改",
            "目前有未儲存的修改，確定要放棄並繼續嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def closeEvent(self, event):
        # Commit any pending debounced edit before checking dirty state.
        # Without this, an in-progress edit would be silently lost because
        # doc.dirty is still False until the timer fires.
        self.rule_editor.flush_pending()
        if self._confirm_discard():
            self._save_workspace()
            event.accept()
        else:
            event.ignore()
