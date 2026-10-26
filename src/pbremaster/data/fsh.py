"""Overlap puzzles: PUZZLE.FSH (loader 0x4e1c30, class COverlapseObject).

A raw dump of the editor's structures (0xCD bytes are MSVC's uninitialised fill):

    'SFHP', u32 version (3)
    i32 cols, rows, cell (px), pieces, stacks, ?, ?, ?, ?
    char picture_path[260], char background_path[260]   (background: OVER/BG_<name>.PNG)
    CBitField: u32 bits (= cols*rows), ceil(bits/8) bytes  - cells shown from the start
    stacks x { u32 capacity, capacity x u32 (index 0 unused, then piece numbers), u32 count, u32 ? }
    pieces x { i32 x, y, shape, rotation, scramble, ?, stack, number }   (32 bytes, 0x4e4960)
    u32 size, JPEG picture (cols*cell x rows*cell; one file has a BMP)

Shapes (table built at 0x4e4780): every piece is three cells, the anchor and two
steps; shape 0 is a straight line, shape 1 an L; the step pair is picked by
(rotation + scramble) % 4, so a piece is the right way round when scramble is 0.
Pieces and the shown cells together cover every cell (checked on all 63 files),
overlapping each other. Anchors may lie outside the picture: those cells show
the background pattern.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

SHAPES = {
    0: [((0, 1), (0, 1)), ((-1, 0), (-1, 0)), ((0, -1), (0, -1)), ((1, 0), (1, 0))],
    1: [((0, 1), (-1, 0)), ((-1, 0), (0, -1)), ((0, -1), (1, 0)), ((1, 0), (0, 1))],
}


def shape_cells(shape, rotation):
    """Cells of a shape relative to its anchor."""
    x = y = 0
    out = [(0, 0)]
    for dx, dy in SHAPES[shape][rotation % 4]:
        x, y = x + dx, y + dy
        out.append((x, y))
    return out


@dataclass
class OverlapPiece:
    number: int
    anchor: tuple[int, int]
    shape: int
    rotation: int        # solution rotation
    scramble: int        # extra quarter turns at the start
    stack: int


@dataclass
class FshPuzzle:
    cols: int
    rows: int
    cell: int
    background: str      # e.g. "BG_PURPLE"
    shown: set[tuple[int, int]]
    stacks: list[list[int]]
    pieces: list[OverlapPiece]
    jpeg: bytes          # the picture (a BMP in one file)


def _cstr(b):
    return b.split(b"\0", 1)[0].decode("latin-1")


def parse(data: bytes) -> FshPuzzle:
    if data[:4] != b"SFHP":
        raise ValueError("FSH: bad magic")
    cols, rows, cell, n, nstacks = struct.unpack_from("<5i", data, 8)
    background = _cstr(data[0x130:0x234]).replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0].upper()
    nbits = struct.unpack_from("<I", data, 0x234)[0]
    nb = (nbits + 7) // 8
    bits = data[0x238:0x238 + nb]
    shown = {(i % cols, i // cols) for i in range(nbits) if bits[i // 8] >> (i % 8) & 1}
    p = 0x238 + nb
    stacks = []
    for _ in range(nstacks):
        cap = struct.unpack_from("<I", data, p)[0]
        ids = struct.unpack_from(f"<{cap}I", data, p + 4)
        count = struct.unpack_from("<I", data, p + 4 + 4 * cap)[0]
        stacks.append(list(ids[1:count + 1]))
        p += 4 + 4 * cap + 8
    pieces = []
    for _ in range(n):
        x, y, shape, rot, scr, _q, stack, num = struct.unpack_from("<8i", data, p)
        pieces.append(OverlapPiece(num, (x, y), shape, rot, scr, stack))
        p += 32
    size = struct.unpack_from("<I", data, p)[0]
    jpeg = data[p + 4:p + 4 + size]
    # The stack arrays keep stale entries from editing (duplicates, ids past the
    # end); each piece's own stack field is what counts. Keep the arrays' order.
    ordered = []
    for k in range(nstacks):
        seen, out = set(), []
        for i in stacks[k]:
            if 0 <= i < n and pieces[i].stack == k and i not in seen:
                seen.add(i)
                out.append(i)
        out += [pc.number for pc in pieces if pc.stack == k and pc.number not in seen]
        ordered.append(out)
    return FshPuzzle(cols, rows, cell, background, shown, ordered, pieces, jpeg)
