"""AVI playback (Indeo 5 video + PCM audio) through PyAV.

The game shows its movies on screen 40: SCREENS/AVIBACK.PNG with the
448x336 video at (176, 132) (0x419322).
"""
from __future__ import annotations

import numpy as np
import pygame

try:
    import av
except ImportError:          # videos are skipped without PyAV
    av = None

RECT = pygame.Rect(176, 132, 448, 336)


class Video:
    def __init__(self, path, sound_on=True):
        self.ok = av is not None
        self.done = not self.ok
        self.frame = None
        self.elapsed = 0.0
        self.channel = None
        if not self.ok:
            return
        self.container = av.open(str(path))
        self.stream = self.container.streams.video[0]
        self.frames = self.container.decode(self.stream)
        self.fps = float(self.stream.average_rate or 15)
        self.shown = -1
        if sound_on and pygame.mixer.get_init():
            self._start_audio(path)

    def _start_audio(self, path):
        with av.open(str(path)) as c:
            if not c.streams.audio:
                return
            freq, _, channels = pygame.mixer.get_init()
            resampler = av.AudioResampler(format="s16", layout="stereo" if channels == 2 else "mono", rate=freq)
            chunks = []
            for frame in c.decode(c.streams.audio[0]):
                for f in resampler.resample(frame):
                    chunks.append(f.to_ndarray().reshape(-1, channels))
            if chunks:
                pcm = np.ascontiguousarray(np.concatenate(chunks))
                self.channel = pygame.sndarray.make_sound(pcm).play()

    def update(self, dt: float):
        if self.done:
            return
        self.elapsed += dt
        want = int(self.elapsed * self.fps)
        while self.shown < want:
            try:
                f = next(self.frames)
            except (StopIteration, av.error.EOFError):
                self.done = True
                break
            self.shown += 1
            if self.shown >= want:
                rgb = f.to_ndarray(format="rgb24")
                self.frame = pygame.image.frombuffer(rgb.tobytes(), (rgb.shape[1], rgb.shape[0]), "RGB")

    def stop(self):
        self.done = True
        if self.channel:
            self.channel.stop()
        if self.ok:
            self.container.close()
