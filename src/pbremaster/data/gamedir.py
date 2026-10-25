"""Locate the original Pandora's Box files. They are read in place and never modified."""
from __future__ import annotations

import os
from pathlib import Path

REQUIRED = ("PANDORA.ROF", "SCREENS.ROF", "LANGENU.DLL")


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


def find(explicit: str | None = None) -> GameDir:
    candidates = [explicit, os.environ.get("PANDORA_DIR"),
                  Path(__file__).resolve().parents[3].parent / "Pandoras_Box_Original",
                  Path.home() / "Projects" / "Pandoras_Box_Original"]
    for c in candidates:
        if c:
            try:
                return GameDir(c)
            except FileNotFoundError:
                pass
    raise FileNotFoundError("Pandora's Box files not found: pass --data DIR or set PANDORA_DIR")
