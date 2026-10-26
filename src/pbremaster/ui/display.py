"""The game window: the 800x600 canvas, scaled to the window on the GPU.

Sharp scaling (the default) blows the canvas up by a whole number with nearest-pixel
sampling into an intermediate texture, then scales that to the window with linear
filtering ("sharp bilinear"): pixel edges stay crisp at any window size, without the
uneven pixels of plain nearest scaling. Smooth scaling stretches the canvas with
linear filtering straight away (softer, like the first remaster builds). Both keep
the 4:3 shape. On a wider window the bars either side show the dark burl of the puzzle
screens (300.RIM, set_side_art), shaded towards the picture; until the game files are
loaded, or with Settings > "Side panels" off, they are black. If no renderer can be
made, the canvas is smooth-scaled on the CPU instead.
"""
from __future__ import annotations

import math

import pygame

from . import hitext

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
        self.text_cache = {}            # (TextInfo, scale) -> image or texture
        self.text_scale = None
        self.sides = None               # (left, right) panels, 600 high, inner edge towards the picture
        self.side_tex = None
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

    # --------------------------------------------------------- side panels
    def set_side_art(self, art: pygame.Surface | None, area=pygame.Rect(75, 42, 650, 540)):
        """Widescreen side panels from a puzzle screen's dark burl (its play area)."""
        self.sides = self.side_tex = None
        if art is None:
            return
        burl = art.subsurface(area.clip(art.get_rect()))
        panel = pygame.transform.smoothscale(burl, (round(burl.get_width() * HEIGHT / burl.get_height()), HEIGHT))
        panel = panel.convert_alpha() if pygame.display.get_surface() else panel.copy()
        shade = pygame.Surface(panel.get_size(), pygame.SRCALPHA)
        w = panel.get_width()
        for x in range(w):              # darker overall, and darkest next to the picture
            t = x / (w - 1)
            edge = max(0.0, (t - 0.9) / 0.1) ** 2
            shade.fill((0, 0, 0, int(255 * min(1.0, 0.35 + 0.6 * edge))), (x, 0, 1, HEIGHT))
        panel.blit(shade, (0, 0))
        self.sides = (panel, pygame.transform.flip(panel, True, False))

    def side_spots(self, d: pygame.Rect):
        """(panel index, source rect, window rect) for the bars left and right of the picture."""
        if not (self.sides and self.settings.side_panels) or d.x <= 0:
            return []
        ww = self.win.size[0]
        scale = d.h / HEIGHT
        pw = self.sides[0].get_width()
        spots = []
        for k, bar in enumerate((pygame.Rect(0, d.y, d.x, d.h), pygame.Rect(d.right, d.y, ww - d.right, d.h))):
            need = min(pw, max(1, round(bar.w / scale)))
            src = pygame.Rect(pw - need if k == 0 else 0, 0, need, HEIGHT)
            spots.append((k, src, bar))
        return spots

    # ------------------------------------------------------------- drawing
    def lift_text(self, canvas):
        """High-resolution text (ui/hitext.py): the canvas without the text to redraw, and that text."""
        scale = self.dest().w / WIDTH
        if not (self.settings.hires_text and scale > 1.05 and hasattr(canvas, "peel")):
            return canvas, []
        if scale != self.text_scale:
            self.text_cache.clear()
            self.text_scale = scale
        return canvas.peel()

    def text_image(self, info, make):
        key = (info, self.text_scale)
        img = self.text_cache.get(key)
        if img is None:
            if len(self.text_cache) > 800:
                self.text_cache.clear()
            img = self.text_cache[key] = make(hitext.render_scaled(info, self.text_scale))
        return img

    def present(self, canvas: pygame.Surface):
        canvas, texts = self.lift_text(canvas)
        if self.renderer is None:
            return self.present_cpu(canvas, texts)
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
        spots = self.side_spots(d)
        if spots and self.side_tex is None:
            self.side_tex = [video.Texture.from_surface(r, s) for s in self.sides]
        for k, src, bar in spots:
            r.blit(self.side_tex[k], bar, src)
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
        for info, rect, shown in texts:
            tex = self.text_image(info, lambda img: video.Texture.from_surface(r, img))
            spot = hitext.place((tex.width, tex.height), rect, shown, d, self.text_scale)
            if spot:
                r.blit(tex, spot[0], spot[1])
        r.present()

    def present_cpu(self, canvas, texts=()):
        surf = self.win.get_surface()
        surf.fill((0, 0, 0))
        d = self.dest()
        for k, src, bar in self.side_spots(d):
            surf.blit(pygame.transform.smoothscale(self.sides[k].subsurface(src), bar.size), bar)
        surf.blit(pygame.transform.smoothscale(canvas, d.size), d)
        for info, rect, shown in texts:
            img = self.text_image(info, lambda img: img)
            spot = hitext.place(img.get_size(), rect, shown, d, self.text_scale)
            if spot:
                surf.blit(img, spot[0], spot[1])
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
