import base64
import copy
import os

from app_info import APP_NAME, APP_VERSION

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QStackedWidget, QFileDialog, QMessageBox, QLabel,
)
from PySide6.QtCore import Qt, QTimer
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
from ui.validation_panel import ValidationPanel
from ui.save_warning_dialog import SaveWarningDialog
from ui.navigation_bar import NavigationBarV4
from core.validator import validate_document, ValidationSeverity
from core.quick_fix import get_quick_fixes, apply_quick_fix
from presenters.status_presenter import StatusPresenter
from controllers.recent_files_controller import RecentFilesController
from controllers.navigation_search_controller import NavigationSearchController
from controllers.quick_filter_controller import QuickFilterController


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
        self._recent_files_controller = RecentFilesController(self, self._settings_mgr)
        self._nav_search = NavigationSearchController()

        # Search state — kept in sync with _nav_search for backward compatibility
        self._search_results: list[int] = []
        self._search_cursor:  int       = -1

        # Category filter (v2.1.0)
        self._active_category: Category = Category.ALL

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1250, 720)

        self._build_ui()
        self._quick_filter = QuickFilterController(self)
        self._build_menus()
        self._build_toolbar()
        self._build_shortcuts()

        # Debounce timer — fires _on_deferred_post_edit 300 ms after last field edit.
        # Keeps per-keystroke cost low: validate + category counts run once per pause.
        self._validation_timer = QTimer(self)
        self._validation_timer.setSingleShot(True)
        self._validation_timer.timeout.connect(self._on_deferred_post_edit)

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

        # Page 1: Editor shell — V4 layout
        central = QWidget()
        central.setObjectName("ContentShell")
        self._main_stack.addWidget(central)

        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # ── Navigation Bar V4 ────────────────────────────────────────────
        self.search_bar = SearchBar()      # navigation search — embedded in nav bar
        self.nav_bar = NavigationBarV4(search_bar=self.search_bar)
        v.addWidget(self.nav_bar)

        # ── Four-column main splitter ────────────────────────────────────
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        self.category_sidebar     = CategorySidebarWidget()
        self.rule_actions_toolbar = RuleActionsToolbar()
        self.filter_search_bar    = SearchBarWidget()
        self.rule_card_browser    = RuleCardBrowser()
        self.rule_detail_editor   = RuleDetailEditor()
        self.preview_panel        = PreviewPanel()
        self.validation_panel     = ValidationPanel()

        # ── Panel 1: Category Sidebar ────────────────────────────────────
        col_category = QWidget()
        col_category.setObjectName("ColCategory")
        col_category.setMinimumWidth(160)
        col_category.setMaximumWidth(240)
        col_cat_layout = QVBoxLayout(col_category)
        col_cat_layout.setContentsMargins(0, 0, 0, 0)
        col_cat_layout.setSpacing(0)
        col_cat_layout.addWidget(self.category_sidebar, stretch=1)

        # ── Panel 2: Rule Browser ────────────────────────────────────────
        col_browser = QWidget()
        col_browser.setObjectName("ColBrowser")
        col_browser.setMinimumWidth(200)
        col_browser.setMaximumWidth(420)
        col_browser_layout = QVBoxLayout(col_browser)
        col_browser_layout.setContentsMargins(0, 0, 0, 0)
        col_browser_layout.setSpacing(0)

        # Browser header — "規則列表 (N)"
        self._rule_browser_hdr = QWidget()
        self._rule_browser_hdr.setObjectName("RuleBrowserHeader")
        hdr_layout = QHBoxLayout(self._rule_browser_hdr)
        hdr_layout.setContentsMargins(10, 0, 10, 0)
        hdr_layout.setSpacing(0)
        self._rule_count_lbl = QLabel("規則列表")
        self._rule_count_lbl.setObjectName("RuleCountLabel")
        hdr_layout.addWidget(self._rule_count_lbl)
        hdr_layout.addStretch()

        col_browser_layout.addWidget(self._rule_browser_hdr)
        col_browser_layout.addWidget(self.rule_actions_toolbar)
        col_browser_layout.addWidget(self.filter_search_bar)
        col_browser_layout.addWidget(self.rule_card_browser, stretch=1)

        # ── Panel 3: Rule Editor (added directly to splitter) ────────────

        # ── Panel 4: Preview Column ──────────────────────────────────────
        col_preview = QWidget()
        col_preview.setObjectName("ColPreview")
        col_preview.setMinimumWidth(180)
        col_preview.setMaximumWidth(360)
        col_prev_layout = QVBoxLayout(col_preview)
        col_prev_layout.setContentsMargins(0, 0, 0, 0)
        col_prev_layout.setSpacing(0)
        col_prev_layout.addWidget(self.preview_panel, stretch=1)

        # Assemble 4-panel splitter
        self._splitter.addWidget(col_category)
        self._splitter.addWidget(col_browser)
        self._splitter.addWidget(self.rule_detail_editor)
        self._splitter.addWidget(col_preview)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 0)
        self._splitter.setStretchFactor(2, 3)
        self._splitter.setStretchFactor(3, 1)
        self._splitter.setSizes([190, 300, 580, 290])

        v.addWidget(self._splitter, stretch=1)
        v.addWidget(self.validation_panel)

        # ── Status Bar V4 ────────────────────────────────────────────────
        status_shell = QWidget()
        status_shell.setObjectName("StatusBarV4")
        status_layout = QHBoxLayout(status_shell)
        status_layout.setContentsMargins(10, 0, 10, 0)
        status_layout.setSpacing(0)

        self._status_lbl = QLabel()
        self._status_lbl.setObjectName("StatusFileInfo")
        status_layout.addWidget(self._status_lbl)

        status_layout.addStretch()

        self._status_rule_count_lbl = QLabel()
        self._status_rule_count_lbl.setObjectName("StatusRuleCount")
        status_layout.addWidget(self._status_rule_count_lbl)

        status_layout.addSpacing(16)

        self._status_validation_lbl = QLabel()
        self._status_validation_lbl.setObjectName("StatusValidationSummary")
        status_layout.addWidget(self._status_validation_lbl)

        v.addWidget(status_shell)

        # ── Signal Connections ───────────────────────────────────────────

        # NavigationBarV4 → file operations
        self.nav_bar.new_requested.connect(self.new_file)
        self.nav_bar.open_requested.connect(self.open_file)
        self.nav_bar.import_backup_requested.connect(self._on_import_backup)
        self.nav_bar.save_requested.connect(self.save_file)
        self.nav_bar.save_as_requested.connect(self.save_file_as)
        self.nav_bar.export_requested.connect(self.save_file_as)
        self.nav_bar.settings_requested.connect(self.open_preferences)

        # Rule browser
        self.rule_card_browser.selected_rule_changed.connect(self._on_rule_selected)
        # P14.1: wizard now handles all browser-originated adds via add_rule_from_wizard.
        self.rule_card_browser.add_rule_from_wizard.connect(self._on_add_rule_from_template)
        self.rule_card_browser.delete_rule_requested.connect(self._on_delete_rule)
        self.rule_card_browser.copy_rule_requested.connect(self._on_copy_rule)
        self.rule_card_browser.move_rule_requested.connect(self._on_move_rule)

        # Rule editor
        self.rule_detail_editor.rule_changed.connect(self._on_detail_rule_changed)

        # Validation panel
        self.validation_panel.issue_clicked.connect(self._on_validation_issue_clicked)
        self.validation_panel.fix_requested.connect(self._on_quick_fix_requested)

        # Rule actions toolbar
        self.rule_actions_toolbar.new_requested.connect(self._on_add_rule)
        self.rule_actions_toolbar.delete_requested.connect(self._on_toolbar_delete)
        self.rule_actions_toolbar.duplicate_requested.connect(self._on_toolbar_duplicate)
        self.rule_actions_toolbar.move_up_requested.connect(self._on_toolbar_move_up)
        self.rule_actions_toolbar.move_down_requested.connect(self._on_toolbar_move_down)

        # Navigation search (SearchBar embedded in nav_bar)
        self.search_bar.search_changed.connect(self._on_search_changed)
        self.search_bar.next_requested.connect(self._on_search_next)
        self.search_bar.prev_requested.connect(self._on_search_prev)

        # Category sidebar
        self.category_sidebar.category_selected.connect(self._on_category_selected)

        # Filter search bar (quick filter inside browser panel)
        self.filter_search_bar.search_changed.connect(self._on_filter_search_changed)
        self.filter_search_bar.clear_requested.connect(self._on_filter_search_clear)

        # Welcome screen
        self.welcome_screen.open_requested.connect(self.open_file)
        self.welcome_screen.new_requested.connect(self.new_file)
        self.welcome_screen.recent_file_requested.connect(self.load_file)

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

        hm = mb.addMenu("說明(&H)")

        self._about_action = QAction("關於(&A)…", self)
        self._about_action.triggered.connect(self._show_about)
        hm.addAction(self._about_action)

    def _show_about(self) -> None:
        from ui.about_dialog import AboutDialog
        dlg = AboutDialog(self)
        dlg.exec()

    def _build_toolbar(self):
        # NavigationBarV4 surfaces file operations visually; keep the QToolBar
        # hidden so keyboard shortcuts and _tb_undo/_tb_redo still work.
        tb = self.addToolBar("工具列")
        tb.setMovable(False)
        tb.setVisible(False)

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
        self._nav_search.reset()
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
        self._recent_files_controller.refresh_views()

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
        self._recent_files_controller.refresh_views()

    def _open_recent(self, path: str) -> None:
        self._recent_files_controller.open_recent(path)

    def _clear_recent_files(self) -> None:
        self._recent_files_controller.clear_recent()

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
    # P10: filter search bar handlers (facade — delegate to QuickFilterController)
    # ------------------------------------------------------------------

    def _on_filter_search_changed(self, query: str, options: dict) -> None:
        self._quick_filter.apply_filter(query, options)

    def _on_filter_search_clear(self) -> None:
        self._quick_filter.clear_filter()

    def _update_filter_search_count(self) -> None:
        self._quick_filter.refresh_count()

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
        # P17.10A-3: category counts deferred — scheduled below after fast status
        self.rule_card_browser.load_rules(self._doc.rules, self._section_map)
        self._clear_rule_ui()
        self.search_bar.clear()
        self._nav_search.reset()
        self._search_results = []
        self._search_cursor  = -1

        # Restore per-file section collapse states
        saved = self._settings.restore_section_collapse_states(path)
        if saved:
            self.rule_card_browser.apply_section_states(saved)

        # P17.10A-1/3: fast status update + defer expensive work to next event loop
        self._refresh_status_fast()           # title + status bar + rule count, no validate
        self._validation_timer.stop()         # cancel any pending debounce from previous edit
        self._schedule_deferred_category_count()
        QTimer.singleShot(0, self._refresh_validation)
        self._refresh_undo_actions()

        self._settings_mgr.last_open_dir = os.path.dirname(os.path.abspath(path))
        self._settings_mgr.set_last_open_file(path)
        self._settings_mgr.save()
        self._recent_files_controller.record_opened(path)
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

    def _check_save_issues(self) -> bool:
        """Return True if it is safe to proceed with saving.

        Runs validate_document; if any ERROR or WARNING issues are found,
        shows SaveWarningDialog.  Returns False if the user cancels.
        INFO issues are never shown and never block saving.
        """
        blocking = [
            i for i in validate_document(self._doc)
            if i.severity in (ValidationSeverity.ERROR, ValidationSeverity.WARNING)
        ]
        if not blocking:
            return True
        return SaveWarningDialog.confirm(blocking, self)

    def _write_to(self, path: str):
        if not self._check_save_issues():
            return
        try:
            text = self._file_mgr.serialize_rules(self._doc.rules)
            self._file_mgr.save_as(text, path)
        except OSError as e:
            QMessageBox.critical(self, "錯誤", f"無法儲存檔案：\n{e}")
            return
        self._doc.set_file_path(path)
        self._doc.clear_dirty()
        self._refresh_status()      # includes _update_title()
        self._settings_mgr.last_open_dir = os.path.dirname(os.path.abspath(path))
        self._settings_mgr.set_last_open_file(path)
        self._settings_mgr.save()
        self._recent_files_controller.record_saved(path)

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
        """Handle rule_changed(index, updated_rule) from RuleDetailEditor.

        Fast path: only the current card is swapped and title/status bar are
        refreshed immediately.  Validation and category counts are deferred via
        a 300 ms debounce timer so per-keystroke cost stays low.
        """
        if not (0 <= index < len(self._doc.rules)):
            return

        old_rule = self._editing_snapshot
        if old_rule is None:
            old_rule = copy.deepcopy(self._doc.rules[index])

        cmd = UpdateRuleCommand(self._doc, index, old_rule, updated_rule)
        self._doc.execute(cmd)

        # doc.rules[index] was replaced (not mutated) by execute(); safe to reference directly.
        self._editing_snapshot = self._doc.rules[index]

        # Immediate lightweight updates
        self.preview_panel.show_rule(self._doc.rules[index])
        # Only refresh nav-search results when a query is active (P17.8 guard)
        if self.search_bar.current_text().strip():
            self._refresh_search()
        self._refresh_status_fast()          # title + status bar, no validate
        self._refresh_undo_actions()
        self.rule_card_browser.update_single_card(index, updated_rule)

        # Defer expensive work — restart timer so it fires 300 ms after LAST edit
        self._validation_timer.start(300)

    def _schedule_deferred_category_count(self) -> None:
        """Schedule a category count refresh after the next event-loop tick.

        Uses a rules-list snapshot to guard against stale updates: if another
        file is loaded before the callback fires, the callback is silently skipped.
        """
        _snap = self._doc.rules
        QTimer.singleShot(0, lambda: self._apply_deferred_category_count(_snap))

    def _apply_deferred_category_count(self, rules_snapshot: list) -> None:
        """Execute deferred category count — no-op when a newer file has loaded."""
        if self._doc.rules is not rules_snapshot:
            return
        self.category_sidebar.update_counts(self._doc.rules)

    def _on_deferred_post_edit(self) -> None:
        """Deferred callback: runs after 300 ms of edit inactivity."""
        self._refresh_validation()
        self.category_sidebar.update_counts(self._doc.rules)

    def _refresh_status_fast(self) -> None:
        """Update status bar text and window title — does NOT run validation."""
        self._status_lbl.setText(
            self._status_presenter.format_status_text(
                self._doc.file_path,
                self._doc.dirty,
                self._doc.visible_count,
            )
        )
        self._update_rule_count_label()
        self._update_title()

    def _on_add_rule(self):
        """Insert a blank rule (toolbar / keyboard shortcut path)."""
        self._insert_new_rule(FilterRule(action="Show", pre_lines=[""]))

    def _on_add_rule_from_template(self, rule: FilterRule) -> None:
        """Insert a wizard-chosen template rule (browser add-button path)."""
        self._insert_new_rule(rule)

    def _insert_new_rule(self, rule: FilterRule) -> None:
        insert_at = (
            self._selected_index + 1
            if 0 <= self._selected_index < len(self._doc.rules)
            else self._doc.tail_insert_pos()
        )
        cmd = AddRuleCommand(self._doc, insert_at, rule)
        self._doc.execute(cmd)

        # Incremental pool update — O(1) widget creation instead of full rebuild
        self._section_map = build_section_map(self._doc.rules)
        self.category_sidebar.update_counts(self._doc.rules)
        self.rule_card_browser.pool_insert_card(insert_at, rule, self._doc.rules)
        self._update_filter_search_count()

        self.rule_card_browser.select_real_index(insert_at)
        self._load_rule_to_ui(insert_at)
        self._refresh_search()
        self._refresh_status_fast()
        self._validation_timer.start(300)
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

        # Incremental pool update — O(1) widget removal instead of full rebuild
        self._section_map = build_section_map(self._doc.rules)
        self.category_sidebar.update_counts(self._doc.rules)
        self.rule_card_browser.pool_remove_card(real_index, self._doc.rules)
        self._update_filter_search_count()

        self._clear_rule_ui()
        self._refresh_search()
        self._refresh_status_fast()
        self._validation_timer.start(300)
        self._refresh_undo_actions()

    def _on_move_rule(self, from_real: int, to_real: int):
        cmd = MoveRuleCommand(self._doc, from_real, to_real)
        if cmd.is_noop:
            return
        self._doc.execute(cmd)

        # Incremental pool update — swap two cards in-place
        self._section_map = build_section_map(self._doc.rules)
        self.category_sidebar.update_counts(self._doc.rules)
        self.rule_card_browser.pool_swap_cards(from_real, to_real, self._doc.rules)
        self._update_filter_search_count()

        self.rule_card_browser.select_real_index(cmd.to_index)
        self._load_rule_to_ui(cmd.to_index)
        self._refresh_search()
        self._refresh_status_fast()
        self._validation_timer.start(300)
        self._refresh_undo_actions()

    def _on_copy_rule(self, real_index: int):
        if not (0 <= real_index < len(self._doc.rules)):
            return
        cmd = DuplicateRuleCommand(self._doc, real_index)
        self._doc.execute(cmd)
        new_index = cmd.new_index

        # Incremental pool update — O(1) widget creation instead of full rebuild
        self._section_map = build_section_map(self._doc.rules)
        self.category_sidebar.update_counts(self._doc.rules)
        self.rule_card_browser.pool_insert_card(
            new_index, self._doc.rules[new_index], self._doc.rules
        )
        self._update_filter_search_count()

        self.rule_card_browser.select_real_index(new_index)
        self._load_rule_to_ui(new_index)
        self._refresh_search()
        self._refresh_status_fast()
        self._validation_timer.start(300)
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

    def _sync_search_state(self) -> None:
        """Keep _search_results/_search_cursor in sync with the controller."""
        self._search_results = self._nav_search.results
        self._search_cursor  = self._nav_search.cursor

    def _on_search_changed(self, text: str) -> None:
        if not text.strip():
            self._nav_search.reset()
            self._sync_search_state()
            self.rule_card_browser.clear_highlights()
            self.search_bar.clear_count()
            return

        state = self._nav_search.run_search(
            self._doc.rules, text, self._filter_indices_by_category
        )
        self._sync_search_state()

        if not state.has_results:
            self.rule_card_browser.set_highlights(set(), -1)
            self.search_bar.set_count(0, 0)
            return

        self.rule_card_browser.set_highlights(set(state.results), state.current_real)
        self.search_bar.set_count(state.total, state.position)
        self._navigate_to(state.current_real)

    def _on_search_next(self) -> None:
        if not self._nav_search.has_results:
            return
        self._nav_search.next()
        self._sync_search_state()
        self._go_to_cursor()

    def _on_search_prev(self) -> None:
        if not self._nav_search.has_results:
            return
        self._nav_search.prev()
        self._sync_search_state()
        self._go_to_cursor()

    def _go_to_cursor(self) -> None:
        current_real = self._search_results[self._search_cursor]
        self.rule_card_browser.set_highlights(set(self._search_results), current_real)
        self.search_bar.set_count(len(self._search_results), self._search_cursor + 1)
        self._navigate_to(current_real)

    def _refresh_search(self) -> None:
        text = self.search_bar.current_text()
        if not text.strip():
            self._nav_search.reset()
            self._sync_search_state()
            self.rule_card_browser.clear_highlights()
            self.search_bar.clear_count()
            return

        state = self._nav_search.refresh(
            self._doc.rules, text, self._filter_indices_by_category
        )
        self._sync_search_state()

        if not state.has_results:
            self.rule_card_browser.set_highlights(set(), -1)
            self.search_bar.set_count(0, 0)
            return

        self.rule_card_browser.set_highlights(set(state.results), state.current_real)
        self.search_bar.set_count(state.total, state.position)

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
        self._update_rule_count_label()
        self._update_title()
        self._refresh_validation()

    def _refresh_validation(self) -> None:
        """Re-run validate_document, compute quick fixes, push to ValidationPanel."""
        self._validation_timer.stop()   # cancel pending debounced call if any
        issues = validate_document(self._doc)
        fixes_per_issue: list[list] = []
        for issue in issues:
            if 0 <= issue.rule_index < len(self._doc.rules):
                rule = self._doc.rules[issue.rule_index]
                fixes_per_issue.append(get_quick_fixes(rule, issue))
            else:
                fixes_per_issue.append([])
        self.validation_panel.refresh(issues, fixes_per_issue)

        # Update NavigationBarV4 validation chip + status-bar summary
        n_errors   = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        n_warnings = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
        if n_errors:
            summary = f"{n_errors} 個錯誤"
            self.nav_bar.set_validation_status(False, summary)
            self._status_validation_lbl.setText(f"✗ {summary}")
        elif n_warnings:
            summary = f"{n_warnings} 個警告"
            self.nav_bar.set_validation_status(True, f"語法檢查：通過（{summary}）")
            self._status_validation_lbl.setText(f"⚠ {summary}")
        else:
            self.nav_bar.set_validation_status(True, "語法檢查：通過")
            self._status_validation_lbl.setText("✓ 語法通過")

    def _on_validation_issue_clicked(self, rule_index: int) -> None:
        """Navigate to the rule associated with a clicked validation issue."""
        if 0 <= rule_index < len(self._doc.rules):
            self._navigate_to(rule_index)

    def _on_quick_fix_requested(self, rule_index: int, fix) -> None:
        """Apply a QuickFix via fast path — no full card rebuild (supports undo)."""
        if not (0 <= rule_index < len(self._doc.rules)):
            return
        old_rule = copy.deepcopy(self._doc.rules[rule_index])
        new_rule = apply_quick_fix(old_rule, fix)
        cmd = UpdateRuleCommand(self._doc, rule_index, old_rule, new_rule)
        self._doc.execute(cmd)
        updated = self._doc.rules[rule_index]
        self.rule_card_browser.update_single_card(rule_index, updated)
        if rule_index == self._selected_index:
            self._editing_snapshot = copy.deepcopy(updated)
            self.rule_detail_editor.set_rule(updated, rule_index)
            self.preview_panel.show_rule(updated)
        self._refresh_status_fast()
        self._refresh_undo_actions()
        self._validation_timer.start(300)

    def _update_rule_count_label(self) -> None:
        """Sync rule count into browser header label and status bar."""
        count = self._doc.visible_count
        self._rule_count_lbl.setText(f"規則列表  ({count})" if count else "規則列表")
        self._status_rule_count_lbl.setText(f"總規則數：{count}" if count else "")

    def _on_import_backup(self) -> None:
        """Stub — import backup functionality planned for a future milestone."""
        QMessageBox.information(self, "匯入備份", "匯入備份功能即將在後續版本推出。")

    def _update_title(self) -> None:
        """Set window title — adds '* ' prefix when there are unsaved changes."""
        self.setWindowTitle(
            self._status_presenter.format_window_title(
                self._doc.file_path,
                self._doc.dirty,
            )
        )

    def _confirm_discard(self) -> bool:
        """Return True if it is safe to abandon the current document.

        When the document is dirty, shows Save / Discard / Cancel:
          Save    → calls save_file(); returns True only if save succeeded
          Discard → returns True  (changes abandoned)
          Cancel  → returns False (operation aborted)
        """
        if not self._doc.dirty:
            return True
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
            return not self._doc.dirty   # False when user cancelled Save As
        if reply == QMessageBox.StandardButton.Discard:
            return True
        return False   # Cancel

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
