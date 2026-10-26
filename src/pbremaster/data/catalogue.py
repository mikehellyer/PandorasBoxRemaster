"""The campaign structure, read from the directory tree of PANDORA.ROF.

    LEVEL.0/PUZZLE.<n>.<kind>/                    tutorial / practice puzzles
    LEVEL.<nn>.<TRICKSTER>/CITY.<id>.<NAME>/      a city on the world map
        PUZZLE.<n>.<kind>/...                     the puzzle's data
        PIECE.<n>     (empty)  solving puzzle n wins the city's box piece
        HINT.<n>      (empty)  solving puzzle n earns a hint
        WILDCARD.<n>  (empty)  solving puzzle n earns a free puzzle
        TIME.<n>.<s>  (empty)  puzzle n is timed, s seconds
    LEVEL.<nn>.<TRICKSTER>/PUZZLE.<n>.<kind>/     the level's master puzzle
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .rof import ROF

# Puzzle kind suffix -> official name (LANGENU.DLL strings 150-161).
KINDS = {
    "IMH": "Image Hole", "IHL": "Image Hole",
    "FPN": "Focus Point", "ZOO": "Focus Point",
    "RTT": "Rotascope", "RTS": "Rotascope",
    "OVL": "Overlap", "FSH": "Overlap",
    "SKN": "Outer Layer", "SKI": "Outer Layer",
    "JES": "Jesse's Strips", "JESS": "Jesse's Strips",
    "SLC": "Slices", "SLICE": "Slices",
    "BGL": "Lens Bender",
    "TRI": "Interlock", "TAN": "Interlock",
    "FNF": "Find and Fill", "F&F": "Find and Fill",
}

# Data file extension inside a puzzle folder -> kind name. Level 8 folders are
# named after the picture ("PUZZLE.11.GIRAFFE"), so the kind comes from here.
DATA_KINDS = {
    "IMH": "Image Hole", "ZOO": "Focus Point", "RTT": "Rotascope", "FSH": "Overlap",
    "SKI": "Outer Layer", "JES": "Jesse's Strips", "WRL": "Slices",
    "BGL": "Lens Bender", "TRI": "Interlock", "FNF": "Find and Fill",
}

_PUZ = re.compile(r"PUZZLE\.(\d+)\.(.+)$")
_CITY = re.compile(r"CITY\.(\d+)\.(.+)$")
_LEVEL = re.compile(r"LEVEL\.(\d+)(?:\.(.+))?$")


@dataclass
class Puzzle:
    path: str                    # ROF directory, e.g. LEVEL.01.MAUI/CITY.06.CAIRO/PUZZLE.02.SLC
    number: int
    kind: str                    # suffix as stored (SLC, FPN, ...)
    files: list[str] = field(default_factory=list)
    piece: bool = False
    hint: bool = False
    wildcard: bool = False
    time_limit: int | None = None
    level: int = 0
    city_id: int = 0             # 0 for level-wide puzzles

    @property
    def name_id(self) -> int:
        """String id of the picture's name (NAMEENU) and credits (PUZENU)."""
        return self.level * 1000 + self.city_id * 20 + self.number

    @property
    def kind_name(self):
        if self.kind in KINDS:
            return KINDS[self.kind]
        for f in self.files:
            ext = f.rsplit(".", 1)[-1]
            if ext in DATA_KINDS:
                return DATA_KINDS[ext]
        return self.kind


@dataclass
class City:
    path: str
    id: int
    name: str
    puzzles: dict[int, Puzzle] = field(default_factory=dict)


@dataclass
class Level:
    path: str
    number: int
    trickster: str | None
    cities: dict[str, City] = field(default_factory=dict)
    puzzles: dict[int, Puzzle] = field(default_factory=dict)   # level-wide (master / practice)


def load(rof: ROF) -> dict[int, Level]:
    levels: dict[int, Level] = {}
    for path in rof.files:
        parts = path.split("/")
        m = _LEVEL.match(parts[0])
        if not m:
            continue
        lv = levels.setdefault(int(m.group(1)), Level(parts[0], int(m.group(1)), m.group(2)))
        rest, owner = parts[1:], lv
        if rest and (cm := _CITY.match(rest[0])):
            owner = lv.cities.setdefault(rest[0], City("/".join(parts[:2]), int(cm.group(1)), cm.group(2)))
            rest = rest[1:]
        if not rest:
            continue
        if pm := _PUZ.match(rest[0]):
            n = int(pm.group(1))
            pz = owner.puzzles.setdefault(n, Puzzle("", n, ""))
            pz.level, pz.city_id = lv.number, getattr(owner, "id", 0)
            pz.path = "/".join(parts[:len(parts) - len(rest) + 1])
            pz.kind = pm.group(2)
            pz.files.append(path)
            continue
        marker = rest[0].split(".")
        if len(rest) == 1 and marker[0] in ("PIECE", "HINT", "WILDCARD", "TIME") and marker[1].isdigit():
            n = int(marker[1])
            pz = owner.puzzles.setdefault(n, Puzzle("", n, ""))
            pz.level, pz.city_id = lv.number, getattr(owner, "id", 0)
            if marker[0] == "TIME":
                pz.time_limit = int(marker[2])
            else:
                setattr(pz, marker[0].lower(), True)
    return dict(sorted(levels.items()))
