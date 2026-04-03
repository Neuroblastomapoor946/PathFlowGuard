# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path


CONDA_BIN = Path(os.environ.get("CONDA_PREFIX", sys.base_prefix)) / "Library" / "bin"
EXTRA_DLLS = [
    "ffi.dll",
    "libbz2.dll",
    "libcrypto-3-x64.dll",
    "libexpat.dll",
    "liblzma.dll",
    "libssl-3-x64.dll",
    "sqlite3.dll",
]
EXTRA_BINARIES = [
    (str(CONDA_BIN / dll_name), ".")
    for dll_name in EXTRA_DLLS
    if (CONDA_BIN / dll_name).exists()
]

try:
    import openslide_bin  # type: ignore
except Exception:
    OPENSLIDE_BIN_DIR = None
else:
    OPENSLIDE_BIN_DIR = Path(openslide_bin.__file__).resolve().parent

if OPENSLIDE_BIN_DIR is not None:
    EXTRA_BINARIES.extend((str(path), ".") for path in OPENSLIDE_BIN_DIR.glob("*.dll"))

a = Analysis(
    ['pathflow_guard_launcher.py'],
    pathex=['src'],
    binaries=EXTRA_BINARIES,
    datas=[('samples', 'samples')],
    hiddenimports=['PIL._imaging', 'openslide', 'openslide.lowlevel', 'openslide_bin'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PathFlowGuard',
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
