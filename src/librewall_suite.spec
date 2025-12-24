# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# --- 1. ANALYSIS FOR THE LAUNCHER (GUI) ---
a_gui = Analysis(
    ['Z:\\projects\\project-wall\\Launcher.py'],
    pathex=['Z:\\projects\\project-wall'],
    binaries=[],
    datas=[('Z:\\projects\\project-wall\\1.ico', '.')], # Launcher icon
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)

# --- 2. ANALYSIS FOR THE ENGINE ---
a_engine = Analysis(
    ['Z:\\projects\\project-wall\\main.py'],
    pathex=['Z:\\projects\\project-wall'],
    binaries=[],
    datas=[
        ('Z:\\projects\\project-wall\\3.ico', '.') # Engine icon
        # Removed 'icon.ico' and 'wallpapers' as requested
    ],
    hiddenimports=['port_map', 'video_widget', 'frontend.engine_assets'], 
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)

pyz_gui = PYZ(a_gui.pure)
pyz_engine = PYZ(a_engine.pure)

# --- 3. EXE DEFINITION FOR LAUNCHER ---
exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    [],
    exclude_binaries=True,
    name='librewall',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='Z:\\projects\\project-wall\\1.ico',
)

# --- 4. EXE DEFINITION FOR ENGINE ---
exe_engine = EXE(
    pyz_engine,
    a_engine.scripts,
    [],
    exclude_binaries=True,
    name='engine',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='Z:\\projects\\project-wall\\3.ico',
)

# --- 5. THE SHARED COLLECTION (One Folder) ---
coll = COLLECT(
    exe_gui,
    a_gui.binaries,
    a_gui.zipfiles,
    a_gui.datas,
    exe_engine,
    a_engine.binaries,
    a_engine.zipfiles,
    a_engine.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='librewall_suite' 
)