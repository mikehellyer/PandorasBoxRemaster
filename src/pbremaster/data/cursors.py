"""Mouse cursors from the RT_CURSOR resources of DATA/PANDORA.EUL.

Each RT_CURSOR is: u16 hotspot_x, u16 hotspot_y, then a DIB (BITMAPINFOHEADER,
palette, XOR bitmap, AND mask) whose height counts both bitmaps. The game loads
cursor 0x6d (109) as its normal pointer (0x4f8b10).
"""
from __future__ import annotations

import struct

import numpy as np
import pefile

RT_CURSOR, RT_GROUP_CURSOR = 1, 12
ARROW = 109


def _rows(data, off, w, h, bpp):
    stride = ((w * bpp + 31) // 32) * 4
    return np.frombuffer(data, np.uint8, h * stride, off).reshape(h, stride)[::-1], off + h * stride


def decode(data: bytes):
    """Return (rgba ndarray (h, w, 4), (hot_x, hot_y))."""
    hx, hy = struct.unpack_from("<HH", data)
    dib = data[4:]
    size, w, h2, _, bpp = struct.unpack_from("<IiiHH", dib)
    h = h2 // 2
    ncol = struct.unpack_from("<I", dib, 32)[0] or (1 << bpp if bpp <= 8 else 0)
    pal = np.frombuffer(dib, np.uint8, ncol * 4, size).reshape(ncol, 4)[:, [2, 1, 0]] if ncol else None
    xor, off = _rows(dib, size + ncol * 4, w, h, bpp)
    andm, _ = _rows(dib, off, w, h, 1)
    if bpp == 1:
        idx = np.unpackbits(xor, axis=1)[:, :w]
    elif bpp == 4:
        idx = np.stack([xor >> 4, xor & 15], axis=-1).reshape(h, -1)[:, :w]
    elif bpp == 8:
        idx = xor[:, :w]
    else:
        raise ValueError(f"cursor bpp {bpp}")
    rgb = pal[idx]
    transparent = np.unpackbits(andm, axis=1)[:, :w].astype(bool)
    alpha = np.where(transparent, 0, 255).astype(np.uint8)
    # AND=1 with XOR!=0 inverts the screen; there is no portable way, show it black.
    rgb[transparent & (idx != 0)] = 0
    alpha[transparent & (idx != 0)] = 255
    return np.dstack([rgb, alpha]), (hx, hy)


def load(path, group_id=ARROW):
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories([pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    res = {}
    for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if t.id in (RT_CURSOR, RT_GROUP_CURSOR):
            for e in t.directory.entries:
                d = e.directory.entries[0].data.struct
                res[(t.id, e.id)] = pe.get_data(d.OffsetToData, d.Size)
    pe.close()
    group = res[(RT_GROUP_CURSOR, group_id)]
    count = struct.unpack_from("<H", group, 4)[0]
    # GRPCURSORDIRENTRY: u16 w, u16 h, u16 planes, u16 bpp, u32 bytes, u16 id (14 bytes)
    best = max((struct.unpack_from("<HHHHIH", group, 6 + 14 * i) for i in range(count)),
               key=lambda e: e[3])
    return decode(res[(RT_CURSOR, best[5])])
