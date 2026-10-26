"""Focus Point puzzles: PUZZLE.ZOO ("Zoommess Ver.04", Kirill Ageev, 1997).

Layout, from the editor's save routine at 0x4a2b80 in PANDORA.EUL:

    0x00  0x44-byte header template ('MAP' 01, a GUID, "Puzzle Desc" ...). Two
          sizes are patched in at 0x35; the header of one shipped file
          (Athens 1) is overwritten with garbage, so it is ignored here.
    0x44  u32 desc_size (= 0x160 + 36 * cells)
    0x48  char copyright[64]
    0x88  0x120 bytes of parameters: u32 cells, i32 x, i32 y, u32 width, u32 height,
          1, 1, u32 (hi word 0-6, lo word 0/1: not used yet), zeros
    0x1a8 cells x 9 x i32:
            home  x+16, y+16, w, h   where the piece's picture is in the image
            slot  x, y, w, h         where the piece starts (a scrambled layout)
            0
    0x48+desc_size  the picture, a JFIF JPEG
    last 0x18 bytes  trailer
    (Three shipped JPEGs are truncated; libjpeg via pygame still decodes them.)

The set of slot rectangles equals the set of home rectangles: the board is a
fixed partition of the picture, and a piece is drawn stretched to whatever
slot it sits in. Solved when every piece is in its own slot.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

TRAILER = 0x18


@dataclass
class ZooPuzzle:
    x: int
    y: int
    width: int
    height: int
    style: int                       # parameter 7, not understood yet
    homes: list[tuple[int, int, int, int]]
    slots: list[tuple[int, int, int, int]]
    jpeg: bytes


def parse(data: bytes) -> ZooPuzzle:
    (desc_size,) = struct.unpack_from("<I", data, 0x44)
    n, x, y, w, h, _, _, style = struct.unpack_from("<8i", data, 0x88)
    if desc_size != 0x160 + 36 * n:
        raise ValueError(f"ZOO: description size {desc_size} does not fit {n} cells")
    homes, slots = [], []
    for k in range(n):
        c = struct.unpack_from("<9i", data, 0x1a8 + 36 * k)
        homes.append((c[0] - 16, c[1] - 16, c[2], c[3]))
        slots.append(tuple(c[4:8]))
    if sorted(homes) != sorted(slots):
        homes = _snap(homes, slots)
    jpeg = data[0x48 + desc_size:len(data) - TRAILER]
    if jpeg[:2] != b"\xff\xd8":
        raise ValueError("ZOO: no JPEG picture")
    return ZooPuzzle(x, y, w, h, style, homes, slots, jpeg)


def _snap(homes, slots):
    """One shipped file (Scalawag 'City Place') stores every home 1 px lower than
    its slot; match each home to the free slot of the same size within 2 px."""
    free = list(slots)
    out = []
    for hx, hy, hw, hh in homes:
        match = next((s for s in free if s[2:] == (hw, hh) and abs(s[0] - hx) <= 2 and abs(s[1] - hy) <= 2), None)
        if match is None:
            raise ValueError("ZOO: slots are not a rearrangement of the pieces")
        free.remove(match)
        out.append(match)
    return out
