"""Overlap (PUZZLE.FSH, COverlapseObject with stack / main panels).

"Complete the picture using the pieces on the left. Click a piece and drag it to
the correct place on the image. Some pieces contain part of the background...
Some pieces overlap part of the picture. Some pieces need to be rotated:
right-click. You can move pieces to other stacks." (LANGENU 5414-5419)

Pieces are three-cell lines or Ls (data/fsh.py) cut from the picture laid on its
background pattern. The left column holds four stacks (OVER/BACKGROUND.PNG,
725x540, drawn from the screen's left edge); each shows its top piece with up /
down arrows (OVER/BUTTONS.PNG) to look through it. The board is the right-hand
540x540 area with the picture centred on OVER/BG_<colour>.PNG and the start
cells shown. A piece dropped on its place the right way round sticks; anywhere
else it goes back to its stack; dropped on a stack it moves there.
Sounds OVER/OL_SEL, OL_ROTAT, OL_RIGHT, OL_WRONG, OL_REORD, OL_DC.
Stack and arrow placement and the thumbnail size are measured from the art, not
traced in code.
"""
from __future__ import annotations

import pygame

from ..data import fsh
from .base import AREA, PuzzleGame, ToggleButton

ORIGIN = (0, AREA.y)                                    # BACKGROUND.PNG is 725 wide
BOARD = pygame.Rect(185, AREA.y, 540, 540)
STACKS = [pygame.Rect(0, AREA.y + y0, 184, y1 - y0) for y0, y1 in ((0, 126), (130, 262), (270, 396), (400, 540))]
THUMB = 104


class Piece:
    def __init__(self, data: fsh.OverlapPiece):
        self.data = data
        self.turns = data.scramble % 4      # extra quarter turns left to undo
        self.placed = False
        self.stack = data.stack

    @property
    def rotation(self):
        return (self.data.rotation + self.turns) % 4

    def cells(self):
        return fsh.shape_cells(self.data.shape, self.rotation)


class Overlap(PuzzleGame):
    SOUND_FOLDER = "OVER"

    def __init__(self, app, puzzle):
        super().__init__(app, puzzle)
        name = next(f for f in puzzle.files if f.endswith(".FSH"))
        self.data = fsh.parse(self.raw(name))
        kind = "p.bmp" if self.data.jpeg[:2] == b"BM" else "p.jpg"
        self.picture = self.image_from_bytes(self.data.jpeg, kind)
        self.background = self.png("OVER/BACKGROUND.PNG")
        pattern = self.png(f"OVER/{self.data.background}.PNG") or self.png("OVER/BG_BLUE.PNG")
        c = self.data.cell
        # the board picture: pattern with the picture centred on it
        self.board = pygame.Surface(BOARD.size)
        self.board.blit(pattern, (0, 0))
        pw, ph = self.data.cols * c, self.data.rows * c
        self.pic_origin = ((BOARD.w - pw) // 2, (BOARD.h - ph) // 2)
        self.board.blit(self.picture, self.pic_origin, pygame.Rect(0, 0, pw, ph))
        self.arrows = self.strip("OVER/BUTTONS.PNG", 6)
        self.rotate = ToggleButton(self, "OVER", "ROTATE", (743, 409))
        self.buttons = [self.rotate]
        self.cache = {}
        self.restart()

    def strip(self, name, n):
        img = self.png(name)
        if img is None:
            return []
        img = img.copy()
        img.set_colorkey((0, 0, 255))
        w = img.get_width() // n
        return [img.subsurface((i * w, 0, w, img.get_height())) for i in range(n)]

    # ----------------------------------------------------------------- state
    def restart(self):
        self.pieces = [Piece(p) for p in self.data.pieces]
        self.stacks = [list(s) for s in self.data.stacks]
        self.top = [0] * len(self.stacks)          # which piece each stack shows
        self.held = None                           # (piece, grab offset)
        self.mouse = (0, 0)
        self.order = []                            # placed pieces, in placing order
        self.hint_mode = False
        self.check()

    def save_state(self):
        return {"pieces": [[p.turns, p.placed, p.stack] for p in self.pieces],
                "stacks": self.stacks, "top": self.top, "order": [self.pieces.index(p) for p in self.order]}

    def load_state(self, state):
        for p, (turns, placed, stack) in zip(self.pieces, state["pieces"]):
            p.turns, p.placed, p.stack = turns, placed, stack
        self.stacks = [list(s) for s in state["stacks"]]
        self.top = list(state["top"])
        self.order = [self.pieces[i] for i in state["order"]]
        self.cache.clear()
        self.check()

    def check(self):
        self.solved = all(p.placed for p in self.pieces)

    def cell_xy(self, cell):
        c = self.data.cell
        return (BOARD.x + self.pic_origin[0] + cell[0] * c, BOARD.y + self.pic_origin[1] + cell[1] * c)

    def showing(self, k):
        s = self.stacks[k]
        if not s:
            return None
        self.top[k] %= len(s)
        return self.pieces[s[self.top[k]]]

    def arrow_rects(self, k):
        r = STACKS[k]
        return (pygame.Rect(r.right - 34, r.y + 8, 28, 28), pygame.Rect(r.right - 34, r.bottom - 36, 28, 28))

    # ---------------------------------------------------------------- images
    def piece_image(self, p: Piece, scale=1.0):
        key = (p.data.number, p.rotation, scale)
        if key in self.cache:
            return self.cache[key]
        c = self.data.cell
        cells = p.cells()
        home = fsh.shape_cells(p.data.shape, p.data.rotation)
        xs = [x for x, _ in cells]
        ys = [y for _, y in cells]
        w, h = (max(xs) - min(xs) + 1) * c, (max(ys) - min(ys) + 1) * c
        img = pygame.Surface((w, h), pygame.SRCALPHA)
        # each cell's picture comes from the home cell it corresponds to, turned
        ax, ay = p.data.anchor
        bx, by = self.pic_origin
        for (cx, cy), (hx, hy) in zip(cells, home):
            src = pygame.Rect(bx + (ax + hx) * c, by + (ay + hy) * c, c, c)
            tile = pygame.Surface((c, c))
            tile.blit(self.board, (0, 0), src)
            if p.turns:
                tile = pygame.transform.rotate(tile, -90 * p.turns)
            img.blit(tile, ((cx - min(xs)) * c, (cy - min(ys)) * c))
        if scale != 1.0:
            img = pygame.transform.smoothscale(img, (max(1, int(w * scale)), max(1, int(h * scale))))
        self.cache[key] = (img, (min(xs), min(ys)))
        return self.cache[key]

    # ----------------------------------------------------------------- input
    def mouse_down(self, pos):
        if self.paused:
            return False
        for k in range(len(self.stacks)):
            up, down = self.arrow_rects(k)
            if up.collidepoint(pos) or down.collidepoint(pos):
                if self.stacks[k]:
                    self.top[k] += -1 if up.collidepoint(pos) else 1
                    self.sound("OL_REORD")
                return True
        for k, r in enumerate(STACKS):
            if r.collidepoint(pos):
                p = self.showing(k)
                if p is None:
                    return True
                if self.hint_mode:
                    self.hint_mode = False
                    self.place(p)
                    self.hint_done = True
                    return True
                img, _ = self.piece_image(p)
                self.held = (p, (img.get_width() // 2, img.get_height() // 2))
                self.mouse = pos
                self.sound("OL_SEL")
                return True
        return False

    def mouse_move(self, pos):
        super().mouse_move(pos)
        self.mouse = pos

    def mouse_up(self, pos):
        if super().mouse_up(pos):
            return True
        if not self.held:
            return False
        p, (gx, gy) = self.held
        self.held = None
        for k, r in enumerate(STACKS):
            if r.collidepoint(pos):
                if k != p.stack:
                    self.stacks[p.stack].remove(p.data.number)
                    self.stacks[k].insert(0, p.data.number)
                    self.top[k] = 0
                    p.stack = k
                    self.sound("OL_DC")
                return True
        if BOARD.collidepoint(pos):
            img, (mx, my) = self.piece_image(p)
            c = self.data.cell
            left = pos[0] - gx - (BOARD.x + self.pic_origin[0])
            top = pos[1] - gy - (BOARD.y + self.pic_origin[1])
            ax = round(left / c) - mx
            ay = round(top / c) - my
            if (ax, ay) == p.data.anchor and p.turns == 0:
                self.place(p)
            else:
                self.sound("OL_WRONG")
        return True

    def right_click(self, pos):
        if self.held:
            self.turn(self.held[0])
            return
        for k, r in enumerate(STACKS):
            if r.collidepoint(pos) and self.showing(k):
                self.turn(self.showing(k))

    def toggled(self, button):
        button.on = False
        target = self.held[0] if self.held else next((self.showing(k) for k in range(4) if self.showing(k)), None)
        if target:
            self.turn(target)

    def turn(self, p):
        p.turns = (p.turns + 1) % 4
        self.sound("OL_ROTAT")
        if self.held and self.held[0] is p:
            img, _ = self.piece_image(p)
            self.held = (p, (img.get_width() // 2, img.get_height() // 2))

    def place(self, p):
        p.turns = 0
        p.placed = True
        self.stacks[p.stack].remove(p.data.number)
        self.order.append(p)
        self.sound("OL_RIGHT")
        self.check()

    def use_hint(self):
        if self.solved:
            return False
        self.hint_mode = True
        return True

    def complete(self):
        for p in self.pieces:
            if not p.placed:
                self.place(p)

    # --------------------------------------------------------------- drawing
    def draw(self, surf):
        if self.background:
            surf.blit(self.background, ORIGIN)
        for b in self.buttons:
            b.draw(surf)
        if self.paused:
            return
        # board: pattern, the cells shown from the start, then placed pieces in order
        surf.fill((25, 10, 4), BOARD)
        c = self.data.cell
        if self.solved:
            surf.blit(self.board, BOARD)
        else:
            pattern_only = self.board.copy()
            pw, ph = self.data.cols * c, self.data.rows * c
            pattern_only.fill((25, 10, 4), pygame.Rect(self.pic_origin, (pw, ph)))
            surf.blit(pattern_only, BOARD)
            for x, y in self.data.shown:
                surf.blit(self.board, self.cell_xy((x, y)), pygame.Rect(self.pic_origin[0] + x * c, self.pic_origin[1] + y * c, c, c))
            for p in self.order:
                img, (mx, my) = self.piece_image(p)
                ax, ay = p.data.anchor
                surf.blit(img, self.cell_xy((ax + mx, ay + my)))
        # stacks
        for k, r in enumerate(STACKS):
            p = self.showing(k)
            if p is not None and not (self.held and self.held[0] is p):
                img, _ = self.piece_image(p)
                scale = min(1.0, THUMB / max(img.get_size()))
                thumb, _ = self.piece_image(p, round(scale, 3))
                surf.blit(thumb, thumb.get_rect(center=(r.centerx - 14, r.centery)))
            if self.arrows and len(self.stacks[k]) > 1:
                up, down = self.arrow_rects(k)
                surf.blit(self.arrows[0], up)
                surf.blit(self.arrows[1], down)
            if self.stacks[k]:
                n = self.app.fonts.get(14).render(str(len(self.stacks[k])), True, (248, 176, 100))
                surf.blit(n, (r.x + 8, r.bottom - 20))
        if self.held:
            p, (gx, gy) = self.held
            img, _ = self.piece_image(p)
            surf.blit(img, (self.mouse[0] - gx, self.mouse[1] - gy))
        if self.hint_mode:
            text = self.app.strings.get(5421, "").replace("\r", " ")
            img = self.app.fonts.get(16).render(text, True, (248, 176, 100))
            surf.blit(img, img.get_rect(midbottom=(BOARD.centerx, BOARD.bottom - 4)))
