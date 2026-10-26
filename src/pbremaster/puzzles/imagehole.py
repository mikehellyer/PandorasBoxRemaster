"""Image Hole (PUZZLE.IMH, CImageHoleObject).

"Match the shape of the hole to the correct part of the image underneath. Click
the selected hole again to lock it down. Holes may be bigger or smaller than the
shape they represent. If you try to lock a piece in the wrong place you receive a
strike." (LANGENU 2052-2057; three strikes restart the puzzle, 2002)

The picture is shown with each hole's place cut out in the puzzle's fill colour.
Holes are windows onto the picture that drift around the play area; click one to
select it, click the background to send it there, click it again to lock it. A
hole locks if its centre is over its place's centre (within LOCK_DISTANCE: the
original tolerance is not known). Controls (rects at 0x4a8f30): strike icon at
(737,348), strike holes at (740,404) with pegs at x 739/760/781, speed cycle
button (slow/medium/fast) at (748,429). Sounds IMG/IM_SEL, IM_MOVE, IM_RIGHT,
IM_X, IM_FAIL. Hole speed units are not known; SPEED_UNIT is a guess.
"""
from __future__ import annotations

import math

import numpy as np
import pygame

from ..data import imh
from .base import AREA, PuzzleGame, ToggleButton

LOCK_DISTANCE = 10
SPEED_UNIT = 6.0            # px per second per speed point at medium
SPEEDS = [("SLOW", 0.5), ("NORM", 1.0), ("FAST", 2.0)]
STRIKE_FRAMES = 9


class Hole:
    def __init__(self, data: imh.Hole, mask_rgb):
        self.data = data
        l, t, r, b = data.place
        region = mask_rgb[t:b, l:r]
        shape = np.all(region == np.array(data.key, np.uint8), axis=-1)
        surf = pygame.Surface((r - l, b - t), pygame.SRCALPHA)
        surf.fill((255, 255, 255, 0))
        alpha = pygame.surfarray.pixels_alpha(surf)
        alpha[:] = (shape.T * 255).astype(np.uint8)
        del alpha
        self.place_mask = surf                                   # unscaled, at its place
        w = max(1, round((r - l) * data.scale))
        h = max(1, round((b - t) * data.scale))
        self.mask = pygame.transform.smoothscale(surf, (w, h))
        self.hit = pygame.mask.from_surface(self.mask, 128)
        self.outline = self.hit.outline()
        self.size = (w, h)
        self.reset()

    def reset(self):
        self.x, self.y = map(float, self.data.start)
        dx, dy = self.data.direction
        n = math.hypot(dx, dy) or 1.0
        self.dir = (dx / n, dy / n)
        self.locked = self.data.locked
        self.target = None

    @property
    def centre(self):
        return self.x + self.size[0] / 2, self.y + self.size[1] / 2

    @property
    def home_centre(self):
        l, t, r, b = self.data.place
        return (l + r) / 2, (t + b) / 2

    def contains(self, p):
        x, y = int(p[0] - self.x), int(p[1] - self.y)
        return 0 <= x < self.size[0] and 0 <= y < self.size[1] and self.hit.get_at((x, y))


class ImageHole(PuzzleGame):
    SOUND_FOLDER = "IMG"

    def __init__(self, app, puzzle):
        super().__init__(app, puzzle)
        name = next(f for f in puzzle.files if f.endswith(".IMH"))
        self.data = imh.parse(self.raw(name))
        jpg = self.find(self.data.picture, (".JPG",))
        png = self.find(self.data.mask, (".PNG", ".BMP"))
        self.picture = self.app.assets.image(jpg).convert()
        mask = pygame.surfarray.array3d(self.app.assets.image(png).convert()).swapaxes(0, 1)
        self.holes = [Hole(h, mask) for h in self.data.holes]
        self.speed_index = 1
        self.speed_btn = ToggleButton(self, "IMG", "NORM", (748, 429))
        self.speed_imgs = {stem: ToggleButton(self, "IMG", stem, (748, 429)) for stem, _ in SPEEDS}
        self.buttons = [self.speed_btn]
        self.move_marker = self.strip("IMG/MOVE.PNG", 8)
        self.strike_anim = self.strip("IMG/STRIKE.PNG", STRIKE_FRAMES)
        self.strike_icon = self.keyed("IMG/STRIKE_ICON.PNG")
        self.strike_holes = self.keyed("IMG/STRIKE_HOLES.PNG")
        self.peg = self.keyed("IMG/STRIKE_PEG.PNG")
        self.restart()

    def find(self, stored_name, exts):
        """The file the IMH names (its extension may differ: the masks were BMPs)."""
        stem = stored_name.rsplit(".", 1)[0].upper()
        files = {f.rsplit("/", 1)[1].rsplit(".", 1)[0]: f for f in self.puzzle.files if f.endswith(exts)}
        if stem in files:
            return files[stem]
        return next(f for f in self.puzzle.files if f.endswith(exts) and "/PUZZLE." not in f)

    def keyed(self, name):
        img = self.png(name)
        if img is not None:
            img = img.copy()
            img.set_colorkey((0, 0, 255))
        return img

    def strip(self, name, n):
        img = self.keyed(name)
        if img is None:
            return []
        w = img.get_width() // n
        return [img.subsurface((i * w, 0, w, img.get_height())) for i in range(n)]

    # ---------------------------------------------------------------- state
    def restart(self):
        for h in self.holes:
            h.reset()
        self.selected = None
        self.strikes = 0
        self.strike_fx = None          # (x, y, seconds)
        self.marker_t = 0.0
        self.hint_mode = False
        self.rebuild()
        self.check()

    def save_state(self):
        return {"holes": [[h.x, h.y, list(h.dir), h.locked] for h in self.holes], "strikes": self.strikes}

    def load_state(self, state):
        for h, (x, y, d, locked) in zip(self.holes, state["holes"]):
            h.x, h.y, h.dir, h.locked = x, y, tuple(d), locked
        self.strikes = state.get("strikes", 0)
        self.rebuild()
        self.check()

    def rebuild(self):
        """The picture with the places of unlocked holes cut out."""
        board = self.picture.copy()
        fill = pygame.Surface(board.get_size(), pygame.SRCALPHA)
        for h in self.holes:
            if not h.locked:
                l, t, _, _ = h.data.place
                tinted = h.place_mask.copy()
                tinted.fill(self.data.fill + (255,), special_flags=pygame.BLEND_RGBA_MULT)
                fill.blit(tinted, (l, t))
        board.blit(fill, (0, 0))
        self.board = board

    def check(self):
        self.solved = all(h.locked for h in self.holes)

    def local(self, p):
        return p[0] - AREA.x, p[1] - AREA.y

    def hole_at(self, p):
        for h in reversed(self.holes):
            if not h.locked and h.contains(p):
                return h
        return None

    # ---------------------------------------------------------------- input
    def toggled(self, button):
        self.speed_index = (self.speed_index + 1) % len(SPEEDS)
        stem = SPEEDS[self.speed_index][0]
        self.speed_btn.images = self.speed_imgs[stem].images
        self.speed_btn.on = False

    def mouse_down(self, pos):
        if self.paused or not AREA.collidepoint(pos):
            return False
        p = self.local(pos)
        h = self.hole_at(p)
        if self.hint_mode:
            if h is None:
                self.app.sounds.play(self.app.sounds.NO_CLICK)
                return True
            self.hint_mode = False
            self.lock(h)
            self.hint_done = True
            return True
        if h is not None:
            if h is self.selected:
                self.try_lock(h)
            else:
                self.selected = h
                h.target = None
                self.sound("IM_SEL")
        elif self.selected is not None:
            self.selected.target = (p[0] - self.selected.size[0] / 2, p[1] - self.selected.size[1] / 2)
            self.marker_t = 0.0
            self.sound("IM_MOVE")
        return True

    def try_lock(self, h):
        hx, hy = h.centre
        tx, ty = h.home_centre
        if math.hypot(hx - tx, hy - ty) <= LOCK_DISTANCE:
            self.lock(h)
            self.sound("IM_RIGHT")
        else:
            self.strikes += 1
            self.strike_fx = (hx, hy, 0.0)
            self.sound("IM_X")
            if self.strikes >= 3:
                self.sound("IM_FAIL")
                self.app.message(self.app.strings.get(2002, ""), (1200,), lambda r: self.restart())

    def lock(self, h):
        l, t, r, b = h.data.place
        h.x, h.y = l + (r - l - h.size[0]) / 2, t + (b - t - h.size[1]) / 2
        h.locked = True
        h.target = None
        if self.selected is h:
            self.selected = None
        self.rebuild()
        self.check()

    def use_hint(self):
        if self.solved:
            return False
        self.hint_mode = True
        return True

    def complete(self):
        for h in self.holes:
            if not h.locked:
                self.lock(h)

    # --------------------------------------------------------------- motion
    def update(self, dt):
        if self.paused or self.solved:
            return
        mult = SPEEDS[self.speed_index][1]
        for h in self.holes:
            if h.locked:
                continue
            v = h.data.speed * SPEED_UNIT * mult
            if h is self.selected:
                if h.target is None:
                    continue                      # a selected hole waits for orders
                dx, dy = h.target[0] - h.x, h.target[1] - h.y
                dist = math.hypot(dx, dy)
                step = v * 1.5 * dt
                if dist <= step:
                    h.x, h.y = h.target
                    h.target = None
                else:
                    h.x += dx / dist * step
                    h.y += dy / dist * step
                continue
            h.x += h.dir[0] * v * dt
            h.y += h.dir[1] * v * dt
            w, ht = h.size
            if h.x < 0 or h.x + w > AREA.w:
                h.dir = (-h.dir[0], h.dir[1])
                h.x = min(max(h.x, 0), AREA.w - w)
            if h.y < 0 or h.y + ht > AREA.h:
                h.dir = (h.dir[0], -h.dir[1])
                h.y = min(max(h.y, 0), AREA.h - ht)
        self.marker_t += dt
        if self.strike_fx:
            x, y, t = self.strike_fx
            self.strike_fx = (x, y, t + dt) if t + dt < 0.6 else None

    # -------------------------------------------------------------- drawing
    def draw(self, surf):
        if self.paused:
            surf.fill((20, 8, 2), AREA)
        else:
            surf.blit(self.board, AREA)
        for b in self.buttons:
            b.draw(surf)
        if self.strike_icon:
            surf.blit(self.strike_icon, (737, 348))
        if self.strike_holes:
            surf.blit(self.strike_holes, (740, 404))
        if self.peg:
            for k in range(self.strikes):
                surf.blit(self.peg, ((739, 760, 781)[k], 404))
        if self.paused:
            return
        for h in self.holes:
            if h.locked:
                continue
            x, y = int(h.x), int(h.y)
            rect = pygame.Rect(x, y, *h.size).clip(pygame.Rect(0, 0, AREA.w, AREA.h))
            if rect.w <= 0 or rect.h <= 0:
                continue
            window = self.picture.subsurface(rect).copy().convert_alpha()
            window.blit(h.mask, (0, 0), area=pygame.Rect(rect.x - x, rect.y - y, rect.w, rect.h),
                        special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(window, (AREA.x + rect.x, AREA.y + rect.y))
            colour = (255, 255, 255) if h is self.selected else self.data.outline
            pts = [(AREA.x + x + px, AREA.y + y + py) for px, py in h.outline]
            if len(pts) > 2:
                pygame.draw.lines(surf, colour, True, pts, 2 if h is self.selected else 1)
        sel = self.selected
        if sel is not None and sel.target is not None and self.move_marker:
            frame = self.move_marker[int(self.marker_t * 12) % len(self.move_marker)]
            cx = AREA.x + sel.target[0] + sel.size[0] / 2
            cy = AREA.y + sel.target[1] + sel.size[1] / 2
            surf.blit(frame, frame.get_rect(center=(cx, cy)))
        if self.strike_fx and self.strike_anim:
            x, y, t = self.strike_fx
            frame = self.strike_anim[min(STRIKE_FRAMES - 1, int(t / 0.6 * STRIKE_FRAMES))]
            surf.blit(frame, frame.get_rect(center=(AREA.x + x, AREA.y + y)))
        if self.hint_mode:
            text = self.app.strings.get(2052, "").replace("\r", " ")
            img = self.app.fonts.get(16).render(text, True, (248, 176, 100))
            surf.blit(img, img.get_rect(midbottom=(AREA.centerx, AREA.bottom - 6)))
