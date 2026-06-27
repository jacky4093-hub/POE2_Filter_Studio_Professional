# CHANGELOG

## [0.9.0-beta] — 2026-06-28

> 第一個 Beta 版本，功能完整但尚未正式打包發布。

### P17 Release Preparation（發布準備）

**P17.4 Beta Release Checklist**
- 新增 README.md（完整功能說明、架構、啟動方式）
- 新增 CHANGELOG.md
- 新增 RELEASE_CHECKLIST.md（手動測試清單）

**P17.3 Packaging Readiness**
- 新增 `packaging/poe2_filter_studio.spec`（PyInstaller 草案）
- 新增 `packaging/README.md`（打包說明）
- 更新 `src/app/bootstrap.py` 使用 `APP_NAME`、`APP_VERSION`
- 新增 packaging smoke tests（40 個）

**P17.2 Release About / Version System**
- 新增 `src/app_info.py`（`APP_NAME`、`APP_VERSION = "0.9.0-beta"`、`APP_AUTHOR`、`APP_DESCRIPTION`）
- 新增 `src/ui/about_dialog.py`（Help → 關於）
- 視窗標題加入版本號（`POE2 Filter Studio 0.9.0-beta`）
- 新增 33 個測試

**P17.1 Dirty State Protection**
- `FilterDocument` 追蹤 `dirty` 狀態，操作後自動標記
- 關閉 / 開新檔 / 載入時若有未儲存修改，顯示 Save / Discard / Cancel 對話框
- `closeEvent` 整合 dirty state 保護
- 新增 35 個測試

### P16 Validation System（自動驗證）

**P16.4 Validation Quick Fix Foundation**
- 新增 `src/core/quick_fix.py`（`QuickFix` dataclass、`get_quick_fixes()`、`apply_quick_fix()`）
- 修復項目：SetFontSize（範圍 1–45）、RGBA（範圍 0–255）、PlayAlertSound 音量（範圍 0–300）
- ValidationPanel 顯示 Fix 按鈕，點擊後透過 `UpdateRuleCommand` 修復（可 Undo）
- 新增 71 個測試

**P16.3 Save Warning Dialog**
- 新增 `src/ui/save_warning_dialog.py`
- 儲存前若有 ERROR/WARNING 跳出確認視窗（Cancel / 仍然儲存）
- INFO 不阻止儲存
- 單一攔截點 `_write_to()` 同時覆蓋 Save 與 Save As
- 新增 39 個測試

**P16.2 Validation Panel**
- 新增 `src/ui/validation_panel.py`（ValidationPanel Widget）
- MainWindow 底部顯示問題計數（ERROR / WARNING / INFO）
- 點擊問題可定位到對應規則
- 新增 44 個測試

**P16.1 Validator Core**
- 新增 `src/core/validator.py`（`ValidationSeverity`、`ValidationIssue`、`validate_rule()`、`validate_document()`）
- 驗證項目：空規則、SetFontSize 範圍、RGBA 範圍、PlayAlertSound 範圍、SetMinimapIcon 參數
- disabled 規則自動降一級嚴重度（ERROR→WARNING、WARNING→INFO）
- 新增 132 個測試

### P15 UI Modernization（介面現代化）

- RuleDetailEditor：`_effect_parse` 重構、Beam Effect 顏色/Temp 解析
- Preview Panel 改版：光柱（Beam）、顏色即時更新
- Minimap 預覽整合

### P14 Undo / Redo

- 命令框架：`AddRuleCommand`、`DeleteRuleCommand`、`UpdateRuleCommand`、`MoveRuleCommand`、`DuplicateRuleCommand`
- `FilterDocument.execute()` / `undo()` / `redo()`
- `Ctrl+Z` / `Ctrl+Y` 快捷鍵
- UndoManager 整合，undo/redo 按鈕狀態自動同步

### 先前版本（P1–P13）

| 版本 | 功能摘要 |
|---|---|
| P13 | Filter Section 折疊 |
| P12 | Preview Panel Live Engine |
| P11 | 類型快速篩選（Quick Filter） |
| P10 | 全文搜尋與導航（`Ctrl+F`） |
| P9  | 拖曳排序（Drag & Drop） |
| P8  | 啟動還原 / Welcome 畫面 |
| P7  | 最近開啟檔案 |
| P6  | Workspace 設定（視窗大小、Splitter） |
| P5  | Schema 驅動屬性系統 |
| P4  | RuleDetailEditor 基礎版 |
| P3  | FilterDocument 層 / Commands 框架 |
| P2  | MVP（Parser / Exporter / 基本 UI） |
| P1  | 專案初始化 |
