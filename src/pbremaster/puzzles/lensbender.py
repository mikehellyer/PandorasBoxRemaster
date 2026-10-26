"""Lens Bender (PUZZLE.BGL, CBumpyGlassObject).

"Compose the picture in the middle using pieces under the lenses. Click the arrow
button on the second lens to attach the piece. A piece must face the right
direction before you can attach it. Move the next piece under each lens until it
faces the right way. ... A piece must have somewhere to connect before it will move
to the middle." (LANGENU 11950-11954)

Six lenses round a big middle lens (layout from BGL/<SET>.INI, art BGL/BGBACK.PNG).
Each outer lens holds a stack of pieces and shows the top one through its
ray-traced table (data.bgl), turned to Angle + 60 * lens degrees. Drag a top piece
to another lens to put it on that stack; the lens's arrow button sends its top
piece to the middle if it faces 0 degrees and touches (Adjacency) a piece already
there. The middle shows the picture built so far through its own table. All
pieces in the middle solves it. The tutorial's steps check out against these rules.
**Interpretation:** right-click / BGL/ROTATE moves a lens's top piece to the bottom of
its stack (the tooltip says "Rotate piece", which would make the lenses pointless);
Difficulty 0-3 picks the TUTOR/EASY/MEDIUM/HARD lens set; pieces are scaled to fit
their lens; the hint moves the clicked piece to the lens where it faces right.
Sounds BGL/BG_CLICK, BG_DRAG, BG_NO, BG_RIGHT, BG_WRONG.
"""
from __future__ import annotations

import math

import numpy as np
import pygame

from ..data import bgl
from .base import AREA, PuzzleGame, ToggleButton

ARROW_ANGLES = (0, 60, 120, 180, 240, 300)


class LensBender(PuzzleGame):
    SOUND_FOLDER = "BGL"

    def __init__(self, app, puzzle):
        super().__init__(app, puzzle)
        folder = puzzle.files[0].rsplit("/", 1)[0]
        self.data = bgl.parse(self.raw(f"{folder}/PUZZLE.BGL"))
        lens_set = self.data.lens_set
        centres, buttons = bgl.layout(self.raw(f"BGL/{lens_set}.INI"))
        self.centres = [(AREA.x + x, AREA.y + y) for x, y in centres]
        self.lenses = []
        for k in range(7):
            name = f"BGL/{lens_set}_LENS{k}"
            table = self.raw(name + ".RTRS") if k == bgl.MIDDLE and self.app.assets.has(name + ".RTRS") \
                else self.raw(name + ".RTRT")
            self.lenses.append(bgl.lens(table))
        self.background = self.png("BGL/BGBACK.PNG")
        tile = next((f for f in puzzle.files if f.rsplit("/", 1)[1].startswith("TILE.")), None)
        self.tile = self.app.assets.image(tile).convert() if tile else self.png("BGL/TILE.PNG")
        self.sprites = []
        for s in self.data.sprites:
            img = self.app.assets.image(f"{folder}/PUZZLE_SPR{s.index}.PNG").convert()
            mask = self.app.assets.image(f"{folder}/PUZZLE_SPR{s.index}A.PNG")
            out = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            out.blit(img, (0, 0))
            alpha = pygame.surfarray.pixels_alpha(out)
            alpha[:] = np.where(pygame.surfarray.array3d(mask)[..., 0] < 128, 255, 0).astype(np.uint8)
            del alpha
            self.sprites.append(out)
        self.arrows = []
        for k, (x, y) in enumerate(buttons):
            cx, cy = AREA.x + x, AREA.y + y
            mx, my = self.centres[bgl.MIDDLE]
            angle = math.degrees(math.atan2(-(my - cy), mx - cx)) % 360
            nearest = min(ARROW_ANGLES, key=lambda a: min(abs(a - angle), 360 - abs(a - angle)))
            b = ToggleButton(self, "BGL", f"SLIDE{nearest:03d}", (0, 0))
            b.rect.center = (cx, cy)
            self.arrows.append(b)
        self.rotate = ToggleButton(self, "BGL", "ROTATE", (743, 409))
        self.buttons = self.arrows + [self.rotate]
        self.views = {}
        self.restart()

    # --------------------------------------------------------------- state
    def restart(self):
        self.stacks = [[] for _ in range(6)]
        self.placed = set()
        for s in sorted(self.data.sprites, key=lambda s: s.order):
            if s.stack == bgl.MIDDLE:
                self.placed.add(s.index)
            else:
                self.stacks[s.stack].append(s.index)          # [0] = top
        self.selected = None
        self.held = None
        self.hint_mode = False
        self.views.clear()
        self.check()

    def check(self):
        self.solved = len(self.placed) == len(self.data.sprites)

    def save_state(self):
        return {"stacks": self.stacks, "placed": sorted(self.placed)}

    def load_state(self, state):
        self.stacks = [list(s) for s in state["stacks"]]
        self.placed = set(state["placed"])
        self.views.clear()
        self.check()

    def facing(self, i, lens):
        return (self.data.sprites[i].angle + 60 * lens) % 360

    def can_attach(self, i, lens):
        s = self.data.sprites[i]
        return abs(self.facing(i, lens)) < 1e-6 and bool(s.adjacent & self.placed)

    def attach(self, lens):
        stack = self.stacks[lens]
        if not stack:
            self.sound("BG_NO")
            return False
        i = stack[0]
        if not self.can_attach(i, lens):
            self.sound("BG_WRONG")
            return False
        stack.pop(0)
        self.placed.add(i)
        self.views.pop(lens, None)
        self.views.pop(bgl.MIDDLE, None)
        self.sound("BG_RIGHT")
        self.check()
        return True

    # ------------------------------------------------------------- drawing
    def canvas_for(self, lens):
        """What sits under a lens, before the glass bends it."""
        table = self.lenses[lens]
        valid = table.src[table.inside]
        w = int(valid[:, 0].max() + valid[:, 0].min() + 1)
        h = int(valid[:, 1].max() + valid[:, 1].min() + 1)
        canvas = pygame.Surface((w, h))
        if self.tile:
            for y in range(0, h, self.tile.get_height()):
                for x in range(0, w, self.tile.get_width()):
                    canvas.blit(self.tile, (x, y))
        if lens == bgl.MIDDLE:
            sw, sh = self.data.solution
            scale = min(1.0, w / sw, h / sh)
            picture = pygame.Surface((sw, sh), pygame.SRCALPHA)
            for i in sorted(self.placed):
                picture.blit(self.sprites[i], self.data.sprites[i].final)
            if scale < 1:
                picture = pygame.transform.smoothscale(picture, (int(sw * scale), int(sh * scale)))
            canvas.blit(picture, picture.get_rect(center=(w // 2, h // 2)))
        elif self.stacks[lens] and not (self.held and self.held[1] == lens):
            i = self.stacks[lens][0]
            canvas.blit(*self.piece_image(i, self.facing(i, lens), w * 0.86, (w // 2, h // 2)))
        return canvas

    def piece_image(self, i, facing, fit, centre):
        img = self.sprites[i]
        diag = math.hypot(*img.get_size())
        scale = min(1.0, fit / diag)
        turned = pygame.transform.rotozoom(img, -facing, scale)
        return turned, turned.get_rect(center=centre)

    def lens_view(self, lens):
        if lens not in self.views:
            table = self.lenses[lens]
            src = pygame.surfarray.array3d(self.canvas_for(lens)).swapaxes(0, 1)
            h, w = table.inside.shape
            out = np.zeros((h, w, 4), np.uint8)
            xs = np.clip(table.src[..., 0], 0, src.shape[1] - 1)
            ys = np.clip(table.src[..., 1], 0, src.shape[0] - 1)
            out[..., :3] = np.clip(src[ys, xs] * table.shade[..., None], 0, 255).astype(np.uint8)
            out[..., 3] = table.inside * 255
            self.views[lens] = pygame.image.frombuffer(out.tobytes(), (w, h), "RGBA").copy()
        return self.views[lens]

    def lens_rect(self, lens):
        w, h = self.lenses[lens].size
        return pygame.Rect(0, 0, w, h).move(self.centres[lens][0] - w // 2, self.centres[lens][1] - h // 2)

    def draw(self, surf):
        if self.background:
            surf.blit(self.background, AREA)
        for b in self.buttons:
            b.draw(surf)
        if self.paused:
            return
        for k in range(7):
            surf.blit(self.lens_view(k), self.lens_rect(k))
        for k in range(6):
            if k == self.selected:
                pygame.draw.circle(surf, (250, 200, 90), self.centres[k], self.lenses[k].size[0] // 2 + 2, 2)
        if self.held:
            i, lens, pos = self.held
            img, rect = self.piece_image(i, self.data.sprites[i].angle, 150, pos)
            surf.blit(img, rect)
        if self.hint_mode:
            text = self.app.strings.get(11924, "").replace("\r", " ")
            img = self.app.fonts.get(16).render(text, True, (248, 176, 100))
            surf.blit(img, img.get_rect(midbottom=(AREA.centerx, AREA.bottom - 6)))

    # --------------------------------------------------------------- input
    def lens_at(self, pos):
        for k in range(6):
            cx, cy = self.centres[k]
            if math.hypot(pos[0] - cx, pos[1] - cy) <= self.lenses[k].size[0] / 2:
                return k
        return None

    def mouse_down(self, pos):
        if self.paused or not AREA.collidepoint(pos):
            return False
        if any(b.rect.collidepoint(pos) for b in self.buttons):
            return False                                  # buttons act on mouse up
        k = self.lens_at(pos)
        if self.hint_mode:
            if k is None or not self.stacks[k]:
                self.app.sounds.play(self.app.sounds.NO_CLICK)
                return True
            self.hint_mode = False
            i = self.stacks[k].pop(0)
            self.stacks[self.data.sprites[i].final_stack].insert(0, i)
            self.views.clear()
            self.selected = self.data.sprites[i].final_stack
            self.hint_done = True
            self.sound("BG_CLICK")
            return True
        if k is None:
            return True
        self.selected = k
        if self.stacks[k]:
            self.held = (self.stacks[k][0], k, pos)
            self.views.pop(k, None)
            self.sound("BG_DRAG")
        return True

    def mouse_move(self, pos):
        super().mouse_move(pos)
        if self.held:
            self.held = (self.held[0], self.held[1], pos)

    def mouse_up(self, pos):
        if self.held:
            i, src, _ = self.held
            self.held = None
            dest = self.lens_at(pos)
            if dest is not None and dest != src:
                self.stacks[src].remove(i)
                self.stacks[dest].insert(0, i)
                self.selected = dest
                self.views.pop(dest, None)
                self.sound("BG_CLICK")
            self.views.pop(src, None)
            return True
        return super().mouse_up(pos)

    def right_click(self, pos):
        k = self.lens_at(pos)
        if k is not None:
            self.selected = k
            self.cycle(k)

    def cycle(self, k):
        if len(self.stacks[k]) > 1:
            self.stacks[k].append(self.stacks[k].pop(0))
            self.views.pop(k, None)
            self.sound("BG_CLICK")
        else:
            self.sound("BG_NO")

    def toggled(self, button):
        button.on = False
        if button is self.rotate:
            if self.selected is None:
                self.app.sounds.play(self.app.sounds.NO_CLICK)
            else:
                self.cycle(self.selected)
        else:
            self.attach(self.arrows.index(button))

    def use_hint(self):
        if self.solved:
            return False
        self.hint_mode = True
        return True

    def complete(self):
        self.placed = {s.index for s in self.data.sprites}
        self.stacks = [[] for _ in range(6)]
        self.views.clear()
        self.check()
