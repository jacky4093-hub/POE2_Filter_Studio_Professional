@echo off
cd /d "%~dp0"
setlocal

set VERSION=1.1.0
set ZIPNAME=POE2FilterStudio_v%VERSION%_win64.zip

echo ============================================================
echo  POE2 Filter Studio ^| Release Packaging
echo ============================================================
echo  Version : %VERSION%
echo  Output  : release\%ZIPNAME%
echo ============================================================
echo.

if not exist "dist\POE2FilterStudio\POE2FilterStudio.exe" (
    echo [ERROR] dist\POE2FilterStudio\POE2FilterStudio.exe not found.
    echo Please run build.bat first.
    pause
    exit /b 1
)

if not exist "release" mkdir "release"

if exist "release\%ZIPNAME%" (
    echo Removing old %ZIPNAME%...
    del /f /q "release\%ZIPNAME%"
)

echo Packaging...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Compress-Archive -Path 'dist\POE2FilterStudio' -DestinationPath 'release\%ZIPNAME%' -Force"

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to create zip.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Done! release\%ZIPNAME%
echo ============================================================
pause
