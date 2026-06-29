"""P21.4 — AliasCompleter: 中文別名自動補全元件。

三層架構：
  AliasCompleterLogic  — 純 Python 資料層，可在無 Qt 環境測試
  AliasCompleterPopup  — 浮動下拉清單（不奪取焦點）
  AliasCompleter       — 協調器，將 QLineEdit 與補全彈窗連結
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QListWidget, QListWidgetItem, QLineEdit,
)

from core.alias_resolver import AliasResolver


# ---------------------------------------------------------------------------
# AliasCompleterLogic — Qt-free data layer
# ---------------------------------------------------------------------------

class AliasCompleterLogic:
    """純 Python 補全邏輯層，無 Qt 依賴。

    suggest(query) 呼叫 AliasResolver，回傳有序 (zh, en) 元組清單。
    結果數量上限 MAX_SUGGESTIONS。
    """

    MAX_SUGGESTIONS = 8

    def __init__(self, resolver: AliasResolver | None = None) -> None:
        self._resolver = resolver or AliasResolver()

    def suggest(self, query: str) -> list[tuple[str, str]]:
        """將輸入文字轉換為補全建議清單。

        Returns:
            List of (zh_name, en_name) tuples, priority-ordered.
            Returns [] for blank query or no matches.
        """
        if not query or not query.strip():
            return []
        en_names = self._resolver.resolve_zh(query)
        result: list[tuple[str, str]] = []
        for en in en_names[: self.MAX_SUGGESTIONS]:
            zh = self._resolver.reverse_resolve(en) or en
            result.append((zh, en))
        return result

    @staticmethod
    def format_display(zh: str, en: str) -> str:
        """格式化為顯示字串：'zh_name\\n(en_name)'"""
        return f"{zh}\n({en})"


# ---------------------------------------------------------------------------
# AliasCompleterPopup — floating QListWidget
# ---------------------------------------------------------------------------

class AliasCompleterPopup(QListWidget):
    """不奪取焦點的浮動補全清單。

    以 WA_ShowWithoutActivating 確保 QLineEdit 維持鍵盤焦點。
    """

    item_activated = Signal(str)  # 傳遞選定的 en_name

    _ITEM_HEIGHT = 46
    _MAX_VISIBLE = 8

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(None)  # 必須為 None，才能成為 top-level Tool 視窗
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setObjectName("AliasCompleterPopup")
        self.setUniformItemSizes(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._apply_style()
        self.itemClicked.connect(self._on_item_clicked)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_below(
        self, anchor: QLineEdit, suggestions: list[tuple[str, str]]
    ) -> None:
        """清空、填充建議項目，然後定位於 anchor 正下方。"""
        self.clear()
        for zh, en in suggestions:
            item = QListWidgetItem(AliasCompleterLogic.format_display(zh, en))
            item.setData(Qt.ItemDataRole.UserRole, en)
            self.addItem(item)
        if self.count() == 0:
            self.hide()
            return
        self.setCurrentRow(0)
        self._reposition(anchor)
        self.show()

    def navigate(self, direction: int) -> None:
        """方向鍵移動選取：direction=1 往下，-1 往上。"""
        count = self.count()
        if count == 0:
            return
        row = self.currentRow()
        if row < 0:
            row = 0 if direction > 0 else count - 1
        else:
            row = max(0, min(count - 1, row + direction))
        self.setCurrentRow(row)

    def accept_current(self) -> None:
        """發射目前選取項目的 item_activated 訊號。"""
        item = self.currentItem()
        if item:
            en = item.data(Qt.ItemDataRole.UserRole)
            if en:
                self.item_activated.emit(en)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _reposition(self, anchor: QLineEdit) -> None:
        pos = anchor.mapToGlobal(anchor.rect().bottomLeft())
        visible = min(self.count(), self._MAX_VISIBLE)
        self.move(pos)
        self.setFixedWidth(max(anchor.width(), 240))
        self.setFixedHeight(visible * self._ITEM_HEIGHT + 4)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        en = item.data(Qt.ItemDataRole.UserRole)
        if en:
            self.item_activated.emit(en)

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QListWidget#AliasCompleterPopup {
                background-color: #0d1421;
                border: 1px solid rgba(124,58,237,0.55);
                border-radius: 6px;
                outline: none;
            }
            QListWidget#AliasCompleterPopup::item {
                color: #c0d0e8;
                padding: 5px 10px 5px 10px;
                border-bottom: 1px solid rgba(255,255,255,0.05);
                font-size: 12px;
                line-height: 1.4;
            }
            QListWidget#AliasCompleterPopup::item:selected {
                background-color: rgba(124,58,237,0.32);
                color: #eef2fb;
                border-left: 2px solid rgba(124,58,237,0.9);
            }
            QListWidget#AliasCompleterPopup::item:hover {
                background-color: rgba(124,58,237,0.15);
                color: #ddeaff;
            }
        """)


# ---------------------------------------------------------------------------
# AliasCompleter — orchestrator
# ---------------------------------------------------------------------------

class AliasCompleter(QObject):
    """將中文別名自動補全附加到 QLineEdit 的協調器。

    使用方式::

        self._completer = AliasCompleter(self._input, parent=self)

    當使用者選擇補全項目後：
    - 將英文名稱 (en_name) 填入 QLineEdit
    - 發射 search_changed 讓搜尋邏輯執行
    - 發射 completed(en_name) 供外部監聽
    """

    completed = Signal(str)  # 發射選定的 en_name

    def __init__(
        self,
        line_edit: QLineEdit,
        resolver: AliasResolver | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._input = line_edit
        self._logic = AliasCompleterLogic(resolver)
        self._popup = AliasCompleterPopup()

        self._input.textChanged.connect(self._on_text_changed)
        self._input.installEventFilter(self)
        self._popup.item_activated.connect(self._on_item_activated)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def hide_popup(self) -> None:
        """強制關閉補全彈窗。"""
        self._popup.hide()

    @property
    def logic(self) -> AliasCompleterLogic:
        """供外部（包含測試）存取邏輯層。"""
        return self._logic

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_text_changed(self, text: str) -> None:
        suggestions = self._logic.suggest(text)
        if not suggestions:
            self._popup.hide()
            return
        self._popup.show_below(self._input, suggestions)

    def _on_item_activated(self, en_name: str) -> None:
        self._popup.hide()
        # blockSignals 避免 textChanged → _on_text_changed → popup 再次顯示
        self._input.blockSignals(True)
        self._input.setText(en_name)
        self._input.blockSignals(False)
        # 手動觸發一次 textChanged，讓上游搜尋邏輯執行
        self._input.textChanged.emit(en_name)
        self.completed.emit(en_name)

    # ------------------------------------------------------------------
    # Event filter — keyboard navigation in _input
    # ------------------------------------------------------------------

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is not self._input:
            return super().eventFilter(obj, event)

        etype = event.type()

        if etype == QEvent.Type.KeyPress:
            key = event.key()
            if self._popup.isVisible():
                if key == Qt.Key.Key_Down:
                    self._popup.navigate(1)
                    return True
                if key == Qt.Key.Key_Up:
                    self._popup.navigate(-1)
                    return True
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self._popup.accept_current()
                    return True
                if key == Qt.Key.Key_Escape:
                    self._popup.hide()
                    return True

        elif etype == QEvent.Type.FocusOut:
            # 延遲關閉，讓 popup 點擊事件先行處理
            QTimer.singleShot(150, self._hide_if_focus_gone)

        return super().eventFilter(obj, event)

    def _hide_if_focus_gone(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        focused = app.focusWidget()
        if focused is not self._input and focused is not self._popup:
            self._popup.hide()
