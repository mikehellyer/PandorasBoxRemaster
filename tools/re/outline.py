"""Outline functions of PANDORA.EUL from extracted/re/pandora.asm.

    python tools/re/outline.py func 0x41f400        # strings, string ids, calls of one function
    python tools/re/outline.py vtable 0x58c3cc 40   # methods of a class
    python tools/re/outline.py start 0x41f5a0       # find the function containing an address

String ids: `push N` right before `call 0x514130` (CString::LoadString(N, hinst)).
"""
import bisect
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pe import Image  # noqa: E402

ASM = "extracted/re/pandora.asm"
EUL = "../Pandoras_Box_Original/DATA/PANDORA.EUL"


def load():
    addrs, lines = [], []
    for line in open(ASM):
        addrs.append(int(line[:8], 16))
        lines.append(line.rstrip("\n"))
    return addrs, lines


def is_prologue(lines, i):
    return (lines[i][10:].startswith("push   -1") and "push   0x5" in lines[i + 1]
            and "fs:[0]" in lines[i + 2]) or (
        lines[i][10:].startswith("push   ebp") and "mov    ebp, esp" in lines[i + 1])


def start_of(addrs, lines, addr):
    i = bisect.bisect_right(addrs, addr) - 1
    while i > 0:
        if is_prologue(lines, i) and ("nop" in lines[i - 1] or "ret" in lines[i - 1] or "int3" in lines[i - 1]):
            return i
        i -= 1
    return 0


def outline(addrs, lines, addr):
    i = bisect.bisect_left(addrs, addr)
    pushes = []
    while i < len(lines):
        line = lines[i]
        a, rest = line[:8], line[10:]
        if rest.startswith("push"):
            pushes.append(rest[7:].split("   ;")[0])
        if "   ; '" in line:
            print(f"{a}  str  {line.split('   ; ', 1)[1]}")
        if rest.startswith("call"):
            tgt = rest[7:].split("   ;")[0]
            if tgt == "0x514130" and pushes:
                print(f"{a}  LoadString {pushes[-1]}")
            elif "!" in line:
                print(f"{a}  api  {line.split('; ', 1)[1]}")
            else:
                print(f"{a}  call {tgt}  args={pushes[-3:][::-1]}")
            pushes = []
        if rest.startswith("ret") and i + 1 < len(lines) and is_prologue(lines, i + 1) or (
                rest.startswith("ret") and "nop" in lines[i + 1] and is_prologue(lines, i + 2)):
            print(f"{a}  ret (end)")
            return
        i += 1


def main():
    cmd = sys.argv[1]
    if cmd == "vtable":
        img = Image(EUL)
        vt, n = int(sys.argv[2], 16), int(sys.argv[3]) if len(sys.argv) > 3 else 30
        for k in range(n):
            print(k, hex(img.u32(vt + 4 * k)))
        return
    addrs, lines = load()
    a = int(sys.argv[2], 16)
    if cmd == "start":
        print(lines[start_of(addrs, lines, a)])
    elif cmd == "func":
        outline(addrs, lines, a)


if __name__ == "__main__":
    main()
