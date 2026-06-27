# CHANGELOG

所有版本紀錄依 [Semantic Versioning](https://semver.org/) 標記，新版本在前。

---

## [1.0.0] - 2026-06-27  Filter Sections / Group Collapse

### 新增
- `src/core/sections.py`：純函數模組，定義 `FilterSection`、`SectionMap`、`build_section_map()`、`detect_section_header()`
- Filter Section 自動辨識：解析規則 `pre_lines` 中的 `#=== / # Name / #===` 格式，識別為 Section 標頭（嚴格比對最後三個非空行）
- 規則列表改用 `QTreeWidget`，Section 下的規則以子節點呈現，支援 `▼/▶` 折疊
- Section 折疊狀態以 `first_rule_index` 為 key 儲存至 `WorkspaceSettings`，避免重名 Section 衝突
- 搜尋命中時自動展開所在 Section
- 跨 Section 拖曳自動拒絕，保護 Section 邊界
- 新增 `tests/test_sections.py`（16 個純邏輯測試）
- 新增 `tests/test_rule_list_tree.py`（8 個 headless Qt 測試）

### 不變
- Parser / Exporter 完全未修改，`pre_lines` 原樣保留，round-trip 無損

---

## [0.9.0] - 2026-06-27  Workspace Settings

### 新增
- `src/services/settings_service.py`：`WorkspaceSettings` 類，INI 格式儲存於 `%APPDATA%\POE2FS\POE2FilterStudio.ini`
- 自動儲存 / 還原：視窗大小、三欄 Splitter 比例、編輯器 CollapsibleSection 展開狀態
- 最近開啟檔案（Recent Files）：最多 10 筆、MRU 順序、自動去重、`File > 最近開啟` 子選單
- 開啟已刪除的最近檔案時顯示警告對話框，不造成崩潰
- `SearchBar` 新增 `Escape` 鍵清除搜尋，走 `search_changed("")` 流程確保高亮同步清除
- 新增 `tests/test_settings.py`（31 個測試，含 pure helpers、roundtrip、headless Qt）

### 修改
- `MainWindow.__init__` 接受 `WorkspaceSettings` 注入（可測試）
- `closeEvent` 於關閉時儲存 workspace 狀態

---

## [0.8.0] - 2026-06-27  Search & Navigation

### 新增
- `src/core/search.py`：純函數 `search_rules(rules, query)`，搜尋所有欄位（action、conditions、actions、inline_comment、pre_lines、unknown_lines）
- `src/widgets/search_bar.py`：搜尋列 Widget，含文字輸入、命中計數（`n / total`）、上一個 / 下一個按鈕
- 快捷鍵：`Ctrl+F` 聚焦搜尋列、`F3` 下一個、`Shift+F3` 上一個
- 命中規則以琥珀色高亮（當前 `#5a4200`，其他 `#2d2000`）
- 新增 `tests/test_search.py`（23 個測試）

---

## [0.7.0] - 2026-06-26  Live Preview Engine

### 新增
- `src/ui/preview_panel.py`：右側 Preview Panel，即時顯示規則外觀效果
- `src/preview/preview_engine.py`：純函數 Preview 渲染引擎，解析 Appearance 動作並繪製預覽
- 預覽項目：文字顏色、邊框顏色、背景色、字體大小、小地圖圖示（形狀＋顏色）、光柱（顏色＋類型）
- 規則選中或編輯時 Preview 即時更新

---

## [0.6.0] - 2026-06-26  Drag & Drop Rule Ordering

### 新增
- 規則列表支援滑鼠拖曳排序
- 拖曳結果透過 `MoveRuleCommand` 整合進 Undo/Redo 框架
- 拖曳只允許同層（後來 v1.0.0 限定為同 Section）

---

## [0.5.0] - 2026-06-26  Command Framework / Undo Redo

### 新增
- `src/core/commands.py`：Command 模式框架，`AbstractCommand` 基類
- 實作命令：`AddRuleCommand`、`DeleteRuleCommand`、`DuplicateRuleCommand`、`UpdateRuleCommand`、`MoveRuleCommand`
- `FilterDocument` 加入命令堆疊（undo stack / redo stack）
- `Ctrl+Z` 復原 / `Ctrl+Y` 取消復原，工具列與選單同步 enable/disable
- `MoveRuleCommand` 含 `is_noop` 防護（邊界值、同位移動自動跳過）

---

## [0.4.0] - 2026-06-26  Professional Property System

### 新增
- `src/core/filter_schema.py`：完整 PoE2 Filter 欄位 Schema（條件、外觀、音效）
- `src/editor/property_widgets.py`：Schema 驅動的屬性 Widget 系統（顏色選擇器、數字輸入、下拉選單等）
- `src/editor/collapsible_section.py`：可折疊面板 Widget（`CollapsibleSection`）
- 編輯器欄位依 Schema 自動生成，未知欄位以 `UnknownPropertyWidget` 保留原文（round-trip 安全）

---

## [0.3.0] - 2026-06-26  Professional Rule Editor

### 新增
- `src/editor/rule_editor.py`：完整規則編輯器，分 General / Conditions / Appearance / Audio 四區
- 條件 / 外觀 / 音效動態新增、移除列
- 編輯器修改即時觸發 `rule_changed` 訊號，主視窗同步更新 Document

---

## [0.2.1] - 2026-06-26  Development Specification

### 新增
- `docs/` 目錄：PROJECT_RULES、DEVELOPMENT_SPEC、API、PARSER_SPEC、FILTER_SPEC、UI_GUIDE 等規格文件
- `CLAUDE.md`：專案核心規則（語言、修改限制、確認流程）

---

## [0.2.0] - 2026-06-26  FilterDocument Layer

### 新增
- `src/core/document.py`：`FilterDocument` 類，封裝規則清單、dirty 狀態、file_path
- `__TAIL__` sentinel 規則，確保 Exporter 保留尾部空行
- 改善規則列表標籤顯示（顯示第一個條件值作為摘要）

### 修改
- MainWindow 改透過 `FilterDocument` 操作規則，不直接操作 list

---

## [0.1.0] - 2026-06-26  MVP

### 新增
- `src/parser/filter_parser.py`：PoE2 Filter 解析器，輸出 `list[FilterRule]`
- `src/parser/filter_exporter.py`：Exporter，`list[FilterRule]` → 原格式文字，round-trip 無損
- `src/core/models.py`：`FilterRule` dataclass
- `src/ui/main_window.py`：主視窗，開啟 / 儲存 / 規則列表 / 基本編輯器
- 基本 Show / Hide 切換與規則選擇
- `pyproject.toml`：pytest 設定（`pythonpath = ["src"]`）
