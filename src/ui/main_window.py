import copy
import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QFileDialog, QMessageBox, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence

from core.document import FilterDocument
from core.models import FilterRule
from core.commands import (
    AddRuleCommand, DeleteRuleCommand,
    DuplicateRuleCommand, UpdateRuleCommand,
)
from widgets.rule_list import RuleListWidget
from editor.rule_editor import RuleEditorWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._doc = FilterDocument()
        self._selected_index: int = -1
        self._editing_snapshot: FilterRule | None = None   # deep-copy taken at load_rule time

        self.setWindowTitle("POE2 Filter Studio")
        self.resize(1150, 720)

        self._build_ui()
        self._build_menus()
        self._build_toolbar()
        self._refresh_status()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        h = QHBoxLayout(central)
        h.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.rule_list = RuleListWidget()
        self.rule_list.setMinimumWidth(200)
        self.rule_list.setMaximumWidth(340)

        self.rule_editor = RuleEditorWidget()

        splitter.addWidget(self.rule_list)
        splitter.addWidget(self.rule_editor)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([240, 860])
        h.addWidget(splitter)

        self._status_lbl = QLabel()
        self.statusBar().addPermanentWidget(self._status_lbl)

        self.rule_list.rule_selected.connect(self._on_rule_selected)
        self.rule_list.add_rule_requested.connect(self._on_add_rule)
        self.rule_list.delete_rule_requested.connect(self._on_delete_rule)
        self.rule_list.copy_rule_requested.connect(self._on_copy_rule)
        self.rule_editor.rule_changed.connect(self._on_rule_changed)

    def _build_menus(self):
        mb = self.menuBar()

        # ── 檔案 ──────────────────────────────────────────────────────
        fm = mb.addMenu("檔案(&F)")

        a = QAction("開啟(&O)…", self)
        a.setShortcut(QKeySequence.StandardKey.Open)
        a.triggered.connect(self.open_file)
        fm.addAction(a)

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

        # ── 編輯 ──────────────────────────────────────────────────────
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

        self._doc.load_from_text(text, path)   # also clears undo/redo stacks
        self._selected_index   = -1
        self._editing_snapshot = None
        self.rule_list.load_rules(self._doc.rules)
        self.rule_editor.setEnabled(False)
        self._refresh_status()
        self._refresh_undo_actions()
        self.setWindowTitle(f"POE2 Filter Studio — {os.path.basename(path)}")

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
        self._doc.undo()
        self._refresh_after_undo_redo()

    def _on_redo(self):
        self._doc.redo()
        self._refresh_after_undo_redo()

    def _refresh_after_undo_redo(self):
        self.rule_list.load_rules(self._doc.rules)

        # Re-load the editor if the selected rule still exists
        if 0 <= self._selected_index < len(self._doc.rules):
            current_rule = self._doc.rules[self._selected_index]
            self.rule_editor.load_rule(current_rule)
            self._editing_snapshot = copy.deepcopy(current_rule)
        else:
            self._selected_index   = -1
            self._editing_snapshot = None
            self.rule_editor.setEnabled(False)

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
    # Rule operations — all routed through Commands
    # ------------------------------------------------------------------

    def _on_rule_selected(self, real_index: int):
        self._selected_index   = real_index
        self._editing_snapshot = copy.deepcopy(self._doc.rules[real_index])
        self.rule_editor.load_rule(self._doc.rules[real_index])

    def _on_rule_changed(self):
        """RuleEditor._apply() has already mutated the rule in-place.
        Wrap the change in an UpdateRuleCommand so it can be undone.
        """
        idx = self._selected_index
        if not (0 <= idx < len(self._doc.rules)):
            return

        old_rule = self._editing_snapshot
        if old_rule is None:
            old_rule = copy.deepcopy(self._doc.rules[idx])

        new_rule = copy.deepcopy(self._doc.rules[idx])

        cmd = UpdateRuleCommand(self._doc, idx, old_rule, new_rule)
        self._doc.execute(cmd)

        # Refresh snapshot for a potential subsequent apply
        self._editing_snapshot = copy.deepcopy(self._doc.rules[idx])

        self.rule_list.refresh()
        self._refresh_status()
        self._refresh_undo_actions()

    def _on_add_rule(self):
        new_rule = FilterRule(action="Show", pre_lines=[""])
        if 0 <= self._selected_index < len(self._doc.rules):
            insert_at = self._selected_index + 1
        else:
            insert_at = self._doc.tail_insert_pos()

        cmd = AddRuleCommand(self._doc, insert_at, new_rule)
        self._doc.execute(cmd)

        self._selected_index   = insert_at
        self._editing_snapshot = copy.deepcopy(self._doc.rules[insert_at])
        self.rule_list.load_rules(self._doc.rules)
        self.rule_list.select_real_index(insert_at)
        self.rule_editor.load_rule(self._doc.rules[insert_at])
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

        self._selected_index   = -1
        self._editing_snapshot = None
        self.rule_list.load_rules(self._doc.rules)
        self.rule_editor.setEnabled(False)
        self._refresh_status()
        self._refresh_undo_actions()

    def _on_copy_rule(self, real_index: int):
        if not (0 <= real_index < len(self._doc.rules)):
            return

        cmd = DuplicateRuleCommand(self._doc, real_index)
        self._doc.execute(cmd)
        new_index = cmd.new_index

        self._selected_index   = new_index
        self._editing_snapshot = copy.deepcopy(self._doc.rules[new_index])
        self.rule_list.load_rules(self._doc.rules)
        self.rule_list.select_real_index(new_index)
        self.rule_editor.load_rule(self._doc.rules[new_index])
        self._refresh_status()
        self._refresh_undo_actions()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _refresh_status(self):
        name  = os.path.basename(self._doc.file_path) if self._doc.file_path else "（未開啟）"
        dirty = " [已修改]" if self._doc.dirty else ""
        count = self._doc.visible_count
        self._status_lbl.setText(f"{name}{dirty}  ·  {count} 條規則")
        self.statusBar().showMessage(self._doc.file_path or "就緒")

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
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
