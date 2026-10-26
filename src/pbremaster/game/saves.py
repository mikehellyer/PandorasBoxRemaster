"""Named saved games (the original's Save and Load dialogs, screens 102 and 101).

Progress is also kept automatically per player (progress.Player); a saved game is a
named snapshot of that progress the player can go back to. Stored as JSON in
<data dir>/saves/<player>/<name>.json, never next to the original files.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import asdict
from pathlib import Path

from ..settings import data_dir
from .progress import Player


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9 _-]+", "_", name).strip(" _") or "save"


def folder(player_name: str, root: Path | None = None) -> Path:
    return (root or data_dir() / "saves") / _safe(player_name)


def list_saves(player_name: str, root: Path | None = None) -> list[tuple[str, Path]]:
    """(name, file) of the player's saved games, newest first."""
    out = []
    for f in folder(player_name, root).glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            out.append((data.get("saved", 0), data.get("name", f.stem), f))
        except (OSError, ValueError):
            continue
    return [(name, f) for _, name, f in sorted(out, key=lambda t: t[0], reverse=True)]


def save_game(player: Player, name: str, root: Path | None = None) -> Path:
    path = folder(player.name, root) / f"{_safe(name)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"name": name.strip(), "saved": time.time(), "player": asdict(player)}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    tmp.replace(path)
    return path


def exists(player_name: str, name: str, root: Path | None = None) -> bool:
    return (folder(player_name, root) / f"{_safe(name)}.json").exists()


def load_game(path: Path, player_name: str) -> Player:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))["player"]
    raw["name"] = player_name
    return Player(**{k: v for k, v in raw.items() if k in Player.__dataclass_fields__})


def delete_save(path: Path):
    Path(path).unlink(missing_ok=True)
