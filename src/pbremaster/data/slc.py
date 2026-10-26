"""Slices puzzles: a folder per puzzle (CLambChopsObject, loader around 0x4c3950).

    OBJECT.WRL      VRML 1.0: four SpotLights, then per piece `DEF <n>obj Separator {
                    MatrixTransform { matrix <4x4, row vectors> } Separator { Coordinate3
                    { point [8 corners] } ... } }` (the piece's bounding box), and a last
                    `wobj` box round the whole object
    STATE.TXT       per piece: "x z flip rotation" then its name ("1obj"): where it starts
                    on the floor and which way it faces
    <n>OBJ_<v>.PNG  the piece pre-rendered in view v (1-8), <n>OBJ_<v>A.PNG its mask
                    (black = solid); WOBJ_<v> the whole object
Views (fitted to WOBJ, 0.985+ silhouette overlap on all 8): v = flip*4 + turn + 1, the
object turned `turn` quarter turns about y, then if flipped turned half over about x.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

TOUCH = 0.05            # boxes this close count as neighbours (all 29 puzzles stay connected)


@dataclass
class SlcPiece:
    name: str           # "1obj": images are "1OBJ_<v>.PNG"
    lo: np.ndarray      # world box in the assembled object
    hi: np.ndarray
    start: tuple[float, float, int, int]     # floor x, z, flip, turn

    @property
    def centre(self):
        return (self.lo + self.hi) / 2

    @property
    def half(self):
        return (self.hi - self.lo) / 2

    def image(self, view: int) -> str:
        return f"{self.name.upper()}_{view}"


@dataclass
class SlcPuzzle:
    pieces: list[SlcPiece]
    neighbours: list[set[int]]


def _boxes(wrl: str):
    parts = re.split(r"DEF\s+(\S+)\s+Separator", wrl)[1:]
    for name, body in zip(parts[::2], parts[1::2]):
        mat = re.search(r"matrix\s+([-\d.eE\s]+)", body)
        m = np.array([float(x) for x in mat.group(1).split()[:16]]).reshape(4, 4) if mat else np.eye(4)
        pts = np.array([[float(x) for x in p.split()]
                        for p in re.search(r"point\s*\[([^\]]*)\]", body).group(1).split(",") if p.strip()])
        world = pts @ m[:3, :3] + m[3, :3]
        yield name, world.min(0), world.max(0)


def parse(wrl: bytes, state: bytes) -> SlcPuzzle:
    starts = {}
    nums = []
    for word in state.decode("latin-1").split():       # numbers, then the piece's name
        try:
            nums.append(float(word))
        except ValueError:
            x, z, flip, turn = (nums + [0, 0, 0, 0])[:4]
            starts[word.lower()] = (x, z, int(flip), int(turn))
            nums = []
    pieces = [SlcPiece(name, lo, hi, starts[name.lower()])
              for name, lo, hi in _boxes(wrl.decode("latin-1")) if name.lower() != "wobj"]
    n = len(pieces)
    neighbours = [{j for j in range(n) if j != i
                   and np.all(pieces[i].lo <= pieces[j].hi + TOUCH) and np.all(pieces[j].lo <= pieces[i].hi + TOUCH)}
                  for i in range(n)]
    return SlcPuzzle(pieces, neighbours)
