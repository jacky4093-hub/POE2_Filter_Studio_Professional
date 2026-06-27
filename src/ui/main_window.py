import base64
import copy
import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QStackedWidget, QFileDialog, QMessageBox, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut

from core.document import FilterDocument
from core.file_manager import FilterFileManager
from core.models import FilterRule
from core.commands import (
    AddRuleCommand, DeleteRuleCommand,
    DuplicateRuleCommand, UpdateRuleCommand,
    MoveRuleCommand,
)
from core.search import search_rules, SearchQuery
from core.sections import build_section_map, SectionMap
from core.categorizer import Category, classify_rule
from core.settings_manager import SettingsManager
from services.settings_service import WorkspaceSettings
from ui.preferences_dialog import PreferencesDialog
from ui.rule_card_browser import RuleCardBrowser
from ui.welcome_screen import WelcomeScreen
from ui.rule_actions_toolbar import RuleActionsToolbar
from ui.search_bar import SearchBarWidget
from widgets.search_bar import SearchBar
from ui.rule_detail_editor import RuleDetailEditor
from ui.preview_panel import PreviewPanel
from ui.category_sidebar import CategorySidebarWidget
from presenters.status_presenter import StatusPresenter


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: WorkspaceSettings | None = None,
        settings_mgr: SettingsManager | None = None,
    ):
        super().__init__()
        self._doc = FilterDocument()
        self._file_mgr = FilterFileManager()
        self._selected_index: int = -1
        self._editing_snapshot: FilterRule | None = None
        self._settings = settings or WorkspaceSettings()
        self._settings_mgr = settings_mgr or SettingsManager()
        self._section_map: SectionMap | None = None
        self._status_presenter = StatusPresenter()

        # Search state
        self._search_results: list[int] = []
        self._search_cursor:  int       = -1

        # Category filter (v2.1.0)
        self._active_category: Category = Category.ALL

        self.setWindowTitle("POE2 Filter Studio")
        self.resize(1250, 720)

        self._build_ui()
        self._build_menus()
        self._build_toolbar()
        self._build_shortcuts()

        # Restore workspace state (geometry, splitter, section states)
        self._restore_workspace_state()
        self._restore_section_states()

        self._refresh_status()
        self._try_startup_restore()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self._main_stack = QStackedWidget()
        self.setCentralWidget(self._main_stack)

        # Page 0: Welcome Screen
        self.welcome_screen = WelcomeScreen()
        self._main_stack.addWidget(self.welcome_screen)

        # Page 1: Editor shell
        central = QWidget()
        central.setObjectName("ContentShell")
        self._main_stack.addWidget(central)

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

        self.category_sidebar = CategorySidebarWidget()

        self.rule_actions_toolbar = RuleActionsToolbar()

        self.filter_search_bar = SearchBarWidget()

        self.rule_card_browser = RuleCardBrowser()

        self.rule_detail_editor = RuleDetailEditor()

        self.preview_panel = PreviewPanel()
        self.preview_panel.setMinimumWidth(180)
        self.preview_panel.setMaximumWidth(340)

        # Left column: sidebar → toolbar → search bar → card browser
        left_col = QWidget()
        left_col.setObjectName("LeftColumn")
        left_col.setMinimumWidth(200)
        left_col.setMaximumWidth(360)
        lc_layout = QVBoxLayout(left_col)
        lc_layout.setContentsMargins(0, 0, 0, 0)
        lc_layout.setSpacing(0)
        lc_layout.addWidget(self.category_sidebar)
        lc_layout.addWidget(self.rule_actions_toolbar)
        lc_layout.addWidget(self.filter_search_bar)
        lc_layout.addWidget(self.rule_card_browser, stretch=1)

        self._splitter.addWidget(left_col)
        self._splitter.addWidget(self.rule_detail_editor)
        self._splitter.addWidget(self.preview_panel)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 3)
        self._splitter.setStretchFactor(2, 1)
        self._splitter.setSizes([280, 660, 280])
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

        self.rule_card_browser.selected_rule_changed.connect(self._on_rule_selected)
        self.rule_card_browser.add_rule_requested.connect(self._on_add_rule)
        self.rule_card_browser.delete_rule_requested.connect(self._on_delete_rule)
        self.rule_card_browser.copy_rule_requested.connect(self._on_copy_rule)
        self.rule_card_browser.move_rule_requested.connect(self._on_move_rule)
        self.rule_detail_editor.rule_changed.connect(self._on_detail_rule_changed)

        self.rule_actions_toolbar.new_requested.connect(self._on_add_rule)
        self.rule_actions_toolbar.delete_requested.connect(self._on_toolbar_delete)
        self.rule_actions_toolbar.duplicate_requested.connect(self._on_toolbar_duplicate)
        self.rule_actions_toolbar.move_up_requested.connect(self._on_toolbar_move_up)
        self.rule_actions_toolbar.move_down_requested.connect(self._on_toolbar_move_down)

        self.search_bar.search_changed.connect(self._on_search_changed)
        self.search_bar.next_requested.connect(self._on_search_next)
        self.search_bar.prev_requested.connect(self._on_search_prev)

        self.category_sidebar.category_selected.connect(self._on_category_selected)

        self.filter_search_bar.search_changed.connect(self._on_filter_search_changed)
        self.filter_search_bar.clear_requested.connect(self._on_filter_search_clear)

        # Welcome screen signals
        self.welcome_screen.open_requested.connect(self.open_file)
        self.welcome_screen.new_requested.connect(self.new_file)
        self.welcome_screen.recent_file_requested.connect(self.load_file)

        # Start on welcome screen; _try_startup_restore() may switch to editor
        self._main_stack.setCurrentIndex(0)

    def _build_menus(self):
        mb = self.menuBar()

        fm = mb.addMenu("檔案(&F)")

        a = QAction("新建(&N)", self)
        a.setShortcut(QKeySequence.StandardKey.New)
        a.triggered.connect(self.new_file)
        fm.addAction(a)

        fm.addSeparator()

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

        self._restore_action = QAction("啟動時恢復上次檔案(&L)", self)
        self._restore_action.setCheckable(True)
        self._restore_action.setChecked(
            self._settings_mgr.get_restore_last_file_on_startup()
        )
        self._restore_action.toggled.connect(self._on_toggle_restore)
        fm.addAction(self._restore_action)

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

        em.addSeparator()

        a = QAction("偏好設定(&P)…", self)
        a.setShortcut(QKeySequence("Ctrl+,"))
        a.triggered.connect(self.open_preferences)
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
        # RuleDetailEditor has no collapsible panels; no panel state to restore.
        pass

    # ------------------------------------------------------------------
    # Welcome / editor switching
    # ------------------------------------------------------------------

    def _show_editor(self) -> None:
        self._main_stack.setCurrentIndex(1)

    def _show_welcome(self) -> None:
        self.welcome_screen.set_recent_files(self._settings_mgr.recent_files())
        self._main_stack.setCurrentIndex(0)

    def _try_startup_restore(self) -> None:
        """Silently restore last file on startup if the setting is enabled.

        Uses load_file(silent=True) so that any I/O failure (missing file,
        permission error, corrupt content) is swallowed without showing a
        QMessageBox — the welcome screen is shown instead.
        """
        if self._settings_mgr.get_restore_last_file_on_startup():
            last = self._settings_mgr.get_last_open_file()
            if last and self.load_file(last, silent=True):
                return   # load_file already called _show_editor()
        self._show_welcome()

    # ------------------------------------------------------------------
    # New filter
    # ------------------------------------------------------------------

    def new_file(self) -> None:
        if not self._confirm_discard():
            return
        self._doc = FilterDocument()
        self._file_mgr = FilterFileManager()
        self._section_map = None
        self._selected_index = -1
        self._editing_snapshot = None
        self._search_results = []
        self._search_cursor = -1
        self._active_category = Category.ALL
        self.category_sidebar.set_active_category(Category.ALL)
        self.category_sidebar.update_counts([])
        self.rule_card_browser.load_rules([], None)
        self._clear_rule_ui()
        self.search_bar.clear()
        self._refresh_status()
        self._refresh_undo_actions()
        self._show_editor()

    # ------------------------------------------------------------------
    # Restore preference toggle
    # ------------------------------------------------------------------

    def _on_toggle_restore(self, checked: bool) -> None:
        self._settings_mgr.set_restore_last_file_on_startup(checked)
        self._settings_mgr.save()

    def open_preferences(self) -> None:
        """Open the Preferences dialog; apply changes when the user confirms."""
        dlg = PreferencesDialog(self._settings_mgr, self)
        dlg.settings_applied.connect(self._on_preferences_applied)
        dlg.exec()

    def _on_preferences_applied(self) -> None:
        """Sync UI after the user applies changes in PreferencesDialog."""
        self._restore_action.setChecked(
            self._settings_mgr.get_restore_last_file_on_startup()
        )
        self._rebuild_recent_menu()
        self.welcome_screen.set_recent_files(self._settings_mgr.recent_files())

    def _restore_workspace_state(self) -> None:
        """Restore window geometry and splitter sizes from JSON settings."""
        raw = self._settings_mgr.window_geometry
        if raw:
            try:
                from PySide6.QtCore import QByteArray
                self.restoreGeometry(QByteArray(base64.b64decode(raw)))
            except Exception:
                pass  # malformed geometry — ignore silently

        sizes = self._settings_mgr.get_splitter_sizes()
        if sizes and len(sizes) == self._splitter.count():
            self._splitter.setSizes(sizes)

    def _save_workspace(self) -> None:
        geom = base64.b64encode(self.saveGeometry().data()).decode()
        self._settings_mgr.window_geometry = geom
        self._settings_mgr.set_splitter_sizes(list(self._splitter.sizes()))
        self._settings_mgr.save()

        if self._doc.file_path:
            self._settings.save_section_collapse_states(
                self._doc.file_path,
                self.rule_card_browser.get_section_states(),
            )

    # ------------------------------------------------------------------
    # Recent Files menu
    # ------------------------------------------------------------------

    def _rebuild_recent_menu(self) -> None:
        self._recent_menu.clear()
        paths = self._settings_mgr.recent_files()
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
        self._settings_mgr.clear_recent_files()
        self._settings_mgr.save()
        self._rebuild_recent_menu()

    # ------------------------------------------------------------------
    # UI synchronization helpers
    # ------------------------------------------------------------------

    def _load_rule_to_ui(self, real_index: int) -> None:
        if 0 <= real_index < len(self._doc.rules):
            rule = self._doc.rules[real_index]
            self._selected_index   = real_index
            self._editing_snapshot = copy.deepcopy(rule)
            self.rule_detail_editor.set_rule(rule, real_index)
            self.preview_panel.show_rule(rule)
            self._refresh_toolbar()
        else:
            self._clear_rule_ui()

    def _clear_rule_ui(self) -> None:
        self._selected_index   = -1
        self._editing_snapshot = None
        self.rule_detail_editor.clear()
        self.preview_panel.show_empty()
        self._refresh_toolbar()

    def _navigate_to(self, real_index: int) -> None:
        self.rule_card_browser.select_real_index(real_index)
        self._load_rule_to_ui(real_index)

    def _reload_rule_list(self) -> None:
        """Rebuild section_map and reload RuleListWidget. Call after every mutation."""
        self._section_map = build_section_map(self._doc.rules)
        self.category_sidebar.update_counts(self._doc.rules)
        self.rule_card_browser.load_rules(self._doc.rules, self._section_map)
        self._update_filter_search_count()

    def _on_category_selected(self, category: Category) -> None:
        self._active_category = category
        self.rule_card_browser.set_category_filter(category)

        if (
            self._selected_index >= 0
            and category != Category.ALL
            and classify_rule(self._doc.rules[self._selected_index]) != category
        ):
            self._clear_rule_ui()

        self._refresh_search()
        self._update_filter_search_count()

    # ------------------------------------------------------------------
    # P10: filter search bar handlers
    # ------------------------------------------------------------------

    def _on_filter_search_changed(self, query: str, options: dict) -> None:
        self.rule_card_browser.set_search_filter(query, options)
        self._update_filter_search_count()
        # If the previously selected card was filtered out, clear the editor.
        if (
            self._selected_index >= 0
            and not self.rule_card_browser.is_rule_visible(self._selected_index)
        ):
            self._clear_rule_ui()

    def _on_filter_search_clear(self) -> None:
        self.rule_card_browser.clear_search_filter()
        self._update_filter_search_count()

    def _update_filter_search_count(self) -> None:
        visible = self.rule_card_browser.get_visible_count()
        total   = self.rule_card_browser.get_total_count()
        self.filter_search_bar.set_result_count(visible, total)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def open_file(self):
        if not self._confirm_discard():
            return
        initial_dir = self._settings_mgr.last_open_dir
        path, _ = QFileDialog.getOpenFileName(
            self, "開啟 Filter 檔案", initial_dir,
            "Filter 檔案 (*.filter *.txt *.filter.backup);;所有檔案 (*.*)"
        )
        if path:
            self.load_file(path)

    def load_file(self, path: str, *, silent: bool = False) -> bool:
        """Load *path* into the editor.

        Returns True on success.  On OSError, returns False; if *silent* is
        False (the default) a QMessageBox is shown to the user.
        Pass ``silent=True`` for automated calls (startup restore) that must
        never block the UI with a dialog.
        """
        try:
            text = self._file_mgr.open(path)
        except OSError as e:
            if not silent:
                QMessageBox.critical(self, "錯誤", f"無法開啟檔案：\n{e}")
            return False

        self._doc.load_from_text(text, path)
        self._section_map = build_section_map(self._doc.rules)
        self._active_category = Category.ALL
        self.category_sidebar.set_active_category(Category.ALL)
        self.rule_card_browser.set_category_filter(None)
        self.category_sidebar.update_counts(self._doc.rules)
        self.rule_card_browser.load_rules(self._doc.rules, self._section_map)
        self._clear_rule_ui()
        self.search_bar.clear()
        self._search_results = []
        self._search_cursor  = -1

        # Restore per-file section collapse states
        saved = self._settings.restore_section_collapse_states(path)
        if saved:
            self.rule_card_browser.apply_section_states(saved)

        self._refresh_status()      # includes _update_title()
        self._refresh_undo_actions()

        self._settings_mgr.add_recent_file(path)
        self._settings_mgr.last_open_dir = os.path.dirname(os.path.abspath(path))
        self._settings_mgr.set_last_open_file(path)
        self._settings_mgr.save()
        self._rebuild_recent_menu()
        self._show_editor()
        return True

    def save_file(self):
        if not self._doc.file_path:
            self.save_file_as()
        else:
            self._write_to(self._doc.file_path)

    def save_file_as(self):
        initial = self._doc.file_path or self._settings_mgr.last_open_dir
        path, _ = QFileDialog.getSaveFileName(
            self, "另存 Filter 檔案", initial,
            "Filter 檔案 (*.filter);;所有檔案 (*.*)"
        )
        if path:
            self._write_to(path)

    def _write_to(self, path: str):
        try:
            text = self._file_mgr.serialize_rules(self._doc.rules)
            self._file_mgr.save_as(text, path)
        except OSError as e:
            QMessageBox.critical(self, "錯誤", f"無法儲存檔案：\n{e}")
            return
        self._doc.set_file_path(path)
        self._doc.clear_dirty()
        self._refresh_status()      # includes _update_title()
        self._settings_mgr.add_recent_file(path)
        self._settings_mgr.last_open_dir = os.path.dirname(os.path.abspath(path))
        self._settings_mgr.set_last_open_file(path)
        self._settings_mgr.save()
        self._rebuild_recent_menu()

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    def _on_undo(self):
        # Commit any in-progress edit first so it appears as its own undo step.
        self.rule_detail_editor.flush_pending()
        last_cmd = self._doc.peek_undo_command()
        self._doc.undo()
        if isinstance(last_cmd, MoveRuleCommand) and not last_cmd.is_noop:
            self._selected_index = last_cmd.from_index
        self._refresh_after_undo_redo()

    def _on_redo(self):
        # Commit any in-progress edit first so the redo target is unambiguous.
        self.rule_detail_editor.flush_pending()
        last_cmd = self._doc.peek_redo_command()
        self._doc.redo()
        if isinstance(last_cmd, MoveRuleCommand) and not last_cmd.is_noop:
            self._selected_index = last_cmd.to_index
        self._refresh_after_undo_redo()

    def _refresh_after_undo_redo(self):
        self._reload_rule_list()
        if 0 <= self._selected_index < len(self._doc.rules):
            self.rule_card_browser.select_real_index(self._selected_index)
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
        self.rule_detail_editor.flush_pending()
        self._load_rule_to_ui(real_index)

    def _on_detail_rule_changed(self, index: int, updated_rule: FilterRule) -> None:
        """Handle rule_changed(index, updated_rule) from RuleDetailEditor."""
        if not (0 <= index < len(self._doc.rules)):
            return

        old_rule = self._editing_snapshot
        if old_rule is None:
            old_rule = copy.deepcopy(self._doc.rules[index])

        cmd = UpdateRuleCommand(self._doc, index, old_rule, updated_rule)
        self._doc.execute(cmd)

        self._editing_snapshot = copy.deepcopy(self._doc.rules[index])
        self.preview_panel.show_rule(self._doc.rules[index])

        self._refresh_search()
        self._refresh_status()
        self._refresh_undo_actions()
        self.category_sidebar.update_counts(self._doc.rules)
        self.rule_card_browser.refresh()

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
        self.rule_card_browser.select_real_index(insert_at)
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
        self.rule_card_browser.select_real_index(cmd.to_index)
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
        self.rule_card_browser.select_real_index(new_index)
        self._load_rule_to_ui(new_index)
        self._refresh_search()
        self._refresh_status()
        self._refresh_undo_actions()

    # ------------------------------------------------------------------
    # Toolbar-triggered rule operations
    # ------------------------------------------------------------------

    def _refresh_toolbar(self) -> None:
        """Sync toolbar button enable state with current selection + doc size."""
        self.rule_actions_toolbar.update_state(
            self._selected_index, self._doc.visible_count
        )

    def _on_toolbar_delete(self) -> None:
        self._on_delete_rule(self._selected_index)

    def _on_toolbar_duplicate(self) -> None:
        self._on_copy_rule(self._selected_index)

    def _on_toolbar_move_up(self) -> None:
        self._on_move_rule(self._selected_index, self._selected_index - 1)

    def _on_toolbar_move_down(self) -> None:
        self._on_move_rule(self._selected_index, self._selected_index + 1)

    # ------------------------------------------------------------------
    # Search — handlers
    # ------------------------------------------------------------------

    def _filter_indices_by_category(self, indices: list[int]) -> list[int]:
        if self._active_category == Category.ALL:
            return indices
        return [
            i for i in indices
            if 0 <= i < len(self._doc.rules)
            and classify_rule(self._doc.rules[i]) == self._active_category
        ]

    def _on_search_changed(self, text: str) -> None:
        if not text.strip():
            self._search_results = []
            self._search_cursor  = -1
            self.rule_card_browser.clear_highlights()
            self.search_bar.clear_count()
            return

        results = search_rules(self._doc.rules, SearchQuery(text=text))
        results = self._filter_indices_by_category(results)
        self._search_results = results
        self._search_cursor  = 0

        if not results:
            self.rule_card_browser.set_highlights(set(), -1)
            self.search_bar.set_count(0, 0)
            return

        current_real = results[0]
        self.rule_card_browser.set_highlights(set(results), current_real)
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
        self.rule_card_browser.set_highlights(set(self._search_results), current_real)
        self.search_bar.set_count(len(self._search_results), self._search_cursor + 1)
        self._navigate_to(current_real)

    def _refresh_search(self) -> None:
        text = self.search_bar.current_text()
        if not text.strip():
            self.rule_card_browser.clear_highlights()
            self.search_bar.clear_count()
            self._search_results = []
            self._search_cursor  = -1
            return

        results = search_rules(self._doc.rules, SearchQuery(text=text))
        results = self._filter_indices_by_category(results)
        old_real = (
            self._search_results[self._search_cursor]
            if 0 <= self._search_cursor < len(self._search_results) else -1
        )
        self._search_results = results

        if not results:
            self._search_cursor = -1
            self.rule_card_browser.set_highlights(set(), -1)
            self.search_bar.set_count(0, 0)
            return

        self._search_cursor = (
            results.index(old_real) if old_real in results else 0
        )
        current_real = results[self._search_cursor]
        self.rule_card_browser.set_highlights(set(results), current_real)
        self.search_bar.set_count(len(results), self._search_cursor + 1)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _refresh_status(self):
        self._status_lbl.setText(
            self._status_presenter.format_status_text(
                self._doc.file_path,
                self._doc.dirty,
                self._doc.visible_count,
            )
        )
        self._update_title()

    def _update_title(self) -> None:
        """Set window title — adds '* ' prefix when there are unsaved changes."""
        self.setWindowTitle(
            self._status_presenter.format_window_title(
                self._doc.file_path,
                self._doc.dirty,
            )
        )

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
        self.rule_detail_editor.flush_pending()

        if not self._doc.dirty:
            self._save_workspace()
            event.accept()
            return

        reply = QMessageBox.question(
            self, "未儲存的修改",
            "目前有未儲存的修改，是否要儲存？",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

        if reply == QMessageBox.StandardButton.Save:
            self.save_file()
            if self._doc.dirty:
                # save_file() ended with no path (user cancelled Save As dialog)
                event.ignore()
                return
            self._save_workspace()
            event.accept()
        elif reply == QMessageBox.StandardButton.Discard:
            self._save_workspace()
            event.accept()
        else:
            event.ignore()
