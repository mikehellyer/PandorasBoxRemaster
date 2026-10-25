"""String tables from the language resource DLLs (LANGENU, PUZENU, NAMEENU, STATENU)."""
from __future__ import annotations

from pathlib import Path

import pefile

RT_STRING = 6


def load_strings(path: str | Path) -> dict[int, str]:
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories([pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    out: dict[int, str] = {}
    for t in getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None).entries:
        if t.id != RT_STRING:
            continue
        for block in t.directory.entries:
            for lang in block.directory.entries:
                d = lang.data.struct
                data = pe.get_data(d.OffsetToData, d.Size)
                pos = 0
                for i in range(16):
                    n = int.from_bytes(data[pos:pos + 2], "little")
                    pos += 2
                    if n:
                        out[(block.id - 1) * 16 + i] = data[pos:pos + n * 2].decode("utf-16-le")
                    pos += n * 2
    pe.close()
    return out
