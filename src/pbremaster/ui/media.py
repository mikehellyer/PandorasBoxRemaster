"""Fonts and sounds from the original files."""
from __future__ import annotations

import pygame

from ..data import gamedir
from .hitext import HiFont


class Fonts:
    """Book Antiqua (DATA/BKANT.TTF), the font every screen uses (LANGENU 31)."""

    def __init__(self, game: gamedir.GameDir):
        try:
            self.path = str(game.file("BKANT.TTF"))
        except FileNotFoundError:
            self.path = None
        self._cache = {}

    def get(self, size: int, bold=False) -> pygame.font.Font:
        # GDI's CreateFont(-size) asks for a character (em) height of `size` pixels,
        # which is what pygame's size means for a TrueType font.
        key = (size, bold)
        if key not in self._cache:
            self._cache[key] = HiFont(self, self.path, size, bold)    # remembers its text (ui/hitext.py)
        return self._cache[key]


class Sounds:
    """UI sound effects from DATA/SCREENS/*.WAV, by the ids the game registers (0x4f89e8)."""

    MOUSE_OVER, CLICK, ALERT, NO_CLICK, HELP = "MO", "CLICK", "ALERT", "NOCLICK", "HELP"

    def __init__(self, game: gamedir.GameDir, settings):
        self.game = game
        self.settings = settings
        self._cache = {}
        self.ok = pygame.mixer.get_init() is not None

    def play(self, name: str, folder="SCREENS"):
        if not (self.ok and self.settings.sound):
            return
        key = (folder, name)
        if key not in self._cache:
            try:
                self._cache[key] = pygame.mixer.Sound(str(self.game.file(folder, name + ".WAV")))
            except (FileNotFoundError, pygame.error):
                self._cache[key] = None
        if self._cache[key]:
            self._cache[key].play()
