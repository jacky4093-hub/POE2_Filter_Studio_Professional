# POE2 Filter Studio — 發布前檢查清單

版本：**0.9.0-beta**
日期：___________
執行人：___________

> 每個項目完成後在 `[ ]` 填入 `[x]`。所有項目通過才可發布。

---

## 一、自動化測試

```bash
python -m pytest
```

- [ ] **全套 pytest 通過（0 failures）**
  - 預期測試數：≥ 1754
  - 指令：`python -m pytest -q`

```bash
python -m pytest tests/test_packaging_smoke.py
```

- [ ] **Packaging smoke 通過（40 個）**
  - 驗證 assets 路徑、bootstrap 入口、spec 草案存在

---

## 二、手動啟動測試

### 2-1 啟動程式

```bash
python src/main.py
```

- [ ] 程式正常啟動，無 Python traceback
- [ ] 顯示 **Welcome 畫面**（非編輯器）
- [ ] 視窗標題為 `POE2 Filter Studio 0.9.0-beta`
- [ ] Help → 關於：顯示 APP_NAME、版本號、作者

---

## 三、檔案操作

### 3-1 開啟 Filter 檔

- [ ] File → 開啟（或 `Ctrl+O`）→ 選擇有效 `.filter` 檔
- [ ] 規則列表正確顯示（Show/Hide 均顯示）
- [ ] 視窗標題更新為 `POE2 Filter Studio 0.9.0-beta — <filename>`

### 3-2 新增 Rule

- [ ] 點擊「新增規則」按鈕（或 `Ctrl+N`）
- [ ] 新規則出現在列表頂部
- [ ] 視窗標題出現 `*` 前綴（dirty state）

### 3-3 修改顏色

- [ ] 在 RuleDetailEditor 修改 SetTextColor RGBA 值
- [ ] Preview Panel 即時更新文字顏色
- [ ] dirty state 正確標記（標題有 `*`）

### 3-4 修改 Minimap

- [ ] 修改 SetMinimapIcon（形狀、顏色、大小）
- [ ] Preview Panel 的小地圖圖示即時更新

### 3-5 修改音效 / 光效

- [ ] 修改 PlayAlertSound（ID、音量）
- [ ] 修改 SetBeam（顏色、Temp 勾選）
- [ ] 欄位值正確儲存（不被截斷）

---

## 四、Undo / Redo

- [ ] `Ctrl+Z` 復原最後一次操作（規則還原）
- [ ] `Ctrl+Y` 重做（復原的操作重新生效）
- [ ] 連續多次 Undo/Redo 不崩潰
- [ ] Quick Fix 後可用 `Ctrl+Z` 還原

---

## 五、Validation Panel

### 5-1 驗證面板正常顯示

- [ ] 開啟有問題的 `.filter` 後，底部 Validation Panel 顯示計數
- [ ] ERROR / WARNING / INFO 個別計數正確

### 5-2 點擊問題定位

- [ ] 點擊 Validation Panel 中的問題項目
- [ ] 規則列表自動捲動並選中對應規則

### 5-3 Quick Fix

- [ ] 有 Quick Fix 可套用的問題顯示 `Fix` 按鈕
- [ ] 點擊 `Fix` → 規則值自動修正（如 SetFontSize 超出範圍 → 自動 clamp）
- [ ] 修復後 `Ctrl+Z` 可還原

---

## 六、Save Warning Dialog

- [ ] 製造一個 ERROR（如 SetFontSize = 0）→ 儲存（`Ctrl+S`）
- [ ] 出現確認對話框顯示問題清單
- [ ] 點擊「取消」：不儲存，保留錯誤
- [ ] 點擊「仍然儲存」：檔案正常儲存

---

## 七、Dirty State 保護

### 7-1 關閉前確認

- [ ] 修改規則後關閉視窗（Alt+F4 / X 按鈕）
- [ ] 出現 Save / Discard / Cancel 對話框
- [ ] 點擊 **Save**：儲存後關閉
- [ ] 點擊 **Discard**：不儲存直接關閉
- [ ] 點擊 **Cancel**：取消關閉，保留變更

### 7-2 開新檔前確認

- [ ] 修改規則後 File → 新增（`Ctrl+N`）
- [ ] 出現 Save / Discard / Cancel 對話框，行為同 7-1

---

## 八、儲存 / 載入

### 8-1 儲存

- [ ] `Ctrl+S` 儲存至原始路徑（無對話框）
- [ ] 儲存後標題 `*` 消失
- [ ] 重新開啟檔案，內容與儲存前一致（解析不遺失）

### 8-2 另存新檔

- [ ] File → 另存新檔（`Ctrl+Shift+S`）→ 新路徑
- [ ] 儲存成功，標題更新為新檔名

---

## 九、搜尋

- [ ] `Ctrl+F` 開啟搜尋列
- [ ] 輸入關鍵字 → 符合規則以琥珀色高亮
- [ ] `F3` 跳下一個，`Shift+F3` 跳上一個
- [ ] `Escape` 清除搜尋、移除高亮

---

## 十、Packaging Smoke（開發環境驗證）

```bash
python -m pytest tests/test_packaging_smoke.py -v
```

- [ ] `assets/styles/*.qss` 均存在且非空
- [ ] `assets/icons/*.svg` 均存在且非空
- [ ] `packaging/poe2_filter_studio.spec` 存在
- [ ] `packaging/README.md` 存在
- [ ] `src/app_info.py` 中的 APP_VERSION 與標題一致

---

## 完成確認

> 以上所有項目 `[x]` 後，視為本版本可進入發布流程。

| 項目 | 通過 |
|---|---|
| 自動化測試（pytest） | |
| 手動 UI 測試 | |
| 儲存 / 載入循環 | |
| Validation + Quick Fix | |
| Dirty State 保護 | |
| Packaging Smoke | |

**簽核：** ___________　　**日期：** ___________
