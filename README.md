# POE2 Filter Studio Professional

> **⚠ 開發狀態：0.9.0-beta — 功能完整但尚未通過完整生產環境測試。**

Path of Exile 2 `.filter` 視覺化編輯器，繁體中文介面。
支援規則瀏覽、即時預覽、Undo/Redo、自動驗證與 Quick Fix。

---

## 快速啟動

**需求：** Python 3.11+、PySide6

```bat
# 1. 安裝相依套件
pip install -r requirements.txt

# 2. 啟動程式
python src/main.py
```

---

## 功能總覽

### 檔案操作
- 開啟 / 儲存 / 另存新檔 `.filter`
- 最近開啟檔案（最多 10 筆，不存在時自動提示）
- 啟動時自動還原上次開啟的檔案（可關閉）
- 未儲存修改（dirty state）保護：關閉/新開時詢問儲存

### 規則瀏覽器
- 所有 Show / Hide 規則一覽，可拖曳排序
- Filter Section 群組折疊（`▼ / ▶`）
- 類型快速篩選（貨幣、裝備、寶石等 9 個類型）
- `Ctrl+F` 全文搜尋，`F3` / `Shift+F3` 導航，`Escape` 清除

### 規則編輯器
- 條件區：ItemLevel、AreaLevel、Class、BaseType 等
- 外觀區：SetTextColor、SetBorderColor、SetFontSize、SetMinimapIcon、SetBeam
- 音效區：PlayAlertSound、PlayAlertSoundPositional、CustomAlertSound
- 各區塊可獨立折疊

### 即時預覽
- 右側 Preview Panel 顯示規則外觀（顏色、邊框、字體、小地圖圖示、光柱）

### Undo / Redo
- `Ctrl+Z` 復原 / `Ctrl+Y` 取消復原
- 支援：新增、刪除、複製、移動、編輯、Quick Fix

### 自動驗證
- 儲存規則時即時掃描錯誤（ERROR）與警告（WARNING）
- ValidationPanel 顯示問題清單，點擊可定位到該規則
- Quick Fix：一鍵修復字型大小超出範圍、RGBA 顏色超出 0–255、PlayAlertSound 音量超出 0–300
- Quick Fix 可 Undo

### 儲存保護
- 儲存前若有 ERROR/WARNING，跳出確認視窗
- INFO 不阻止儲存

### 版本資訊
- Help → 關於 顯示 APP_NAME、APP_VERSION、作者、說明
- 視窗標題包含版本號

### Workspace 設定
- 自動記住視窗大小、Splitter 比例、編輯器折疊狀態
- 設定儲存於 `%APPDATA%\POE2FS\POE2FilterStudio.ini`

---

## 執行測試

```bash
# 從專案根目錄執行（需要 pytest、PySide6）
python -m pytest

# 僅執行特定模組
python -m pytest tests/test_validator.py
python -m pytest tests/test_quick_fix.py
python -m pytest tests/test_packaging_smoke.py
```

目前測試數：**1754 個**（全部通過）

---

## 技術架構

| 層 | 技術 |
|---|---|
| UI | PySide6 / Qt6 |
| 語言 | Python 3.11 |
| 設定儲存 | QSettings（INI 格式） |
| 測試框架 | pytest |
| 打包（草案） | PyInstaller（見 `packaging/`） |

### 目錄結構

```
src/
├── app/          # 啟動入口（bootstrap、settings service）
├── app_info.py   # 版本常數（APP_NAME、APP_VERSION）
├── core/         # 核心模組（parser、exporter、validator、commands）
├── presenters/   # 格式化輔助（標題列、狀態列）
├── services/     # Workspace 設定服務
├── ui/           # 所有 PySide6 Widget
│   ├── main_window.py
│   ├── validation_panel.py
│   ├── about_dialog.py
│   └── ...
└── assets/
    ├── styles/   # QSS 主題檔
    └── icons/    # SVG 圖示

tests/            # pytest 測試（1754 個）
packaging/        # PyInstaller spec 草案
```

---

## 不包含

- 市場價格 API
- 自動估價
- 雲端同步

---

## 版本紀錄

詳見 [CHANGELOG.md](CHANGELOG.md)。
