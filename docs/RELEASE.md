# Release Guide

## 快速打包流程

```bat
# Step 1：建置 EXE（--onedir 模式，無 UPX）
build.bat

# Step 2：打包成 zip 供發布
release.bat
```

輸出：`release\POE2FilterStudio_v{VERSION}_win64.zip`

---

## 建置設定（POE2FilterStudio.spec）

| 項目 | 設定值 |
|---|---|
| 模式 | `--onedir`（資料夾，啟動快） |
| Console | 關閉（`windowed=True`） |
| UPX | 關閉（`upx=False`，降低 AV 誤報） |
| Icon | 暫無（v1.2.0+ 補加） |
| Version Resource | `version_info.txt` |
| 排除模組 | Qt3D / QtBluetooth / QtWebEngine 等未使用模組 |

---

## 版本號管理

需同步更新以下三處：

1. `version_info.txt` — `filevers` / `prodvers` / `FileVersion` / `ProductVersion`
2. `release.bat` — `set VERSION=x.x.x`
3. `docs/CHANGELOG.md` — 新增版本條目

---

## 輸出結構

```
dist\POE2FilterStudio\
  POE2FilterStudio.exe
  Qt6Core.dll / Qt6Gui.dll / Qt6Widgets.dll / ...
  data\
    items_zhTW.json
    aliases.json
  assets\
    icons\ / images\ / sounds\
  _internal\          ← PyInstaller 6.x 內部模組
```

zip 內結構：`POE2FilterStudio\POE2FilterStudio.exe`（同上）

---

## Windows Defender / SmartScreen 說明

- 首次執行可能出現 SmartScreen 警告（"無法辨識的應用程式"）
- 點選「更多資訊 > 仍要執行」即可
- 使用 `--onedir` + `upx=False` 已降低觸發機率
- 根本解決方案：購買程式碼簽章憑證（非此版範圍）

---

## Workspace Settings 在打包版本的行為

設定路徑不受 PyInstaller 影響，仍儲存於：

```
%APPDATA%\POE2FS\POE2FilterStudio.ini
```

---

## CI 自動化（未來）

`.github/workflows/ci.yml` 目前只跑 pytest。
若需要 CI 自動打包，可在 workflow 新增：

```yaml
- run: pip install pyinstaller
- run: pyinstaller --noconfirm POE2FilterStudio.spec
- uses: actions/upload-artifact@v4
  with:
    name: POE2FilterStudio-win64
    path: dist/POE2FilterStudio/
```
