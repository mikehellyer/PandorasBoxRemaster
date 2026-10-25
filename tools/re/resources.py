"""Dump string tables / resource directory of the Pandora's Box resource DLLs."""
import sys

import pefile


def walk(pe):
    for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        tname = str(t.name) if t.name else pefile.RESOURCE_TYPE.get(t.id, t.id)
        for n in t.directory.entries:
            for lang in n.directory.entries:
                d = lang.data.struct
                yield tname, (str(n.name) if n.name else n.id), pe.get_data(d.OffsetToData, d.Size)


def strings(pe):
    for tname, rid, data in walk(pe):
        if tname != "RT_STRING":
            continue
        pos = 0
        for i in range(16):
            ln = int.from_bytes(data[pos:pos + 2], "little")
            pos += 2
            if ln:
                yield (rid - 1) * 16 + i, data[pos:pos + ln * 2].decode("utf-16-le")
            pos += ln * 2


if __name__ == "__main__":
    pe = pefile.PE(sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2] == "list":
        for tname, rid, data in walk(pe):
            print(tname, rid, len(data))
    else:
        for sid, s in strings(pe):
            print(sid, repr(s))
