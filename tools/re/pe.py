"""Helpers for studying the unprotected PANDORA.EUL build (a plain PE32).

    python tools/re/pe.py ORIG/DATA/PANDORA.EUL dis 0x401000 [count]
    python tools/re/pe.py ORIG/DATA/PANDORA.EUL xref-str "some text"
    python tools/re/pe.py ORIG/DATA/PANDORA.EUL imports
"""
import struct
import sys

import capstone
import pefile


class Image:
    def __init__(self, path):
        self.pe = pefile.PE(path)
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.mem = self.pe.get_memory_mapped_image()
        self.md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        self.imports = {}
        for entry in getattr(self.pe, "DIRECTORY_ENTRY_IMPORT", []):
            for imp in entry.imports:
                name = imp.name.decode() if imp.name else f"#{imp.ordinal}"
                self.imports[imp.address] = f"{entry.dll.decode()}!{name}"

    def u32(self, va):
        return struct.unpack_from("<I", self.mem, va - self.base)[0]

    def cstr(self, va):
        off = va - self.base
        end = self.mem.index(b"\0", off)
        return self.mem[off:end].decode("latin-1")

    def text(self):
        s = self.pe.sections[0]
        return self.base + s.VirtualAddress, s.Misc_VirtualSize

    def dis(self, va, count=40):
        off = va - self.base
        out = []
        for ins in self.md.disasm(self.mem[off:off + count * 15], va):
            out.append(f"{ins.address:08x}  {ins.mnemonic:6} {ins.op_str}{self.note(ins)}")
            count -= 1
            if not count:
                break
        return "\n".join(out)

    def note(self, ins):
        import re
        for m in re.findall(r"0x[0-9a-f]{6,8}", ins.op_str):
            v = int(m, 16)
            if v in self.imports:
                return f"   ; {self.imports[v]}"
            if self.base <= v < self.base + len(self.mem):
                try:
                    s = self.cstr(v)
                    if len(s) >= 3 and s.isprintable():
                        return f"   ; {s!r}"
                except ValueError:
                    pass
        return ""

    def find_bytes(self, needle):
        hits, i = [], self.mem.find(needle)
        while i >= 0:
            hits.append(self.base + i)
            i = self.mem.find(needle, i + 1)
        return hits

    def xrefs(self, va):
        """Instructions in .text that mention the 32-bit value `va`."""
        return self.find_bytes(struct.pack("<I", va))


def main():
    img = Image(sys.argv[1])
    cmd = sys.argv[2]
    if cmd == "dis":
        print(img.dis(int(sys.argv[3], 16), int(sys.argv[4]) if len(sys.argv) > 4 else 40))
    elif cmd == "imports":
        for a, n in sorted(img.imports.items()):
            print(f"{a:08x} {n}")
    elif cmd == "xref-str":
        for s in img.find_bytes(sys.argv[3].encode() + b"\0"):
            print(f"string @ {s:08x}:", ", ".join(f"{x:08x}" for x in img.xrefs(s)))
    elif cmd == "xref":
        print(", ".join(f"{x:08x}" for x in img.xrefs(int(sys.argv[3], 16))))


if __name__ == "__main__":
    main()
