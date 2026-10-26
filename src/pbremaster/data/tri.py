"""Interlock puzzles: PUZZLE.TRI ('trgm', loader 0x5116e0, CTrigramsObject / CTangram / CPiece).

    'trgm', u32 version (1)
    u32 n, char path[n]                 (the picture, as on the author's disk)
    u32 shapes (1)
    shape: u32 n, char name[n] ("shape 1"), COLORREF piece colour,
           7 x piece { u32 type, u8 flip, i32 x, i32 y, i32 rotation }   - the solution
           i32 w, h, w*h bytes, i32 ?, i32 ?, u32 triangle size (px)
    7 x { u32 type, u8 flip, i32 x, i32 y, i32 rotation, i32 ?, i32 ?, u32 size }  - start
        (the start records came after the Feb 2000 loader)

The board is a grid of equilateral triangles: column step size/2, row height
size*sqrt(3)/2 (0x511170); a piece's cells come from data/iamonds.py, the
triangle at its (0, 0) pointing down or up as the shape says.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from .iamonds import SHAPES


@dataclass
class Placement:
    type: int
    flip: int
    x: int
    y: int
    rotation: int

    def cells(self):
        w, h, down, rows = SHAPES[self.type][self.rotation % 6][self.flip & 1]
        return {(self.x + i, self.y + j) for j, row in enumerate(rows) for i, ch in enumerate(row) if ch == "#"}

    @property
    def down(self):
        return SHAPES[self.type][self.rotation % 6][self.flip & 1][2]


@dataclass
class TriPuzzle:
    picture: str
    colour: tuple[int, int, int]
    size: int
    solution: list[Placement]
    start: list[Placement]


def parse(data: bytes) -> TriPuzzle:
    if data[:4] != b"trgm":
        raise ValueError("TRI: bad magic")
    n = struct.unpack_from("<I", data, 8)[0]
    picture = data[12:12 + n].split(b"\0")[0].decode("latin-1").replace("\\", "/").rsplit("/", 1)[-1]
    p = 12 + n + 4
    n = struct.unpack_from("<I", data, p)[0]
    p += 4 + n
    c = struct.unpack_from("<I", data, p)[0]
    p += 4
    solution = []
    for _ in range(7):
        t = struct.unpack_from("<I", data, p)[0]
        x, y, r = struct.unpack_from("<3i", data, p + 5)
        solution.append(Placement(t, data[p + 4], x, y, r))
        p += 17
    w, h = struct.unpack_from("<2i", data, p)
    p += 8 + w * h + 8
    size = struct.unpack_from("<I", data, p)[0]
    p += 4
    start = []
    for _ in range(7):
        t = struct.unpack_from("<I", data, p)[0]
        x, y, r = struct.unpack_from("<3i", data, p + 5)
        start.append(Placement(t, data[p + 4], x, y, r))
        p += 29
    return TriPuzzle(picture, (c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF), size, solution, start)
