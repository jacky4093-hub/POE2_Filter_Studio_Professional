import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QFileDialog, QMessageBox, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence

from core.document import FilterDocument
from core.models import FilterRule
from widgets.rule_list import RuleListWidget
from editor.rule_editor import RuleEditorWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._doc = FilterDocument()
        self._selected_index: int = -1

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
        self._selected_index = -1
        self.rule_list.load_rules(self._doc.rules)
        self.rule_editor.setEnabled(False)
        self._refresh_status()
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
    # Rule operations — routed through FilterDocument
    # ------------------------------------------------------------------

    def _on_rule_selected(self, real_index: int):
        self._selected_index = real_index
        self.rule_editor.load_rule(self._doc.rules[real_index])

    def _on_rule_changed(self):
        # The editor mutates the rule object in-place; notify the document.
        if 0 <= self._selected_index < len(self._doc.rules):
            self._doc.update_rule(
                self._selected_index, self._doc.rules[self._selected_index]
            )
        self.rule_list.refresh()
        self._refresh_status()

    def _on_add_rule(self):
        new_rule = FilterRule(action="Show", pre_lines=[""])
        if 0 <= self._selected_index < len(self._doc.rules):
            insert_at = self._selected_index + 1
        else:
            insert_at = self._doc.tail_insert_pos()

        self._doc.insert_rule(insert_at, new_rule)
        self._selected_index = insert_at
        self.rule_list.load_rules(self._doc.rules)
        self.rule_list.select_real_index(insert_at)
        self.rule_editor.load_rule(new_rule)
        self._refresh_status()

    def _on_delete_rule(self, real_index: int):
        if not (0 <= real_index < len(self._doc.rules)):
            return
        reply = QMessageBox.question(
            self, "確認刪除", "確定要刪除這條規則嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._doc.remove_rule(real_index)
        self._selected_index = -1
        self.rule_list.load_rules(self._doc.rules)
        self.rule_editor.setEnabled(False)
        self._refresh_status()

    def _on_copy_rule(self, real_index: int):
        if not (0 <= real_index < len(self._doc.rules)):
            return
        new_index = self._doc.duplicate_rule(real_index)
        self._selected_index = new_index
        self.rule_list.load_rules(self._doc.rules)
        self.rule_list.select_real_index(new_index)
        self.rule_editor.load_rule(self._doc.rules[new_index])
        self._refresh_status()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _refresh_status(self):
        name = os.path.basename(self._doc.file_path) if self._doc.file_path else "（未開啟）"
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
