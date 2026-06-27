# POE2 Filter Studio — 打包說明

> **⚠ 草案階段：本目錄的打包設定尚未通過完整生產環境測試，請謹慎使用。**

## 目前狀態

| 項目 | 狀態 |
|------|------|
| PyInstaller spec 草案 | ✅ 已建立 |
| 版本常數集中管理 | ✅ `src/app_info.py` |
| Assets 路徑（dev） | ✅ 正常 |
| Assets 路徑（frozen） | 草案（待測試） |
| Windows EXE 打包 | 草案（待驗證） |

---

## 版本更新

版本號集中管理於 `src/app_info.py`：

```python
APP_VERSION = "0.9.0-beta"   # ← 修改這裡
```

打包前確認此值已更新，EXE 的應用程式名稱會自動使用 `APP_NAME`。

---

## 打包步驟（草案）

### 1. 安裝依賴

```bash
pip install pyinstaller PySide6
```

### 2. 從專案根目錄執行打包

```bash
pyinstaller packaging/poe2_filter_studio.spec
```

### 3. 輸出位置

打包完成後，EXE 位於：

```
dist/POE2FilterStudio.exe
```

---

## 注意事項

- **Python 版本**：需要 Python 3.11 以上
- **PySide6**：`QtSvg`、`QtXml`、`QtPrintSupport` 已列為 `hiddenimports`
- **Assets**：`src/assets/styles/` 與 `src/assets/icons/` 會被自動包進 EXE
- **圖示**：spec 中的 `icon=` 行目前已被註解，日後加入 `app_icon.ico` 後啟用
- **console=False**：打包後不會顯示命令提示字元視窗

---

## 開發啟動方式（不受影響）

開發時仍使用原本方式啟動，本目錄不影響開發流程：

```bash
cd src
python main.py
```

或直接從 IDE 執行 `src/main.py`。
