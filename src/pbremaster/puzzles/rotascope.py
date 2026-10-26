"""Rotascope (PUZZLE.RTT, CRotoscopeObject).

"Reassemble the picture by moving pieces in the disk. To move a piece to the
empty space next to it, click the piece. Only pieces next to the empty space can
move. In the solution, the center piece is always empty." (HELP/PANDORA.M20)

A circle cut from the picture into rings x sectors plus a centre disc. A piece
moves to the gap if it is next to it: the neighbouring sector of the same ring,
the same sector of the next ring in or out, or between the centre and any sector
of the innermost ring. A piece is drawn by mapping its home section of the
picture onto the section it occupies (rotated, stretched across rings), so it
only looks right at home. Hint (LANGENU 4312-4315): click a piece to put it home.
Sounds RTT/RO_SPIN (within a ring), RO_SB / RO_BS (out / in), RO_CLICK.
"""
from __future__ import annotations

import math

import numpy as np
import pygame

from ..data import rtt
from .base import AREA, PuzzleGame, ToggleButton

MOVE_TIME = 0.3
CENTRE = "centre"


class Shape:
    """An annular sector (r0..r1, a0..a1 degrees) or the centre disc (a0..a1 = 0..360)."""

    def __init__(self, r0, r1, a0, a1):
        self.r0, self.r1, self.a0, self.a1 = r0, r1, a0, a1

    @staticmethod
    def lerp(a, b, t):
        """In between two shapes: radii linearly, the start angle the short way round."""
        da = (b.a0 - a.a0 + 180) % 360 - 180
        span = (a.a1 - a.a0) + ((b.a1 - b.a0) - (a.a1 - a.a0)) * t
        a0 = a.a0 + da * t
        return Shape(a.r0 + (b.r0 - a.r0) * t, a.r1 + (b.r1 - a.r1) * t, a0, a0 + span)


class Rotascope(PuzzleGame):
    SOUND_FOLDER = "RTT"

    def __init__(self, app, puzzle):
        super().__init__(app, puzzle)
        name = next(f for f in puzzle.files if f.endswith(".RTT"))
        self.data = rtt.parse(self.raw(name))
        pic = self.image_from_bytes(self.data.jpeg)
        self.src = pygame.surfarray.array3d(pic).swapaxes(0, 1)          # (h, w, 3)
        h, w = self.src.shape[:2]
        self.src_centre = (w / 2, h / 2)
        outer = min(w, h) * 0.5 - 1
        if outer < 10 or outer > 250:
            outer = 250
        n = self.data.rings
        self.radii = [outer / self.data.ratio ** (n - k) for k in range(n + 1)]   # radii[0] = centre disc
        self.step = 360 / self.data.sectors
        self.background = self.png("RTT/312.PNG")
        self.anim = ToggleButton(self, "RTT", "ANIM", (743, 409), on=True)
        self.grid_btn = ToggleButton(self, "RTT", "GRID", (743, 467), on=True)
        self.buttons = [self.anim, self.grid_btn]
        self.centre = (AREA.centerx, AREA.centery)
        self.cache = {}
        self.hint_mode = False
        self.restart()

    # ------------------------------------------------------------ geometry
    def shape(self, pos):
        if pos == CENTRE:
            return Shape(0.0, self.radii[0], 0.0, 360.0)
        ring, sector = pos
        a0 = self.data.angle + sector * self.step
        return Shape(self.radii[ring], self.radii[ring + 1], a0, a0 + self.step)

    def positions(self):
        return [(r, s) for r in range(self.data.rings) for s in range(self.data.sectors)] + [CENTRE]

    def neighbours(self, pos):
        S, R = self.data.sectors, self.data.rings
        if pos == CENTRE:
            return [(0, s) for s in range(S)]
        r, s = pos
        out = [(r, (s - 1) % S), (r, (s + 1) % S)]
        out.append(CENTRE if r == 0 else (r - 1, s))
        if r + 1 < R:
            out.append((r + 1, s))
        return out

    def pos_at(self, point):
        dx, dy = point[0] - self.centre[0], self.centre[1] - point[1]
        rho = math.hypot(dx, dy)
        if rho < self.radii[0]:
            return CENTRE
        if rho >= self.radii[-1]:
            return None
        ring = next(k for k in range(self.data.rings) if rho < self.radii[k + 1])
        ang = (math.degrees(math.atan2(dy, dx)) - self.data.angle) % 360
        return ring, int(ang // self.step) % self.data.sectors

    # --------------------------------------------------------------- state
    def restart(self):
        self.at = dict(self.data.grid)            # position -> piece
        self.at[CENTRE] = self.data.centre
        self.moving = None                        # (piece, from shape, to shape)
        self.move_t = 0.0
        self.hint_mode = False
        self.check()

    def save_state(self):
        return {"at": [[list(pos) if isinstance(pos, tuple) else pos, list(pc) if isinstance(pc, tuple) else pc] for pos, pc in self.at.items()]}

    def load_state(self, state):
        from .base import tup
        self.at = {tup(pos): tup(pc) for pos, pc in state["at"]}
        self.check()

    def check(self):
        self.solved = self.at[CENTRE] == rtt.GAP and all(
            self.at[p] == p for p in self.positions() if p != CENTRE)

    def gap(self):
        return next(p for p, piece in self.at.items() if piece == rtt.GAP)

    def move(self, pos):
        g = self.gap()
        piece = self.at[pos]
        self.moving = (piece, self.shape(pos), self.shape(g))
        self.move_t = 0.0 if self.anim.on else MOVE_TIME
        self.at[g], self.at[pos] = piece, rtt.GAP
        if pos == CENTRE or g == CENTRE:
            self.sound("RO_BS" if g == CENTRE else "RO_SB")
        elif pos[0] != g[0]:
            self.sound("RO_SB" if g[0] > pos[0] else "RO_BS")
        else:
            self.sound("RO_SPIN")
        self.check()

    def mouse_down(self, point):
        if self.paused or (self.moving and self.move_t < MOVE_TIME):
            return False
        pos = self.pos_at(point)
        if pos is None:
            return False
        if self.hint_mode:
            return self.hint_at(pos)
        if self.at[pos] != rtt.GAP and self.gap() in self.neighbours(pos):
            self.move(pos)
        else:
            self.app.sounds.play(self.app.sounds.NO_CLICK)
        return True

    # Hints: the next click puts that piece home (LANGENU 4313-4315).
    def use_hint(self):
        if self.solved:
            return False
        self.hint_mode = True
        return True

    def hint_at(self, pos):
        piece = self.at[pos]
        if piece == rtt.GAP or piece == pos:
            self.app.sounds.play(self.app.sounds.NO_CLICK)
            return True
        self.hint_mode = False
        home = piece
        self.at[pos], self.at[home] = self.at[home], piece
        self.sound("RO_CLICK")
        self.hint_done = True
        self.check()
        return True

    def complete(self):
        self.at = {p: p for p in self.positions() if p != CENTRE}
        self.at[CENTRE] = rtt.GAP
        self.moving = None
        self.check()

    def update(self, dt):
        if self.moving:
            self.move_t += dt
            if self.move_t >= MOVE_TIME:
                self.moving = None

    # ------------------------------------------------------------- drawing
    def render(self, piece, target: Shape):
        """The piece's home section of the picture mapped onto `target`.
        Returns (surface, offset of its top-left from the disk centre)."""
        key = (piece, round(target.r0, 1), round(target.r1, 1), round(target.a0, 1), round(target.a1, 1))
        if key in self.cache:
            return self.cache[key]
        src = self.shape(piece)
        span = target.a1 - target.a0
        full = span >= 359.9
        if full:
            x0 = y0 = -int(target.r1) - 1
            x1 = y1 = int(target.r1) + 1
        else:                                   # bounding box of the annular sector
            angs = np.radians(np.append(np.linspace(target.a0, target.a1, 24),
                                        [a for a in (0, 90, 180, 270, 360, 450, 540, 630)
                                         if target.a0 <= a <= target.a1 or target.a0 <= a - 360 <= target.a1]))
            px = np.concatenate([target.r0 * np.cos(angs), target.r1 * np.cos(angs)])
            py = np.concatenate([-target.r0 * np.sin(angs), -target.r1 * np.sin(angs)])
            x0, x1 = int(np.floor(px.min())) - 1, int(np.ceil(px.max())) + 1
            y0, y1 = int(np.floor(py.min())) - 1, int(np.ceil(py.max())) + 1
        ys, xs = np.mgrid[y0:y1, x0:x1]
        rho = np.hypot(xs, ys)
        ang = np.degrees(np.arctan2(-ys, xs))
        v = ((ang - target.a0) % 360) / (360 if full else span)
        mask = (rho >= target.r0) & (rho < target.r1) & (v < 1.0)
        u = (rho - target.r0) / max(target.r1 - target.r0, 1e-6)
        srho = src.r0 + u * (src.r1 - src.r0)
        sang = np.radians(src.a0 + v * (src.a1 - src.a0))
        h, w = self.src.shape[:2]
        sx = np.clip((self.src_centre[0] + srho * np.cos(sang)).astype(int), 0, w - 1)
        sy = np.clip((self.src_centre[1] - srho * np.sin(sang)).astype(int), 0, h - 1)
        rgba = np.zeros(xs.shape + (4,), np.uint8)
        rgba[..., :3] = self.src[sy, sx]
        rgba[..., 3] = mask * 255
        surf = pygame.image.frombuffer(rgba.tobytes(), (xs.shape[1], xs.shape[0]), "RGBA").copy()
        if len(self.cache) > 400:
            self.cache.clear()
        self.cache[key] = (surf, (x0, y0))
        return self.cache[key]

    def blit(self, surf, piece, shape):
        img, (ox, oy) = self.render(piece, shape)
        surf.blit(img, (self.centre[0] + ox, self.centre[1] + oy))

    def draw(self, surf):
        if self.background:
            surf.blit(self.background, AREA)
        for b in self.buttons:
            b.draw(surf)
        if self.paused:
            return
        cx, cy = self.centre
        pygame.draw.circle(surf, (0, 0, 0), self.centre, int(self.radii[-1]) + 1)
        moving_piece = self.moving[0] if self.moving and self.move_t < MOVE_TIME else None
        for pos, piece in self.at.items():
            if piece == rtt.GAP or piece == moving_piece:
                continue
            self.blit(surf, piece, self.shape(pos))
        if moving_piece is not None:
            t = min(1.0, self.move_t / MOVE_TIME)
            self.blit(surf, moving_piece, Shape.lerp(self.moving[1], self.moving[2], t))
        if self.grid_btn.on and not self.solved:
            col = self.data.colour
            for r in self.radii:
                pygame.draw.circle(surf, col, self.centre, int(r), 1)
            for s in range(self.data.sectors):
                a = math.radians(self.data.angle + s * self.step)
                p0 = (cx + self.radii[0] * math.cos(a), cy - self.radii[0] * math.sin(a))
                p1 = (cx + self.radii[-1] * math.cos(a), cy - self.radii[-1] * math.sin(a))
                pygame.draw.line(surf, col, p0, p1, 1)
        if self.hint_mode:
            text = self.app.strings.get(4313, "").replace("\r", " ")
            img = self.app.fonts.get(16).render(text, True, (248, 176, 100))
            surf.blit(img, img.get_rect(midbottom=(AREA.centerx, AREA.bottom - 6)))
