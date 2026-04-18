# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata

block_cipher = None

a_gui = Analysis(
    ['Launcher.py'],
    pathex=['.'],
    binaries=[],
    datas=[('1.ico', '.')] + copy_metadata('certifi'),
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)

a_engine = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('3.ico', '.') 
    ] + copy_metadata('certifi'),
    hiddenimports=['port_map', 'video_widget', 'frontend.engine_assets'], 
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)

pyz_gui = PYZ(a_gui.pure)
pyz_engine = PYZ(a_engine.pure)

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
    icon='1.ico',
)

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
    icon='3.ico',
)

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