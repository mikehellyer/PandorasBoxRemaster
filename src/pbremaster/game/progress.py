"""A player's campaign progress and the rules that change it.

Rules (LANGENU / STATENU texts, city marker files):
  * every 10 puzzles solved earn a Free Puzzle token (STATENU 306, 501)
  * HINT.n / WILDCARD.n puzzles earn a Hint / a Free Puzzle token
  * PIECE.n holds the city's piece of the box; five pieces open the trickster's
    Challenge (the level's own puzzles), which captures the trickster
  * leaving a city resets half-done puzzles (LANGENU 1003) - solved ones stay solved
Saved as JSON in the remaster's data folder, one file per player.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..settings import data_dir

TOKEN_EVERY = 10
SPEED_TOKENS = 3            # a speed puzzle beaten when the city's piece is already known (LANGENU 1037)
MASTER_FREE_COST = 3        # a Challenge puzzle costs three Free Puzzle tokens (0x436430, LANGENU 1041)
PIECES_PER_LEVEL = 5


@dataclass
class Player:
    name: str
    level: int = 1
    city: str | None = None              # ROF city folder, e.g. "CITY.06.CAIRO" (in it now: resume there)
    last_city: str | None = None         # the city last visited: "Current location" on the map
    solved: dict[str, list[int]] = field(default_factory=dict)   # "LEVEL.01.MAUI/CITY.06.CAIRO" -> numbers
    pieces: list[str] = field(default_factory=list)              # city paths whose piece was found
    revealed: list[str] = field(default_factory=list)            # city paths whose piece puzzle a speed bonus showed
    master_solved: dict[str, list[int]] = field(default_factory=dict)
    captured: list[int] = field(default_factory=list)            # levels whose trickster is captured
    videos_seen: list[int] = field(default_factory=list)         # levels whose intro video was shown
    hints: int = 0
    free: int = 0
    toward_token: int = 0
    total_solved: int = 0
    finished: bool = False
    best: dict[str, float] = field(default_factory=dict)          # puzzle folder -> best seconds

    # ------------------------------------------------------------- queries
    def is_solved(self, city_path: str, number: int) -> bool:
        return number in self.solved.get(city_path, [])

    def record_time(self, puzzle_path: str, seconds: float) -> bool:
        """Keep the player's best time for a puzzle; True if this one is a new best."""
        old = self.best.get(puzzle_path)
        if old is None or seconds < old:
            self.best[puzzle_path] = round(seconds, 2)
            return True
        return False

    def level_pieces(self, level_path: str) -> list[str]:
        return [p for p in self.pieces if p.startswith(level_path + "/")]

    # --------------------------------------------------------------- rules
    def solve(self, city, puzzle, used_free=False, beat_clock=False) -> list[str]:
        """Record a solved city puzzle; returns the events it caused, in order:
        'token', 'hint', 'wildcard', 'piece', 'challenge', 'revealed' / 'speed_tokens', 'city_done'.
        beat_clock: a speed puzzle (TIME.<n>.<secs>) solved in time without a Hint or Free token;
        it shows where the city's piece is hidden, or (piece already found or shown) gives
        three Free Puzzle tokens (0x403fe9: string 1036 or 1037)."""
        events = []
        done = self.solved.setdefault(city.path, [])
        if puzzle.number in done:
            return events
        done.append(puzzle.number)
        self.total_solved += 1
        self.toward_token += 1
        if self.toward_token >= TOKEN_EVERY:
            self.toward_token = 0
            self.free += 1
            events.append("token")
        if used_free:
            self.free -= 1
        if puzzle.hint:
            self.hints += 1
            events.append("hint")
        if puzzle.wildcard:
            self.free += 1
            events.append("wildcard")
        if puzzle.piece and city.path not in self.pieces:
            self.pieces.append(city.path)
            events.append("piece")
            level_path = city.path.split("/")[0]
            if len(self.level_pieces(level_path)) >= PIECES_PER_LEVEL:
                events.append("challenge")
        if beat_clock and puzzle.time_limit:
            if city.path not in self.pieces and city.path not in self.revealed:
                self.revealed.append(city.path)
                events.append("revealed")
            else:
                self.free += SPEED_TOKENS
                events.append("speed_tokens")
        if len(done) >= len(city.puzzles):
            events.append("city_done")
        return events

    def solve_master(self, level, puzzle, used_free=False) -> list[str]:
        done = self.master_solved.setdefault(level.path, [])
        if puzzle.number not in done:
            done.append(puzzle.number)
            if used_free:
                self.free -= MASTER_FREE_COST
        if len(done) >= len(level.puzzles) and level.number not in self.captured:
            self.captured.append(level.number)
            return ["captured"]
        return []

    def next_level(self, last_level: int):
        if self.level >= last_level:
            self.finished = True
        else:
            self.level += 1
        self.city = None
        self.last_city = None

    # --------------------------------------------------------- persistence
    @staticmethod
    def path_for(name: str, folder: Path | None = None) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") or "player"
        return (folder or data_dir() / "players") / f"{safe}.json"

    def save(self, folder: Path | None = None):
        path = self.path_for(self.name, folder)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=1), encoding="utf-8")
        tmp.replace(path)

    @classmethod
    def load(cls, name: str, folder: Path | None = None) -> "Player":
        try:
            raw = json.loads(cls.path_for(name, folder).read_text(encoding="utf-8"))
            return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})
        except (OSError, ValueError, TypeError):
            return cls(name)

    @classmethod
    def exists(cls, name: str, folder: Path | None = None) -> bool:
        return cls.path_for(name, folder).exists()
