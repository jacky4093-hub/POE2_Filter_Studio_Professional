# -*- mode: python ; coding: utf-8 -*-
# POE2FilterStudio.spec — PyInstaller build definition
#
# All paths are relative to the project root (where this file lives).
# Run from project root:  pyinstaller --noconfirm POE2FilterStudio.spec
#
# Output:  dist/POE2FilterStudio/POE2FilterStudio.exe  (--onedir mode)

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('data',        'data'),    # items_zhTW.json, aliases.json
        ('assets',      'assets'),  # root-level assets (future use)
        ('src/assets',  'assets'),  # v2 theme QSS + icons
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Unused Qt modules — reduces output size
        'PySide6.Qt3DCore',
        'PySide6.Qt3DRender',
        'PySide6.QtBluetooth',
        'PySide6.QtCharts',
        'PySide6.QtDataVisualization',
        'PySide6.QtLocation',
        'PySide6.QtMultimedia',
        'PySide6.QtNfc',
        'PySide6.QtPdf',
        'PySide6.QtQuick',
        'PySide6.QtSensors',
        'PySide6.QtSql',
        'PySide6.QtTest',
        'PySide6.QtWebEngine',
        'PySide6.QtWebSockets',
        'PySide6.QtXml',
        # Unused stdlib modules
        'tkinter',
        'unittest',
        'email',
        'http',
        'xmlrpc',
        'ftplib',
        'imaplib',
        'poplib',
        'smtplib',
        'telnetlib',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='POE2FilterStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # --noupx: avoid AV false positives
    console=False,       # --windowed: no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon omitted — no app.ico yet (v1.2.0+)
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='POE2FilterStudio',
)
