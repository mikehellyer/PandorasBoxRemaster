"""Slices (folder with OBJECT.WRL, STATE.TXT and pre-rendered pieces; CLambChopsObject).

"Click a piece to select it. Drag the selected piece to move it. Drag the selected
piece onto another piece to connect them. Both pieces must face the same
direction. ... right-click to rotate it ... click to flip it." (LANGENU 10900-10905)

An object cut into pieces lies scattered on a checkerboard floor. The scene uses
the original's camera (0x4c5d00, the mouse-to-floor pick): orthographic, looking
along (-2, -1, -2)/3 with up (-1, 4, -1)/(3*sqrt 2), 14 world units per 480 pixels,
floor at y = -0.48, x and z from -10 to 10. Each piece is drawn as its pre-rendered
sprite for its facing (data.slc: view = flip*4 + turn + 1), centred on its projected
box centre. Pieces joined in a group keep their places in the assembled object;
dropping a group on another facing the same way joins them if a piece of one
touches a piece of the other in the object. One group holding every piece solves it.
Buttons SLICE/ROTATEP (turn), FLIPP (flip), REVLF / REVRT (turn the whole table),
ANIM (spin the selected group). Sounds SLICE/SL_SEL, SL_MOVE, SL_ROTAT, SL_FLIP,
SL_RIGHT, SL_WRONG, SL_TICK.
**Interpretation:** turning a group about its centre, the neighbour rule for joining,
hint = join one neighbour to the clicked piece's group, button positions, and the
selection marker (SLICE/HI_SQUARE_1 under the group).
"""
from __future__ import annotations

import math

import numpy as np
import pygame

from ..data import slc
from .base import AREA, PuzzleGame, ToggleButton

SCALE = 480 / 14                          # pixels per world unit
FLOOR = -0.48
EDGE = 9.5                                # how far from the middle a group may sit
RIGHT = np.array([1, 0, -1]) / math.sqrt(2)
UP = np.array([-1, 4, -1]) / (3 * math.sqrt(2))
NEAR = np.array([2, 1, 2])                # larger = nearer the camera
FX = np.diag([1, -1, -1])
CENTRE = (AREA.x + AREA.w // 2, AREA.y + AREA.h // 2)
SPIN = 0.35                               # seconds per quarter turn while animating


def turn_matrix(k):
    c, s = round(math.cos(k * math.pi / 2)), round(math.sin(k * math.pi / 2))
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def orientation(flip, turn):
    return (FX if flip else np.eye(3, dtype=int)) @ turn_matrix(turn)


def project(p):
    return CENTRE[0] + SCALE * float(p @ RIGHT), CENTRE[1] - SCALE * float(p @ UP)


def floor_at(pos):
    """The floor point under a screen position (the inverse of project at y = FLOOR)."""
    sx, sy = (pos[0] - CENTRE[0]) / SCALE, -(pos[1] - CENTRE[1]) / SCALE
    a = math.sqrt(2) * sx                 # x - z
    b = 4 * FLOOR - 3 * math.sqrt(2) * sy  # x + z
    return np.array([(a + b) / 2, FLOOR, (b - a) / 2])


class Group:
    """Pieces joined together: piece i sits at origin + R @ centre_i."""

    def __init__(self, members, flip, turn, origin):
        self.members = list(members)
        self.flip, self.turn = flip, turn
        self.origin = np.array(origin, float)

    @property
    def R(self):
        return orientation(self.flip, self.turn)

    @property
    def view(self):
        return self.flip * 4 + self.turn + 1


class Slices(PuzzleGame):
    SOUND_FOLDER = "SLICE"

    def __init__(self, app, puzzle):
        super().__init__(app, puzzle)
        folder = puzzle.files[0].rsplit("/", 1)[0]
        self.folder = folder
        self.data = slc.parse(self.raw(f"{folder}/OBJECT.WRL"), self.raw(f"{folder}/STATE.TXT"))
        self.background = self.png("SLICE/BACKGROUND.PNG")
        self.marker = self.masked("SLICE/HI_SQUARE_1")
        self.rotate = ToggleButton(self, "SLICE", "ROTATEP", (740, 300))
        self.flip = ToggleButton(self, "SLICE", "FLIPP", (741, 348))
        self.rev_left = ToggleButton(self, "SLICE", "REVLF", (741, 394))
        self.rev_right = ToggleButton(self, "SLICE", "REVRT", (741, 440))
        self.animate = ToggleButton(self, "SLICE", "ANIM", (735, 488))
        self.buttons = [self.rotate, self.flip, self.rev_left, self.rev_right, self.animate]
        self.sprites = {}
        self.restart()

    # ------------------------------------------------------------- pieces
    def masked(self, stem):
        """A pre-rendered image with its mask (stem + 'A', black = solid) as alpha."""
        img, mask = self.png(stem + ".PNG"), self.png(stem + "A.PNG")
        if img is None:
            return None
        out = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        out.blit(img, (0, 0))
        if mask is not None:
            alpha = pygame.surfarray.pixels_alpha(out)
            alpha[:] = np.where(pygame.surfarray.array3d(mask)[..., 0] < 128, 255, 0).astype(np.uint8)
            del alpha
        return out

    def sprite(self, i, view):
        key = (i, view)
        if key not in self.sprites:
            surf = self.masked(f"{self.folder}/{self.data.pieces[i].image(view)}")
            self.sprites[key] = (surf, pygame.mask.from_surface(surf, 127))
        return self.sprites[key]

    def restart(self):
        self.groups = []
        for i, p in enumerate(self.data.pieces):
            x, z, flip, turn = p.start
            g = Group([i], flip, turn, np.zeros(3))
            g.origin = np.array([x, 0, z]) - g.R @ p.centre
            self.settle(g)
            self.groups.append(g)
        self.selected = None
        self.held = None
        self.spin = 0.0
        self.animate.on = False
        self.hint_mode = False
        self.check()

    def check(self):
        self.solved = len(self.groups) == 1

    def world(self, g, i):
        return g.origin + g.R @ self.data.pieces[i].centre

    def centre(self, g):
        return np.mean([self.world(g, i) for i in g.members], axis=0)

    def settle(self, g):
        """Stand the group on the floor."""
        R = np.abs(g.R)
        bottom = min(self.world(g, i)[1] - (R @ self.data.pieces[i].half)[1] for i in g.members)
        g.origin[1] += FLOOR - bottom

    def turned(self, g, flip, turn):
        """Face the group another way, keeping its centre on the same floor spot."""
        c = self.centre(g)
        g.flip, g.turn = flip, turn
        g.origin += c - self.centre(g)
        self.settle(g)

    def move_to(self, g, x, z):
        x, z = max(-EDGE, min(EDGE, x)), max(-EDGE, min(EDGE, z))
        c = self.centre(g)
        g.origin += np.array([x - c[0], 0, z - c[2]])

    def touching(self, a, b):
        return any(self.data.neighbours[i] & set(b.members) for i in a.members)

    def join(self, keep, other):
        """Put `other` in its place against `keep` (same facing) and make them one group."""
        keep.members += other.members
        self.groups.remove(other)
        self.settle(keep)
        if self.selected is other:
            self.selected = keep
        self.check()

    # ------------------------------------------------------------- drawing
    def placed_sprites(self):
        """(depth, piece, group, surface, mask, top-left) for everything, far first."""
        out = []
        for g in self.groups:
            for i in g.members:
                p = self.world(g, i)
                surf, mask = self.sprite(i, g.view)
                x, y = project(p)
                tl = (round(x - (surf.get_width() - 1) / 2), round(y - (surf.get_height() - 1) / 2))
                depth = float(p @ NEAR) + (1000 if self.held and g is self.held[0] else 0)
                out.append((depth, i, g, surf, mask, tl))
        out.sort(key=lambda t: t[0])
        return out

    def group_at(self, pos, skip=None):
        for _, _, g, surf, mask, tl in reversed(self.placed_sprites()):
            if g is skip:
                continue
            x, y = pos[0] - tl[0], pos[1] - tl[1]
            if 0 <= x < surf.get_width() and 0 <= y < surf.get_height() and mask.get_at((x, y)):
                return g
        return None

    def piece_at(self, pos):
        for _, i, g, surf, mask, tl in reversed(self.placed_sprites()):
            x, y = pos[0] - tl[0], pos[1] - tl[1]
            if 0 <= x < surf.get_width() and 0 <= y < surf.get_height() and mask.get_at((x, y)):
                return g, i
        return None

    def draw(self, surf):
        if self.background:
            surf.blit(self.background, self.background.get_rect(center=CENTRE))
        for b in self.buttons:
            b.draw(surf)
        if self.paused:
            return
        if self.selected and self.marker and not self.solved:
            c = self.centre(self.selected)
            surf.blit(self.marker, self.marker.get_rect(center=project(np.array([c[0], FLOOR, c[2]]))))
        clip = surf.get_clip()
        surf.set_clip(AREA)
        for *_, sprite, _, tl in self.placed_sprites():
            surf.blit(sprite, tl)
        surf.set_clip(clip)
        if self.hint_mode:
            text = self.app.strings.get(10910, "").replace("\r", " ")
            img = self.app.fonts.get(16).render(text, True, (248, 176, 100))
            surf.blit(img, img.get_rect(midbottom=(AREA.centerx, AREA.bottom - 6)))

    def update(self, dt):
        if not self.animate.on or self.paused:
            return
        g = self.selected or (self.groups[0] if self.solved else None)
        if g is None:
            self.animate.on = False
            return
        self.spin += dt
        while self.spin >= SPIN:
            self.spin -= SPIN
            self.turned(g, g.flip, (g.turn + 1) % 4)

    # --------------------------------------------------------------- input
    def mouse_down(self, pos):
        if self.paused or not AREA.collidepoint(pos):
            return False
        hit = self.piece_at(pos)
        if self.hint_mode:
            if hit is None:
                self.app.sounds.play(self.app.sounds.NO_CLICK)
                return True
            self.hint_mode = False
            if self.hint_join(*hit):
                self.hint_done = True
            return True
        if hit is None:
            self.selected = None
            return True
        g = hit[0]
        self.selected = g
        c = self.centre(g)
        f = floor_at(pos)
        self.held = (g, (c[0] - f[0], c[2] - f[2]), (c[0], c[2]), False)
        self.sound("SL_SEL")
        return True

    def mouse_move(self, pos):
        super().mouse_move(pos)
        if self.held:
            g, (ox, oz), home, _ = self.held
            f = floor_at(pos)
            self.move_to(g, f[0] + ox, f[2] + oz)
            self.held = (g, (ox, oz), home, True)

    def mouse_up(self, pos):
        if super().mouse_up(pos):
            return True
        if not self.held:
            return False
        g, _, home, moved = self.held
        self.held = None
        if not moved:
            return True
        target = self.group_at(pos, skip=g)
        if target is None:
            self.sound("SL_MOVE")
        elif (target.flip, target.turn) == (g.flip, g.turn) and self.touching(g, target):
            g.origin = target.origin.copy()
            self.join(target, g)
            self.sound("SL_RIGHT")
        else:
            self.move_to(g, *home)
            self.sound("SL_WRONG")
        return True

    def right_click(self, pos):
        hit = self.piece_at(pos)
        g = hit[0] if hit else self.selected
        if g:
            self.selected = g
            self.turned(g, g.flip, (g.turn + 1) % 4)
            self.sound("SL_ROTAT")

    def toggled(self, button):
        if button is self.animate:
            if not (self.selected or self.solved):
                button.on = False
                self.app.sounds.play(self.app.sounds.NO_CLICK)
            self.spin = 0.0
            return
        button.on = False
        if button in (self.rev_left, self.rev_right):
            self.revolve(1 if button is self.rev_left else -1)
            self.sound("SL_ROTAT")
            return
        g = self.selected
        if g is None:
            self.app.sounds.play(self.app.sounds.NO_CLICK)
        elif button is self.rotate:
            self.turned(g, g.flip, (g.turn + 1) % 4)
            self.sound("SL_ROTAT")
        else:
            self.turned(g, g.flip ^ 1, g.turn)
            self.sound("SL_FLIP")

    def revolve(self, step):
        """Turn the whole table a quarter turn about its middle."""
        Y = turn_matrix(step)
        for g in self.groups:
            # Y @ FX^f @ turn(k) == FX^f @ turn(k +- step)
            g.origin = Y @ g.origin
            g.turn = (g.turn + (step if g.flip == 0 else -step)) % 4

    def hint_join(self, g, i):
        """Bring one piece that touches the clicked one (in the object) into its group."""
        others = [j for j in self.data.neighbours[i] if j not in g.members]
        if not others:
            others = [j for k in g.members for j in self.data.neighbours[k] if j not in g.members]
        if not others:
            self.app.sounds.play(self.app.sounds.NO_CLICK)
            return False
        other = next(h for h in self.groups if others[0] in h.members)
        other.flip, other.turn = g.flip, g.turn
        other.origin = g.origin.copy()
        self.join(g, other)
        self.sound("SL_RIGHT")
        return True

    def use_hint(self):
        if self.solved:
            return False
        self.hint_mode = True
        return True

    def complete(self):
        g = self.groups[0]
        for other in self.groups[1:]:
            other.flip, other.turn, other.origin = g.flip, g.turn, g.origin.copy()
            g.members += other.members
        self.groups = [g]
        self.move_to(g, 0, 0)
        self.settle(g)
        self.selected = None
        self.check()
