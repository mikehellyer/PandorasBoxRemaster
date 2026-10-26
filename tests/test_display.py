"""The window's widescreen side panels (ui/display.py)."""
import os

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


@pytest.fixture
def display():
    from pbremaster.settings import Settings
    from pbremaster.ui.display import Display

    pygame.init()

    class Win:                        # a CPU window of any size
        size = (1920, 1080)

        def get_surface(self):
            if getattr(self, "surf", None) is None or self.surf.get_size() != self.size:
                self.surf = pygame.Surface(self.size)
            return self.surf

        def flip(self):
            pass

    d = object.__new__(Display)
    d.settings, d.win, d.renderer = Settings(), Win(), None
    d.text_cache, d.text_scale, d.sides, d.side_tex = {}, None, None, None
    art = pygame.Surface((800, 600))
    art.fill((200, 120, 60))
    d.set_side_art(art)
    yield d
    pygame.quit()


def test_bars_either_side_are_filled(display):
    canvas = pygame.Surface((800, 600))
    canvas.fill((0, 0, 255))
    display.present(canvas)
    s = display.win.surf
    picture = display.dest()
    assert picture.x == 240 and picture.w == 1440
    left, right = s.get_at((100, 540)), s.get_at((1820, 540))
    assert left[:3] != (0, 0, 0) and left[:3] == right[:3]            # mirrored panels
    assert s.get_at((236, 540))[0] < left[0]                          # shaded next to the picture
    assert s.get_at((960, 540))[:3] == (0, 0, 255)


def test_off_or_without_art_the_bars_are_black(display):
    canvas = pygame.Surface((800, 600))
    display.settings.side_panels = False
    display.present(canvas)
    assert display.win.surf.get_at((100, 540))[:3] == (0, 0, 0)
    display.settings.side_panels = True
    display.set_side_art(None)
    display.present(canvas)
    assert display.win.surf.get_at((100, 540))[:3] == (0, 0, 0)


def test_no_panels_on_a_4_3_window(display):
    display.win.size = (1600, 1200)
    assert display.side_spots(display.dest()) == []
