"""What every puzzle game shares: the play area, its own toggle buttons, sounds."""
from __future__ import annotations

import io

import pygame

AREA = pygame.Rect(75, 42, 650, 540)


class ToggleButton:
    """A puzzle's own button: four PNGs (_u, _uh, _d, _dh) with pure-blue colour key."""

    def __init__(self, game, folder, stem, pos, on=False, tip=""):
        self.game = game
        self.images = {}
        for state in ("u", "uh", "d", "dh"):
            img = game.png(f"{folder}/{stem}_{state}.PNG")
            if img is not None:
                img.set_colorkey((0, 0, 255))
            self.images[state] = img
        size = next((i.get_size() for i in self.images.values() if i), (48, 37))
        self.rect = pygame.Rect(pos, size)
        self.on = on
        self.hover = False
        self.tip = tip

    def draw(self, surf):
        key = ("d" if self.on else "u") + ("h" if self.hover else "")
        img = self.images.get(key) or self.images.get(key[0])
        if img:
            surf.blit(img, self.rect)


class PuzzleGame:
    """Base class. Subclasses load their data in __init__ and set self.solved."""
    SOUND_FOLDER = ""

    def __init__(self, app, puzzle):
        self.app, self.puzzle = app, puzzle
        self.solved = False
        self.paused = False
        self.hint_mode = False     # Hint pressed: the next click picks the piece to place
        self.hint_done = False     # set when a hint has been used (the scene charges it)
        self.buttons: list[ToggleButton] = []

    # helpers
    def raw(self, name):
        return self.app.assets.raw(name)

    def png(self, name):
        try:
            return self.app.assets.image(name)
        except KeyError:
            return None

    def image_from_bytes(self, data, name="p.jpg"):
        return pygame.image.load(io.BytesIO(data), name).convert()

    def sound(self, name):
        self.app.sounds.play(name, folder=self.SOUND_FOLDER)

    # interface used by PuzzleScene
    def update(self, dt):
        pass

    def draw(self, surf):
        pass

    def mouse_move(self, pos):
        for b in self.buttons:
            b.hover = b.rect.collidepoint(pos)

    def mouse_down(self, pos):
        return False

    def mouse_up(self, pos):
        for b in self.buttons:
            if b.rect.collidepoint(pos):
                b.on = not b.on
                self.app.sounds.play(self.app.sounds.CLICK)
                self.toggled(b)
                return True
        return False

    def toggled(self, button):
        pass

    def use_hint(self) -> bool:
        """Start hint mode (the player then clicks the piece to place, as in the
        original: LANGENU 2052/3318/4313); False if there is nothing to place."""
        return False

    def complete(self):
        """Solve it (Free Puzzle token)."""
        self.solved = True

    def restart(self):
        pass
