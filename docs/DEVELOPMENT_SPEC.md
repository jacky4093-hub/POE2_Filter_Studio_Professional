# POE2 Filter Studio — 開發規範

## 1. Project Goal

- POE2 Filter Studio 是 Windows 桌面版 POE2 過濾器編輯器
- UI 框架：PySide6（不可更換）
- 不做市場價格、Trade API、poe.ninja、poe.watch 等任何外部報價功能

---

## 2. Architecture Rules

### 分層職責

| 層級 | 模組 | 職責 |
|------|------|------|
| 解析層 | `parser/filter_parser.py` | 純文字 → `FilterRule` 清單，不含任何 UI 或狀態 |
| 輸出層 | `parser/filter_exporter.py` | `FilterRule` 清單 → 純文字，不含任何 UI 或狀態 |
| 文件層 | `core/document.py` | 管理整份 filter：rules、file_path、dirty 狀態、所有規則操作 |
| UI 層 | `ui/`、`widgets/`、`editor/` | 只讀取或呼叫 FilterDocument，不直接操作 parser/exporter |

### 嚴格規定

- `MainWindow` 不可直接呼叫 `parse_filter` 或 `export_filter`
- `RuleListWidget`、`RuleEditorWidget` 不可持有或操作檔案路徑
- Parser / Exporter 屬於核心模組，修改前必須在 PR/commit 中說明影響範圍
- 修改超過 3 個核心模組前，必須先向使用者確認

### 未來擴充預留

以下功能的資料流架構必須從現在開始設計正確，即使功能本身尚未實作：

- **Undo/Redo**：所有規則修改必須透過 `FilterDocument` 的方法，不得在 UI 中直接改寫 `_rules`
- **Drag & Drop**：Rule 清單的排序邏輯必須在 `FilterDocument` 層處理
- **Preview**：預覽引擎讀取 `FilterDocument.rules`，不直接解析原始文字
- **Search**：搜尋對象是 `FilterDocument.rules`，結果回傳 index 清單給 UI

---

## 3. Data Preservation Rules

- 空白行、`#` 開頭的註解行，必須以 `pre_lines` 保存於相鄰 `FilterRule` 中
- 未知指令（不在已知 conditions / actions 清單內）必須存入 `FilterRule.unknown_lines`
- 匯出時 `unknown_lines` 必須原文輸出，不可刪除或改寫
- Parser / Exporter 的 round-trip 測試是每次 commit 前的必要條件
- 任何對 `FilterRule` 資料結構的修改，必須同步更新 exporter 確保不遺失

---

## 4. UI Design Rules

- 方向：Professional Editor（參考 VS Code、JetBrains 風格）
- Rule Editor 未來要改成 Property Grid 風格，避免現在把欄位硬編碼
- Rule List 要能支援大型 filter（500+ rules），不可用每次全清的方式更新
- UI 層不可把資料邏輯（排序、複製、驗證）寫死在 widget 內，一律透過 `FilterDocument`
- 所有使用者可見的文字（按鈕、標題、錯誤訊息）一律使用繁體中文

---

## 5. Git Rules

- 每個版本功能完成後必須執行全套測試（見第 7 條）
- 測試全部通過後才允許 commit
- commit message 格式：`v{版本號} {簡短說明}`，例如：

  ```
  v0.3.0 Professional Rule Editor
  ```

- 不可 commit `__pycache__/`、`.env`、`*.pyc` 等暫存檔（已由 `.gitignore` 排除）

---

## 6. Roadmap

| 版本 | 狀態 | 內容 |
|------|------|------|
| v0.1.0 | ✅ 完成 | MVP：開啟、解析、編輯、儲存、Rule 增刪複製 |
| v0.2.0 | ✅ 完成 | FilterDocument 架構層、改善 Rule List 顯示 |
| v0.2.1 | ✅ 完成 | 新增開發規範文件 |
| v0.3.0 | ✅ 完成 | Professional Rule Editor（Property Grid 風格） |
| v0.4.0 | ✅ 完成 | Professional Property System（Registry + ValidationResult + CollapsibleSection） |
| v0.5.0 | 規劃中 | Undo / Redo Command Pattern |
| v0.6.0 | 規劃中 | Drag & Drop Rule Ordering |
| v0.6.0 | 規劃中 | Preview Engine（模擬物品掉落顯示） |
| v0.7.0 | 規劃中 | Search / Filter / Goto Rule |
| v0.8.0 | 規劃中 | POE2 Item Database + 中文搜尋 |
| v0.9.0 | 規劃中 | Performance Optimization（大型 filter） |
| v1.0.0 | 規劃中 | Stable Windows Release + 打包 .exe |

---

## 7. Claude Code Working Rules

以下規則適用於本專案的所有 AI 輔助開發工作：

1. **不可整個重寫專案**——每次只完成一個明確功能，以小範圍 diff 為原則
2. **不可更換 PySide6**——UI 框架已定，不討論替代方案
3. **不可加入市場價格功能**——任何形式的 Trade API、poe.ninja、poe.watch 均禁止
4. **修改前先列出檔案清單**——說明會修改哪些檔案，確認影響範圍
5. **修改超過 3 個核心檔案前，先向使用者確認**
6. **每個版本完成後列出 Summary**，格式：修改檔案 / 修改原因 / 測試方式
7. **每次測試必須包含以下四項**：
   - Parser round-trip（原文 → parse → export 必須與原文一致）
   - Edge cases（空檔案、純註解、未知指令、無條件 rule）
   - GUI headless（offscreen 平台，確認所有 import 與 widget 建立無錯誤）
   - Integration（FilterDocument + MainWindow 操作流程）
