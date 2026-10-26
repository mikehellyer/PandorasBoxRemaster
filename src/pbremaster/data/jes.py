"""Jesse's Strips puzzles: PUZZLE.JES + picture .JPG (loader 0x4b6e30, class CJesseStripsObject).

    u32 ?, u32 version, i32 cell (30/25/20 px), i32 ?, i32 ?, i32 ?,
    u32 tray columns, u32 tray rows (always ~570x480 px), u32 pieces, u32 ?, u8 ?
    char name[]\\0 ("puzzle.jes"), char picture[]\\0
    5 x u32 tray counts, then each tray's piece numbers (u32)
    pieces x 57 bytes (CTStrip):
        i32 x, y, u32 dir      start cell on its tray, orientation 1-4
        i32 x, y, u32 dir      (same as the start in every file)
        i32 x, y, u32 dir      solution cell on the board; dir 1 vertical, 2 horizontal
        u8 ?, u32 length (cells), RECT the strip in the picture (pixels)
    u32 n, n x (i32 x, i32 y)  board cells whose picture is shown from the start

A strip is a 1 x length run of picture cells. Orientation counts quarter turns
from the strip's own direction (dir - solution dir, mod 4). The board is the
picture placed on the tray grid at (solution cell - rect / cell), the same for
every strip of a puzzle.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass
class Strip:
    start: tuple[int, int]
    start_dir: int
    home: tuple[int, int]
    home_dir: int              # 1 vertical, 2 horizontal
    length: int
    rect: tuple[int, int, int, int]


@dataclass
class JesPuzzle:
    cell: int
    cols: int
    rows: int
    picture: str
    trays: list[list[int]]     # 5 lists of strip numbers
    strips: list[Strip]
    given: list[tuple[int, int]]
    board: tuple[int, int]     # tray cell of the picture's top-left


def parse(data: bytes) -> JesPuzzle:
    _, _, cell, _, _, _, cols, rows, n, _ = struct.unpack_from("<2I4i4I", data)
    p = 41
    p = data.index(b"\0", p) + 1
    e = data.index(b"\0", p)
    picture = data[p:e].decode("latin-1")
    p = e + 1
    counts = struct.unpack_from("<5I", data, p)
    p += 20
    trays = []
    for c in counts:
        trays.append(list(struct.unpack_from(f"<{c}I", data, p)))
        p += 4 * c
    strips = []
    for _ in range(n):
        sx, sy, sd, _, _, _, hx, hy, hd = struct.unpack_from("<2iI2iI2iI", data, p)
        length = struct.unpack_from("<I", data, p + 37)[0]
        rect = struct.unpack_from("<4i", data, p + 41)
        strips.append(Strip((sx, sy), sd, (hx, hy), hd, length, rect))
        p += 57
    (g,) = struct.unpack_from("<I", data, p)
    given = [struct.unpack_from("<2i", data, p + 4 + 8 * k) for k in range(g)]
    s = strips[0]
    board = (s.home[0] - s.rect[0] // cell, s.home[1] - s.rect[1] // cell)
    return JesPuzzle(cell, cols, rows, picture, trays, strips, [tuple(c) for c in given], board)
