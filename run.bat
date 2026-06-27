@echo off
cd /d "%~dp0"
python src\main.py
if errorlevel 1 (
    echo.
    echo [錯誤] 啟動失敗，請確認已安裝 Python 3.11 與 PySide6
    echo 安裝指令：pip install -r requirements.txt
    pause
)
