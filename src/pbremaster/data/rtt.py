"""Rotascope puzzles: PUZZLE.RTT (loader 0x4efea0, class CRotoscopeObject).

    char  'Zero', u32 version (3)
    char  name[] NUL-terminated ("New Puzzle")
    u32   ?, u32 ?, COLORREF outline colour, u32 ?
    64 x (u8 ring, u8 sector)   layout grid [ring][sector] (8x8, unused cells 0):
                                which piece sits in each ring section; (255,255) = the gap
    u8 ring, u8 sector          the piece in the centre (255,255 = the gap)   } added after the
    u32 ?, u32 ?                                                              } Feb 2000 build
    u32   start angle in degrees (the first sector's edge)
    char  source path[] NUL-terminated
    u32   jpeg size, JPEG
The tutorial puzzle wraps the same record in a 'MAP' container (like PUZZLE.ZOO).

Geometry (configs at 0x5b2630, built at 0x4f0a00): 4 sectors x 2 rings (radius ratio 3),
5 x 3 (ratio 2) or 6 x 4 (ratio 1.64). The outer radius is min(w, h) / 2 - 1 (at most 250),
each ring inside is the previous radius / ratio, and the innermost radius is the centre disc.
Ring 0 is the innermost ring. Solved: every piece home and the gap in the centre.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

GAP = (255, 255)
CONFIGS = {4: (2, 3.0), 5: (3, 2.0), 6: (4, 1.64)}       # sectors -> (rings, ratio)


@dataclass
class RttPuzzle:
    sectors: int
    rings: int
    ratio: float
    angle: int
    colour: tuple[int, int, int]
    grid: dict[tuple[int, int], tuple[int, int]]          # position (ring, sector) -> piece
    centre: tuple[int, int]
    jpeg: bytes


def parse(data: bytes) -> RttPuzzle:
    start = data.find(b"Zero")
    if start < 0:
        raise ValueError("RTT: no 'Zero' record")
    p = start + 8
    p = data.index(b"\0", p) + 1
    _, _, colour, _ = struct.unpack_from("<4I", data, p)
    p += 16
    cells = [(data[p + 2 * i], data[p + 2 * i + 1]) for i in range(64)]
    p += 128
    centre = (data[p], data[p + 1])
    p += 10
    (angle,) = struct.unpack_from("<I", data, p)
    p += 4
    p = data.index(b"\0", p) + 1
    (size,) = struct.unpack_from("<I", data, p)
    jpeg = data[p + 4:p + 4 + size]
    for sectors, (rings, ratio) in CONFIGS.items():
        grid = {(r, s): cells[r * 8 + s] for r in range(rings) for s in range(sectors)}
        want = sorted([(r, s) for r in range(rings) for s in range(sectors)] + [GAP])
        if sorted(list(grid.values()) + [centre]) == want:
            rgb = (colour & 0xFF, (colour >> 8) & 0xFF, (colour >> 16) & 0xFF)
            return RttPuzzle(sectors, rings, ratio, angle % 360, rgb, grid, centre, jpeg)
    raise ValueError("RTT: layout fits no disk")
