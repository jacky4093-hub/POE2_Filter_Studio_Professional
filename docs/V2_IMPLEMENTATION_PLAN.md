# POE2 Filter Studio — V2 實作計畫

> 依據 [v2_architecture_design.md](./v2_architecture_design.md) 與 [v2_review_notes.md](./v2_review_notes.md) 整理。  
> 目標 UI 參考：`reference/v2_target_ui.png.png`  
> **本文件僅為計畫，不含程式碼修改。**

---

## 總覽

| 階段 | 版本代號 | 目標 | 預估工時 |
|------|----------|------|----------|
| **第一階段** | v2.0.0 | 暗色主題 + 主視窗外殼（零功能改動） | 2–3 天 |
| 第二階段 | v2.1.0 | 分類側欄（Category Sidebar） | 3–4 天 |
| 第三階段 | v2.2.0 | 規則卡片列表（Rule Card Browser） | 5–7 天 |
| 第四階段 | v2.3.0 | 視覺化效果選擇器（光柱 / 小地圖） | 3–4 天 |
| 第五階段 | v2.4.0 | 預覽面板（Ground / Minimap / Syntax / Audio） | 4–5 天 |
| 第六階段 | v2.5.0 | 頂部導覽列整合與細節打磨 | 3–4 天 |

### Review 決策（全程適用）

1. **不實作 Favorite / Star** — 規則卡片不含星號標記，`FilterRule` 不加 `starred` 欄位。
2. **Category Sidebar 不顯示 Section** — 側欄只顯示物品分類（通貨、地圖…），不列出 `.filter` 檔內的段落標題。
3. **Rule Browser 第一版不用 Delegate** — 改用 `QListWidget` + 自訂 `RuleCardWidget`，而非 `QListView` + `QStyledItemDelegate`。

---

## 禁止修改區（Parser / Exporter 與核心資料層）

以下檔案在 **所有階段均不得修改**，除非發現阻斷 UI 工作的致命 bug 且需另行評估：

| 檔案 | 原因 |
|------|------|
| `src/parser/filter_parser.py` | 過濾器讀取核心；修改可能破壞 round-trip |
| `src/parser/filter_exporter.py` | 過濾器匯出核心；修改可能改變 `.filter` 輸出格式 |
| `src/core/document.py` | 文件狀態、load/save 流程的中樞 |
| `src/core/models.py` | 規則資料模型 |
| `src/core/commands.py` | Undo / Redo 命令堆疊 |
| `src/core/filter_schema.py` | 欄位型別與 schema 定義 |
| `src/core/search.py` | 搜尋邏輯 |
| `src/core/sections.py` | Section 對應邏輯（v2 側欄不顯示，但邏輯層保留） |
| `src/services/settings_service.py` | 工作區設定持久化 |

### 可修改但需謹慎的檔案

| 檔案 | 限制 |
|------|------|
| `src/editor/property_widgets.py` | 第四階段前 **零修改**；第四階段僅透過新 widget 替換 PlayEffect / MinimapIcon 的 **視覺層**，`get_raw_value()` / `set_raw_value()` 格式必須與現有一致 |
| `src/editor/rule_editor.py` | debounce、flush、auto-save 路徑不可改；僅允許替換 widget 與加 inline preview |
| `src/widgets/search_bar.py` | 直接複用，原則不修改 |

---

## 現有架構對照（分析摘要）

| 職責 | 現有檔案 |
|------|----------|
| 主視窗 UI | `src/ui/main_window.py` |
| 應用程式啟動 | `src/main.py` → `src/app/bootstrap.py` |
| 規則編輯 | `src/editor/rule_editor.py`、`src/editor/collapsible_section.py`、`src/editor/property_widgets.py` |
| 規則列表 | `src/widgets/rule_list.py` |
| 預覽 | `src/ui/preview_panel.py`、`src/preview/preview_engine.py` |
| 讀取 / 儲存 | `src/ui/main_window.py`（UI 觸發）→ `src/core/document.py` → `src/parser/` |
| 搜尋列 | `src/widgets/search_bar.py` |

---

## 第一階段：v2.0.0 — 暗色主題與主視窗外殼

### 目標

- 套用深藍暗色主題，視覺接近 v2 目標圖的底色與面板層次。
- 重構 `MainWindow` 的 **佈局骨架**（4 欄 Splitter + 頂部/底部占位），現有功能 widget 暫時嵌入新殼中，行為不變。
- **不做**：分類過濾、卡片列表、視覺選擇器、NavBar 完整功能、Preview 重寫。

### 要修改 / 新增的檔案

| 動作 | 檔案 | 說明 |
|------|------|------|
| **新增** | `src/assets/theme.py` | 色彩常數（BG、TEXT、BORDER、ACCENT 等） |
| **新增** | `src/assets/styles/base.qss` | 全域暗色樣式（QWidget、QScrollBar、QSplitter、QGroupBox…） |
| **新增** | `src/assets/styles/shell.qss` | 主視窗外殼占位面板樣式 |
| **修改** | `src/app/bootstrap.py` | 新增 `apply_theme(app)`，啟動時載入 QSS |
| **修改** | `src/ui/main_window.py` | 佈局改為 4 欄 Splitter；加 Category / NavBar / StatusBar **占位 widget**；signal/slot 邏輯原封保留 |
| **修改** | `src/editor/collapsible_section.py` | 移除 header 的 hardcoded `setStyleSheet`，改 `objectName` 由 QSS 控制 |
| **可選修改** | `POE2FilterStudio.spec` | 若打包需含 `assets/styles/`，確認 `datas` 路徑 |

### 主視窗外殼結構（第一階段）

```
QMainWindow
└── Central Widget
    └── QVBoxLayout
        ├── NavBarPlaceholder      ← 固定高度 ~48px，顯示品牌文字即可
        ├── QSplitter (Horizontal, 4 欄)
        │   ├── CategoryPlaceholder   ← 固定寬 ~160px，顯示「分類（即將推出）」
        │   ├── RuleListWidget        ← 現有 widget，直接搬入
        │   ├── RuleEditorWidget      ← 現有 widget，直接搬入
        │   └── PreviewPanel          ← 現有 widget，直接搬入
        └── StatusBarPlaceholder   ← 固定高度 ~24px，顯示規則數 / 檔名占位
```

- MenuBar / Toolbar **暫時保留**（第六階段才移除並整合進 NavBar），避免第一階段破壞快捷鍵與檔案操作習慣。
- Splitter 比例寫入 `WorkspaceSettings` 的既有 restore 流程，不新增持久化欄位。

### 第一階段完成後的測試

| 類型 | 測試方式 | 通過標準 |
|------|----------|----------|
| 自動化 | `pytest`（專案根目錄） | 全部現有測試通過，零新增失敗 |
| 視覺 | `python src/main.py` 或 `scripts/run_dev.bat` | 整體為暗色；4 欄佈局可見；占位區塊有正確背景色 |
| 功能迴歸 | 開啟 `.filter` → 選規則 → 編輯 → 儲存 | 與 v1 行為完全一致 |
| 功能迴歸 | Undo / Redo、Ctrl+F 搜尋、Auto-save | 正常運作 |
| 功能迴歸 | 調整 Splitter 寬度 → 關閉重開 | 幾何與 splitter 狀態正確還原 |
| 打包（可選） | `build.bat` / PyInstaller | EXE 啟動後 QSS 正確載入（非白底） |

---

## 第二階段：v2.1.0 — Category Sidebar

### 目標

左側占位替換為真實分類側欄；點選分類過濾中間規則列表。不顯示 Section 子區塊。

### 要修改 / 新增的檔案

| 動作 | 檔案 | 說明 |
|------|------|------|
| **新增** | `src/core/categorizer.py` | `classify_rule(rule) -> Category` 純函式 |
| **新增** | `src/ui/category_sidebar.py` | `CategorySidebarWidget` |
| **新增** | `src/assets/styles/sidebar.qss` | 側欄樣式 |
| **修改** | `src/ui/main_window.py` | 替換 CategoryPlaceholder；連接 `category_selected` → 過濾 rule list |
| **新增** | `tests/test_categorizer.py` | 分類邏輯單元測試 |

### 第二階段完成後的測試

| 類型 | 測試方式 | 通過標準 |
|------|----------|----------|
| 自動化 | `pytest tests/test_categorizer.py` | ≥12 個案例：通貨、地圖、碎片、裝備、其他等 |
| 自動化 | `pytest`（全 suite） | 無迴歸 |
| 手動 | 開啟含多類規則的 `.filter`，點「通貨」 | 中間列表只顯示通貨規則 |
| 手動 | 點「全部規則」 | 列表恢復完整 |
| 手動 | 編輯規則 Class 後 flush | 側欄計數更新（規則可能換分類） |
| 手動 | Ctrl+F 搜尋 + 分類篩選同時使用 | 高亮與結果正確 |

---

## 第三階段：v2.2.0 — Rule Card Browser

### 目標

將 `RuleListWidget`（QTreeWidget 純文字）替換為 `QListWidget` + `RuleCardWidget` 卡片式列表。保留既有 public API。

### 要修改 / 新增的檔案

| 動作 | 檔案 | 說明 |
|------|------|------|
| **新增** | `src/ui/rule_card_widget.py` | 單張規則卡片 widget（色條、標題、條件摘要、字體 badge） |
| **新增** | `src/ui/rule_card_browser.py` | `RuleCardBrowser`：QListWidget 容器 + 載入 / 選取 / 高亮 API |
| **新增** | `src/assets/styles/browser.qss` | 卡片列表樣式 |
| **修改** | `src/ui/main_window.py` | `rule_list` → `rule_card_browser`；signal 重新連接 |
| **保留不刪** | `src/widgets/rule_list.py` | 並存至本階段測試通過，方便回退 |
| **新增** | `tests/test_rule_card_browser.py` | API 與 real_index 映射測試 |

### 必須保留的 API（與 `rule_list.py` 一致）

```python
rule_selected = Signal(int)          # real_index
load_rules(rules, section_map)
set_highlights(indices: set[int])
clear_highlights()
select_real_index(real_index: int)
```

### 第三階段完成後的測試

| 類型 | 測試方式 | 通過標準 |
|------|----------|----------|
| 自動化 | `pytest tests/test_rule_card_browser.py` | real_index 映射、高亮、section header 行 |
| 自動化 | `pytest tests/test_rule_list_highlight.py` | 改接新 browser 後仍通過 |
| 手動 | 捲動含 500+ 規則的 filter | 無明顯 lag |
| 手動 | 選取、新增、刪除、複製規則 | Editor / Preview 同步更新 |
| 手動 | Show / Hide / Continue 規則 | 左色條顏色正確 |
| 手動 | disabled 規則 | 卡片降低不透明度 |

---

## 第四階段：v2.3.0 — Visual Effects Pickers

### 目標

PlayEffect（光柱）與 MinimapIcon 從 dropdown 改為視覺化選擇器；`get_raw_value()` 輸出格式與舊 widget **完全一致**。

### 要修改 / 新增的檔案

| 動作 | 檔案 | 說明 |
|------|------|------|
| **新增** | `src/editor/widgets/beam_color_picker.py` | 彩色圓圈光柱選擇器 + Temp checkbox |
| **新增** | `src/editor/widgets/minimap_icon_picker.py` | 大小 + 形狀圖示格 + 顏色圓圈 |
| **修改** | `src/editor/rule_editor.py` | 替換 PlayEffect / MinimapIcon 對應 widget；**flush 路徑不動** |
| **修改** | `src/assets/styles/editor.qss` | 編輯器與新 picker 樣式 |
| **新增** | `tests/test_visual_pickers.py` | `"Red"`, `"Orange Temp"`, `""` 等格式 round-trip |

### 第四階段完成後的測試

| 類型 | 測試方式 | 通過標準 |
|------|----------|----------|
| 自動化 | `pytest tests/test_visual_pickers.py` | get/set raw value 格式一致 |
| 自動化 | `pytest tests/test_parser.py` | Exporter 輸出無意外變化 |
| 手動 | 選光柱 Orange + Temp → 儲存 → 重開 | `.filter` 含 `PlayEffect Orange Temp` |
| 手動 | 選小地圖 Star Yellow → 儲存 → 重開 | `MinimapIcon 1 Yellow Star` 正確 |
| 手動 | Auto-save（750ms） | 修改 picker 後自動 flush，無 double-flush |

---

## 第五階段：v2.4.0 — Preview Panel

### 目標

右側 Preview 升級為 4-tab：Ground / Minimap / Syntax / Audio，含 QPainter 遊戲風格渲染。

### 要修改 / 新增的檔案

| 動作 | 檔案 | 說明 |
|------|------|------|
| **新增** | `src/ui/panels/item_ground_renderer.py` | 地面物品標籤 + 光柱 |
| **新增** | `src/ui/panels/minimap_renderer.py` | 小地圖圖示渲染 |
| **新增** | `src/ui/panels/syntax_preview.py` | 唯讀語法 + QSyntaxHighlighter |
| **重寫** | `src/ui/preview_panel.py` | QTabWidget 容器；**保留** `update_preview(rule)` API |
| **新增** | `src/assets/styles/preview.qss` | 預覽區樣式 |
| **新增** | `tests/test_renderers.py` | paintEvent 不 crash |
| **新增** | `tests/test_syntax_preview.py` | 內容與 Exporter 一致 |

### 第五階段完成後的測試

| 類型 | 測試方式 | 通過標準 |
|------|----------|----------|
| 自動化 | `pytest tests/test_renderers.py` | 任意合法 rule 不拋例外 |
| 自動化 | `pytest tests/test_syntax_preview.py` | Syntax tab 文字 == `export_filter([rule])` |
| 手動 | 切換 Ground / Minimap / Syntax / Audio tab | 各 tab 正確顯示 |
| 手動 | 編輯 TextColor / PlayEffect | Ground tab 即時更新 |
| 手動 | 切換規則 | 所有 tab 同步更新 |

---

## 第六階段：v2.5.0 — Navigation Bar 整合與打磨

### 目標

移除 MenuBar / 舊 Toolbar / StatusBarPlaceholder，功能整合進 NavBar；加入 SVG icon、inline item preview、底部狀態列最終版。

### 要修改 / 新增的檔案

| 動作 | 檔案 | 說明 |
|------|------|------|
| **新增** | `src/ui/navigation_bar.py` | Logo、檔案操作、Undo/Redo、SearchBar、檔名、語法檢查指示 |
| **新增** | `src/assets/icons/*.svg` | open、save、undo、redo、search 等 ~15 個 |
| **新增** | `src/assets/styles/navbar.qss` | 導覽列樣式 |
| **新增** | `src/assets/styles/dialogs.qss` | QMenu、QDialog、QMessageBox |
| **新增** | `src/editor/widgets/item_label_preview.py` | 編輯器頂部 inline 物品標籤預覽 |
| **修改** | `src/ui/main_window.py` | 移除 MenuBar/Toolbar；接入 NavigationBar；StatusBar 最終版 |
| **修改** | `src/editor/rule_editor.py` | 頂部加入 ItemLabelPreview |
| **修改** | `POE2FilterStudio.spec` | 確認 `assets/icons/`、`assets/styles/` 打包 |
| **新增** | `tests/test_ui_smoke.py` | MainWindow 實例化 + 基本操作流程 |

### 第六階段完成後的測試

| 類型 | 測試方式 | 通過標準 |
|------|----------|----------|
| 自動化 | `pytest`（全 suite） | 全部通過，含 smoke test |
| 手動 | 所有 NavBar 按鈕 | 開啟、儲存、另存、Undo、Redo 正常 |
| 手動 | 快捷鍵 Ctrl+O / Ctrl+S / Ctrl+Z / Ctrl+Y | 仍有效（即使無 MenuBar） |
| 手動 | 與 `reference/v2_target_ui.png.png` 並排對照 | 佈局、色系、4 欄比例接近 |
| 打包 | `build.bat` → 執行 EXE | icon、QSS、中文顯示正常 |

---

## 各階段檔案修改總表

| 檔案 | P1 | P2 | P3 | P4 | P5 | P6 |
|------|:--:|:--:|:--:|:--:|:--:|:--:|
| `src/parser/*` | — | — | — | — | — | — |
| `src/core/document.py` 等核心 | — | — | — | — | — | — |
| `src/app/bootstrap.py` | ✓ | | | | | |
| `src/ui/main_window.py` | ✓ | ✓ | ✓ | | | ✓ |
| `src/editor/collapsible_section.py` | ✓ | | | | | |
| `src/assets/theme.py` | ✓ | | | | | |
| `src/assets/styles/*.qss` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `src/core/categorizer.py` | | ✓ | | | | |
| `src/ui/category_sidebar.py` | | ✓ | | | | |
| `src/ui/rule_card_browser.py` | | | ✓ | | | |
| `src/ui/rule_card_widget.py` | | | ✓ | | | |
| `src/editor/widgets/beam_color_picker.py` | | | | ✓ | | |
| `src/editor/widgets/minimap_icon_picker.py` | | | | ✓ | | |
| `src/editor/rule_editor.py` | | | | ✓ | | ✓ |
| `src/ui/preview_panel.py` | | | | | ✓ | |
| `src/ui/panels/*.py` | | | | | ✓ | |
| `src/ui/navigation_bar.py` | | | | | | ✓ |
| `src/assets/icons/*.svg` | | | | | | ✓ |
| `POE2FilterStudio.spec` | ○ | | | | | ✓ |

✓ = 必改　○ = 可選　— = 不碰

---

## 風險與緩解

| 風險 | 階段 | 緩解 |
|------|------|------|
| MainWindow signal 漏接 | P1、P3、P6 | 每階段跑完整手動迴歸 + smoke test |
| PlayEffect 格式不一致 | P4 | 明確格式測試 + parser round-trip |
| QListWidget 大量規則效能 | P3 | 卡片 widget 輕量化；必要時 lazy load |
| QPainter 與遊戲視覺不一致 | P5 | UI 標示「示意預覽」，不保證像素一致 |
| QSS 移除 hardcoded style 後破版 | P1 | 先完成 base.qss 再改 collapsible_section |

---

## 參考文件

- 架構設計：`docs/v2_architecture_design.md`
- Review 決策：`docs/v2_review_notes.md`
- UI 色票：`docs/UI_GUIDE.md`
- 現況截圖：`reference/v1_current_ui.png`
- 目標截圖：`reference/v2_target_ui.png.png`
