"""Locate the original Pandora's Box files. They are read in place and never modified.

The player supplies their own copy: the CD (or a copy of its DATA folder), or a folder
the original installer filled. The setup screen (ui/setup.py) offers what `detect()`
finds, checks a folder with `check()`, can copy the data to this computer with
`copy_data()`, and saves the choice in Settings.game_dir, which `find()` reads.
"""
from __future__ import annotations

import os
import shutil
import string
import sys
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED = ("PANDORA.ROF", "SCREENS.ROF", "LANGENU.DLL")
# Without these the game can't start (strings, screens, puzzles).
NEEDED = REQUIRED + ("STATENU.DLL", "NAMEENU.DLL", "PUZENU.DLL")
# Without these it runs with something missing (music, voices, videos, help, font).
WANTED = {"MUSIC": "music", "VO": "voices", "OPEN.AVI": "videos", "HELP": "quick help",
          "BKANT.TTF": "the game's font"}
INSTALL_DIRS = ("Microsoft Games/Pandora's Box", "Microsoft Games/Pandoras Box", "Pandora's Box",
                "Pandoras Box")


def _data_subdir(root: Path) -> Path | None:
    for cand in (root, root / "DATA", root / "data"):
        if all(_ci(cand, f) for f in REQUIRED):
            return cand
    return None


def _ci(folder: Path, name: str) -> Path | None:
    """Case-insensitive lookup (the CD uses upper case, installs may not)."""
    p = folder / name
    if p.exists():
        return p
    if folder.is_dir():
        low = name.lower()
        for child in folder.iterdir():
            if child.name.lower() == low:
                return child
    return None


class GameDir:
    def __init__(self, root: str | Path):
        data = _data_subdir(Path(root).expanduser())
        if data is None:
            raise FileNotFoundError(
                f"{root}: no Pandora's Box data found (need {', '.join(REQUIRED)})")
        self.data = data

    def file(self, *parts: str) -> Path:
        p = self.data
        for part in parts:
            nxt = _ci(p, part)
            if nxt is None:
                raise FileNotFoundError(p / part)
            p = nxt
        return p


@dataclass
class Check:
    """What a folder holds: `data` is its game data folder, None if unusable."""
    folder: Path
    data: Path | None = None
    missing: list[str] = field(default_factory=list)        # needed files not there
    lacking: list[str] = field(default_factory=list)        # optional parts not there
    removable: bool = False

    @property
    def ok(self):
        return self.data is not None

    def size(self) -> int:
        return sum(f.stat().st_size for f in self.data.rglob("*") if f.is_file()) if self.data else 0


def check(folder: str | Path) -> Check:
    folder = Path(folder).expanduser()
    result = Check(folder, removable=is_removable(folder))
    best, best_missing = None, None
    for cand in (folder, folder / "DATA", folder / "data"):
        if not cand.is_dir():
            continue
        missing = [f for f in NEEDED if not _ci(cand, f)]
        if best_missing is None or len(missing) < len(best_missing):
            best, best_missing = cand, missing
    if best is None:
        result.missing = list(NEEDED)
        return result
    result.missing = best_missing
    if not best_missing:
        result.data = best
        result.lacking = [what for name, what in WANTED.items() if not _ci(best, name)]
    return result


def is_removable(path: Path) -> bool:
    """On a CD/DVD (or other removable drive), so worth copying to this computer."""
    path = Path(path).expanduser().resolve() if Path(path).expanduser().exists() else Path(path)
    if sys.platform == "win32":
        try:
            import ctypes
            root = path.anchor or str(path)[:3]
            return ctypes.windll.kernel32.GetDriveTypeW(root) in (2, 5)   # REMOVABLE, CDROM
        except (AttributeError, OSError):
            return False
    parts = path.parts
    return len(parts) > 1 and parts[1] in ("media", "mnt", "cdrom") or parts[:3] == ("/", "run", "media")


def search_roots() -> list[Path]:
    """Places the original may be: CD/DVD drives, mounted media, install folders, Wine."""
    roots: list[Path] = []
    if sys.platform == "win32":
        roots += [Path(f"{d}:\\") for d in string.ascii_uppercase[2:] if Path(f"{d}:\\").exists()]
        for env in ("ProgramFiles(x86)", "ProgramFiles"):
            base = os.environ.get(env)
            if base:
                roots += [Path(base) / d for d in INSTALL_DIRS]
    else:
        user = os.environ.get("USER", "")
        for base in (Path("/media") / user, Path("/run/media") / user, Path("/media"), Path("/mnt")):
            if base.is_dir():
                try:
                    roots += [p for p in base.iterdir() if p.is_dir()]
                except OSError:
                    pass
        roots.append(Path("/cdrom"))
        for prefix in (Path.home() / ".wine", *(Path.home() / ".local/share/wineprefixes").glob("*")):
            for pf in ("Program Files", "Program Files (x86)"):
                roots += [prefix / "drive_c" / pf / d for d in INSTALL_DIRS]
    return roots


def detect() -> list[Check]:
    """Usable copies found in the usual places, the copied one first."""
    found, seen = [], set()
    for root in [copied_dir(), *search_roots()]:
        try:
            if not root.is_dir():
                continue
            c = check(root)
        except OSError:
            continue
        if c.ok and c.data.resolve() not in seen:
            seen.add(c.data.resolve())
            found.append(c)
    return found


def copied_dir() -> Path:
    """Where 'Copy to this computer' puts the data (the remaster's own data folder)."""
    from ..settings import data_dir
    return data_dir() / "game"


def copy_data(src: Path, dest: Path | None = None, progress=None, cancelled=lambda: False) -> Path:
    """Copy a checked data folder to `dest`/DATA (all of it: about 520 MB from the CD).
    Copies into a temporary folder and renames at the end, so a half copy is never used.
    progress(done_bytes, total_bytes) is called as it goes. Returns the new folder."""
    dest = Path(dest or copied_dir())
    files = [f for f in Path(src).rglob("*") if f.is_file()]
    total = sum(f.stat().st_size for f in files)
    dest.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(dest).free < total + (50 << 20):
        raise OSError(f"Not enough free space: the copy needs {total >> 20} MB.")
    tmp = dest / "DATA.partial"
    shutil.rmtree(tmp, ignore_errors=True)
    done = 0
    for f in files:
        if cancelled():
            shutil.rmtree(tmp, ignore_errors=True)
            raise InterruptedError("Copy cancelled.")
        target = tmp / f.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "rb") as fi, open(target, "wb") as fo:
            while chunk := fi.read(1 << 20):
                fo.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
        os.chmod(target, 0o644)               # CD files are read-only
    final = dest / "DATA"
    shutil.rmtree(final, ignore_errors=True)
    tmp.rename(final)
    return final


def find(explicit: str | None = None, saved: str | None = None) -> GameDir:
    """--data, then PANDORA_DIR, then the saved choice, then the developer's copy."""
    candidates = [explicit, os.environ.get("PANDORA_DIR"), saved]
    if not getattr(sys, "frozen", False):          # running from source: the developer's copy
        candidates += [Path(__file__).resolve().parents[3].parent / "Pandoras_Box_Original",
                       Path.home() / "Projects" / "Pandoras_Box_Original"]
    for c in candidates:
        if c:
            try:
                return GameDir(c)
            except FileNotFoundError:
                pass
    raise FileNotFoundError("Pandora's Box files not found: pass --data DIR or set PANDORA_DIR")
