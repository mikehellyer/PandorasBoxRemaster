"""High-resolution text (ours): text is drawn again at the window's resolution.

Everything is drawn into the 800x600 canvas, so text scaled up with the art comes out soft
(smooth scaling) or blocky (sharp scaling). Fonts.get hands out HiFonts, whose render()
remembers what each text surface says; the canvas (a TextCanvas) notes every such
surface blitted straight onto it, with the pixels before and after.

When the frame is shown, peel() works backwards through those notes. A text whose pixels
are still exactly as it left them is taken out again (the pixels from before it go
back) and handed to the display, which draws it at the window's scale over the scaled
canvas, in the original order. Text that anything else later drew over (a dialog, a
dragged piece, a dimmed overlay) stays as it is in the canvas, so nothing can show
through. Text rendered onto another surface first, or drawn rotated or scaled, keeps
the canvas's resolution.
"""
from __future__ import annotations

import weakref
from dataclasses import dataclass

import pygame

MAX_NOTES = 2000            # per frame; a canvas that's never shown (tests) stops noting


@dataclass(frozen=True)
class TextInfo:
    fonts: object               # the Fonts that made it, for the same face at another size
    size: int
    bold: bool
    italic: bool
    underline: bool
    text: str
    antialias: bool
    colour: tuple
    background: tuple | None


_texts: "weakref.WeakKeyDictionary[pygame.Surface, TextInfo]" = weakref.WeakKeyDictionary()


def colour_tuple(c):
    return None if c is None else tuple(pygame.Color(c))


class HiFont(pygame.font.Font):
    def __init__(self, fonts, path, size, bold=False):
        super().__init__(path, size)
        self.fonts, self.em = fonts, size
        self.bold = bold

    def render(self, text, antialias, color, bgcolor=None, wraplength=0):
        surf = super().render(text, antialias, color, bgcolor, wraplength)
        if text and not wraplength and "\n" not in text:
            _texts[surf] = TextInfo(self.fonts, self.em, self.bold, self.italic, self.underline,
                                    text, bool(antialias), colour_tuple(color), colour_tuple(bgcolor))
        return surf

    def render_plain(self, info: TextInfo):
        old = self.italic, self.underline
        self.italic, self.underline = info.italic, info.underline
        try:
            return pygame.font.Font.render(self, info.text, info.antialias, info.colour, info.background)
        finally:
            self.italic, self.underline = old


@dataclass
class Note:
    info: TextInfo
    rect: pygame.Rect           # where the whole text went on the canvas
    shown: pygame.Rect          # the part inside the clip
    before: pygame.Surface      # the canvas there before it
    after: bytes                # ... and after


class TextCanvas(pygame.Surface):
    """The 800x600 canvas, noting the text blitted onto it this frame."""

    def __init__(self, size):
        super().__init__(size)
        self.notes: list[Note] = []

    def begin(self):
        self.notes.clear()

    def blit(self, source, dest, area=None, special_flags=0):
        info = _texts.get(source) if area is None and not special_flags else None
        if info is None or len(self.notes) >= MAX_NOTES:
            return super().blit(source, dest, area, special_flags)
        at = dest.topleft if isinstance(dest, pygame.Rect) else (int(dest[0]), int(dest[1]))
        rect = pygame.Rect(at, source.get_size())
        shown = rect.clip(self.get_clip())
        if not shown:
            return super().blit(source, dest)
        before = self.subsurface(shown).copy()
        done = super().blit(source, dest)
        self.notes.append(Note(info, rect, shown, before, pygame.image.tobytes(self.subsurface(shown), "RGB")))
        return done

    def peel(self):
        """A copy of the canvas without the text that can be redrawn sharply, and that text
        as (info, whole rect, shown part) in drawing order."""
        out = self.copy()
        lifted = []
        for n in reversed(self.notes):
            if pygame.image.tobytes(out.subsurface(n.shown), "RGB") == n.after:
                out.blit(n.before, n.shown)
                lifted.append((n.info, n.rect, n.shown))
        lifted.reverse()
        return out, lifted


def render_scaled(info: TextInfo, scale: float) -> pygame.Surface:
    font = info.fonts.get(max(1, round(info.size * scale)), info.bold)
    return font.render_plain(info)


def place(img_size, rect: pygame.Rect, shown: pygame.Rect, d: pygame.Rect, scale: float):
    """Where the high-resolution image goes in the window: centred on the scaled text box,
    cut to the scaled clip. Returns (destination, source rect in the image) or None."""
    box = pygame.Rect(round(d.x + rect.x * scale), round(d.y + rect.y * scale),
                      round(rect.w * scale), round(rect.h * scale))
    dest = pygame.Rect((0, 0), img_size)
    dest.center = box.center
    if shown != rect:
        clip = pygame.Rect(round(d.x + shown.x * scale), round(d.y + shown.y * scale),
                           round(shown.w * scale), round(shown.h * scale))
        visible = dest.clip(clip)
        if not visible:
            return None
        return visible, visible.move(-dest.x, -dest.y)
    return dest, pygame.Rect((0, 0), img_size)
