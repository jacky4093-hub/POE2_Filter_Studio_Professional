@echo off
cd /d "%~dp0"
echo ============================================================
echo  POE2 Filter Studio ^| Build
echo ============================================================
echo.

where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pyinstaller not found.
    echo Please install: pip install pyinstaller
    pause
    exit /b 1
)

echo Running PyInstaller...
echo.
pyinstaller --noconfirm POE2FilterStudio.spec

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. Check errors above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Build complete!
echo  Output: dist\POE2FilterStudio\POE2FilterStudio.exe
echo ============================================================
pause
