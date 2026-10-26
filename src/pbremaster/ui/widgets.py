"""Screens and controls from SCREEN.DAT, drawn and driven like the original.

Rendering rules come from PANDORA.EUL:
  * button images: [up, down, up-hover, down-hover], or one strip of the four
    states side by side; pure blue is transparent unless an 'A' mask exists
  * button label (0x5017e2): Book Antiqua 16, centred, baseline at h/2 + 1,
    an orange (#F8B064) copy at +1,+1 under dark brown (#3F0F00) text;
    the whole label moves +1,+1 while the button is down
  * a button without a label shows its own string as a 14 px caption under it
    while hovered (0x5018a2)
  * every button plays MO.WAV on hover and CLICK.WAV on click (0x4ffcd5, 0x500186)
  * labels (0x4fea70): text baseline 5 px above the rect bottom; align 0 left,
    1 right, 2 centred; a rect without size is measured from the text, with the
    point as top-left (0), bottom-right (1) or centre (2)
"""
from __future__ import annotations

import pygame

from ..data import screens as sd

LABEL_FG = (63, 15, 0)
LABEL_SHADOW = (248, 176, 100)
CAPTION = (248, 176, 100)


class UI:
    """What widgets need from the app: assets, fonts, sounds and strings."""

    def __init__(self, assets, fonts, sounds, strings, layout):
        self.assets, self.fonts, self.sounds = assets, fonts, sounds
        self.strings, self.layout = strings, layout

    def text(self, sid: int) -> str:
        return self.strings.get(sid, "")

    def control_image(self, bmp: str):
        name = sd.rim_name(bmp)
        if not self.assets.has(name):
            return None
        return self.assets.image(name, colorkey=True)


class Widget:
    focusable = False

    def __init__(self, ui: UI, ctl: sd.Control, origin):
        self.ui, self.ctl = ui, ctl
        l, t, r, b = ctl.rect
        ox, oy = origin
        self.rect = pygame.Rect(l + ox, t + oy, max(r - l, 0), max(b - t, 0))
        self.visible = True
        self.enabled = True

    @property
    def id(self):
        return self.ctl.id

    def draw(self, surf):
        pass

    def draw_overlay(self, surf):
        """Drawn after every widget (hover captions)."""


class Button(Widget):
    def __init__(self, ui, ctl: sd.Button, origin):
        super().__init__(ui, ctl, origin)
        self.images = [ui.control_image(n) for n in ctl.images]
        self.frames = self._frames()
        if self.frames and not ctl.rect[2]:
            self.rect.size = self.frames[0].get_size()
        self.label = ui.text(ctl.label_id) if ctl.label_id else ""
        self.caption = "" if ctl.label_id else ui.text(ctl.id)
        self.hover = False
        self.pressed = False         # mouse held down on it
        self.on = False              # toggles and radio buttons

    def _frames(self):
        imgs = [i for i in self.images if i is not None]
        if not imgs:
            return []
        if self.ctl.strip:
            strip = imgs[0]
            w, h = strip.get_width() // 4, strip.get_height()
            return [strip.subsurface((i * w, 0, w, h)) for i in range(4)]
        return [i for i in self.images]

    def frame(self):
        down = self.on or (self.pressed and self.hover)
        idx = (1 if down else 0) + (2 if self.hover else 0)
        for i in (idx, idx & 1, 0):
            if i < len(self.frames) and self.frames[i] is not None:
                return self.frames[i]
        return None

    def draw(self, surf):
        if not self.visible:
            return
        img = self.frame()
        if img is not None:
            surf.blit(img, self.rect)
        if self.label:
            font = self.ui.fonts.get(16)
            down = self.on or (self.pressed and self.hover)
            x = self.rect.x + self.rect.w // 2 + (1 if down else 0)
            base = self.rect.y + self.rect.h // 2 + 1 + (1 if down else 0)
            for dx, colour in ((1, LABEL_SHADOW), (0, LABEL_FG)):
                txt = font.render(self.label, True, colour)
                surf.blit(txt, (x + dx - txt.get_width() // 2, base + dx - font.get_ascent()))

    def draw_overlay(self, surf):
        if self.visible and self.hover and self.caption:
            font = self.ui.fonts.get(14)
            txt = font.render(self.caption, True, CAPTION)
            x = self.rect.centerx - txt.get_width() // 2
            x = max(2, min(x, surf.get_width() - txt.get_width() - 2))
            surf.blit(txt, (x, self.rect.bottom + 3))


class Label(Widget):
    def __init__(self, ui, ctl: sd.Label, origin):
        super().__init__(ui, ctl, origin)
        self.font = ui.fonts.get(max(ctl.size, 6))
        self.colour = ctl.color
        self.set_text(ui.text(ctl.string_id) if ctl.string_id else "")

    def set_text(self, text: str):
        self.text = text
        ctl = self.ctl
        if ctl.rect[3] == 0:              # size from the text
            w, h = self.font.size(text or " ")
            x, y = self.rect.topleft
            if ctl.align == 1:
                x, y = x - w, y - h
            elif ctl.align == 2:
                x, y = x - w // 2, y - h // 2
            self._box = pygame.Rect(x, y, w, h)
        else:
            self._box = self.rect

    def draw(self, surf):
        if not (self.visible and self.text):
            return
        txt = self.font.render(self.text, True, self.colour)
        box = self._box
        base = box.bottom - 5
        if self.ctl.align == 1:
            x = box.right - txt.get_width()
        elif self.ctl.align == 2:
            x = box.centerx - txt.get_width() // 2
        else:
            x = box.x
        surf.blit(txt, (x, base - self.font.get_ascent()))


class Picture(Widget):
    def __init__(self, ui, ctl, origin):
        super().__init__(ui, ctl, origin)
        self.image = ui.control_image(ctl.image)
        if self.image is not None and not ctl.rect[2]:
            self.rect.size = self.image.get_size()

    def draw(self, surf):
        if self.visible and self.image is not None:
            surf.blit(self.image, self.rect)


class Panel(Picture):
    """List boxes and edit fields: a picture plus code-drawn content in `inner`."""

    def __init__(self, ui, ctl: sd.Panel, origin):
        super().__init__(ui, ctl, origin)
        l, t, r, b = ctl.inner
        self.inner = pygame.Rect(l + origin[0], t + origin[1], r - l, b - t)


class ListBox(Panel):
    ROW = 18
    FG = (248, 176, 100)
    SELECTED = (255, 236, 190)

    def __init__(self, ui, ctl, origin):
        super().__init__(ui, ctl, origin)
        self.items: list[str] = []
        self.selected = -1

    def draw(self, surf):
        super().draw(surf)
        font = self.ui.fonts.get(16)
        clip = surf.get_clip()
        surf.set_clip(self.inner)
        for i, item in enumerate(self.items):
            y = self.inner.y + 2 + i * self.ROW
            if i == self.selected:
                pygame.draw.rect(surf, (90, 40, 10), (self.inner.x, y, self.inner.w, self.ROW))
            surf.blit(font.render(item, True, self.SELECTED if i == self.selected else self.FG),
                      (self.inner.x + 4, y))
        surf.set_clip(clip)

    def index_at(self, pos):
        if not self.inner.collidepoint(pos):
            return -1
        i = (pos[1] - self.inner.y - 2) // self.ROW
        return i if 0 <= i < len(self.items) else -1


class EditBox(Panel):
    focusable = True
    FG = (248, 176, 100)
    MAX = 31

    def __init__(self, ui, ctl, origin):
        super().__init__(ui, ctl, origin)
        self.value = ""
        self.focused = False

    def key(self, ev):
        if ev.key == pygame.K_BACKSPACE:
            self.value = self.value[:-1]
        elif ev.unicode and ev.unicode.isprintable() and len(self.value) < self.MAX:
            self.value += ev.unicode

    def draw(self, surf):
        super().draw(surf)
        font = self.ui.fonts.get(16)
        txt = font.render(self.value, True, self.FG)
        y = self.inner.centery - font.get_height() // 2
        clip = surf.get_clip()
        surf.set_clip(self.inner)
        surf.blit(txt, (self.inner.x + 3, y))
        if self.focused and (pygame.time.get_ticks() // 500) % 2:
            cx = self.inner.x + 4 + txt.get_width()
            pygame.draw.line(surf, self.FG, (cx, y + 2), (cx, y + font.get_height() - 2))
        surf.set_clip(clip)


def make(ui, ctl, origin):
    cls = {sd.BUTTON: Button, sd.LABEL: Label, sd.PICTURE: Picture,
           sd.LIST: ListBox, sd.EDIT: EditBox}.get(ctl.kind, Widget)
    return cls(ui, ctl, origin)


class ScreenView:
    """One SCREEN.DAT screen. Dialog screens are centred over the screen below."""

    def __init__(self, ui: UI, screen_id: int, size=(800, 600), background: str | None = None,
                 controls=None):
        self.ui, self.id = ui, screen_id
        self.screen = ui.layout.screens.get(screen_id) or sd.Screen(screen_id, "", "", [])
        self.background = None
        self.scene = None            # optional code-drawn content (ui/campaign.py)
        bg = background or self.screen.background
        if bg and ui.assets.has(sd.rim_name(bg)):
            self.background = ui.assets.image(sd.rim_name(bg))
        bw, bh = self.background.get_size() if self.background else size
        self.dialog = (bw, bh) != tuple(size)
        self.origin = ((size[0] - bw) // 2, (size[1] - bh) // 2) if self.dialog else (0, 0)
        self.rect = pygame.Rect(self.origin, (bw, bh))
        if controls is None:
            controls = ui.layout.controls_of(screen_id)
        self.widgets = [make(ui, c, self.origin) for c in controls]
        self.by_id = {w.id: w for w in self.widgets}
        self.capture = None          # button holding the mouse
        self.focus = next((w for w in self.widgets if w.focusable), None)
        if self.focus:
            self.focus.focused = True

    def __getitem__(self, cid):
        return self.by_id[cid]

    def draw(self, surf):
        if self.background is not None:
            surf.blit(self.background, self.origin)
        if self.scene:
            self.scene.draw_back(surf)
        for w in self.widgets:
            w.draw(surf)
        if self.scene:
            self.scene.draw_front(surf)
        for w in self.widgets:
            w.draw_overlay(surf)

    def buttons(self):
        return [w for w in self.widgets if isinstance(w, Button) and w.visible and w.enabled]

    def button_at(self, pos):
        for w in reversed(self.buttons()):
            if w.rect.collidepoint(pos):
                return w
        return None

    def mouse_move(self, pos):
        for b in self.buttons():
            inside = b.rect.collidepoint(pos)
            if inside and not b.hover and (self.capture in (None, b)):
                self.ui.sounds.play(self.ui.sounds.MOUSE_OVER)
            b.hover = inside and self.capture in (None, b)

    def mouse_down(self, pos):
        """Returns ('list', widget, index) for list clicks, else None."""
        b = self.button_at(pos)
        if b:
            self.capture = b
            b.pressed = True
            self.ui.sounds.play(self.ui.sounds.CLICK)
            return None
        for w in self.widgets:
            if isinstance(w, ListBox) and w.rect.collidepoint(pos):
                return ("list", w, w.index_at(pos))
            if isinstance(w, EditBox) and w.rect.collidepoint(pos):
                self.set_focus(w)
        return None

    def mouse_up(self, pos):
        """Returns the button that was clicked (pressed and released on it), or None."""
        b, self.capture = self.capture, None
        if not b:
            return None
        b.pressed = False
        if not b.rect.collidepoint(pos):
            return None
        if b.ctl.style == sd.STYLE_TOGGLE:
            b.on = not b.on
        elif b.ctl.style == sd.STYLE_RADIO:
            self.select_radio(b.id)
        return b

    def select_radio(self, cid):
        b = self.by_id[cid]
        for sibling in b.ctl.group:
            if sibling in self.by_id:
                self.by_id[sibling].on = sibling == cid

    def set_focus(self, w):
        if self.focus:
            self.focus.focused = False
        self.focus = w
        w.focused = True
