"""High-resolution text (ui/hitext.py): which text is lifted off the canvas to be redrawn."""
import os

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


@pytest.fixture
def fonts():
    from pbremaster.ui.hitext import HiFont

    pygame.init()

    class Fonts:                      # the shape of ui.media.Fonts, with pygame's own font
        def __init__(self):
            self.cache = {}

        def get(self, size, bold=False):
            return self.cache.setdefault((size, bold), HiFont(self, None, size, bold))

    yield Fonts()
    pygame.quit()


def canvas():
    from pbremaster.ui.hitext import TextCanvas

    c = TextCanvas((200, 100))
    c.fill((40, 20, 10))
    return c


def test_text_is_lifted_and_the_background_put_back(fonts):
    c = canvas()
    blank = pygame.image.tobytes(c, "RGB")
    shadow = fonts.get(16).render("Hello", True, (0, 0, 0))
    text = fonts.get(16).render("Hello", True, (255, 255, 255))
    c.blit(shadow, (12, 12))                  # a drop shadow under the text, overlapping it
    c.blit(text, (10, 10))
    out, lifted = c.peel()
    assert [i.colour[:3] for i, _, _ in lifted] == [(0, 0, 0), (255, 255, 255)]   # drawing order
    assert pygame.image.tobytes(out, "RGB") == blank
    assert lifted[1][1] == pygame.Rect((10, 10), text.get_size())


def test_text_drawn_over_stays_in_the_canvas(fonts):
    c = canvas()
    c.blit(fonts.get(16).render("Covered", True, (255, 255, 255)), (10, 10))
    c.blit(fonts.get(16).render("Free", True, (255, 255, 255)), (10, 60))
    patch = pygame.Surface((8, 8))
    patch.fill((0, 0, 255))
    c.blit(patch, (14, 14))                   # e.g. a dialog or a dragged piece
    before = pygame.image.tobytes(c.subsurface((0, 0, 200, 50)), "RGB")
    out, lifted = c.peel()
    assert [i.text for i, _, _ in lifted] == ["Free"]
    assert pygame.image.tobytes(out.subsurface((0, 0, 200, 50)), "RGB") == before


def test_clipped_text_keeps_its_clip(fonts):
    from pbremaster.ui.hitext import place

    c = canvas()
    c.set_clip(pygame.Rect(0, 0, 30, 100))
    c.blit(fonts.get(16).render("A long line", True, (255, 255, 255)), (10, 10))
    c.set_clip(None)
    _, [(info, rect, shown)] = c.peel()
    assert shown.right == 30 and rect.right > 30
    img = fonts.get(32).render_plain(info)
    dest, src = place(img.get_size(), rect, shown, pygame.Rect(0, 0, 400, 200), 2.0)
    assert dest.right <= 60 and src.size == dest.size


def test_redrawn_at_the_scaled_size(fonts):
    from pbremaster.ui.hitext import render_scaled

    info = fonts.get(16, bold=True).render("Hi", True, (255, 0, 0))
    from pbremaster.ui.hitext import _texts
    big = render_scaled(_texts[info], 2.0)
    assert big.get_height() > info.get_height() * 1.7
    assert fonts.get(32, True).bold
