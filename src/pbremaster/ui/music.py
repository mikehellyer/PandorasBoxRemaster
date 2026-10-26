"""Music, following the MediaGraph script DATA/MUSIC/PANDORA.MGD.

LocationCF cross-fades between: 0 silence, 1 the city's region track,
2 MAP.WAV (map and menus), 3 the region's _P track while in a puzzle,
4 LEVEND.WAV. INTRO.WAV plays once at start-up, then the map music.
One-shots on their own channel: S_<region>.WAV on success, CHWIN.WAV when a
challenge is won, C_<trickster>.WAV for the trickster, VO/SX_<name><n>.WAV for
the story when a piece is found, CHMODE.WAV for the challenge.
"""
from __future__ import annotations

import pygame

FADE = 2.0          # seconds, LocationCF.FadeTo(..., 2, ...)


class Music:
    def __init__(self, game, settings):
        self.game, self.settings = game, settings
        self.ok = pygame.mixer.get_init() is not None
        self.cache: dict[str, pygame.mixer.Sound | None] = {}
        self.loop_name = None
        self.loops: list[list] = []          # [channel, sound name, volume, target]
        self.after_sting = None      # loop to start when the current one-shot ends
        if self.ok:
            pygame.mixer.set_num_channels(16)
            self.channels = [pygame.mixer.Channel(i) for i in (12, 13, 14, 15)]

    def _sound(self, rel):
        if rel not in self.cache:
            try:
                parts = rel.split("/")
                self.cache[rel] = pygame.mixer.Sound(str(self.game.file(*parts)))
            except (FileNotFoundError, pygame.error):
                self.cache[rel] = None
        return self.cache[rel]

    @property
    def volume(self):
        return 1.0 if self.settings.music else 0.0

    def play_loop(self, rel: str | None):
        """Cross-fade to a looping track (None = silence)."""
        if not self.ok or rel == self.loop_name:
            return
        self.after_sting = None
        self.loop_name = rel
        for entry in self.loops:
            entry[3] = 0.0
        if rel is None:
            return
        snd = self._sound(rel)
        if snd is None:
            return
        busy = {id(e[0]) for e in self.loops}
        ch = next((c for c in self.channels[:3] if id(c) not in busy), None)
        if ch is None:
            oldest = self.loops.pop(0)
            oldest[0].stop()
            ch = oldest[0]
        ch.play(snd, loops=-1)
        ch.set_volume(0.0)
        self.loops.append([ch, rel, 0.0, 1.0])

    def play_once(self, rel: str):
        if not self.ok:
            return
        snd = self._sound(rel)
        if snd is not None:
            self.channels[3].play(snd)
            self.channels[3].set_volume(self.volume)

    def theme(self, rel: str):
        """Loop `rel`, but only after a playing one-shot ends (INTRO.WAV, then MAP.WAV)."""
        if self.ok and self.channels[3].get_busy():
            self.play_loop(None)
            self.after_sting = rel
        else:
            self.play_loop(rel)

    def update(self, dt):
        if not self.ok:
            return
        step = dt / FADE
        keep = []
        for entry in self.loops:
            ch, _, vol, target = entry
            vol = min(target, vol + step) if vol < target else max(target, vol - step)
            entry[2] = vol
            ch.set_volume(vol * self.volume)
            if vol <= 0.0 and target == 0.0:
                ch.stop()
            else:
                keep.append(entry)
        self.loops = keep
        self.channels[3].set_volume(self.volume)
        if self.after_sting and not self.channels[3].get_busy():
            rel, self.after_sting = self.after_sting, None
            self.play_loop(rel)

    def stop(self):
        if self.ok:
            for c in self.channels:
                c.stop()
        self.loops, self.loop_name = [], None
