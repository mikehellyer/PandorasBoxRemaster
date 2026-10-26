"""Find and Fill (PUZZLE.FNF, CFindNFillObject).

"Find a black shape from the image on the left and fill it with a single color.
Make sure you don't fill any extra spaces! ... Some images may be rotated or
upside-down." (LANGENU 13126-13132)

The board (data.fnf) is a pile of overlapping, turned objects; its lines are the
boundaries between cells covered by different sets of objects, and the areas
between lines are what you fill. An object is found when one colour covers
exactly its areas (less those already locked by earlier finds) and nothing else;
its picture then shows on the board and its areas lock, except those another
unfound object still needs (five puzzles have an object wholly inside another). Boards are 250x250 to
1256x430: ones that fit are scaled up to fill the view, larger ones scroll
with the arrows, the mouse wheel and shift+wheel. Palette: FNF/BLUE, YLLW, RED, GRN, FILL (black =
erase) and ERASE (clear all), textures from FNF/PATTERNS.PNG.

**Interpretation:** the screen layout (left column with the reference pictures,
button and arrow positions; left/right arrows are FNF/UPARROW turned, as only
up/down art exists), the outline colour, and the found picture being the object's
sprite turned to fit its place on the board (the turn is fitted, not read).
Sounds FNF/FF_COLOR, FF_FILL, FF_ERASE, OUTLINE, SUCCESS, BADCLICK.
"""
from __future__ import annotations

import copy
import math

import numpy as np
import pygame

from ..data import fnf
from .base import AREA, PuzzleGame, ToggleButton

LEFT = pygame.Rect(0, AREA.y, 185, 540)
VIEW = pygame.Rect(185, AREA.y, 540, 540)
COLOURS = [("BLUE", 0), ("YLLW", 1), ("RED", 2), ("GRN", 3), ("FILL", None)]   # pattern row, None = erase
MIN_AREA = 12
OUTLINE = (235, 205, 150)
SCROLL = 40


class FindAndFill(PuzzleGame):
    SOUND_FOLDER = "FNF"

    def __init__(self, app, puzzle):
        super().__init__(app, puzzle)
        name = next(f for f in puzzle.files if f.endswith(".FNF"))
        self.data = fnf.parse(self.raw(name))
        self.left_bg = self.app.assets.image("FNF/301.RIM")
        self.tray = self.png("FNF/TRAY2.PNG")
        pat = self.png("FNF/PATTERNS.PNG")
        self.patterns = [pat.subsurface((0, 128 * k, 128, 128)) for k in range(8)] if pat else []
        self.palette = []
        for k, (stem, _) in enumerate(COLOURS):
            self.palette.append(ToggleButton(self, "FNF", stem, (736, 285 + 44 * k), on=(k == 0)))
        self.erase_all = ToggleButton(self, "FNF", "ERASE", (736, 285 + 44 * len(COLOURS)))
        self.up = ToggleButton(self, "FNF", "UPARROW", (VIEW.right - 32, VIEW.y + 4))
        self.down = ToggleButton(self, "FNF", "DNARROW", (VIEW.right - 32, VIEW.bottom - 32))
        self.left = turned(self.up, (VIEW.x + 4, VIEW.bottom - 32), 90)
        self.right = turned(self.up, (VIEW.right - 64, VIEW.bottom - 32), -90)
        self.arrows = [self.up, self.down, self.left, self.right]
        self.buttons = self.palette + [self.erase_all] + self.arrows
        self.colour = 0
        self.build_board()
        self.restart()

    # --------------------------------------------------------------- board
    def build_board(self):
        board = self.data.board
        h, w = board.shape
        self.scale = max(1.0, min(VIEW.w / w, VIEW.h / h))
        if self.scale > 1:                            # blow small boards up to fill the view
            w, h = int(w * self.scale), int(h * self.scale)
            board = board[(np.arange(h) / self.scale).astype(int)][:, (np.arange(w) / self.scale).astype(int)]
        self.cells = board
        self.size = (w, h)
        self.origin = (max(0, (VIEW.w - w) // 2), max(0, (VIEW.h - h) // 2))   # board offset in the view
        lines = np.zeros((h, w), bool)
        lines[:, :-1] |= board[:, :-1] != board[:, 1:]
        lines[:-1, :] |= board[:-1, :] != board[1:, :]
        self.lines = lines.copy()                     # 2 px lines, so areas never touch diagonally
        self.lines[:, 1:] |= lines[:, :-1]
        self.lines[1:, :] |= lines[:-1, :]
        free = (board != 0) & ~self.lines
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        alpha = pygame.surfarray.pixels_alpha(surf)
        alpha[:] = (free.T * 255).astype(np.uint8)
        del alpha
        comps = pygame.mask.from_surface(surf, 127).connected_components(MIN_AREA)
        self.labels = np.full((h, w), -1, np.int32)
        self.owned = [set() for _ in self.data.objects]      # areas of each object
        for i, comp in enumerate(comps):
            r = comp.get_bounding_rects()[0]
            s = pygame.Surface(r.size, pygame.SRCALPHA)
            comp.to_surface(s, setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0), dest=(-r.x, -r.y))
            a = pygame.surfarray.array_alpha(s).T > 0
            self.labels[r.y:r.bottom, r.x:r.right][a] = i
            value = int(board[r.y:r.bottom, r.x:r.right][a][0])
            for k in range(len(self.data.objects)):
                if value >> k & 1:
                    self.owned[k].add(i)
        self.region_count = len(comps)
        self.pictures = [place(o.rgb, o.mask, board >> k & 1 == 1) for k, o in enumerate(self.data.objects)]
        self.fill_cache = {}

    # --------------------------------------------------------------- state
    def restart(self):
        self.fill = {}                 # area -> pattern row
        self.found = [False] * len(self.data.objects)
        self.locked = set()
        self.revealed = set()          # objects whose outline a hint shows
        self.scroll = self.scroll_x = 0
        self.hint_mode = False
        self.render_board()
        self.check()

    def check(self):
        self.solved = all(self.found)

    def save_state(self):
        return {"fill": [[int(r), int(v)] for r, v in self.fill.items()], "found": self.found,
                "revealed": sorted(self.revealed)}

    def load_state(self, state):
        self.found = list(state["found"])
        self.revealed = set(state["revealed"])
        self.relock()
        self.fill = {r: v for r, v in state["fill"] if r not in self.locked}
        self.render_board()
        self.check()

    def region_at(self, pos):
        if not VIEW.collidepoint(pos):
            return None
        x = pos[0] - VIEW.x - self.origin[0] + self.scroll_x
        y = pos[1] - VIEW.y - self.origin[1] + self.scroll
        if not (0 <= y < self.size[1] and 0 <= x < self.size[0]):
            return None
        r = int(self.labels[y, x])
        return r if r >= 0 else None

    def evaluate(self):
        for k, regions in enumerate(self.owned):
            if self.found[k]:
                continue
            todo = regions - self.locked
            if not todo:
                continue
            colours = {self.fill.get(r) for r in todo}
            if len(colours) != 1 or None in colours:
                continue
            c = colours.pop()
            painted = {r for r, v in self.fill.items() if v == c and r not in self.locked}
            if painted == todo:
                self.found[k] = True
                for r in regions:
                    self.fill.pop(r, None)
                self.relock()
                self.sound("SUCCESS")
        self.check()

    def relock(self):
        """Lock the areas of found objects that no unfound object still needs."""
        done = set().union(*(o for k, o in enumerate(self.owned) if self.found[k]))
        self.locked = done - set().union(*(o for k, o in enumerate(self.owned) if not self.found[k]))
        for r in self.locked:
            self.fill.pop(r, None)

    # --------------------------------------------------------------- input
    def mouse_down(self, pos):
        if self.paused:
            return False
        r = self.region_at(pos)
        if self.hint_mode:
            if r is None:
                return True
            k = next((k for k, own in enumerate(self.owned) if r in own and not self.found[k]), None)
            if k is None:
                self.app.sounds.play(self.app.sounds.NO_CLICK)
                return True
            self.hint_mode = False
            self.revealed.add(k)
            self.hint_done = True
            self.sound("OUTLINE")
            self.render_board()
            return True
        if r is None or r in self.locked:
            if r is not None:
                self.sound("BADCLICK")
            return r is not None
        c = COLOURS[self.colour][1]
        if c is None:
            self.fill.pop(r, None)
            self.sound("FF_ERASE")
        else:
            self.fill[r] = c
            self.sound("FF_FILL")
        self.evaluate()
        self.render_board()
        return True

    def right_click(self, pos):
        r = self.region_at(pos)
        if r is not None and r in self.fill:
            del self.fill[r]
            self.sound("FF_ERASE")
            self.render_board()

    def toggled(self, button):
        if button in self.palette:
            self.colour = self.palette.index(button)
            for b in self.palette:
                b.on = b is button
            self.sound("FF_COLOR")
        elif button is self.erase_all:
            button.on = False
            self.fill.clear()
            self.sound("FF_ERASE")
            self.render_board()
        else:
            button.on = False
            dx, dy = {self.up: (0, -1), self.down: (0, 1), self.left: (-1, 0), self.right: (1, 0)}[button]
            self.scroll_by(dx * SCROLL, dy * SCROLL)

    def scroll_by(self, dx, dy):
        self.scroll = max(0, min(self.size[1] - VIEW.h, self.scroll + dy))
        self.scroll_x = max(0, min(self.size[0] - VIEW.w, self.scroll_x + dx))

    def wheel(self, dy):
        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
            self.scroll_by(-dy * SCROLL, 0)
        else:
            self.scroll_by(0, -dy * SCROLL)

    def use_hint(self):
        if self.solved:
            return False
        self.hint_mode = True
        return True

    def complete(self):
        self.found = [True] * len(self.found)
        self.fill.clear()
        self.relock()
        self.render_board()
        self.check()

    # ------------------------------------------------------------- drawing
    def pattern_surface(self, row):
        if row not in self.fill_cache:
            w, h = self.size
            s = pygame.Surface((w, h))
            if self.patterns:
                tile = self.patterns[row]
                for y in range(0, h, 128):
                    for x in range(0, w, 128):
                        s.blit(tile, (x, y))
            self.fill_cache[row] = pygame.surfarray.array3d(s).swapaxes(0, 1)
        return self.fill_cache[row]

    def render_board(self):
        w, h = self.size
        img, shown = self.found_layer()
        img = img.copy()
        colour = np.full(self.region_count + 1, -1, np.int8)     # by area; index -1 = no area
        for r, v in self.fill.items():
            colour[r] = v
        colour = colour[self.labels]
        for c in set(self.fill.values()):
            sel = colour == c
            img[sel] = self.pattern_surface(c)[sel]
        if shown.any():                          # keep lines only round areas still open
            is_open = np.ones(self.region_count + 1, bool)
            is_open[list(self.locked)] = False
            is_open[-1] = False
            open_ = is_open[self.labels]
            for _ in range(2):
                open_ = open_ | np.roll(open_, 1, 0) | np.roll(open_, -1, 0) | np.roll(open_, 1, 1) | np.roll(open_, -1, 1)
            img[self.lines & (~shown | open_)] = OUTLINE
        else:
            img[self.lines] = OUTLINE
        for k in self.revealed:
            if not self.found[k]:
                m = self.cells >> k & 1 == 1
                edge = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
                img[edge] = (255, 255, 255)
        self.board = pygame.image.frombuffer(np.ascontiguousarray(img).tobytes(), (w, h), "RGB").copy()

    def found_layer(self):
        """Dark wood with the found pictures on it, and where they are (kept until the next find)."""
        key = tuple(self.found)
        if self.fill_cache.get("layer_key") != key:
            img = self.pattern_surface(4).copy()                 # dark wood
            shown = np.zeros(self.lines.shape, bool)
            for k, (rgb, mask) in enumerate(self.pictures):
                if self.found[k]:
                    img[mask] = rgb[mask]
                    shown |= mask
            self.fill_cache["layer_key"], self.fill_cache["layer"] = key, (img, shown)
        return self.fill_cache["layer"]

    def draw(self, surf):
        surf.blit(self.left_bg, LEFT)
        surf.fill((20, 8, 2), VIEW)
        for b in self.palette + [self.erase_all]:
            b.draw(surf)
        if self.paused:
            return
        at = (VIEW.x + self.origin[0], VIEW.y + self.origin[1])
        surf.blit(self.board, at, pygame.Rect(self.scroll_x, self.scroll, VIEW.w, VIEW.h))
        if self.size[1] > VIEW.h:
            self.up.draw(surf)
            self.down.draw(surf)
        if self.size[0] > VIEW.w:
            self.left.draw(surf)
            self.right.draw(surf)
        self.draw_left(surf)
        if self.hint_mode:
            text = self.app.strings.get(13132, "").replace("\r", " ")
            img = self.app.fonts.get(16).render(text, True, (248, 176, 100))
            surf.blit(img, img.get_rect(midbottom=(VIEW.centerx, VIEW.bottom - 4)))

    def draw_left(self, surf):
        """The reference pictures still to finish, each with its shapes (black until found)."""
        todo = [k for k in range(len(self.data.strips))
                if any(not self.found[i] for i, o in enumerate(self.data.objects) if o.picture == k)]
        if not todo:
            return
        slot = min(200, LEFT.h // len(todo))
        for n, k in enumerate(todo):
            top = LEFT.y + n * slot
            objs = [i for i, o in enumerate(self.data.objects) if o.picture == k]
            th = max(14, min(32, slot // 5))
            rows = 1 + (len(objs) - 1) // max(1, (LEFT.w - 12) // (th + 4))
            pic = self.strip_picture(k)
            scale = min(1.0, (slot - 10 - rows * (th + 4)) / pic.get_height(), 150 / pic.get_width())
            pic = pygame.transform.smoothscale(pic, (max(1, int(pic.get_width() * scale)), max(1, int(pic.get_height() * scale))))
            box = pic.get_rect(midtop=(LEFT.centerx, top + 4))
            if self.tray and scale == 1.0:
                surf.blit(self.tray, self.tray.get_rect(center=box.center))
            surf.blit(pic, box)
            x, y = LEFT.x + 8, box.bottom + 4
            for i in objs:
                o = self.data.objects[i]
                sh, sw = o.mask.shape
                f = min(th / sh, (th * 1.5) / sw)
                tw, tht = max(1, int(sw * f)), max(1, int(sh * f))
                if x + tw > LEFT.right - 4:
                    x, y = LEFT.x + 8, y + th + 4
                rgba = np.zeros(o.mask.shape + (4,), np.uint8)
                if self.found[i]:
                    rgba[..., :3] = o.rgb
                rgba[..., 3] = o.mask * 255
                s = pygame.image.frombuffer(rgba.tobytes(), (sw, sh), "RGBA")
                surf.blit(pygame.transform.smoothscale(s, (tw, tht)), (x, y))
                x += tw + 4

    def strip_picture(self, k):
        key = ("strip", k)
        if key not in self.fill_cache:
            pic = self.data.strips[k][:, :140]
            keep = ~((pic[..., 0] > 240) & (pic[..., 1] < 20) & (pic[..., 2] > 240))
            cols, rows = np.where(keep.any(0))[0], np.where(keep.any(1))[0]
            if len(cols) and len(rows):
                pic = pic[rows.min():rows.max() + 1, cols.min():cols.max() + 1]
            self.fill_cache[key] = pygame.image.frombuffer(
                np.ascontiguousarray(pic).tobytes(), (pic.shape[1], pic.shape[0]), "RGB").copy()
        return self.fill_cache[key]


def turned(button, pos, angle):
    """A copy of an arrow button pointing another way."""
    b = copy.copy(button)
    b.images = {k: pygame.transform.rotate(v, angle) if v else None for k, v in button.images.items()}
    b.rect = pygame.Rect(pos, b.rect.size)
    return b


def place(rgb, mask, cells):
    """Turn and scale an object's sprite to fit the board cells it covers.

    Returns (rgb, mask) in board size: the sprite turned by the best of 360 whole
    degrees and scaled to the cells' extent, kept only where the cells are. Both
    are fitted: the file's own per-object fields didn't predict them.
    """
    h, w = cells.shape
    by, bx = cells.nonzero()
    ys, xs = mask.nonzero()
    pts = np.stack([xs - (mask.shape[1] - 1) / 2, ys - (mask.shape[0] - 1) / 2], 1)
    inner = np.zeros_like(mask)
    inner[1:-1, 1:-1] = mask[1:-1, 1:-1] & mask[:-2, 1:-1] & mask[2:, 1:-1] & mask[1:-1, :-2] & mask[1:-1, 2:]
    edge = pts[~inner[ys, xs]]                       # the extremes, for the size check
    pts = pts[::max(1, len(pts) // 4000)]            # a sample is plenty to score a turn
    bw, bh = np.ptp(bx) + 1, np.ptp(by) + 1
    clipped = bx.min() == 0 or by.min() == 0 or bx.max() == w - 1 or by.max() == h - 1
    by_area = math.sqrt(len(bx) / len(xs))
    best, fit = -1.0, (0, by_area, w / 2, h / 2)
    for deg in range(360):
        t = math.radians(deg)
        c, s = math.cos(t), math.sin(t)                  # pygame turns anticlockwise
        EX, EY = edge[:, 0] * c + edge[:, 1] * s, -edge[:, 0] * s + edge[:, 1] * c
        if clipped:
            f = by_area
        else:
            fx, fy = bw / (np.ptp(EX) + 1), bh / (np.ptp(EY) + 1)
            if abs(fx / fy - 1) > 0.04:
                continue
            f = (fx + fy) / 2
        X = (pts[:, 0] * c + pts[:, 1] * s) * f
        Y = (-pts[:, 0] * s + pts[:, 1] * c) * f
        if clipped:                                      # centre of mass, as the extent is cut
            ox, oy = bx.mean() - X.mean(), by.mean() - Y.mean()
        else:
            ox = (bx.min() + bx.max()) / 2 - (EX.min() + EX.max()) * f / 2
            oy = (by.min() + by.max()) / 2 - (EY.min() + EY.max()) * f / 2
        gx, gy = np.rint(X + ox).astype(int), np.rint(Y + oy).astype(int)
        ok = (gx >= 0) & (gy >= 0) & (gx < w) & (gy < h)
        hit = cells[gy[ok], gx[ok]].mean() if ok.any() else 0
        if hit > best:
            best, fit = hit, (deg, f, ox, oy)
    deg, f, ox, oy = fit
    rgba = np.zeros(mask.shape + (4,), np.uint8)
    rgba[..., :3] = rgb
    covered = mask.copy()
    for _ in range(3):                    # bleed edge colours out, so smoothing never mixes in magenta
        _grow_into(covered, rgba)
    rgba[..., 3] = mask * 255
    sprite = pygame.image.frombuffer(rgba.tobytes(), (mask.shape[1], mask.shape[0]), "RGBA")
    sprite = pygame.transform.rotozoom(sprite, deg, f)
    canvas = pygame.Surface((w, h), pygame.SRCALPHA)
    canvas.blit(sprite, (round(ox - (sprite.get_width() - 1) / 2), round(oy - (sprite.get_height() - 1) / 2)))
    out = pygame.surfarray.array3d(canvas).swapaxes(0, 1)
    alpha = pygame.surfarray.array_alpha(canvas).T > 127
    # cells the turned sprite just misses take their neighbour's colour
    return out, cells & alpha | cells & ~alpha & _grow(alpha, out)


def _grow_into(covered, out):
    """Give the pixels next to covered ones their neighbour's colour, and cover them."""
    covered |= _grow(covered.copy(), out)


def _grow(alpha, out):
    """Cells next to the turned sprite (one pixel), copying their neighbour's colour into out."""
    near = np.zeros_like(alpha)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        moved = np.roll(np.roll(alpha, dy, 0), dx, 1)
        add = moved & ~alpha & ~near
        src = np.roll(np.roll(out, dy, 0), dx, 1)
        out[add] = src[add]
        near |= add
    return near
