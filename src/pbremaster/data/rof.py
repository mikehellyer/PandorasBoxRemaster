"""Reader for Pandora's Box .ROF archives (PANDORA.ROF, SCREENS.ROF).

A ROF is a tree of directories. Every directory block is:

    u32 count          number of entries
    u32 names_size     bytes in the name table that follows the entries
    count x entry      5 x u32: offset, size, kind, name_len, name_off
    names              NUL-terminated names, name_off is relative to here

kind 1 is a sub-directory (offset points at its block, size is 0),
kind 0 is a file (offset/size locate its bytes in the archive).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

DIR = 1
FILE = 0


@dataclass(frozen=True)
class Entry:
    path: str          # upper-case, '/' separated, relative to the archive root
    offset: int
    size: int


class ROF:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._fh = open(self.path, "rb")
        self.files: dict[str, Entry] = {}
        self._walk(0, "")

    def _read(self, offset, size):
        self._fh.seek(offset)
        return self._fh.read(size)

    def _walk(self, offset, prefix):
        count, names_size = struct.unpack("<II", self._read(offset, 8))
        table = self._read(offset + 8, count * 20)
        names = self._read(offset + 8 + count * 20, names_size)
        for i in range(count):
            off, size, kind, name_len, name_off = struct.unpack_from("<5I", table, i * 20)
            name = names[name_off:name_off + name_len].rstrip(b"\0").decode("latin-1")
            full = f"{prefix}{name}".upper()
            if kind == DIR:
                self._walk(off, full + "/")
            elif kind == FILE:
                self.files[full] = Entry(full, off, size)
            else:
                raise ValueError(f"{self.path.name}: unknown entry kind {kind} for {full}")

    def __contains__(self, name):
        return name.upper().replace("\\", "/") in self.files

    def read(self, name: str) -> bytes:
        e = self.files[name.upper().replace("\\", "/")]
        return self._read(e.offset, e.size)

    def listdir(self, prefix: str = ""):
        prefix = prefix.upper().strip("/") + "/" if prefix else ""
        return sorted(p for p in self.files if p.startswith(prefix))

    def close(self):
        self._fh.close()
