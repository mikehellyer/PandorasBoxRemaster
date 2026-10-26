"""The game window: the 800x600 canvas, scaled to the window on the GPU.

Sharp scaling (the default) blows the canvas up by a whole number with nearest-pixel
sampling into an intermediate texture, then scales that to the window with linear
filtering ("sharp bilinear"): pixel edges stay crisp at any window size, without the
uneven pixels of plain nearest scaling. Smooth scaling stretches the canvas with
linear filtering straight away (softer, like the first remaster builds). Both keep
the 4:3 shape with black borders. If no renderer can be made, the canvas is
smooth-scaled on the CPU instead.
"""
from __future__ import annotations

import math

import pygame

WIDTH, HEIGHT = 800, 600

try:
    from pygame._sdl2 import video
except ImportError:                     # pragma: no cover - pygame-ce always has it
    video = None


def app_icon() -> pygame.Surface | None:
    try:
        from importlib.resources import files
        return pygame.image.load(str(files("pbremaster") / "resources" / "icon.png"))
    except (OSError, pygame.error, ModuleNotFoundError):
        return None


def default_size() -> tuple[int, int]:
    """About 85% of the desktop, in half steps of 800x600 (1200x900 on 1080p, 2400x1800 on 4K)."""
    try:
        dw, dh = pygame.display.get_desktop_sizes()[0]
    except (pygame.error, IndexError):
        return WIDTH, HEIGHT
    s = max(1.0, math.floor(min(dw * 0.85 / WIDTH, dh * 0.85 / HEIGHT) * 2) / 2)
    return int(WIDTH * s), int(HEIGHT * s)


class Display:
    def __init__(self, settings, title="Pandora's Box Remaster"):
        self.settings = settings
        if pygame.display.get_surface() is None:
            # Surface.convert() needs the display module's pixel format; a hidden 1x1
            # window supplies it while the real window below draws through a renderer.
            pygame.display.set_mode((1, 1), pygame.HIDDEN)
        size = tuple(settings.window_size) if settings.window_size else default_size()
        self.win = video.Window(title, size=size, resizable=True)
        icon = app_icon()
        if icon is not None:
            self.win.set_icon(icon)
        self.renderer = None
        for vsync in (True, False):
            try:
                self.renderer = video.Renderer(self.win, vsync=vsync)
                break
            except pygame.error:
                continue
        self.canvas_tex = None
        self.big = None
        self.windowed_size = size
        if settings.fullscreen:
            self.win.set_fullscreen(desktop=True)

    # ------------------------------------------------------------ geometry
    def get_size(self):
        return self.win.size

    def dest(self) -> pygame.Rect:
        ww, wh = self.win.size
        scale = min(ww / WIDTH, wh / HEIGHT)
        w, h = int(WIDTH * scale), int(HEIGHT * scale)
        return pygame.Rect((ww - w) // 2, (wh - h) // 2, w, h)

    def to_canvas(self, pos):
        d = self.dest()
        return int((pos[0] - d.x) * WIDTH / d.w), int((pos[1] - d.y) * HEIGHT / d.h)

    # ------------------------------------------------------------- drawing
    def present(self, canvas: pygame.Surface):
        if self.renderer is None:
            return self.present_cpu(canvas)
        r, d = self.renderer, self.dest()
        sharp = self.settings.sharp
        quality = 0 if sharp else 1
        if self.canvas_tex is None or self.canvas_tex_quality != quality:
            self.canvas_tex = video.Texture(r, (WIDTH, HEIGHT), streaming=True, scale_quality=quality)
            self.canvas_tex_quality = quality
        self.canvas_tex.update(canvas)
        r.target = None
        r.draw_color = (0, 0, 0, 255)
        r.clear()
        if sharp:
            k = max(1, math.ceil(d.w / WIDTH - 1e-6))
            if self.big is None or self.big.width != WIDTH * k:
                self.big = video.Texture(r, (WIDTH * k, HEIGHT * k), target=True, scale_quality=1)
            r.target = self.big
            r.blit(self.canvas_tex, self.big.get_rect())
            r.target = None
            r.blit(self.big, d)
        else:
            r.blit(self.canvas_tex, d)
        r.present()

    def present_cpu(self, canvas):
        surf = self.win.get_surface()
        surf.fill((0, 0, 0))
        d = self.dest()
        surf.blit(pygame.transform.smoothscale(canvas, d.size), d)
        self.win.flip()

    # ---------------------------------------------------------- window state
    def set_fullscreen(self, on: bool):
        if on:
            self.windowed_size = self.win.size
            self.win.set_fullscreen(desktop=True)
        else:
            self.win.set_windowed()
            self.win.size = self.windowed_size
        self.big = None

    def set_title(self, title):
        self.win.title = title

    def minimize(self):
        self.win.minimize()

    def remember_size(self):
        """Keep the windowed size for next time (not while fullscreen)."""
        if not self.settings.fullscreen:
            self.settings.window_size = list(self.win.size)

    def close(self):
        self.win.destroy()
