# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for CursorDAW Bridge
# Build with: pyinstaller bridge.spec

import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Collect all watchdog submodules (needed for file watching)
hiddenimports = collect_submodules('watchdog')

a = Analysis(
    ['cloud_bridge.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports + [
        'requests',
        'urllib3',
        'numpy',
        'watchdog.observers',
        'watchdog.events',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude stuff we don't need to keep size down
        'tkinter',
        'matplotlib',
        'PIL',
        'scipy',
        'pandas',
        'IPython',
        'notebook',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CursorDAW_Bridge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress if UPX is available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Show console window with logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: icon='bridge_icon.ico'
)

