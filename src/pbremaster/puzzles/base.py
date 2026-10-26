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
        self.on_event = None       # set by the puzzle screen when a tutorial is running

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
        self.emit(name)

    def emit(self, event):
        """Tell the tutorial what the player just did (sound names double as events)."""
        if self.on_event:
            self.on_event(event)

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
                self.press(b)
                return True
        return False

    # The type's Rotate / Flip buttons, if it has them: the R and F keys press them (ours).
    rotate = flip = None

    def press(self, button):
        button.on = not button.on
        self.app.sounds.play(self.app.sounds.CLICK)
        self.toggled(button)

    def toggled(self, button):
        pass

    def right_click(self, pos):
        pass

    def wheel(self, dy):
        pass

    def key(self, ev) -> bool:
        return False

    def use_hint(self) -> bool:
        """Start hint mode (the player then clicks the piece to place, as in the
        original: LANGENU 2052/3318/4313); False if there is nothing to place."""
        return False

    def complete(self):
        """Solve it (Free Puzzle token)."""
        self.solved = True

    def restart(self):
        pass

    # Half-finished puzzles: the player's progress keeps save_state() when the puzzle is left
    # unsolved and hands it to load_state() next time. None means "nothing to keep".
    def save_state(self):
        return None

    def load_state(self, state):
        pass

    # Undo (ours): the puzzle screen keeps save_state() after every move. UNDO is off for a
    # type whose pieces move by themselves; undo_key() leaves out what only changes the view.
    UNDO = True

    def undo_key(self, state):
        return state

    def carrying(self) -> bool:
        """A piece is picked up or being dragged: not a finished move yet."""
        return any(getattr(self, a, None) for a in ("held", "drag", "band"))

    def undo_to(self, state):
        self.load_state(state)
        self.hint_mode = False
        for a in ("selected", "hover", "moving", "held", "drag", "band"):
            if hasattr(self, a):
                setattr(self, a, [] if isinstance(getattr(self, a), list) else None)


def tup(x):
    """JSON lists back to tuples, all the way down (positions, rects)."""
    return tuple(tup(v) for v in x) if isinstance(x, list) else x
