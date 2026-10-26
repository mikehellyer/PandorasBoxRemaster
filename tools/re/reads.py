"""Summarise a Serialize/Load method of PANDORA.EUL as its sequence of stream reads.

The game's stream class reads with `call [vtbl+4](dst, size)` (or the twin
`[vtbl+0x34]` path for another stream mode); every read is emitted twice.
This walks the function in address order (stopping at `ret`), and prints
one line per read plus every other call (until the ret before
nop/int3 padding), so a record layout can be read off.

    python tools/re/reads.py PANDORA.EUL 0x4fb590
"""
import re
import sys

from pe import Image


def summarise(img, start, limit=3000):
    off = start - img.base
    pushes, lea = [], {}
    last_read_pc = None
    for ins in img.md.disasm(img.mem[off:off + limit * 8], start):
        m, op = ins.mnemonic, ins.op_str
        if m == "lea":
            reg, src = op.split(", ", 1)
            lea[reg] = src
        if m == "push":
            pushes.append(lea.get(op, op))
        elif m == "call":
            if re.fullmatch(r"dword ptr \[e\w\w \+ 0x34\]", op):
                pushes = []
                continue           # twin path, the [+4] call follows
            if re.fullmatch(r"dword ptr \[e\w\w \+ 4\]", op) and len(pushes) >= 2:
                size, dst = pushes[-1], pushes[-2]
                print(f"{ins.address:08x}  READ {int(size, 0) if size.startswith('0x') or size.isdigit() else size:>5}  -> {dst}")
            else:
                print(f"{ins.address:08x}  call {op}{img.note(ins)}   args={pushes[-3:][::-1]}")
            pushes = []
        elif m in ("cmp", "test") or m.startswith("j") and m != "jmp":
            pass
        if m == "ret":
            print(f"{ins.address:08x}  ret")
            nxt = img.mem[ins.address + ins.size - img.base]
            if nxt in (0x90, 0xCC):        # MSVC pads between functions
                break


if __name__ == "__main__":
    summarise(Image(sys.argv[1]), int(sys.argv[2], 16))
