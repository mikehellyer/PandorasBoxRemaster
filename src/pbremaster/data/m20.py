"""HELP/PANDORA.M20: the quick-help topics (a MediaView 2.0 title).

The game's own viewer (0x5075d0) opens it at the topic named by the screen's help
field in SCREEN.DAT ("mainqh.rtf", "bumpy.rtf", ...).

    u32 magic 0x01045F3F, u32 directory offset, ...
    directory (a one-leaf B-tree): from offset + 0x3C, entries until a 0 byte:
        u8 n, name[n], varint offset, varint size, u8 flags
    (varint: 7 bits per byte, low first, high bit = more)
Internal files: |CONTEXT |FONT |MVCHARTAB |Phrases |SUBTOPICS |SYSTEM |TTLBTREE, the
images free.bmp / hintsmll.bmp, and one file per topic named ">%08X" % hash(name),
where hash is WinHelp's context hash: h = h * 43 + value(c), value = 0-9 for digits,
0x11.. for letters (either case). 16 topics, one per help name in SCREEN.DAT except
the two cut puzzles (Chiseler, sheet).
A topic is formatting records each ending in 0xFF, a short header, then the text:
NUL-separated runs (each NUL is a change of format; an empty run ends a paragraph),
U+00B7 starting a bullet. The text is stored uncompressed.
"""
from __future__ import annotations

import re
import struct

MAGIC = 0x01045F3F


def _varint(data, p):
    value = shift = 0
    while True:
        c = data[p]
        p += 1
        value |= (c & 0x7F) << shift
        shift += 7
        if not c & 0x80:
            return value, p


def directory(data: bytes) -> dict[str, tuple[int, int]]:
    magic, start = struct.unpack_from("<II", data)
    if magic != MAGIC:
        raise ValueError("not a MediaView 2.0 file")
    files, p = {}, start + 0x3C
    while data[p]:
        n = data[p]
        name = data[p + 1:p + 1 + n].decode("latin-1")
        off, p = _varint(data, p + 1 + n)
        size, p = _varint(data, p)
        files[name] = (off, size)
        p += 1
    return files


def context_hash(name: str) -> int:
    h = 0
    for c in name:
        if c.isdigit():
            v = ord(c) - ord("0")
        elif c.isalpha():
            v = ord(c.upper()) - ord("A") + 0x11
        else:
            v = 0
        h = (h * 43 + v) & 0xFFFFFFFF
    return h


def topic(data: bytes, name: str) -> list[str] | None:
    """Paragraphs of a topic ("mainqh.rtf" or "mainqh"); the first is its title.
    Bullet paragraphs start with '• '. None if the title has no such topic."""
    stem = name.rsplit(".", 1)[0]
    entry = directory(data).get(">%08X" % context_hash(stem))
    if entry is None:
        return None
    off, size = entry
    t = data[off:off + size]
    m = re.compile(rb"[\x20-\x7e\x80-\xfe]{3,}").search(t, t.rfind(b"\xff") + 1)
    if not m:
        return []
    paragraphs, current = [], ""
    for run in t[m.start():].split(b"\0"):
        text = run.decode("cp1252", "replace").replace("\r", " ").replace("\n", " ")
        text = "".join(c for c in text if c >= " ")
        if text.strip() == "·":
            if current.strip():
                paragraphs.append(current.strip())
            current = "• "
        elif text:
            current += text
        elif current.strip() and current.strip() != "•":
            paragraphs.append(current.strip())
            current = ""
    if current.strip() and current.strip() != "•":
        paragraphs.append(current.strip())
    return paragraphs
