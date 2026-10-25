"""Load images from the original files as pygame surfaces."""
from __future__ import annotations

import io

import numpy as np
import pygame

from . import deft, gamedir
from .rof import ROF


class Assets:
    def __init__(self, game: gamedir.GameDir):
        self.game = game
        self.pandora = ROF(game.file("PANDORA.ROF"))
        self.screens = ROF(game.file("SCREENS.ROF"))
        self._cache: dict[str, pygame.Surface] = {}

    def _rof_for(self, name):
        return self.screens if name.upper().startswith("SCREENS/") else self.pandora

    def raw(self, name: str) -> bytes:
        return self._rof_for(name).read(name)

    def image(self, name: str) -> pygame.Surface:
        """An image from an archive: .RIM (with its 'A' mask if present), .PNG, .JPG, .BMP."""
        key = name.upper()
        if key in self._cache:
            return self._cache[key]
        rof = self._rof_for(key)
        if key.endswith(".RIM"):
            rgb = deft.decode_rim(rof.read(key))
            mask_name = key[:-4] + "A.RIM"
            if mask_name in rof:
                alpha = deft.decode_rim(rof.read(mask_name))
                rgba = np.dstack([rgb, alpha])
                surf = pygame.image.frombuffer(rgba.tobytes(), rgba.shape[1::-1], "RGBA").copy()
            else:
                surf = pygame.image.frombuffer(rgb.tobytes(), rgb.shape[1::-1], "RGB").copy()
        else:
            surf = pygame.image.load(io.BytesIO(rof.read(key)), key)
        self._cache[key] = surf
        return surf

    def loose_image(self, *parts: str) -> pygame.Surface:
        """An image stored as a plain file in the DATA folder (SPLASH.PNG, LOADBAR.PNG)."""
        return pygame.image.load(str(self.game.file(*parts)))
