# P23 Item Selector UX Review

**日期：** 2026-06-29
**版本：** P23.3 完成後
**審查範圍：** `src/ui/item_selector_widget.py`、`src/ui/rule_detail_editor.py` (`_create_item_selector_dialog`)、`src/assets/styles/editor.qss` (P23.2/P23.3 區塊)

---

## 問題清單

### HIGH

---

#### H-01 雙擊物品無確定動作

**分類：** Dialog 流程  
**描述：**  
目前流程強制使用者：①點選物品 → ②再按「確定」按鈕。  
業界慣例（檔案選擇器、設定對話框、VS Code Quick Pick）均支援「雙擊即確定」。  
目前的 `_item_list.currentItemChanged` 訊號只發射 `item_selected`，但 Dialog 不連接此訊號。  
`itemDoubleClicked` 訊號完全未連接。

**修改建議：**  
在 `_create_item_selector_dialog` 中，`selector` 建立後加入：
```python
selector._item_list.itemDoubleClicked.connect(dlg.accept)
```
此一行即可完整實作雙擊確定，不需改動 `ItemSelectorWidget`。

**預估成本：** XS（1 行，加入 `_create_item_selector_dialog`）

---

#### H-02 搜尋無結果時無空狀態提示

**分類：** Search UX  
**描述：**  
當搜尋文字不符合任何物品，`_populate_list([])` 被呼叫，`_item_list` 變成空白。  
使用者無法判斷是「輸入錯誤」、「資料庫不含此物品」還是「功能故障」。  
`_item_list.count() == 0` 時應顯示提示文字。

**修改建議：**  
方案 A（最小改動）：在 `_on_search_changed` 中搜尋結果為空時，加入一個禁用的 `QListWidgetItem` 作為提示：
```python
if not results:
    placeholder = QListWidgetItem("找不到符合的物品")
    placeholder.setFlags(Qt.ItemFlag.NoItemFlags)  # 不可選取
    self._item_list.addItem(placeholder)
```
方案 B：在 `_item_list` 上方或下方放置隱藏 `QLabel`，搜尋結果為空時顯示。

推薦方案 A：實作簡單，不需新增 Widget。

**預估成本：** S（約 10 行，含 QSS 樣式）

---

### MEDIUM

---

#### M-01 Item 列表雙行無視覺層次

**分類：** Item List UX  
**描述：**  
每個 item 顯示為：
```
中文名稱
English Name
```
兩行使用同樣的顏色（`#c8d8f0`）、同樣的字型大小（12px）、同樣的粗細。  
使用者需要花時間辨認哪行是中文主名稱、哪行是英文次要名稱。  
對快速選取流程影響明顯。

**修改建議：**  
以 QSS `::first-line` 偽元素強化中文行（Qt 支援有限），或改用 `QStyledItemDelegate` 自訂繪製。  
最實用的無 delegate 方案：利用 QSS 為 `#ItemSelectorItemList` 的字型設定稍大，  
並在 `QListWidgetItem` text 加入 HTML（若 Qt rich text list item 可支援，Qt6 通常不直接支援）。  
**建議使用 QStyledItemDelegate**：中文行 bold + 100% 亮度，英文行 80% 亮度 + italic 或小字。

實作成本高但 UX 提升大。可先以簡單方式替代：在中英文之間加入分隔空格使視覺分層：
```python
f"{item.name_zh}\n  {item.name_en}"  # 英文行縮排 2 space 視覺暗示「次要」
```
此方式成本極低，有一定效果。

**預估成本：**  
- 簡易方案（縮排）：XS（1 行）  
- 完整方案（QStyledItemDelegate）：L（新增 50-80 行 Delegate 類別）

---

#### M-02 `QDialogButtonBox` OK / Cancel 未套用深色主題 QSS

**分類：** QSS Review  
**描述：**  
`_create_item_selector_dialog` 建立的 `QDialogButtonBox` 使用系統預設樣式（Windows 淺色按鈕）。  
在深色背景（`#07090f`）Dialog 中，OK / Cancel 按鈕顯示為系統原生灰白色，視覺嚴重不一致。  
P22.5 的 `#ConditionPresetApplyBtn`、P23.3 的 `#BaseTypePickBtn` 都有深色主題 QSS，  
唯獨 Dialog 按鈕被遺漏。

**修改建議：**  
在 `editor.qss` 末尾加入：
```qss
#ItemSelectorDialog QPushButton {
    background: #0f1a2e;
    color: #c8d8f0;
    border: 1px solid #1c2845;
    border-radius: 4px;
    min-height: 28px;
    padding: 4px 16px;
    font-size: 12px;
}
#ItemSelectorDialog QPushButton:hover {
    background: #1a2f50;
    border-color: #3b82f6;
}
#ItemSelectorDialog QPushButton:default {
    border-color: #3b82f6;
    color: #93c5fd;
}
```
同時需將 `dlg` 的 stylesheet 繼承確保 QSS 生效（應已生效，因 Dialog 繼承 app stylesheet）。

**預估成本：** S（15 行 QSS）

---

#### M-03 `_populate_list` 缺少 `setUpdatesEnabled(False/True)` 造成重繪閃爍

**分類：** Performance  
**描述：**  
`_populate_list` 使用 `blockSignals(True/False)` 防止訊號重複觸發，但 **不防止重繪**。  
每次 `addItem` 都可能觸發 viewport 更新。  
Currency 分類有 ~108 個物品，Weapons 約 40+，  
在 Category 切換時，`clear()` + 108 次 `addItem` 每次都可能引發重繪，造成可見閃爍。

**修改建議：**  
在 `_populate_list` 的 `blockSignals(True)` 後加入：
```python
self._item_list.setUpdatesEnabled(False)
```
在 `blockSignals(False)` 前加入：
```python
self._item_list.setUpdatesEnabled(True)
```
共 2 行，完全解決問題。

**預估成本：** XS（2 行）

---

#### M-04 Enter 鍵在 Item List 中無法確認 Dialog

**分類：** Keyboard UX  
**描述：**  
使用者以 ↑↓ 瀏覽物品後，直覺按 Enter 確認。  
但 `QListWidget` 在收到 Enter 時，會觸發 `itemActivated` 訊號（item 激活），  
並**消耗**該按鍵事件，不傳遞給 Dialog 的預設按鍵處理（OK 按鈕）。  
結果：Enter 在列表中無任何確認效果，使用者必須移動焦點至 OK 按鈕再按 Space/Enter。

**修改建議：**  
在 `_create_item_selector_dialog` 中，連接 `itemActivated` 訊號到 `dlg.accept`：
```python
selector._item_list.itemActivated.connect(lambda _: dlg.accept())
```
`itemActivated` 在 Enter 及雙擊時均觸發（與 H-01 雙擊確定配合使用效果最佳）。  
此方案與 H-01 修正可合併為 1~2 行。

**預估成本：** XS（1 行，可與 H-01 合併）

---

### LOW

---

#### L-01 `#ItemSelectorItemList::item:focus` 未定義 QSS

**分類：** QSS Review / Keyboard UX  
**描述：**  
鍵盤 ↑↓ 導航時，Qt 繪製預設焦點矩形（通常為虛線框），  
在深色主題中幾乎不可見（預設顏色接近背景）。  
已定義 `::item:hover` 和 `::item:selected`，但缺少 `::item:focus`。

**修改建議：**  
在 `editor.qss` 加入：
```qss
#ItemSelectorItemList::item:focus {
    outline: none;
}
```
同時確保 `:selected` 狀態視覺足夠清楚（目前 `#1e3a5f` 已足夠）。  
若需額外 focus ring：
```qss
#ItemSelectorItemList { outline: 1px solid #3b82f6; }
```

**預估成本：** XS（3 行 QSS）

---

#### L-02 動作按鈕顏色風格不一致

**分類：** QSS Review  
**描述：**  
| 按鈕 | 顏色 | objectName |
|------|------|-----------|
| ConditionPresetApplyBtn | 靛藍 `#6366f1` | P22.5 |
| ConditionAddBtn | 靛藍 `#6366f1` | P22.5 |
| BaseTypePickBtn | 藍色 `#3b82f6` | P23.3（本次新增）|

`BaseTypePickBtn` 使用與其他動作按鈕不同的色調。  
雖然語義上 `BaseTypePickBtn` 是「開啟選擇器」的次要動作，靛藍用於「套用 / 確認」類動作，  
但視覺不一致仍值得統一。

**修改建議：**  
將 `BaseTypePickBtn` 改用靛藍色調（`#6366f1` 家族），或維持藍色但補充文件說明命名規則：  
- 靛藍 = 套用 / 確認類動作  
- 藍色 = 開啟輔助視窗類動作  

若採統一方案，修改 `editor.qss` 中 `#BaseTypePickBtn` 的顏色值即可。

**預估成本：** XS（3 行 QSS 顏色值替換）

---

#### L-03 `setSizeHint(QSize(0, 42))` 寬度語義不明確

**分類：** Code Review  
**描述：**  
`_populate_list` 中每個 item 設定 `setSizeHint(QSize(0, 42))`。  
`QSize(0, 42)` 的寬度為 0，語義為「0 像素寬」。  
在 `QListWidget` 的 `ListMode`（垂直排列）中，item 寬度由視圖決定，size hint 的寬度通常被忽略，  
但此用法語義不明確，正確寫法應為 `QSize(-1, 42)`（`-1` 代表「交由視圖決定」）。

**修改建議：**  
```python
lw.setSizeHint(QSize(-1, 42))
```

**預估成本：** XS（1 字元修改）

---

#### L-04 `setSpacing(1)` + `border-bottom: 1px` 可能造成 2px 視覺間隔

**分類：** Item List UX  
**描述：**  
`_item_list.setSpacing(1)` 在每個 item 外圍加 1px 間距（上下各 0.5px，或上 1px）。  
QSS 中 `#ItemSelectorItemList::item` 同時設定 `border-bottom: 1px solid #0d1424`。  
兩者疊加可能在部分平台顯示為 2px 的 item 分隔。

**修改建議：**  
二擇一：
1. 移除 `setSpacing(1)`，讓 `border-bottom` 獨立負責分隔視覺
2. 移除 `border-bottom` QSS，讓 `setSpacing(1)` 負責視覺分隔

建議方案 1：保留 QSS border（色調可控），移除 `setSpacing`。

**預估成本：** XS（1 行刪除）

---

#### L-05 搜尋框置於底部，Tab 順序對「先搜後選」習慣不直觀

**分類：** Search UX / Keyboard UX  
**描述：**  
佈局順序：Category → Subcategory → Item List → **Search（底部）**  
Tab 順序同佈局順序，使用者按 Tab 需經過 3 個元件才能到達搜尋框。  
對「先打字搜尋再確認」的使用習慣（類似 VS Code Quick Pick、macOS Spotlight），  
搜尋框不在首位略顯不便。

**評估：**  
此設計為有意的「瀏覽優先」UX（先分類瀏覽，有需要再搜尋），  
與 Item Selector 的三層瀏覽定位一致。  
**暫不建議修改佈局**，但可透過以下方式改善：
- Dialog 開啟時主動設定搜尋框焦點（若需要「立即搜尋」流程）
- 或保持 Category combo 焦點（若需要「先分類再搜尋」流程）

**預估成本：** XS（1 行 `setFocus()` 設定初始焦點）

---

## 優先度總表

| # | 優先度 | 分類 | 標題 | 預估成本 |
|---|--------|------|------|----------|
| H-01 | HIGH | Dialog 流程 | 雙擊物品無確定動作 | XS |
| H-02 | HIGH | Search UX | 搜尋無結果無空狀態提示 | S |
| M-01 | MEDIUM | Item List UX | 雙行視覺層次不足 | XS ~ L |
| M-02 | MEDIUM | QSS | Dialog 按鈕未套深色主題 | S |
| M-03 | MEDIUM | Performance | `_populate_list` 缺少 `setUpdatesEnabled` | XS |
| M-04 | MEDIUM | Keyboard UX | Enter 在 item list 無法確認 Dialog | XS |
| L-01 | LOW | QSS | `::item:focus` 未定義 | XS |
| L-02 | LOW | QSS | 動作按鈕顏色不一致 | XS |
| L-03 | LOW | Code | `QSize(0, 42)` 語義不明確 | XS |
| L-04 | LOW | Item List | `setSpacing` + `border-bottom` 雙倍間距 | XS |
| L-05 | LOW | Keyboard UX | 搜尋框置底 Tab 順序不直觀 | XS |

---

## 建議修正順序

**Phase 1（成本最低、效益最高）：**
- H-01 + M-04 合併（`itemDoubleClicked` + `itemActivated` 各 1 行）
- M-03（`setUpdatesEnabled`，2 行）
- M-02（Dialog 按鈕 QSS，15 行）
- L-01、L-02、L-03、L-04（各 1-3 行）

**Phase 2（需較多設計討論）：**
- H-02（空狀態提示，需決定 UI 方案）
- M-01（雙行視覺層次，若採完整 Delegate 方案）
- L-05（初始焦點策略，需確認 UX 偏好）

---

*Review by Claude Sonnet 4.6 — P23.4 UX Polish Report*
