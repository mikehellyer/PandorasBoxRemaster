"""Focus Point (PUZZLE.ZOO, class CFocalPointObject).

"Reassemble the picture. Click two pieces to make them switch places. Some pieces
look right in a small space, but distorted in a big space." (HELP/PANDORA.M20)

The board is a fixed set of rectangles; every piece is drawn stretched into the
rectangle it occupies. Clicking one piece selects it, clicking another swaps them.
A piece that reaches its own rectangle locks in place. The start position is
the scrambled layout stored in the file. Buttons (0x4a12e9): animation at
(743, 409) and outlines at (743, 467), art in FPN/ANIM_*.PNG and FPN/GRID_*.PNG.
Sounds: FPN/FP_SEL, FP_DESEL, FP_MOVE, FP_LOCK, FP_MO.
"""
from __future__ import annotations

import pygame

from ..data import zoo
from .base import AREA, PuzzleGame, ToggleButton

SWAP_TIME = 0.35
OUTLINE = (20, 8, 2)
SELECT = (255, 236, 160)


class FocusPoint(PuzzleGame):
    SOUND_FOLDER = "FPN"

    def __init__(self, app, puzzle):
        super().__init__(app, puzzle)
        name = next(f for f in puzzle.files if f.endswith(".ZOO"))
        self.data = zoo.parse(self.raw(name))
        self.picture = self.image_from_bytes(self.data.jpeg)
        self.background = self.png("FPN/312.PNG")
        w, h = self.data.width, self.data.height
        # Boards are centred in the play area (all but two files store exactly that).
        self.origin = (AREA.x + (AREA.w - w) // 2, AREA.y + (AREA.h - h) // 2)
        self.anim = ToggleButton(self, "FPN", "ANIM", (743, 409), on=True)
        self.grid = ToggleButton(self, "FPN", "GRID", (743, 467), on=True)
        self.buttons = [self.anim, self.grid]
        self.cache = {}
        self.restart()

    # ------------------------------------------------------------------ state
    def restart(self):
        self.where = list(self.data.slots)            # piece i is drawn in rect where[i]
        self.locked = [self.where[i] == self.data.homes[i] for i in range(len(self.where))]
        self.selected = None
        self.hover = None
        self.moving = []                              # (piece, from, to)
        self.move_t = 0.0
        self.solved = all(self.locked)

    def save_state(self):
        return {"where": [list(r) for r in self.where]}

    def load_state(self, state):
        from .base import tup
        self.where = [tup(r) for r in state["where"]]
        self.locked = [self.where[i] == self.data.homes[i] for i in range(len(self.where))]
        self.solved = all(self.locked)

    def piece_at(self, pos):
        x, y = pos[0] - self.origin[0], pos[1] - self.origin[1]
        for i, (rx, ry, rw, rh) in enumerate(self.where):
            if rx <= x < rx + rw and ry <= y < ry + rh:
                return i
        return None

    def swap(self, a, b):
        self.moving = [(a, self.where[a], self.where[b]), (b, self.where[b], self.where[a])]
        self.move_t = 0.0 if self.anim.on else SWAP_TIME
        self.where[a], self.where[b] = self.where[b], self.where[a]
        self.sound("FP_MOVE")
        locked_now = False
        for i in (a, b):
            if not self.locked[i] and self.where[i] == self.data.homes[i]:
                self.locked[i] = True
                locked_now = True
        if locked_now:
            self.sound("FP_LOCK")
        if all(self.locked):
            self.solved = True

    # ----------------------------------------------------------------- input
    def mouse_move(self, pos):
        super().mouse_move(pos)
        i = self.piece_at(pos)
        if i is not None and self.locked[i]:
            i = None
        if i != self.hover and i is not None:
            self.sound("FP_MO")
        self.hover = i

    def mouse_down(self, pos):
        if self.paused or self.moving and self.move_t < SWAP_TIME:
            return False
        i = self.piece_at(pos)
        if i is None:
            return False
        if self.hint_mode:                      # LANGENU 3318: click the piece to place
            if self.locked[i]:
                self.app.sounds.play(self.app.sounds.NO_CLICK)
                return True
            self.hint_mode = False
            self.selected = None
            self.swap(i, self.where.index(self.data.homes[i]))
            self.hint_done = True
            return True
        if self.locked[i]:
            self.app.sounds.play(self.app.sounds.NO_CLICK)
        elif self.selected is None:
            self.selected = i
            self.sound("FP_SEL")
        elif self.selected == i:
            self.selected = None
            self.sound("FP_DESEL")
        else:
            a, self.selected = self.selected, None
            self.swap(a, i)
        return True

    def use_hint(self):
        if self.solved:
            return False
        self.hint_mode = True
        self.selected = None
        return True

    def complete(self):
        self.where = list(self.data.homes)
        self.locked = [True] * len(self.where)
        self.selected = None
        self.solved = True

    # --------------------------------------------------------------- drawing
    def update(self, dt):
        if self.moving:
            self.move_t += dt
            if self.move_t >= SWAP_TIME:
                self.moving = []

    def tile(self, i, size):
        key = (i, size)
        if key not in self.cache:
            src = self.picture.subsurface(pygame.Rect(self.data.homes[i]).clip(self.picture.get_rect()))
            self.cache[key] = pygame.transform.smoothscale(src, size) if src.get_size() != size else src
        return self.cache[key]

    def draw(self, surf):
        if self.background:
            surf.blit(self.background, AREA)
        for b in self.buttons:
            b.draw(surf)
        if self.paused:
            return
        ox, oy = self.origin
        moving = {m[0]: m for m in self.moving}
        t = min(1.0, self.move_t / SWAP_TIME) if self.moving else 1.0
        order = [i for i in range(len(self.where)) if i not in moving] + list(moving)
        for i in order:
            if i in moving:
                _, (ax, ay, aw, ah), (bx, by, bw, bh) = moving[i]
                rect = (ax + (bx - ax) * t, ay + (by - ay) * t, aw + (bw - aw) * t, ah + (bh - ah) * t)
            else:
                rect = self.where[i]
            r = pygame.Rect(round(rect[0]) + ox, round(rect[1]) + oy, max(1, round(rect[2])), max(1, round(rect[3])))
            surf.blit(self.tile(i, r.size), r)
            if self.grid.on and not self.solved:
                pygame.draw.rect(surf, OUTLINE, r, 1)
        if self.selected is not None and not self.moving:
            r = pygame.Rect(self.where[self.selected]).move(ox, oy)
            pygame.draw.rect(surf, SELECT, r, 2)
        elif self.hover is not None and not self.moving:
            r = pygame.Rect(self.where[self.hover]).move(ox, oy)
            pygame.draw.rect(surf, (200, 150, 90), r, 1)
        if self.hint_mode:
            text = self.app.strings.get(3318, "").replace("\r", " ")
            img = self.app.fonts.get(16).render(text, True, (248, 176, 100))
            surf.blit(img, img.get_rect(midbottom=(AREA.centerx, AREA.bottom - 6)))
