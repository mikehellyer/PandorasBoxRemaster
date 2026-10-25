"""'defT' chunked-deflate containers and the .RIM raw images they hold.

Container (.RIM, .RTR, TRICKS.RTR):

    char[4] 'defT'
    u32     chunk_size     uncompressed bytes per chunk (always 80000)
    u32     total_size     uncompressed size of the payload
    then, until total_size bytes are produced:
        u32 comp_size, comp_size bytes of zlib data (inflates to <= chunk_size)

RIM payload (a raw DIB-style image):

    u32 width, u32 height, u32 bpp, i32 stride (bytes per row, 4-byte aligned)
    height rows of |stride| bytes. A negative stride means the rows are stored
    bottom-up, as in a Windows DIB.
    bpp 16: little-endian RGB555 colour.  bpp 8: an alpha mask (0..255);
    masks are named like the colour image plus 'A' (106U.RIM / 106UA.RIM).
"""
from __future__ import annotations

import struct
import zlib

import numpy as np

MAGIC = b"defT"


def is_deft(data: bytes) -> bool:
    return data[:4] == MAGIC


def inflate(data: bytes) -> bytes:
    magic, _chunk, total = struct.unpack_from("<4sII", data)
    if magic != MAGIC:
        raise ValueError("not a defT container")
    out, pos = bytearray(), 12
    while len(out) < total:
        (comp,) = struct.unpack_from("<I", data, pos)
        pos += 4
        out += zlib.decompress(data[pos:pos + comp])
        pos += comp
    if len(out) != total:
        raise ValueError(f"defT: expected {total} bytes, got {len(out)}")
    return bytes(out)


def rgb555_to_rgb(pix: np.ndarray) -> np.ndarray:
    """uint16 RGB555 array (h, w) -> uint8 RGB array (h, w, 3)."""
    r = (pix >> 10) & 0x1F
    g = (pix >> 5) & 0x1F
    b = pix & 0x1F
    rgb = np.stack([r, g, b], axis=-1).astype(np.uint8)
    return (rgb << 3) | (rgb >> 2)


def decode_rim(data: bytes) -> np.ndarray:
    """Decode a .RIM file (defT-wrapped or raw).

    Returns an (h, w, 3) uint8 RGB array for 16-bit images, or an (h, w)
    uint8 alpha array for 8-bit masks, top row first.
    """
    raw = inflate(data) if is_deft(data) else data
    w, h, bpp, stride = struct.unpack_from("<IIIi", raw)
    if bpp not in (8, 16):
        raise ValueError(f"RIM: unsupported bpp {bpp}")
    dtype = "<u2" if bpp == 16 else "u1"
    step = abs(stride) // (bpp // 8)
    pix = np.frombuffer(raw, dtype=dtype, count=h * step, offset=16).reshape(h, step)[:, :w]
    if stride < 0:
        pix = pix[::-1]
    return rgb555_to_rgb(pix) if bpp == 16 else pix.copy()
