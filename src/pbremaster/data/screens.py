"""SCREENS/SCREEN.DAT: the layout of every UI screen and its controls.

Decoded from the loader at 0x4fb7f0 in PANDORA.EUL (see notes/file-formats.md).

    u32 screen_count
    screen_count x Screen:
        u32 id, char background[32], char help_rtf[28], u32 n, u32 control_ids[n]
    u32 control_count
    control_count x Control:
        u32 kind, u32 id, i32 left, i32 top, i32 right, i32 bottom, kind-specific bytes

Image names say ".bmp" but the files are SCREENS/<NAME>.RIM. A right/bottom of 0
means "size from the image" (buttons) or "size from the text" (labels).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

BUTTON, PICTURE, LABEL, REGION, LIST, EDIT = 1, 2, 3, 4, 5, 6

# Button action types (button +208), from the jump table at 0x500838.
ACT_CLOSE = 1          # post WM_CLOSE to the screen
ACT_HELP = 2           # quick help for the screen
ACT_SCREEN = 3         # show screen <arg>
ACT_COMMAND = 10       # run the command registered for id <arg> (map at 0x5d4100)
ACT_QUIT = 12          # leave the game
ACT_NOTIFY = 14        # tell the screen this control was clicked
ACT_END_DIALOG = 15    # end a dialog with result <arg> (1 OK, 2 Cancel, 6 Yes, 7 No)

STYLE_PUSH, STYLE_TOGGLE, STYLE_RADIO = 1, 2, 3
_EXTRA = {BUTTON: 244, PICTURE: 32, LABEL: 48, REGION: 8, LIST: 44, EDIT: 44}


def _cstr(b: bytes) -> str:
    return b.split(b"\0", 1)[0].decode("latin-1")


@dataclass
class Screen:
    id: int
    background: str          # "100.bmp" -> SCREENS/100.RIM ("" for screens drawn by code)
    help_rtf: str
    control_ids: list[int]


@dataclass
class Control:
    kind: int
    id: int
    rect: tuple[int, int, int, int]      # left, top, right, bottom (right/bottom may be 0)

    @property
    def pos(self):
        return self.rect[0], self.rect[1]


@dataclass
class Button(Control):
    label_id: int = 0          # LANGENU string drawn on the button; 0 -> id's string is a hover caption
    images: list[str] = field(default_factory=list)   # up, down, up-hover, down-hover (or one 4-state strip)
    group: list[int] = field(default_factory=list)    # sibling ids of a radio group (puzzle type pickers)
    action: int = ACT_COMMAND  # ACT_* above
    arg: int = 0               # screen id, command id or dialog result
    style: int = STYLE_PUSH

    @property
    def strip(self) -> bool:
        """One image holding the four states side by side (names ending in 'b.bmp')."""
        return len(self.images) == 1


@dataclass
class Picture(Control):
    image: str = ""


@dataclass
class Label(Control):
    string_id: int = 0
    size: int = 12             # font height in pixels
    align: int = 0             # 0 left, 1 right, 2 centre (of rect, or around the point)
    f12: int = 0
    color: tuple[int, int, int] = (0, 0, 0)
    font: str = "Book Antiqua"


@dataclass
class Region(Control):
    origin: tuple[int, int] = (0, 0)   # text origin for code-drawn content


@dataclass
class Panel(Control):                   # LIST and EDIT share the layout
    image: str = ""
    inner: tuple[int, int, int, int] = (0, 0, 0, 0)


def _parse_control(kind, cid, rect, ex):
    if kind == BUTTON:
        names = [_cstr(ex[o:o + 28]) for o in (8, 36, 64, 92, 120)]
        group = [g for g in struct.unpack_from("<12i", ex, 148) if g]
        action, arg = struct.unpack_from("<ii", ex, 208)
        return Button(kind, cid, rect, label_id=struct.unpack_from("<i", ex, 0)[0],
                      images=[n for n in names if n], group=group, action=action, arg=arg,
                      style=struct.unpack_from("<i", ex, 240)[0])
    if kind == PICTURE:
        return Picture(kind, cid, rect, image=_cstr(ex[:28]))
    if kind == LABEL:
        sid, size, align, f12, colorref = struct.unpack_from("<5i", ex)
        rgb = (colorref & 0xFF, (colorref >> 8) & 0xFF, (colorref >> 16) & 0xFF)
        return Label(kind, cid, rect, string_id=sid, size=size, align=align, f12=f12,
                     color=rgb, font=_cstr(ex[20:48]))
    if kind == REGION:
        return Region(kind, cid, rect, origin=struct.unpack_from("<ii", ex))
    if kind in (LIST, EDIT):
        return Panel(kind, cid, rect, image=_cstr(ex[:28]), inner=struct.unpack_from("<4i", ex, 28))
    raise ValueError(f"SCREEN.DAT: unknown control kind {kind}")


@dataclass
class Layout:
    screens: dict[int, Screen]
    controls: dict[int, Control]

    def controls_of(self, screen_id: int) -> list[Control]:
        return [self.controls[c] for c in self.screens[screen_id].control_ids if c in self.controls]


def parse(data: bytes) -> Layout:
    (n,) = struct.unpack_from("<I", data)
    pos, screens = 4, {}
    for _ in range(n):
        sid = struct.unpack_from("<I", data, pos)[0]
        bg, rtf = _cstr(data[pos + 4:pos + 36]), _cstr(data[pos + 36:pos + 64])
        (cnt,) = struct.unpack_from("<I", data, pos + 64)
        ids = list(struct.unpack_from(f"<{cnt}I", data, pos + 68))
        screens[sid] = Screen(sid, bg, rtf, ids)
        pos += 68 + 4 * cnt
    (n,) = struct.unpack_from("<I", data, pos)
    pos += 4
    controls = {}
    for _ in range(n):
        kind, cid, *rect = struct.unpack_from("<6i", data, pos)
        ex = data[pos + 24:pos + 24 + _EXTRA[kind]]
        controls[cid] = _parse_control(kind, cid, tuple(rect), ex)
        pos += 24 + _EXTRA[kind]
    if pos != len(data):
        raise ValueError(f"SCREEN.DAT: {len(data) - pos} trailing bytes")
    return Layout(screens, controls)


def rim_name(bmp: str) -> str:
    """'103u.bmp' / '509b.rim' -> 'SCREENS/103U.RIM'."""
    return "SCREENS/" + bmp.rsplit(".", 1)[0].upper() + ".RIM"
