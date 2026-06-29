"""P24.2 — QuickRuleCreatorDialog: 快速規則建立對話框。

流程：選模板 → 選物品（可選） → 預覽 → 建立 Rule

公開 API
---------
selected_template_id() -> str
selected_item()        -> ItemDefinition | None
create_rule()          -> FilterRule   （建立規則並關閉對話框）
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.item_database import ItemDefinition
from core.models import FilterRule
from core.rule_templates import (
    RuleTemplate,
    create_rule_from_template,
    get_template,
    get_templates,
)
from parser.filter_exporter import export_filter


class QuickRuleCreatorDialog(QDialog):
    """選模板 → 選物品 → 預覽 → 建立 FilterRule。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("快速建立規則")
        self.setObjectName("QuickRuleCreatorDialog")
        self.setMinimumSize(400, 440)
        self.resize(460, 520)

        self._selected_item: Optional[ItemDefinition] = None
        self._created_rule: Optional[FilterRule] = None
        self._templates: list[RuleTemplate] = []

        self._setup_ui()
        self._load_templates()

    # ── 公開 API ──────────────────────────────────────────────────────────

    def selected_template_id(self) -> str:
        """回傳目前選取的模板 id；無項目時回傳空字串。"""
        return self._template_combo.currentData() or ""

    def selected_item(self) -> Optional[ItemDefinition]:
        """回傳使用者選取的 ItemDefinition；未選取時回傳 None。"""
        return self._selected_item

    def create_rule(self) -> FilterRule:
        """建立 FilterRule、儲存結果並關閉對話框（Accepted）。

        連接至「建立規則」按鈕，亦可由呼叫端在 exec() 完成後直接呼叫。
        """
        rule = self._build_rule()
        self._created_rule = rule
        self.accept()
        return rule

    # ── UI 建構 ──────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)

        # Template 選擇
        self._template_combo = QComboBox()
        self._template_combo.setObjectName("QuickRuleTplCombo")
        form.addRow("模板：", self._template_combo)

        # Description
        self._desc_label = QLabel("—")
        self._desc_label.setObjectName("QuickRuleDescLabel")
        self._desc_label.setWordWrap(True)
        form.addRow("說明：", self._desc_label)

        # Item selector button
        self._item_btn = QPushButton("選擇物品 …")
        self._item_btn.setObjectName("QuickRuleItemBtn")
        form.addRow("物品：", self._item_btn)

        layout.addLayout(form)

        # Preview
        preview_lbl = QLabel("規則預覽")
        preview_lbl.setObjectName("QuickRulePreviewLabel")

        self._preview = QTextEdit()
        self._preview.setObjectName("QuickRulePreview")
        self._preview.setReadOnly(True)
        self._preview.setMinimumHeight(100)
        self._preview.setMaximumHeight(180)

        layout.addWidget(preview_lbl)
        layout.addWidget(self._preview)
        layout.addStretch()

        # 按鈕區
        btn_box = QDialogButtonBox()
        self._create_btn = btn_box.addButton(
            "建立規則", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self._create_btn.setObjectName("QuickRuleCreateBtn")
        self._create_btn.setDefault(True)
        btn_box.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        btn_box.accepted.connect(self.create_rule)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        # 訊號連接
        self._template_combo.currentIndexChanged.connect(self._on_template_changed)
        self._item_btn.clicked.connect(self._open_item_selector)

    # ── 資料載入 ──────────────────────────────────────────────────────────

    def _load_templates(self) -> None:
        self._templates = get_templates()
        self._template_combo.blockSignals(True)
        for tmpl in self._templates:
            self._template_combo.addItem(tmpl.name, tmpl.id)
        self._template_combo.blockSignals(False)
        if self._templates:
            self._on_template_changed(0)

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_template_changed(self, _idx: int) -> None:
        template_id = self._template_combo.currentData()
        tmpl = get_template(template_id) if template_id else None
        self._desc_label.setText(tmpl.description if tmpl else "—")
        self._update_preview()

    def _open_item_selector(self) -> None:
        dlg, selector = self._create_item_selector_dialog()
        if dlg.exec() == QDialog.DialogCode.Accepted:
            item = selector.selected_item()
            if item is not None:
                self._selected_item = item
                self._item_btn.setText(f"{item.name_zh}  {item.name_en}")
                self._update_preview()

    def _create_item_selector_dialog(self) -> tuple:
        """建立物品選擇對話框（可被測試 monkeypatch 覆寫）。"""
        from PySide6.QtWidgets import QVBoxLayout, QDialogButtonBox
        from ui.item_selector_widget import ItemSelectorWidget

        dlg = QDialog(self)
        dlg.setWindowTitle("選擇物品")
        dlg.setObjectName("ItemSelectorDialog")
        dlg.setMinimumSize(360, 480)
        dlg.resize(400, 520)

        inner = QVBoxLayout(dlg)
        inner.setContentsMargins(8, 8, 8, 8)
        inner.setSpacing(8)

        selector = ItemSelectorWidget(parent=dlg)
        inner.addWidget(selector, stretch=1)

        sub_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        sub_box.accepted.connect(dlg.accept)
        sub_box.rejected.connect(dlg.reject)
        selector._item_list.itemActivated.connect(lambda _: dlg.accept())
        inner.addWidget(sub_box)

        return dlg, selector

    # ── 業務邏輯 ──────────────────────────────────────────────────────────

    def _build_rule(self) -> FilterRule:
        """依目前模板 + 選取物品建立 FilterRule（不關閉對話框）。"""
        template_id = self.selected_template_id()
        rule = create_rule_from_template(template_id) if template_id else None
        if rule is None:
            rule = FilterRule()
            rule.action = "Show"
            rule.enabled = True
        if self._selected_item is not None:
            rule.conditions.append(
                ["BaseType", f'"{self._selected_item.name_en}"']
            )
        return rule

    def _update_preview(self) -> None:
        """重新產生規則預覽文字（不影響已儲存的 _created_rule）。"""
        rule = self._build_rule()
        self._preview.setPlainText(export_filter([rule]))
