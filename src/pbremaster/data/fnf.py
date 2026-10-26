"""Find and Fill puzzles: PUZZLE.FNF (loader 0x499eb0, CFindNFillObject).

    'fnf_', u32 version (1), u32 pictures, u32 strip width, u32 121, u32 16
    per picture:
        image   strip: the reference picture (140 px, magenta border) and the
                black silhouettes of its objects
        u32     objects
        objects x { image (the object as in the picture, magenta = transparent),
                    u32 1, COLORREF, f64 angle (degrees), f64 -height/2,
                    RECT in the source picture, i32, i32, outline / scanline data ...,
                    u32 n + name[n] }
    u32 n + source picture path[n] ... (ends ".bmp")
    f64 angle (radians), u32 layout (0/1 square pile, 2 wide strip), u32 size,
    u32 W, u32 H, u16 board[H][W]
    image = u32 width, u32 height, u32 bpp (16), rows of RGB555, 4-byte aligned

The board is the puzzle: each cell's bits 4+k say which objects cover it (bit 3
is set on some cells, unknown). Objects are piled on it overlapping and turned;
their outlines are the boundaries between cells of different value. Some files
carry stale bytes after the board (an older, larger save written over in place).

The outline data has no length field, so the next object is found by its image
header followed by the object's u32 1, and the board by the first ".bmp" string
followed by a plausible header (checked on all 45 files).
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass

import numpy as np

from .deft import rgb555_to_rgb

KEY = 0x7C1F          # RGB555 magenta
_STRIP = re.compile(rb"[\x00-\xff]{2}\x00\x00\x79\x00\x00\x00\x10\x00\x00\x00", re.S)
_BOARD = re.compile(rb"\.bmp(.{24})", re.S | re.I)


@dataclass
class FnfObject:
    rgb: np.ndarray            # (h, w, 3)
    mask: np.ndarray           # (h, w) bool
    rect: tuple[int, int, int, int]    # in the source picture
    picture: int               # which reference picture it belongs to


@dataclass
class FnfPuzzle:
    strips: list[np.ndarray]   # (121, w, 3) per reference picture
    objects: list[FnfObject]
    board: np.ndarray          # (H, W) uint16, bit k set where object k lies
    layout: int


def _image(data, p):
    w, h, bpp = struct.unpack_from("<3I", data, p)
    if bpp != 16 or not (0 < w < 2000 and 0 < h < 2000):
        raise ValueError
    stride = ((w * 16 + 31) // 32) * 4
    raw = np.frombuffer(data, "<u2", count=h * stride // 2, offset=p + 12).reshape(h, stride // 2)[:, :w]
    return raw, p + 12 + stride * h


def _is_object(data, p):
    try:
        raw, e = _image(data, p)
    except (ValueError, struct.error):
        return False
    if e + 48 > len(data) or struct.unpack_from("<I", data, e)[0] != 1:
        return False
    l, t, r, b = struct.unpack_from("<4i", data, e + 24)
    return (r - l, b - t) == (raw.shape[1], raw.shape[0])


def parse(data: bytes) -> FnfPuzzle:
    if data[:4] != b"fnf_":
        raise ValueError("FNF: bad magic")
    pictures = struct.unpack_from("<I", data, 8)[0]
    p = 12
    strips, objects = [], []
    for k in range(pictures):
        if k:                                  # skip to the next strip (w, 121, 16)
            m = _STRIP.search(data, p)
            if not m:
                raise ValueError("FNF: picture strip missing")
            p = m.start()
        raw, p = _image(data, p)
        strips.append(rgb555_to_rgb(raw))
        count = struct.unpack_from("<I", data, p)[0]
        p += 4
        for _ in range(count):
            while not _is_object(data, p):
                p += 1
            raw, e = _image(data, p)
            rect = struct.unpack_from("<4i", data, e + 24)
            objects.append(FnfObject(rgb555_to_rgb(raw), raw != KEY, rect, k))
            p = e + 48
    for m in _BOARD.finditer(data, p):
        angle, layout, size, w, h = struct.unpack("<d4i", m.group(1))
        if 50 <= w <= 2000 and 50 <= h <= 2000 and -7 < angle < 7 and m.end() + 2 * w * h <= len(data):
            cells = np.frombuffer(data, "<u2", count=w * h, offset=m.end()).reshape(h, w)
            return FnfPuzzle(strips, objects, (cells >> 4).astype(np.uint16), layout)
    raise ValueError("FNF: board missing")
