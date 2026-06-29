# P22 UX Review — P21 + P22 整體體驗檢查

> 版本：P22.3 完成後  
> 日期：2026-06-29  
> 範圍：P21（中文 Alias）、P22.1（ConditionBuilder 核心）、P22.2（Rule Editor 整合）、P22.3（Condition Presets）

---

## 問題索引

| # | 等級 | 類別 | 標題 | 成本 |
|---|------|------|------|------|
| [F-01](#f-01) | **HIGH** | 重複 UI | Class/BaseType 在兩個卡片同時顯示 | M |
| [F-02](#f-02) | **HIGH** | 資料流 | AliasCompleter 選取後 rule 未立即更新 | S |
| [F-03](#f-03) | **HIGH** | 樣式 | ConditionBuilderCard 未繼承 QSS 主題 | S |
| [F-04](#f-04) | **HIGH** | 樣式 | P22 所有 widget objectName 無 QSS 規則 | M |
| [M-05](#m-05) | Medium | 捲軸 | 雙層 QScrollArea 滾動衝突 | M |
| [M-06](#m-06) | Medium | 高度 | ConditionBuilderWidget 高度上限 300px 可能截斷 | S |
| [M-07](#m-07) | Medium | UX | Preset 套用後 Combo 未重設 | S |
| [M-08](#m-08) | Medium | 程式碼 | `ConditionValue` 在方法內重複 import 4 次 | S |
| [M-09](#m-09) | Medium | 效能 | RuleEditorAliasService 建立兩份 | S |
| [M-10](#m-10) | Medium | UX | Preset 沒有預覽，容易誤選 | M |
| [L-11](#l-11) | Low | UX | "×" 移除按鈕觸控目標過小 | S |
| [L-12](#l-12) | Low | 文字 | Placeholder "Gems" 與實際 class "Skill Gem" 不符 | XS |
| [L-13](#l-13) | Low | UX | 套用 Preset 後無法復原（缺 Undo） | L |
| [L-14](#l-14) | Low | 文字 | 條件標籤寬度 68px 在部分字型下可能截斷 | XS |
| [L-15](#l-15) | Low | 資料流 | update_condition 空值不移除既有列 | S |

---

## 修改成本說明

| 符號 | 說明 |
|------|------|
| XS | < 10 行，無副作用 |
| S | 10–50 行，影響 1–2 個檔案 |
| M | 50–150 行，影響 2–4 個檔案，需補充測試 |
| L | > 150 行，涉及架構調整或新元件 |

---

## HIGH — 必須修正

### F-01

**重複 UI：Class/BaseType 在兩個卡片同時顯示**

**問題描述**

Rule Editor 目前同時存在兩個可編輯 Class/BaseType 的區域：

```
[條件] 卡片                     [基本條件] 卡片（ConditionBuilderWidget）
  ├─ Class:     "Currency"        ├─ 類別    "Currency"       ← 同一個 key
  └─ BaseType:  "Divine Orb"      ├─ 基底類型 "Divine Orb"    ← 同一個 key
                                  ├─ 稀有度   >= Rare
                                  └─ 物品等級 >= 70
```

載入含 `Class = "Currency"` 的 rule 時，Class 欄位**出現兩次**。使用者不清楚哪個是主要編輯入口，兩個區域的同步延遲也可能造成資料不一致感。

**影響**

- 使用者困惑：Class 修改在哪裡操作？
- 視覺重複：Rule Editor 垂直空間浪費
- 新手學習成本高

**建議方案**

選項 A（推薦）：**隱藏「條件」卡片的 Class/BaseType 欄位**，僅保留兩者的 QGroupBox 框架供無 ConditionBuilderWidget 時 fallback 使用。

```python
# _build_condition_card 末尾加入
if self._cond_builder is not None:
    self._class_edit.setVisible(False)
    self._basetype_edit.setVisible(False)
    # 如果 card 只有這兩個 row，也可直接 box.setVisible(False)
```

選項 B：完全保留舊卡片，但在舊卡片頂部加 Note Label「Class/BaseType 請於下方基本條件欄位編輯」。成本最低，但 UX 仍不理想。

**預估成本：M**（改完需驗證 fallback 路徑與現有測試）

---

### F-02

**資料流：AliasCompleter 選取後 rule 未立即更新**

**問題描述**

使用者從 AliasCompleter popup 選取項目後：

1. `AliasCompleter._on_item_activated` → `completed.emit(en_name)`
2. `_on_basetype_completed` 被呼叫 → `_basetype_edit.setText(quoted)` (blockSignals) → `_cond_builder.update_condition(cv)`
3. **但沒有呼叫 `_on_any_field_changed()`**

結果：rule 不更新，直到使用者再次按 Tab / Enter 觸發 `editingFinished`。

```python
# 現況
def _on_basetype_completed(self, en_name: str) -> None:
    ...
    self._cond_builder.update_condition(cv)
    # ← 缺少 self._on_any_field_changed()
```

同樣問題出現在 `_on_class_completed`。

**影響**

- 選取補全結果後 Preview Panel 未即時更新
- 使用者誤以為選取失敗，重複操作
- 操作體感卡頓

**建議方案**

在 `_on_basetype_completed` 與 `_on_class_completed` 末尾補上：

```python
self._on_any_field_changed()
```

同時確認 ConditionBuilderWidget 的 `_on_string_completed` 也呼叫 `_emit_changed()`（目前已呼叫，正確）。

**預估成本：S**（2 行修改 + 測試驗證）

---

### F-03

**樣式：ConditionBuilderCard 未繼承 QSS 主題**

**問題描述**

`_build_condition_builder_card` 建立的 QGroupBox 使用 `objectName = "ConditionBuilderCard"`，但 QSS 只定義了 `QGroupBox#RuleEditorCard` 的樣式。

```python
# rule_detail_editor.py:597
box = QGroupBox("基本條件")
box.setObjectName("ConditionBuilderCard")   # ← 未被 QSS 匹配
```

```qss
/* editor.qss — 沒有 #ConditionBuilderCard 規則 */
QGroupBox#RuleEditorCard { ... }            /* 其他卡片套用此規則 */
```

結果：「基本條件」卡片使用系統預設外觀（白色背景 + 系統字型），與其他深色卡片完全不一致。

**建議方案**

方案 A（推薦）：將 objectName 改為 `"RuleEditorCard"` 並在 QSS 追加「基本條件」的 accent color：

```python
box.setObjectName("RuleEditorCard")   # 繼承 QSS 基礎樣式
```

```qss
/* 基本條件 (Condition Builder) — indigo accent */
QGroupBox#RuleEditorCard[title="基本條件"] {
    border-left-color: #6366f1;
}
QGroupBox#RuleEditorCard[title="基本條件"]::title {
    color: #818cf8;
}
```

方案 B：在 QSS 追加 `#ConditionBuilderCard` 規則（複製 `#RuleEditorCard` 樣式並修改）。成本稍高，維護兩套樣式。

**預估成本：S**

---

### F-04

**樣式：P22 所有 widget objectName 無 QSS 規則**

**問題描述**

ConditionBuilderWidget 的所有子 widget 都有 objectName，但 editor.qss 中**一個都沒有對應的 QSS 規則**：

```
ConditionBuilderScroll    → 無樣式
ConditionRowsContainer    → 無樣式
ConditionLabel            → 無樣式（顯示為白色標籤）
ConditionOpCombo          → 無樣式（白色 combo box）
ConditionValueCombo       → 無樣式
ConditionSpinBox          → 無樣式（白色 spinbox）
ConditionStringEdit       → 無樣式（白色輸入框）
ConditionRemoveBtn        → 無樣式（灰色按鈕）
ConditionPresetLabel      → 無樣式
ConditionPresetCombo      → 無樣式
ConditionPresetApplyBtn   → 無樣式
ConditionAddCombo         → 無樣式
ConditionAddBtn           → 無樣式
```

結果：整個 P22 Condition Builder 以系統原生外觀渲染，在深色主題中顯示為白色/灰色系 widget，與其他深色卡片強烈對比，視覺上極不協調。

**建議方案**

在 editor.qss（或獨立的 `condition_builder.qss`）中新增對應的深色主題樣式。

關鍵樣式目標：
- Label：`color: #6a7a96`（與 `QGroupBox#RuleEditorCard QLabel` 一致）
- QLineEdit：背景 `#0a0e18`，邊框 `#1c2845`，focus `#3b82f6`
- QComboBox：同 QLineEdit 風格
- QSpinBox：同 QLineEdit 風格
- QPushButton "×"：小型、半透明紅色風格
- QPushButton "新增條件"/"套用"：深色主色調按鈕

範例（最小必要樣式）：

```qss
/* ConditionBuilderWidget 內部元件 */
#ConditionLabel {
    color: #6a7a96;
    font-size: 11px;
}

#ConditionStringEdit,
#ConditionOpCombo,
#ConditionValueCombo,
#ConditionAddCombo,
#ConditionPresetCombo {
    background: #0a0e18;
    color: #c8d8f0;
    border: 1px solid #1c2845;
    border-radius: 3px;
    min-height: 24px;
    padding: 2px 6px;
    font-size: 12px;
}

#ConditionSpinBox {
    background: #0a0e18;
    color: #c8d8f0;
    border: 1px solid #1c2845;
    border-radius: 3px;
    min-height: 24px;
}

#ConditionRemoveBtn {
    background: rgba(239, 68, 68, 0.15);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 3px;
    font-weight: bold;
}
#ConditionRemoveBtn:hover {
    background: rgba(239, 68, 68, 0.3);
    border-color: rgba(239, 68, 68, 0.6);
}

#ConditionAddBtn, #ConditionPresetApplyBtn {
    background: rgba(99, 102, 241, 0.15);
    color: #a5b4fc;
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 3px;
    min-height: 24px;
    padding: 2px 10px;
}
#ConditionAddBtn:hover, #ConditionPresetApplyBtn:hover {
    background: rgba(99, 102, 241, 0.28);
}

#ConditionBuilderScroll {
    background: transparent;
    border: none;
}
```

**預估成本：M**（純 QSS，不改邏輯；但需人工 QA 每種 condition type 的視覺效果）

---

## Medium — 建議修正

### M-05

**雙層 QScrollArea 滾動衝突**

**問題描述**

`ConditionBuilderWidget` 內部有 `QScrollArea`（`ConditionBuilderScroll`），而它被嵌入在 Rule Editor 的主 `QScrollArea`（`RuleDetailScrollArea`）內。

當使用者滑鼠停在 ConditionBuilderWidget 上方滾動時：
- Windows 預設行為：觸發內層 scroll（ConditionBuilderWidget 的列滾動）
- 使用者預期：外層 scroll（瀏覽整個 Rule Editor）

若列數少於 5 個，內層 scroll 不會出現，此時 scroll 事件會向上傳遞。但當列數多時（> 6 個），使用者滾動滑鼠輪無法移動到 Rule Editor 的外觀/音效等下方卡片。

**建議方案**

在 `ConditionBuilderWidget` 的 scroll area 加入 scroll event 上傳機制：

```python
# 繼承 QScrollArea 並 override wheelEvent
class _ConditionScrollArea(QScrollArea):
    def wheelEvent(self, event):
        # 若垂直捲動桿不可動（最頂或已到底），傳給父層
        bar = self.verticalScrollBar()
        at_edge = (
            (event.angleDelta().y() > 0 and bar.value() == bar.minimum()) or
            (event.angleDelta().y() < 0 and bar.value() == bar.maximum())
        )
        if at_edge or not self.verticalScrollBar().isVisible():
            event.ignore()
        else:
            super().wheelEvent(event)
```

或更激進的方案：設定 `setMaximumHeight` 足夠大，讓內層 scroll bar 幾乎不出現（由外層負責滾動）。

**預估成本：M**

---

### M-06

**ConditionBuilderWidget 高度上限 300px 可能截斷**

**問題描述**

```python
self._cond_builder.setMinimumHeight(180)
self._cond_builder.setMaximumHeight(300)
```

每列 ConditionRowWidget 高約 36px，Preset 工具列約 34px，新增條件列約 34px，邊距約 16px。

可見列數 ≈ (300 - 34 - 34 - 16) / 36 ≈ 6 列。

第 7 個條件開始被截斷到內部 scroll area。結合 M-05 的雙層 scroll 問題，這會造成操作困難。

**建議方案**

提高上限至 `420px` 或完全移除 `setMaximumHeight`，讓 `ConditionBuilderWidget` 根據內容自然擴展（外層 scroll 處理整體高度）。

```python
self._cond_builder.setMinimumHeight(160)
# 移除 setMaximumHeight
```

**預估成本：S**（改 1 行，需目視驗證）

---

### M-07

**Preset 套用後 Combo 未重設**

**問題描述**

使用者套用 "後期稀有裝備" preset 後，Combo 仍顯示 "後期稀有裝備"。若使用者誤操作再按 "套用"，會再次出現確認對話框，體驗繁瑣。

**建議方案**

`apply_preset` 成功後，將 combo 重設回佔位符：

```python
def apply_preset(self, key: str, skip_confirm: bool = False) -> None:
    ...
    self.set_conditions(conditions)
    self._on_condition_changed()
    # 重設 combo 回佔位符
    self._preset_combo.setCurrentIndex(0)
```

**預估成本：S**

---

### M-08

**`ConditionValue` 在方法內重複 import 4 次**

**問題描述**

`rule_detail_editor.py` 中有 4 處一模一樣的 lazy import：

```python
# 出現在 _resolve_basetype_alias, _resolve_class_alias,
#           _on_basetype_completed, _on_class_completed
from core.condition_builder import ConditionValue
```

Python 的 import 機制會 cache，效能影響極小，但程式碼風格不一致（其他 `core.*` import 都在模組頂層）。

**建議方案**

移至檔案頂層 import 區塊（有條件可選：`TYPE_CHECKING` guard 或直接無條件 import）：

```python
# rule_detail_editor.py 頂層
try:
    from core.condition_builder import ConditionValue as _ConditionValue
except ImportError:
    _ConditionValue = None  # fallback
```

或更簡單：直接無條件加入 `from core.condition_builder import ConditionValue`，因為 `condition_builder.py` 已是確定存在的核心模組。

**預估成本：S**

---

### M-09

**RuleEditorAliasService 建立兩份實例**

**問題描述**

`RuleEditorAliasService` 在兩處各自初始化：

1. `RuleDetailEditor.__init__` → `self._alias_svc = RuleEditorAliasService()`
2. `ConditionBuilderWidget.__init__` → 若 `alias_svc is None` → `self._alias_svc = RuleEditorAliasService()`

但 P22.2 整合時，`RuleDetailEditor` 建立 `ConditionBuilderWidget` 時已傳入 `alias_svc=self._alias_svc`，所以 `ConditionBuilderWidget` 不應再自行建立。

問題在於 `ConditionBuilderWidget` 也可以被**獨立使用**（不在 `RuleDetailEditor` 中），此時需自建 `alias_svc`。架構上沒有錯，但在 Rule Editor 流程中，兩個物件持有相同資料的不同副本：

- 每個 `RuleEditorAliasService` 內建一個 `AliasResolver`
- 每個 `AliasResolver` 讀取並 parse `bundled_aliases_zh_tw.json`（~數百 KB）
- Rule Editor 的 `ConditionRowWidget`（String type）又各自建立一個 `AliasCompleter` → `AliasCompleterLogic` → `AliasResolver`

在一個 Rule Editor 中，最多可能有 `3 個 AliasResolver 實例`（editor、builder widget、row widget），全部讀取同一個 JSON 檔案。

**建議方案**

將 `AliasResolver` 改為 module-level singleton 或明確在初始化時傳入：

```python
# core/alias_resolver.py
_instance: AliasResolver | None = None

def get_shared_resolver() -> AliasResolver:
    global _instance
    if _instance is None:
        _instance = AliasResolver()
    return _instance
```

此方案可讓所有層共享同一個已解析的資料，減少記憶體與 I/O。

**預估成本：M**（需改 `AliasResolver`、`AliasCompleterLogic`、`RuleEditorAliasService` 初始化邏輯）

---

### M-10

**Preset 沒有預覽，容易誤選**

**問題描述**

Preset combo 只顯示中文標籤（如「高價值通貨」），使用者選擇前不知道該 preset 包含哪些條件，確認對話框也沒有顯示條件摘要，只問「確認覆蓋？」。

**建議方案**

方案 A：在確認對話框中顯示 preset 條件摘要：

```python
conditions_summary = "\n".join(f"  • {k}: {v}" for k, v in preset.conditions)
QMessageBox.question(
    self,
    "套用模板",
    f"套用「{preset.label}」，將設定以下條件：\n{conditions_summary}\n\n確認覆蓋目前條件？",
    ...
)
```

方案 B（進階）：Combo hover 時以 Tooltip 顯示條件列表。實作成本較低，但觸發方式較隱晦。

**預估成本：M**（A 方案 S，B 方案 M）

---

## Low — 日後改善

### L-11

**"×" 移除按鈕觸控目標過小**

```python
rm.setFixedSize(22, 22)
```

22×22px 在觸控螢幕或高 DPI 顯示器上容易點偏。建議改為 `28×28` 或保持 22×22 但加 `padding` 讓點擊區域更大。

**預估成本：XS**

---

### L-12

**Placeholder "Gems" 與實際 class "Skill Gem" 不符**

`_class_edit.setPlaceholderText('"Currency" "Gems" …')`  
但 POE2 的分類名稱是 `"Skill Gem"`（非 `"Gems"`），這可能導致使用者直接輸入 `Gems` 而不匹配任何物品。

ConditionRowWidget 的 Class placeholder 同樣使用 `'"Currency" "Gems" …'`，建議統一改為：  
`'"Currency" "Skill Gem" …'`

**預估成本：XS**（改 2 行字串）

---

### L-13

**套用 Preset 後無法復原（缺 Undo）**

使用者誤套用 preset 後，原有條件（如精心設定的多條件組合）永久遺失，目前唯一的保護是確認對話框。

長期方向：實作 Condition Undo Stack（`QUndoStack`）。短期緩解方案：套用前暫存到剪貼簿欄位或 "上次條件" 功能。

**預估成本：L**（完整 Undo Stack 架構）

---

### L-14

**條件標籤寬度 68px 在部分字型下可能截斷**

```python
lbl.setFixedWidth(68)
```

「連結插槽」（4 字 × ~15px = 60px）在預設字型下剛好，但若系統使用較大預設字型或使用者放大 DPI，可能截斷。

建議改為 `setMinimumWidth(68)` 而非 `setFixedWidth`，或改為 `72px`。

**預估成本：XS**

---

### L-15

**update_condition 空值不移除既有列**

```python
def update_condition(self, cv: ConditionValue) -> None:
    for row in self._rows:
        if row._cdef.key == cv.key:
            row.set_value(cv)   # ← 即使 cv.is_empty()，列仍保留
            return
    if not cv.is_empty():
        self._add_row(cv)
```

當使用者清空舊「條件」卡片的 `Class` 欄位後，`update_condition(ConditionValue("Class","",""))` 被呼叫，但 ConditionBuilderWidget 的 Class 列仍然存在（只是顯示空白）。

`_build_rule_from_fields` → `get_conditions` → `save_to_rule` 在遇到空值時會正確跳過輸出，所以**功能上正確**，但 UI 上留有一個空的 Class 列讓人困惑。

**建議方案**

```python
def update_condition(self, cv: ConditionValue) -> None:
    for row in self._rows:
        if row._cdef.key == cv.key:
            if cv.is_empty():
                self._on_remove_row(row)   # 清空 → 移除列
            else:
                row.set_value(cv)
            return
    if not cv.is_empty():
        self._add_row(cv)
```

注意：`_on_remove_row` 會發射 `conditions_changed`，需確認此處不造成信號迴圈。

**預估成本：S**（5 行修改 + 3 個邊界測試）

---

## 效能觀察

### Rule 切換（set_rule）

`set_rule` → `_populate_fields` → `_cond_builder.set_conditions` → `_rebuild_rows`

每個 `ConditionRowWidget`（String type）在建構時初始化 `AliasCompleter` → `AliasCompleterLogic` → `AliasResolver`（可能讀 JSON）。

若一個 rule 有 Class + BaseType，切換規則時需建立 2 個 AliasResolver。如果 AliasResolver 使用 module-level singleton（見 M-09），此問題自動消失。

**目前評估：可接受，但 M-09 修正後可顯著改善。**

### Condition 更新（conditions_changed signal）

每次 widget 任意欄位改變 → `conditions_changed` → `_on_cond_builder_changed` → `_on_any_field_changed` → `_build_rule_from_fields`（deepcopy）→ `rule_changed`。

`deepcopy(self._rule)` 的成本取決於 rule 大小（conditions + actions 清單）。對於一般 rule，此成本極小（< 1ms）。

**目前評估：無問題。**

### 搜尋補全（AliasCompleter）

`textChanged` → `suggest(query)` → `AliasResolver.resolve_zh(query)` → list scan。

`AliasResolver.resolve_zh` 是同步操作。若資料量大且每次都 full-scan，在低階硬體上 keystroke 可能延遲。

目前 `MAX_SUGGESTIONS = 8`，已有合理限制。若 `AliasResolver` 使用記憶體中的 dict 做精確/前綴查詢（而非全文 scan），效能已足夠。

**目前評估：需實際量測，理論上無問題。**

---

## 修正優先順序建議

### 第一批（本次衝刺）

| # | 說明 | 成本 |
|---|------|------|
| F-02 | 補 `_on_any_field_changed()` 在 completed 回呼 | S |
| F-03 | 修正 ConditionBuilderCard objectName | S |
| M-07 | Preset 套用後重設 combo | S |
| M-08 | 移除重複 import | S |
| L-12 | 修正 placeholder 文字 | XS |
| L-14 | 條件 label 改用 setMinimumWidth | XS |

### 第二批（下個衝刺）

| # | 說明 | 成本 |
|---|------|------|
| F-01 | 隱藏舊 Class/BaseType 欄位（或整合） | M |
| F-04 | 補齊 QSS 樣式 | M |
| M-05 | 雙層 scroll 修正 | M |
| M-06 | 移除 maxHeight 限制 | S |
| M-10 | Preset 確認對話框加條件摘要 | M |
| L-15 | update_condition 空值移除列 | S |

### 第三批（架構改善）

| # | 說明 | 成本 |
|---|------|------|
| M-09 | AliasResolver singleton | M |
| L-13 | Undo Stack | L |

---

## 程式碼耦合分析

### 過度耦合點

**rule_detail_editor.py ↔ ConditionBuilderWidget**

`_on_cond_builder_changed` 直接存取 `self._class_edit`、`self._basetype_edit` 文字欄位做同步。若未來移除舊文字欄位，需同步更新此方法。

建議：加入 `# P22.2 legacy sync — 移除舊 Class/BaseType 欄位後可刪除此區塊` 標記，方便未來清理。

**ConditionRowWidget ← AliasCompleter**

每個 STRING type row 各自持有 AliasCompleter 實例（見 M-09）。

### 重複邏輯

**`_get_from_list` 與 `_update_in_list`**

這兩個靜態方法在 `RuleDetailEditor` 中定義，但 `ConditionBuilderService.save_to_rule` 已有等效實作。長期可考慮統一至 `FilterRule` 或 `ConditionBuilderService`，但目前分離合理（兩者用途不完全相同）。

**中文 alias 解析流程重複**

`RuleDetailEditor` 的 `_resolve_class_alias` 與 `ConditionRowWidget` 的 `_on_string_editing_finished` 做相同的事：`resolve_filter_value` → 設回欄位 → 更新 tooltip。這段邏輯在兩處分別實作，建議抽取為共用 helper（低優先）。

### 可抽取共用元件

- `_sync_text_field_to_widget(field: QLineEdit, key: str)` — 封裝 blockSignals + setText + update_condition 的組合
- `_apply_condition_tooltip(edit: QLineEdit, svc, key: str, value: str)` — 封裝 tooltip 更新邏輯
