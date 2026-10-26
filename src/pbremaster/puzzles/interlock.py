"""Interlock (PUZZLE.TRI, CTrigramsObject).

"Use the seven pieces to cover the black triangles and complete the picture.
To select a piece, click it, and then move it where you want it to go. To rotate
a piece, right-click or click the Rotate button. To flip a piece, click the Flip
button." (HELP/PANDORA.M20, LANGENU 12900-12903)

Seven pieces made of equilateral triangles (data/iamonds.py) on a triangle grid.
The picture is centred in the play area with the solution's triangles blacked
out; a piece that covers exactly its own triangles sticks and shows its part of
the picture. Pieces are drawn in the puzzle's colour until placed.
**Interpretation:** the picture/black-triangle presentation, the grid origin at
the play area's corner and the button positions are not traced in code.
Sounds TRIGRAMS/TG_SELB.. (select), TG_ROTAT, TG_FLIP, TG_DROPI (in place), TG_DROPO.
"""
from __future__ import annotations

import math

import pygame

from ..data import tri
from .base import AREA, PuzzleGame, ToggleButton

ROOT3 = math.sqrt(3)


def board_down(x, y):
    """The board triangle at (x, y) points down when x + y is even (all solutions agree)."""
    return (x + y) % 2 == 0


class Piece:
    def __init__(self, start: tri.Placement, home: tri.Placement):
        self.home = home
        self.at = tri.Placement(start.type, start.flip, start.x, start.y, start.rotation)
        self.placed = False

    def cells(self):
        return self.at.cells()


class Interlock(PuzzleGame):
    SOUND_FOLDER = "TRIGRAMS"

    def __init__(self, app, puzzle):
        super().__init__(app, puzzle)
        name = next(f for f in puzzle.files if f.endswith(".TRI"))
        self.data = tri.parse(self.raw(name))
        stem = self.data.picture.rsplit(".", 1)[0].upper()
        jpg = next((f for f in puzzle.files if f.rsplit("/", 1)[1].rsplit(".", 1)[0] == stem),
                   next(f for f in puzzle.files if f.endswith(".JPG")))
        self.picture = self.app.assets.image(jpg).convert()
        self.pic_pos = (AREA.x + (AREA.w - self.picture.get_width()) // 2,
                        AREA.y + (AREA.h - self.picture.get_height()) // 2)
        self.background = self.png("TRIGRAMS/BACKGROUND.JPG")
        self.size = self.data.size
        self.rotate = ToggleButton(self, "TRIGRAMS", "ROTATE", (743, 409))
        self.flip = ToggleButton(self, "TRIGRAMS", "FLIP", (743, 467))
        self.buttons = [self.rotate, self.flip]
        self.holes = set().union(*(p.cells() for p in self.data.solution))
        self.restart()

    # -------------------------------------------------------------- geometry
    def tri_points(self, x, y, down):
        s, h = self.size, self.size * ROOT3 / 2
        x0, y0 = AREA.x + x * s / 2, AREA.y + y * h
        if down:
            return [(x0, y0), (x0 + s, y0), (x0 + s / 2, y0 + h)]
        return [(x0, y0 + h), (x0 + s / 2, y0), (x0 + s, y0 + h)]

    def piece_polys(self, pl: tri.Placement):
        w, h, down, rows = tri.SHAPES[pl.type][pl.rotation % 6][pl.flip & 1]
        out = []
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch == "#":
                    d = down ^ bool(i % 2) ^ bool(j % 2)
                    out.append(self.tri_points(pl.x + i, pl.y + j, d))
        return out

    def cell_at(self, pos):
        s, h = self.size, self.size * ROOT3 / 2
        r = int((pos[1] - AREA.y) // h)
        fx = (pos[0] - AREA.x) / (s / 2)
        for c in (int(fx) - 1, int(fx)):
            poly = self.tri_points(c, r, board_down(c, r))
            if _inside(pos, poly):
                return c, r
        return int(fx), r

    # ----------------------------------------------------------------- state
    def restart(self):
        self.pieces = [Piece(s, next(h for h in self.data.solution if h.type == s.type)) for s in self.data.start]
        self.held = None          # (piece, grab offset in cells)
        self.selected = None
        self.hint_mode = False
        self.check()

    def check(self):
        self.solved = all(p.placed for p in self.pieces)

    def piece_at(self, pos):
        for p in reversed(self.pieces):
            if not p.placed and any(_inside(pos, poly) for poly in self.piece_polys(p.at)):
                return p
        return None

    def try_place(self, p):
        if p.cells() == p.home.cells():
            p.placed = True
            p.at = tri.Placement(p.home.type, p.home.flip, p.home.x, p.home.y, p.home.rotation)
            if self.selected is p:
                self.selected = None
            self.sound("TG_DROPI")
            self.check()
            return True
        return False

    def snap(self, p, x, y):
        """Move so the piece sits on the lattice: its (0, 0) triangle must point the board's way."""
        if p.at.down != board_down(x, y):
            x += 1
        p.at.x, p.at.y = x, y

    # ----------------------------------------------------------------- input
    def mouse_down(self, pos):
        if self.paused or not AREA.collidepoint(pos):
            return False
        p = self.piece_at(pos)
        if self.hint_mode:
            if p is None:
                self.app.sounds.play(self.app.sounds.NO_CLICK)
                return True
            self.hint_mode = False
            p.at = tri.Placement(p.home.type, p.home.flip, p.home.x, p.home.y, p.home.rotation)
            self.try_place(p)
            self.hint_done = True
            return True
        if p is None:
            self.selected = None
            return True
        self.selected = p
        self.pieces.remove(p)
        self.pieces.append(p)                      # on top
        cx, cy = self.cell_at(pos)
        self.held = (p, (p.at.x - cx, p.at.y - cy))
        self.sound("TG_SELB")
        return True

    def mouse_move(self, pos):
        super().mouse_move(pos)
        if self.held:
            p, (ox, oy) = self.held
            cx, cy = self.cell_at(pos)
            self.snap(p, cx + ox, cy + oy)

    def mouse_up(self, pos):
        if super().mouse_up(pos):
            return True
        if not self.held:
            return False
        p, _ = self.held
        self.held = None
        if not self.try_place(p):
            self.sound("TG_DROPO")
        return True

    def right_click(self, pos):
        p = self.piece_at(pos) or self.selected
        if p:
            self.selected = p
            self.turn(p, rotate=True)

    def toggled(self, button):
        button.on = False
        if self.selected and not self.selected.placed:
            self.turn(self.selected, rotate=button is self.rotate)
        else:
            self.app.sounds.play(self.app.sounds.NO_CLICK)

    def turn(self, p, rotate):
        if rotate:
            p.at.rotation = (p.at.rotation + 1) % 6
            self.sound("TG_ROTAT")
        else:
            p.at.flip ^= 1
            self.sound("TG_FLIP")
        self.snap(p, p.at.x, p.at.y)
        self.try_place(p)

    def use_hint(self):
        if self.solved:
            return False
        self.hint_mode = True
        return True

    def complete(self):
        for p in self.pieces:
            if not p.placed:
                p.at = tri.Placement(p.home.type, p.home.flip, p.home.x, p.home.y, p.home.rotation)
                p.placed = True
        self.check()

    # --------------------------------------------------------------- drawing
    def draw(self, surf):
        if self.background:
            surf.blit(self.background, AREA)
        for b in self.buttons:
            b.draw(surf)
        if self.paused:
            return
        surf.blit(self.picture, self.pic_pos)
        placed = set().union(*(p.cells() for p in self.pieces if p.placed)) if any(p.placed for p in self.pieces) else set()
        for x, y in self.holes - placed:
            pygame.draw.polygon(surf, (0, 0, 0), self.tri_points(x, y, board_down(x, y)))
        colour = self.data.colour
        edge = tuple(max(0, c - 90) for c in colour)
        for p in self.pieces:
            if p.placed:
                continue
            for poly in self.piece_polys(p.at):
                pygame.draw.polygon(surf, colour, poly)
                pygame.draw.polygon(surf, edge, poly, 1)
            if p is self.selected:
                for poly in self.piece_polys(p.at):
                    pygame.draw.polygon(surf, (255, 236, 160), poly, 2)
        if self.hint_mode:
            text = self.app.strings.get(12950, "").replace("\r", " ")
            img = self.app.fonts.get(16).render(text, True, (248, 176, 100))
            surf.blit(img, img.get_rect(midbottom=(AREA.centerx, AREA.bottom - 4)))


def _inside(p, poly):
    (x1, y1), (x2, y2), (x3, y3) = poly
    x, y = p
    d1 = (x - x2) * (y1 - y2) - (x1 - x2) * (y - y2)
    d2 = (x - x3) * (y2 - y3) - (x2 - x3) * (y - y3)
    d3 = (x - x1) * (y3 - y1) - (x3 - x1) * (y - y1)
    neg = d1 < 0 or d2 < 0 or d3 < 0
    pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (neg and pos)
