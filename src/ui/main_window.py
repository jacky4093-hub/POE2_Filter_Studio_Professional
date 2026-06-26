import copy
import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QFileDialog, QMessageBox, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence

from core.models import FilterRule
from parser.filter_parser import parse_filter
from parser.filter_exporter import export_filter
from widgets.rule_list import RuleListWidget
from editor.rule_editor import RuleEditorWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._rules: list[FilterRule] = []
        self._filepath: str = ""
        self._dirty: bool = False
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

        # Permanent status label on right side of status bar
        self._status_lbl = QLabel()
        self.statusBar().addPermanentWidget(self._status_lbl)

        # Wire up rule-list signals
        self.rule_list.rule_selected.connect(self._on_rule_selected)
        self.rule_list.add_rule_requested.connect(self._on_add_rule)
        self.rule_list.delete_rule_requested.connect(self._on_delete_rule)
        self.rule_list.copy_rule_requested.connect(self._on_copy_rule)

        # Wire up editor signal
        self.rule_editor.rule_changed.connect(self._on_rule_changed)

    def _build_menus(self):
        mb = self.menuBar()

        # ── File ──
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

        self._rules = parse_filter(text)
        self._filepath = path
        self._dirty = False
        self._selected_index = -1
        self.rule_list.load_rules(self._rules)
        self.rule_editor.setEnabled(False)
        self._refresh_status()
        self.setWindowTitle(f"POE2 Filter Studio — {os.path.basename(path)}")

    def save_file(self):
        if not self._filepath:
            self.save_file_as()
        else:
            self._write_to(self._filepath)

    def save_file_as(self):
        default = self._filepath or ""
        path, _ = QFileDialog.getSaveFileName(
            self, "另存 Filter 檔案", default,
            "Filter 檔案 (*.filter);;所有檔案 (*.*)"
        )
        if path:
            self._write_to(path)

    def _write_to(self, path: str):
        try:
            text = export_filter(self._rules)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
        except OSError as e:
            QMessageBox.critical(self, "錯誤", f"無法儲存檔案：\n{e}")
            return
        self._filepath = path
        self._dirty = False
        self._refresh_status()
        self.setWindowTitle(f"POE2 Filter Studio — {os.path.basename(path)}")

    # ------------------------------------------------------------------
    # Rule list operations
    # ------------------------------------------------------------------

    def _on_rule_selected(self, real_index: int):
        self._selected_index = real_index
        self.rule_editor.load_rule(self._rules[real_index])

    def _on_rule_changed(self):
        self._dirty = True
        self.rule_list.refresh()
        self._refresh_status()

    def _on_add_rule(self):
        new_rule = FilterRule(action="Show", pre_lines=[""])

        # Insert after currently selected rule; fall back to before TAIL
        if 0 <= self._selected_index < len(self._rules):
            insert_at = self._selected_index + 1
        else:
            insert_at = self._tail_insert_pos()

        self._rules.insert(insert_at, new_rule)
        self._dirty = True
        self._selected_index = insert_at
        self.rule_list.load_rules(self._rules)
        self.rule_list.select_real_index(insert_at)
        self.rule_editor.load_rule(new_rule)
        self._refresh_status()

    def _on_delete_rule(self, real_index: int):
        if not (0 <= real_index < len(self._rules)):
            return
        reply = QMessageBox.question(
            self, "確認刪除", "確定要刪除這條規則嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._rules.pop(real_index)
        self._dirty = True
        self._selected_index = -1
        self.rule_list.load_rules(self._rules)
        self.rule_editor.setEnabled(False)
        self._refresh_status()

    def _on_copy_rule(self, real_index: int):
        if not (0 <= real_index < len(self._rules)):
            return
        original = self._rules[real_index]
        dup = copy.deepcopy(original)
        dup.pre_lines = [""]
        insert_at = real_index + 1
        self._rules.insert(insert_at, dup)
        self._dirty = True
        self._selected_index = insert_at
        self.rule_list.load_rules(self._rules)
        self.rule_list.select_real_index(insert_at)
        self.rule_editor.load_rule(dup)
        self._refresh_status()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _tail_insert_pos(self) -> int:
        """Return insert position just before any __TAIL__ sentinel."""
        if self._rules and self._rules[-1].action == "__TAIL__":
            return len(self._rules) - 1
        return len(self._rules)

    def _visible_rule_count(self) -> int:
        return sum(1 for r in self._rules if r.action != "__TAIL__")

    def _refresh_status(self):
        count = self._visible_rule_count()
        dirty = " [已修改]" if self._dirty else ""
        name = os.path.basename(self._filepath) if self._filepath else "（未開啟）"
        self._status_lbl.setText(f"{name}{dirty}  ·  {count} 條規則")
        self.statusBar().showMessage(self._filepath or "就緒")

    def _confirm_discard(self) -> bool:
        if not self._dirty:
            return True
        reply = QMessageBox.question(
            self, "未儲存的修改",
            "目前有未儲存的修改，確定要放棄並繼續嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    # ------------------------------------------------------------------
    # Close guard
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
