"""Extract the command-id -> handler table registered into the map at 0x5d4100.

Buttons whose action type (SCREEN.DAT button +208) is 10 look their argument
(+212) up in this map. Registration code is a run of:
    mov [ebp - X], <id> ... call 0x443770 ... mov [eax + 0x10], <handler>
Reads extracted/re/pandora.asm (see notes) and prints "id handler".
"""
import re
import sys

asm = open(sys.argv[1] if len(sys.argv) > 1 else "extracted/re/pandora.asm").read().splitlines()
pending, table = None, []
for line in asm:
    m = re.match(r"([0-9a-f]{8})  mov    dword ptr \[ebp - 0x(18|28|20|30|3c)\], (0x[0-9a-f]+|\d+)$", line)
    if m:
        pending = int(m.group(3), 0)
        continue
    m = re.match(r"([0-9a-f]{8})  mov    dword ptr \[e[a-d]x \+ 0x10\], (0x[0-9a-f]+)", line)
    if m and pending is not None and int(m.group(1), 16) in range(0x442400, 0x444000):
        table.append((pending, int(m.group(2), 16)))
        pending = None
for cid, h in table:
    print(cid, hex(h))
