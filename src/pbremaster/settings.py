"""Remaster settings and player profiles, stored in the user's data folder.

Never written next to the original game files.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


def data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "pbremaster"


@dataclass
class Settings:
    # The original's Options dialog (screen 103): Sound, Music, Timer toggles.
    sound: bool = True
    music: bool = True
    timer: bool = True
    players: list[str] = field(default_factory=list)   # most recent first
    fullscreen: bool = False

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        path = path or data_dir() / "settings.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        known = {k: v for k, v in raw.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def save(self, path: Path | None = None):
        path = path or data_dir() / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=1), encoding="utf-8")

    def use_player(self, name: str):
        """Make `name` the current player (adds it if new)."""
        self.players = [name] + [p for p in self.players if p != name]
