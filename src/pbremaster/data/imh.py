"""Image Hole puzzles: PUZZLE.IMH + <picture>.JPG (650x540) + <picture>.PNG (hole mask).

Loader at 0x4ace50 in PANDORA.EUL:

    u32 ?            (not the file size; ignored)
    u32 version      1 or 2
    u32 holes
    COLORREF fill    the colour the holes' places are cut out with
    COLORREF outline
    char title[]\\0, char picture[]\\0 (the .JPG), char mask[]\\0 (a .BMP name; the CD has a .PNG)
    holes x 58 bytes:
        u8   ?
        f32  scale        a hole may be bigger or smaller than its place (0.5 - 1.4)
        f32  ?            always 0
        f32  speed        3 - 21
        u8   locked       1: starts locked in place
        RECT place        left, top, right, bottom of its shape in the mask
        POINT home        = place top-left
        POINT start       where the hole starts
        POINT direction   (-5..5, -5..5)
        COLORREF key      the hole's colour in the mask
    version 2: u32 0
"""
from __future__ import annotations

import struct
from dataclasses import dataclass


def _rgb(c):
    return c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF


@dataclass
class Hole:
    scale: float
    speed: float
    locked: bool
    place: tuple[int, int, int, int]       # left, top, right, bottom
    start: tuple[int, int]
    direction: tuple[int, int]
    key: tuple[int, int, int]


@dataclass
class ImhPuzzle:
    title: str
    picture: str
    mask: str
    fill: tuple[int, int, int]
    outline: tuple[int, int, int]
    holes: list[Hole]


def parse(data: bytes) -> ImhPuzzle:
    _, version, n, fill, outline = struct.unpack_from("<5I", data)
    p, names = 20, []
    for _ in range(3):
        e = data.index(b"\0", p)
        names.append(data[p:e].decode("latin-1"))
        p = e + 1
    holes = []
    for _ in range(n):
        scale, _zero, speed = struct.unpack_from("<3f", data, p + 1)
        locked = data[p + 13]
        l, t, r, b, _hx, _hy, sx, sy, dx, dy, key = struct.unpack_from("<10iI", data, p + 14)
        holes.append(Hole(scale, speed, bool(locked), (l, t, r, b), (sx, sy), (dx, dy), _rgb(key)))
        p += 58
    return ImhPuzzle(names[0], names[1], names[2], _rgb(fill), _rgb(outline), holes)
