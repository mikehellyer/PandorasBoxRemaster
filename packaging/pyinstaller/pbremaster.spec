# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Windows and Linux (onedir).

Built with: pyinstaller --noconfirm packaging/pyinstaller/pbremaster.spec (from the repo root).
Nothing from the original game goes in: players point the app at their own copy.
"""
import re
import sys
from pathlib import Path

if sys.version_info < (3, 12):
    raise SystemExit(f"Build with Python 3.12+ (this is {sys.version.split()[0]}); CI uses 3.13.")

root = Path(SPECPATH).resolve().parent.parent
src = root / "src"
icons = root / "packaging" / "icons"
version = re.search(r'__version__ = "([^"]+)"', (src / "pbremaster" / "__init__.py").read_text()).group(1)

a = Analysis(
    [str(root / "packaging" / "pyinstaller" / "launch.py")],
    pathex=[str(src)],
    datas=[(str(src / "pbremaster" / "resources" / "icon.png"), "pbremaster/resources")],
    hiddenimports=["pygame._sdl2.video"],
    excludes=["PIL", "capstone", "pytest", "pbremaster.tools"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PandorasBoxRemaster",
    console=False,
    upx=False,
    icon=str(icons / "icon.ico") if sys.platform == "win32" else None,
)
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name="PandorasBoxRemaster")
