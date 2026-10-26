"""Jesse's Strips (PUZZLE.JES, CJesseStripsObject / CTStrip / CTray).

"Use storage trays to help organize pieces in this version of a jigsaw puzzle.
Select a piece (SHIFT, or drag the pointer over several, for more), drag it; drag it onto a numbered tab to move
it to that tray; right-click (or the button) rotates; click a tab or press 1-5
to switch trays." (HELP/PANDORA.M20, tutorial LANGENU 8007-8015)

The board - the picture at the puzzle's board offset on the tray grid, with its
given cells showing - is shown on every tray; each tray holds its own loose strips.
A strip dropped onto its own place in the right orientation sticks. Strips that
are in no tray start in place. The board drawn on every tray, tray tints, the
snap rule and the tab hold time are interpretations (see notes/game-logic.md).
Sounds JES/JS_SEL, JS_DESEL, JS_DROP, JS_RIGHT, JS_NO, JS_TAB, JS_ROTAT, JS_MO.
"""
from __future__ import annotations

import pygame

from ..data import jes
from .base import AREA, PuzzleGame, ToggleButton

TRAY = pygame.Rect(AREA.x + 33, AREA.y + 39, 580, 484)      # inside JES/BACKGROUND.PNG
TABS = [pygame.Rect(AREA.x + 52 + 80 * k, AREA.y + 6, 68, 34) for k in range(5)]
TINTS = [(150, 150, 150), (200, 60, 60), (90, 150, 60), (70, 90, 220), (160, 70, 170)]
TAB_HOLD = 0.6          # seconds a dragged strip waits over a tab before the tray switches


class Piece:
    def __init__(self, n, strip: jes.Strip, tray):
        self.n, self.strip = n, strip
        self.tray = tray                  # 0-4, or None when placed on the board
        self.cell = strip.start
        self.turns = (strip.start_dir - strip.home_dir) % 4

    @property
    def placed(self):
        return self.tray is None

    def footprint(self):
        vertical = (self.strip.home_dir == 1) == (self.turns % 2 == 0)
        x, y = self.cell
        n = self.strip.length
        return (x, y, 1, n) if vertical else (x, y, n, 1)


class JessesStrips(PuzzleGame):
    SOUND_FOLDER = "JES"

    def __init__(self, app, puzzle):
        super().__init__(app, puzzle)
        name = next(f for f in puzzle.files if f.endswith(".JES"))
        self.data = jes.parse(self.raw(name))
        stem = self.data.picture.rsplit(".", 1)[0].upper()
        jpg = next((f for f in puzzle.files if f.rsplit("/", 1)[1].rsplit(".", 1)[0] == stem),
                   next(f for f in puzzle.files if f.endswith(".JPG")))
        self.picture = self.app.assets.image(jpg).convert()
        self.background = self.png("JES/BACKGROUND.PNG")
        self.tab_art = [self.keyed(f"JES/TAB{k + 1}.PNG") for k in range(5)]
        self.rotate = ToggleButton(self, "JES", "ROTATE", (743, 409))
        self.buttons = [self.rotate]
        c = self.data.cell
        self.origin = (TRAY.x + (TRAY.w - self.data.cols * c) // 2, TRAY.y + (TRAY.h - self.data.rows * c) // 2)
        self.cache = {}
        self.restart()

    def keyed(self, name):
        img = self.png(name)
        if img is not None:
            img = img.copy()
            img.set_colorkey((0, 0, 255))
        return img

    # ----------------------------------------------------------------- state
    def restart(self):
        on_tray = {n: t for t, ids in enumerate(self.data.trays) for n in ids}
        self.pieces = []
        for n, s in enumerate(self.data.strips):
            p = Piece(n, s, on_tray.get(n))
            if p.placed:
                p.cell, p.turns = s.home, 0
            self.pieces.append(p)
        # Open on the last tray with strips: the tutorial says "...then return to tray 5", and
        # every campaign puzzle leaves tray 1 empty for sorting.
        self.tray = max((t for t, ids in enumerate(self.data.trays) if ids), default=0)
        self.selected: list[Piece] = []
        self.drag = None            # (grab cell offset per piece, mouse start cell)
        self.tab_hover = None
        self.band = None            # drag-select: (start, current, shift held)
        self.hint_mode = False
        self.check()

    def save_state(self):
        return {"tray": self.tray, "pieces": [[p.tray, list(p.cell), p.turns] for p in self.pieces]}

    def load_state(self, state):
        for p, (tray, cell, turns) in zip(self.pieces, state["pieces"]):
            p.tray, p.cell, p.turns = tray, tuple(cell), turns
        self.tray = state.get("tray", self.tray)
        self.check()

    def check(self):
        self.solved = all(p.placed for p in self.pieces)

    def cell_at(self, pos):
        c = self.data.cell
        return (pos[0] - self.origin[0]) // c, (pos[1] - self.origin[1]) // c

    def loose(self):
        return [p for p in self.pieces if p.tray == self.tray]

    def piece_at(self, pos):
        cx, cy = self.cell_at(pos)
        for p in reversed(self.loose()):
            x, y, w, h = p.footprint()
            if x <= cx < x + w and y <= cy < y + h:
                return p
        return None

    def fits(self, p):
        return p.turns == 0 and p.cell == p.strip.home

    def place(self, p):
        p.tray, p.cell, p.turns = None, p.strip.home, 0
        if p in self.selected:
            self.selected.remove(p)
        self.sound("JS_RIGHT")
        self.check()

    # ----------------------------------------------------------------- input
    def mouse_down(self, pos):
        if self.paused:
            return False
        for k, r in enumerate(TABS):
            if r.collidepoint(pos):
                self.switch(k)
                return True
        if not TRAY.collidepoint(pos):
            return False
        p = self.piece_at(pos)
        if self.hint_mode:
            if p is None:
                self.app.sounds.play(self.app.sounds.NO_CLICK)
            else:
                self.hint_mode = False
                self.place(p)
                self.hint_done = True
            return True
        shift = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
        if p is None:
            self.band = (pos, pos, shift)          # select by dragging over pieces
            return True
        if shift:
            if p in self.selected:
                self.selected.remove(p)
            else:
                self.selected.append(p)
        elif p not in self.selected:
            self.selected = [p]
        self.sound("JS_SEL")
        mx, my = self.cell_at(pos)
        self.drag = {q.n: (q.cell[0] - mx, q.cell[1] - my) for q in self.selected}
        return True

    def mouse_move(self, pos):
        super().mouse_move(pos)
        if self.band:
            self.band = (self.band[0], pos, self.band[2])
            return
        if not self.drag:
            return
        mx, my = self.cell_at(pos)
        for q in self.selected:
            ox, oy = self.drag[q.n]
            q.cell = (mx + ox, my + oy)
        over = next((k for k, r in enumerate(TABS) if r.collidepoint(pos)), None)
        if over != (self.tab_hover[0] if self.tab_hover else None):
            self.tab_hover = (over, 0.0) if over is not None and over != self.tray else None

    def band_rect(self):
        (x0, y0), (x1, y1), _ = self.band
        return pygame.Rect(min(x0, x1), min(y0, y1), abs(x1 - x0) + 1, abs(y1 - y0) + 1)

    def piece_rect(self, p):
        c = self.data.cell
        x, y, w, h = p.footprint()
        return pygame.Rect(self.origin[0] + x * c, self.origin[1] + y * c, w * c, h * c)

    def mouse_up(self, pos):
        if self.band:
            rect, shift = self.band_rect(), self.band[2]
            self.band = None
            caught = [p for p in self.loose() if rect.colliderect(self.piece_rect(p))] if rect.w * rect.h > 9 else []
            before = list(self.selected)
            self.selected = (before if shift else []) + [p for p in caught if not (shift and p in before)]
            if self.selected and self.selected != before:
                self.sound("JS_SEL")
            elif before and not self.selected:
                self.sound("JS_DESEL")
            return True
        if super().mouse_up(pos):
            return True
        if not self.drag:
            return False
        self.drag = None
        self.tab_hover = None
        landed = False
        for q in list(self.selected):
            x, y, w, h = q.footprint()
            q.cell = (min(max(x, 0), self.data.cols - w), min(max(y, 0), self.data.rows - h))
            if self.fits(q):
                self.place(q)
                landed = True
        if not landed:
            self.sound("JS_DROP")
        return True

    def right_click(self, pos):
        p = self.piece_at(pos)
        if p is not None and p not in self.selected:
            self.selected = [p]
        self.rotate_selected()

    def toggled(self, button):
        button.on = False
        self.rotate_selected()

    def rotate_selected(self):
        if len(self.selected) != 1:
            self.app.sounds.play(self.app.sounds.NO_CLICK)
            return
        p = self.selected[0]
        p.turns = (p.turns + 1) % 4
        self.sound("JS_ROTAT")
        if self.fits(p):
            self.place(p)

    def key(self, ev):
        if pygame.K_1 <= ev.key <= pygame.K_5:
            self.switch(ev.key - pygame.K_1)
            return True
        return False

    def switch(self, k):
        if k == self.tray:
            return
        moving = self.selected if self.drag else []
        for q in moving:
            q.tray = k                    # dragged strips travel with the view
        if moving:
            self.emit("move_tray")
        if not self.drag:
            self.selected = []
        self.tray = k
        self.sound("JS_TAB")

    def use_hint(self):
        if self.solved:
            return False
        self.hint_mode = True
        return True

    def complete(self):
        for p in self.pieces:
            if not p.placed:
                p.tray, p.cell, p.turns = None, p.strip.home, 0
        self.selected = []
        self.check()

    def update(self, dt):
        if self.tab_hover:
            k, t = self.tab_hover
            t += dt
            if t >= TAB_HOLD:
                self.switch(k)
                self.tab_hover = None
            else:
                self.tab_hover = (k, t)

    # --------------------------------------------------------------- drawing
    def strip_image(self, p):
        key = (p.n, p.turns)
        if key not in self.cache:
            l, t, r, b = p.strip.rect
            img = self.picture.subsurface(pygame.Rect(l, t, r - l, b - t).clip(self.picture.get_rect())).copy()
            if p.turns:
                img = pygame.transform.rotate(img, -90 * p.turns)
            self.cache[key] = img
        return self.cache[key]

    def draw(self, surf):
        if self.background:
            surf.blit(self.background, AREA)
        if self.tab_art[self.tray]:
            surf.blit(self.tab_art[self.tray], (TABS[self.tray].x - 6, TABS[self.tray].y - 1))
        tint = pygame.Surface(TRAY.inflate(-8, -8).size, pygame.SRCALPHA)
        tint.fill(TINTS[self.tray] + (60,))
        surf.blit(tint, TRAY.inflate(-8, -8))
        for b in self.buttons:
            b.draw(surf)
        if self.paused:
            return
        c = self.data.cell
        ox, oy = self.origin
        bx, by = self.data.board
        pw, ph = self.picture.get_width() // c, self.picture.get_height() // c
        grid = pygame.Rect(ox, oy, self.data.cols * c, self.data.rows * c)
        board = pygame.Rect(ox + bx * c, oy + by * c, pw * c, ph * c).clip(grid)   # tall pictures overhang
        shade = pygame.Surface(board.size, pygame.SRCALPHA)
        shade.fill((0, 0, 0, 90))
        surf.blit(shade, board)
        for gx, gy in self.data.given:
            src = pygame.Rect((gx - bx) * c, (gy - by) * c, c, c)
            if self.picture.get_rect().contains(src):
                surf.blit(self.picture, (ox + gx * c, oy + gy * c), src)
        for p in self.pieces:
            if p.placed:
                surf.blit(self.strip_image(p), (ox + p.cell[0] * c, oy + p.cell[1] * c))
        if not self.solved:
            pygame.draw.rect(surf, (60, 25, 5), board, 1)
        for p in self.loose():
            r = self.piece_rect(p)
            surf.blit(self.strip_image(p), r)
            colour = (255, 236, 160) if p in self.selected else (40, 15, 0)
            pygame.draw.rect(surf, colour, r, 2 if p in self.selected else 1)
        if self.band:
            pygame.draw.rect(surf, (255, 236, 160), self.band_rect(), 1)
        if self.hint_mode:
            text = self.app.strings.get(8006, "").replace("\r", " ")
            img = self.app.fonts.get(16).render(text, True, (248, 176, 100))
            surf.blit(img, img.get_rect(midbottom=(AREA.centerx, AREA.bottom - 4)))
