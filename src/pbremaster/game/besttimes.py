"""The best times ever on this computer (the Gallery's "Best Times" column).

The original kept these in DATA/BESTTIME.DAT next to the game (the CD's copy only
holds a few leftover test entries); the remaster never writes there, so they live
in <data dir>/besttimes.json as {puzzle folder: [seconds, player name]}.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..settings import data_dir


def _path(root: Path | None = None) -> Path:
    return (root or data_dir()) / "besttimes.json"


def load(root: Path | None = None) -> dict[str, tuple[float, str]]:
    try:
        raw = json.loads(_path(root).read_text(encoding="utf-8"))
        return {k: (float(v[0]), str(v[1])) for k, v in raw.items()}
    except (OSError, ValueError, TypeError, IndexError):
        return {}


def record(puzzle_path: str, seconds: float, player: str, root: Path | None = None) -> bool:
    """Store a time if it beats the best ever for that puzzle; True if it did."""
    best = load(root)
    old = best.get(puzzle_path)
    if old is not None and old[0] <= seconds:
        return False
    best[puzzle_path] = (round(seconds, 2), player)
    path = _path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({k: list(v) for k, v in best.items()}, indent=1), encoding="utf-8")
    return True
