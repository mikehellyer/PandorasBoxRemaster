"""Outer Layer (3DSKIN.SKI, C3DSkinObject).

"Click a piece on the left, and then drag it over the egg and place it where you
think it fits. ... Right-click to rotate a selected piece. ... You can move pieces
to different stacks. ... Click the direction arrows on the table to change your
point of view." (LANGENU 6208-6212)

A picture is wrapped round a 3D object. The view is one of four pre-rendered
cameras: where its warp map (data.ski) shows the object, a pixel is the texture
under it times MULT plus ADD; elsewhere the BACK render. Pieces sit on four
stacks on the left (UPARROW/DNARROW step through a stack) or on the texture; drag
one onto the object and the point you hold it by lands on the texture point under
the cursor (so a piece whose middle no camera shows, as 59 of 1323 are, can be laid
by an edge); the warp map also picks pieces up. A piece dropped near its place facing
upright snaps in and stays. All pieces in place solves it.
**Interpretation:** stack layout and arrow positions, the snap distance (a fifth
of a piece), pieces that start on the object in place counting as placed,
REVLF/REVRT (and number keys 1-4) for the cameras instead of hotspots on the
table arrows, hint = put the clicked piece in its place, BRACKET0-3 round the
selection. Sounds as other puzzles' (3DSKIN has none of its own).
"""
from __future__ import annotations

import pygame
import numpy as np

from ..data import ski
from .base import AREA, PuzzleGame, ToggleButton

LEFT = pygame.Rect(0, AREA.y, 185, 540)
VIEW = pygame.Rect(185, AREA.y, 540, 540)
TRAY_H = LEFT.h // ski.TRAYS
THUMB = 96


class Piece:
    def __init__(self, sprite: ski.SkiSprite, image):
        self.sprite = sprite
        self.image = image
        self.angle = sprite.start_angle
        self.pos = sprite.start if sprite.tray == ski.ON_OBJECT else None    # top-left in the texture
        self.placed = False

    @property
    def right(self):
        return self.pos == self.sprite.final and self.angle == self.sprite.final_angle

    def turned(self):
        return pygame.transform.rotate(self.image, -self.angle) if self.angle else self.image


class OuterLayer(PuzzleGame):
    SOUND_FOLDER = "SCREENS"

    def __init__(self, app, puzzle):
        super().__init__(app, puzzle)
        folder = puzzle.files[0].rsplit("/", 1)[0]
        self.folder = folder
        self.data = ski.parse(self.raw(f"{folder}/3DSKIN.SKI"))
        self.bare = self.app.assets.image(f"{folder}/3DSKIN_BACK.PNG").convert()
        self.images = {s.index: self.app.assets.image(f"{folder}/3DSKIN_SPR{s.index}.PNG").convert()
                       for s in self.data.sprites}
        cams = sorted({f.split("/")[-2] for f in puzzle.files if "/CAMERA" in f})
        self.cameras = []
        for c in cams:
            inside, x, y = ski.warp(self.raw(f"{folder}/{c}/WARPER.MAP"))
            files = {f.rsplit("/", 1)[1].split(".")[0]: f for f in puzzle.files if f"/{c}/" in f}
            arr = lambda n: pygame.surfarray.array3d(self.app.assets.image(files[n])).swapaxes(0, 1)
            self.cameras.append((inside, x, y, arr("BACK"), arr("MULT") / 255.0, arr("ADD").astype(np.float32)))
        self.left_bg = self.png("3DSKIN/302.PNG")
        self.brackets = [self.png(f"3DSKIN/BRACKET{k}.PNG") for k in range(4)]
        for b in self.brackets:
            if b:
                b.set_colorkey((0, 0, 255))
        self.ups, self.downs = [], []
        for t in range(ski.TRAYS):
            top = LEFT.y + t * TRAY_H
            self.ups.append(ToggleButton(self, "3DSKIN", "UPARROW", (LEFT.right - 34, top + 8)))
            self.downs.append(ToggleButton(self, "3DSKIN", "DNARROW", (LEFT.right - 34, top + TRAY_H - 36)))
        self.rotate = ToggleButton(self, "3DSKIN", "ROTATE", (740, 300))
        self.go_left = ToggleButton(self, "3DSKIN", "REVLF", (741, 350))
        self.go_right = ToggleButton(self, "3DSKIN", "REVRT", (741, 396))
        self.buttons = self.ups + self.downs + [self.rotate, self.go_left, self.go_right]
        self.restart()

    # --------------------------------------------------------------- state
    def restart(self):
        self.pieces = [Piece(s, self.images[s.index]) for s in self.data.sprites]
        self.stacks = [[] for _ in range(ski.TRAYS)]
        for p in sorted(self.pieces, key=lambda p: p.sprite.tray_order):
            if p.sprite.tray == ski.ON_OBJECT:
                p.placed = p.right
            else:
                self.stacks[p.sprite.tray % ski.TRAYS].append(p)       # [0] = shown
        self.camera = min(self.data.camera, len(self.cameras) - 1)
        self.selected = None
        self.held = None
        self.hint_mode = False
        self.dirty = True
        self.check()

    def check(self):
        self.solved = all(p.placed for p in self.pieces)

    def save_state(self):
        return {"pieces": [[p.angle, list(p.pos) if p.pos is not None else None, p.placed] for p in self.pieces],
                "stacks": [[self.pieces.index(p) for p in s] for s in self.stacks], "camera": self.camera}

    def undo_key(self, state):
        return state["pieces"], state["stacks"]      # turning the view isn't a move

    def load_state(self, state):
        for p, (angle, pos, placed) in zip(self.pieces, state["pieces"]):
            p.angle, p.pos, p.placed = angle, tuple(pos) if pos is not None else None, placed
        self.stacks = [[self.pieces[i] for i in s] for s in state["stacks"]]
        self.camera = min(state.get("camera", self.camera), len(self.cameras) - 1)
        self.dirty = True
        self.check()

    def on_object(self):
        return [p for p in self.pieces if p.pos is not None]

    def texture_at(self, pos):
        if not VIEW.collidepoint(pos):
            return None
        inside, x, y = self.cameras[self.camera][:3]
        vx, vy = pos[0] - VIEW.x, pos[1] - VIEW.y
        return (int(x[vy, vx]), int(y[vy, vx])) if inside[vy, vx] else None

    def piece_on_texture(self, point):
        for p in reversed(self.on_object()):
            w, h = p.image.get_size()
            if p.pos[0] <= point[0] < p.pos[0] + w and p.pos[1] <= point[1] < p.pos[1] + h:
                return p
        return None

    def take(self, p):
        for s in self.stacks:
            if p in s:
                s.remove(p)
        if p.pos is not None:
            p.pos = None
            self.dirty = True

    def put_on_object(self, p, point, grab=None):
        """Lay the piece so its point `grab` (default: its middle) is on texture `point`."""
        w, h = p.image.get_size()
        gx, gy = grab if grab else (w // 2, h // 2)
        x, y = point[0] - gx, point[1] - gy
        fx, fy = p.sprite.final
        if p.angle == p.sprite.final_angle and abs(x - fx) <= w // 5 and abs(y - fy) <= h // 5:
            x, y = fx, fy
        p.pos = (x, y)
        self.pieces.remove(p)
        self.pieces.append(p)                       # drawn on top
        p.placed = p.right
        self.dirty = True
        self.check()
        return p.placed

    # ------------------------------------------------------------- drawing
    def render_view(self):
        tex = self.bare.copy()
        for p in self.on_object():
            tex.blit(p.turned(), p.pos)
        t = pygame.surfarray.array3d(tex).swapaxes(0, 1)
        inside, x, y, back, mult, add = self.cameras[self.camera]
        x = np.clip(x, 0, t.shape[1] - 1)
        y = np.clip(y, 0, t.shape[0] - 1)
        lit = np.clip(t[y, x] * mult + add, 0, 255).astype(np.uint8)
        out = np.where(inside[..., None], lit, back)
        self.view = pygame.image.frombuffer(np.ascontiguousarray(out).tobytes(), (540, 540), "RGB").copy()
        self.dirty = False

    def draw(self, surf):
        if self.left_bg:
            surf.blit(self.left_bg, LEFT)
        for b in [self.rotate, self.go_left, self.go_right]:
            b.draw(surf)
        if self.paused:
            return
        if self.dirty:
            self.render_view()
        surf.blit(self.view, VIEW)
        for t, stack in enumerate(self.stacks):
            box = self.tray_box(t)
            shown = [p for p in stack if not (self.held and self.held[0] is p)]
            if shown:
                p = shown[0]
                img = pygame.transform.smoothscale(p.turned(), (THUMB, THUMB))
                surf.blit(img, img.get_rect(center=box.center))
                if p is self.selected:
                    self.draw_brackets(surf, img.get_rect(center=box.center))
                if len(shown) > 1:
                    self.ups[t].draw(surf)
                    self.downs[t].draw(surf)
                    n = self.app.fonts.get(14).render(str(len(shown)), True, (248, 176, 100))
                    surf.blit(n, (box.x + 6, box.y + 6))
        if self.held:
            p, pos, (gx, gy) = self.held
            w, h = p.image.get_size()
            img = pygame.transform.smoothscale(p.turned(), (THUMB, THUMB))
            surf.blit(img, (pos[0] - gx * THUMB // w, pos[1] - gy * THUMB // h))
        if self.hint_mode:
            text = self.app.strings.get(6206, "").replace("\r", " ")
            img = self.app.fonts.get(16).render(text, True, (248, 176, 100))
            surf.blit(img, img.get_rect(midbottom=(VIEW.centerx, VIEW.bottom - 6)))

    def draw_brackets(self, surf, r):
        b = self.brackets
        if all(b):
            surf.blit(b[0], (r.x - 4, r.y - 4))
            surf.blit(b[1], (r.right - b[1].get_width() + 4, r.y - 4))
            surf.blit(b[2], (r.x - 4, r.bottom - b[2].get_height() + 4))
            surf.blit(b[3], (r.right - b[3].get_width() + 4, r.bottom - b[3].get_height() + 4))

    def tray_box(self, t):
        return pygame.Rect(LEFT.x + 10, LEFT.y + t * TRAY_H + 4, LEFT.w - 50, TRAY_H - 8)

    def tray_at(self, pos):
        if not LEFT.collidepoint(pos):
            return None
        return min(ski.TRAYS - 1, (pos[1] - LEFT.y) // TRAY_H)

    # --------------------------------------------------------------- input
    def mouse_down(self, pos):
        if self.paused:
            return False
        if any(b.rect.collidepoint(pos) for b in self.buttons):
            return False
        p, grab = None, None
        t = self.tray_at(pos)
        if t is not None and self.stacks[t]:
            p = self.stacks[t][0]
            w, h = p.image.get_size()
            r = pygame.Rect(0, 0, THUMB, THUMB)
            r.center = self.tray_box(t).center
            gx = max(0, min(THUMB - 1, pos[0] - r.x)) * w // THUMB
            gy = max(0, min(THUMB - 1, pos[1] - r.y)) * h // THUMB
            grab = (gx, gy)
        elif t is None:
            point = self.texture_at(pos)
            q = self.piece_on_texture(point) if point else None
            if q and not q.placed:
                p = q
                grab = (point[0] - q.pos[0], point[1] - q.pos[1])
        if self.hint_mode:
            if p is None:
                self.app.sounds.play(self.app.sounds.NO_CLICK)
                return True
            self.hint_mode = False
            self.take(p)
            p.angle = p.sprite.final_angle
            self.put_on_object(p, p.sprite.final, (0, 0))
            self.hint_done = True
            return True
        if p is None:
            return bool(t is not None or VIEW.collidepoint(pos))
        self.selected = p
        if p.pos is not None:
            self.take(p)
        self.held = (p, pos, grab)
        self.app.sounds.play(self.app.sounds.CLICK)
        return True

    def mouse_move(self, pos):
        super().mouse_move(pos)
        if self.held:
            self.held = (self.held[0], pos, self.held[2])

    def mouse_up(self, pos):
        if not self.held:
            return super().mouse_up(pos)
        p, _, grab = self.held
        self.held = None
        point = self.texture_at(pos)
        t = self.tray_at(pos)
        if point is not None:
            self.take(p)
            if self.put_on_object(p, point, grab):
                self.app.sounds.play(self.app.sounds.CLICK)
                self.emit("place")
        elif t is not None:
            self.take(p)
            self.stacks[t].insert(0, p)
            self.emit("stack")
        elif p.pos is None and not any(p in s for s in self.stacks):
            self.stacks[0].insert(0, p)                # picked off the object, dropped nowhere
        return True

    def right_click(self, pos):
        t = self.tray_at(pos)
        p = self.stacks[t][0] if t is not None and self.stacks[t] else self.selected
        if p is not None and not p.placed and self.data.rotation:
            self.selected = p
            p.angle = (p.angle + 90) % 360
            self.emit("rotate")
            if p.pos is not None:
                self.dirty = True
                p.placed = p.right
                self.check()

    def toggled(self, button):
        button.on = False
        if button in self.ups or button in self.downs:
            t = (self.ups + self.downs).index(button) % ski.TRAYS
            s = self.stacks[t]
            if len(s) > 1:
                if button in self.ups:
                    s.insert(0, s.pop())
                else:
                    s.append(s.pop(0))
        elif button is self.rotate:
            if self.selected is not None and not self.selected.placed:
                self.right_click((-1, -1))
            else:
                self.app.sounds.play(self.app.sounds.NO_CLICK)
        else:
            step = -1 if button is self.go_left else 1
            self.camera = (self.camera + step) % len(self.cameras)
            self.dirty = True
            self.emit("view")

    def key(self, ev):
        if pygame.K_1 <= ev.key < pygame.K_1 + len(self.cameras):
            self.camera = ev.key - pygame.K_1
            self.dirty = True
            self.emit("view")
            return True
        return False

    def use_hint(self):
        if self.solved:
            return False
        self.hint_mode = True
        return True

    def complete(self):
        for p in self.pieces:
            self.take(p)
            p.angle = p.sprite.final_angle
            p.pos = p.sprite.final
            p.placed = True
        self.dirty = True
        self.check()
