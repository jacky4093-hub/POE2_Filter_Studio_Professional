# POE2 Filter Studio Professional

Path of Exile 2 `.filter` 視覺化編輯器，繁體中文介面。

開啟、編輯、儲存 Filter 規則，支援 Show/Hide 切換、條件/外觀/音效設定、Section 群組折疊、即時預覽、全文搜尋與 Undo/Redo。

---

## 快速啟動

**需求：** Python 3.11+

```bat
# 1. 安裝相依套件
pip install -r requirements.txt

# 2. 雙擊啟動（Windows）
run.bat

# 或手動執行
python src/main.py
```

---

## 目前功能（v1.0.0）

### 檔案操作
- 開啟 / 儲存 / 另存新檔 `.filter`
- 最近開啟檔案（File > 最近開啟，最多 10 筆）
- 不存在的最近檔案開啟時提示警告，不造成程式崩潰

### 規則列表
- 顯示所有 Show / Hide 規則，可拖曳排序
- Filter Section 群組折疊（`▼ / ▶`），自動辨識 `#=== / # Name / #===` 格式
- 折疊狀態依檔案儲存，下次開啟自動還原

### 規則編輯器
- 條件區（Conditions）：ItemLevel、AreaLevel、Class、BaseType 等可動態新增/移除
- 外觀區（Appearance）：SetTextColor、SetBorderColor、SetFontSize、SetMinimapIcon、SetBeam 等
- 音效區（Audio）：PlayAlertSound、PlayAlertSoundPositional、CustomAlertSound 等
- 每個區塊可獨立折疊

### 即時預覽
- 右側 Preview Panel 即時顯示規則的視覺效果（顏色、邊框、字體、小地圖圖示、光柱）

### 搜尋
- `Ctrl+F` 開啟搜尋列，全文搜尋所有規則欄位
- `F3` / `Shift+F3` 下一個 / 上一個
- `Escape` 清除搜尋
- 搜尋結果以琥珀色高亮，自動展開所在 Section

### Undo / Redo
- `Ctrl+Z` 復原 / `Ctrl+Y` 取消復原
- 支援：新增、刪除、複製、移動、編輯規則

### Workspace 設定
- 自動記住：視窗大小與位置、Splitter 比例、編輯器展開/折疊狀態
- 設定以 INI 格式儲存於 `%APPDATA%\POE2FS\POE2FilterStudio.ini`

---

## 版本進度

| 版本 | 功能 |
|---|---|
| v1.0.0 | Filter Section 群組折疊 |
| v0.9.0 | Workspace Settings / 最近開啟 / Escape 清除搜尋 |
| v0.8.0 | 全文搜尋與導航 |
| v0.7.0 | Live Preview 引擎 |
| v0.6.0 | 拖曳排序 |
| v0.5.0 | Undo / Redo 命令框架 |
| v0.4.0 | Schema 驅動屬性系統 |
| v0.3.0 | 規則編輯器 |
| v0.2.0 | FilterDocument 層 |
| v0.1.0 | MVP（Parser / Exporter / 基本 UI） |

詳細版本紀錄見 [docs/CHANGELOG.md](docs/CHANGELOG.md)。

---

## 技術架構

| 層 | 技術 |
|---|---|
| UI | PySide6 / Qt6 |
| 語言 | Python 3.11 |
| 設定儲存 | QSettings（INI 格式） |
| 測試 | pytest（81 tests） |
| 打包 | PyInstaller（`scripts/build_exe.bat`） |

---

## 不包含

- 市場價格 API
- 自動估價
- 雲端同步
- 跨 Section 拖曳（規劃於 v1.1.0）
