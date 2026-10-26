"""Lens Bender puzzles (CBumpyGlassObject).

PUZZLE.BGL is an INI file:
    [BumpyGlass]    ObjectCount, Difficulty (0-3: lens set TUTOR/EASY/MEDIUM/HARD),
                    SolutionWidth/Height, shading constants (LensDepth, LensIndex, ...)
    [BumpySpriteN]  FinalXpos/FinalYpos (place in the solution), InitialStack (lens 0-5,
                    6 = already in the middle), InitialStackOrder (0 = top), FinalStack
                    (the lens where it faces the right way), Adjacency (letters A.. of the
                    sprites it touches), Angle (degrees), CentroidX/Y (optional)
with PUZZLE_SPR<n-1>.PNG / ...A.PNG (mask, black = solid) and TILE.PNG/BMP per puzzle.

BGL/<SET>.INI places the lenses (Lens1..7 centres, 7 = the middle) and the arrow
buttons (Button1..6) in the 650x540 play area. BGL/<SET>_LENS<k>.RTRT (and .RTRS for
the middle lens) are ray-traced lens tables:
    u32 w, u32 h, 50 bytes (flags, float bounds), i16 (x, y)[h][w] source pixel
    (-16383 = outside the lens), u16 shade[h][w] (65536 = full light)
A piece under lens k faces Angle + 60k degrees; at FinalStack that is 0 for all 313
pieces in the 22 puzzles.
"""
from __future__ import annotations

import configparser
import struct
from dataclasses import dataclass

import numpy as np

SETS = ["TUTOR", "EASY", "MEDIUM", "HARD"]
MIDDLE = 6
OUTSIDE = -16383


@dataclass
class BglSprite:
    index: int
    final: tuple[int, int]
    stack: int
    order: int
    final_stack: int
    adjacent: set[int]
    angle: float
    centroid: tuple[int, int] | None


@dataclass
class BglPuzzle:
    sprites: list[BglSprite]
    difficulty: int
    solution: tuple[int, int]

    @property
    def lens_set(self):
        return SETS[max(0, min(3, self.difficulty))]


@dataclass
class Lens:
    size: tuple[int, int]
    src: np.ndarray            # (h, w, 2) int16 source x, y
    shade: np.ndarray          # (h, w) float 0..1
    inside: np.ndarray         # (h, w) bool


def _ini(data: bytes):
    cp = configparser.ConfigParser(strict=False, interpolation=None)
    cp.optionxform = str
    cp.read_string(data.decode("latin-1"))
    return cp


def parse(data: bytes) -> BglPuzzle:
    cp = _ini(data)
    main = cp["BumpyGlass"]
    sprites = []
    for n in range(1, int(main["ObjectCount"]) + 1):
        s = cp[f"BumpySprite{n}"]
        centroid = (int(s["CentroidX"]), int(s["CentroidY"])) if "CentroidX" in s else None
        sprites.append(BglSprite(
            n - 1, (int(s["FinalXpos"]), int(s["FinalYpos"])), int(s["InitialStack"]),
            int(s["InitialStackOrder"]), int(s["FinalStack"]),
            {ord(c) - ord("A") for c in s.get("Adjacency", "").strip().upper() if c.isalpha()},
            float(s["Angle"]), centroid))
    return BglPuzzle(sprites, int(main.get("Difficulty", "0")),
                     (int(main["SolutionWidth"]), int(main["SolutionHeight"])))


def layout(data: bytes):
    """Lens centres (7, the last is the middle) and arrow button centres (6)."""
    s = _ini(data)["BumpyGlassLayout"]
    lenses = [(int(s[f"Lens{k}PosX"]), int(s[f"Lens{k}PosY"])) for k in range(1, int(s["LensCount"]) + 1)]
    buttons = [(int(s[f"Button{k}PosX"]), int(s[f"Button{k}PosY"])) for k in range(1, 7)]
    return lenses, buttons


def lens(data: bytes) -> Lens:
    w, h = struct.unpack_from("<II", data)
    src = np.frombuffer(data, "<i2", count=w * h * 2, offset=58).reshape(h, w, 2)
    shade = np.frombuffer(data, "<u2", count=w * h, offset=58 + w * h * 4).reshape(h, w) / 65536
    return Lens((w, h), src, shade, src[..., 0] != OUTSIDE)
