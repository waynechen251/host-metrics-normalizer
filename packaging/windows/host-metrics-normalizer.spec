# -*- mode: python ; coding: utf-8 -*-
import os

REPO_ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")

a = Analysis(
    [os.path.join(SPECPATH, "entry.py")],
    pathex=[SRC_DIR],
    binaries=[],
    datas=[],
    hiddenimports=["pynvml"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="host-metrics-normalizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
