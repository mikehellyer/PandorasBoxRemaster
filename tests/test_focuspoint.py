import os

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture
def app(game, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from pbremaster.settings import Settings
    from pbremaster.ui.app import App

    pygame.init()
    a = App(game, Settings.load())
    a.open_window()
    yield a
    pygame.quit()


def fpn_puzzles(app):
    return [p for lv in app.levels.values()
            for p in list(lv.puzzles.values()) + [q for c in lv.cities.values() for q in c.puzzles.values()]
            if p.kind_name == "Focus Point"]


def test_every_focus_point_loads(app):
    from pbremaster.puzzles.focuspoint import FocusPoint

    puzzles = fpn_puzzles(app)
    assert len(puzzles) == 71
    for p in puzzles:
        g = FocusPoint(app, p)
        assert not g.solved
        g.draw(app.canvas)


def test_swapping_solves_and_locks(app):
    from pbremaster.puzzles.focuspoint import FocusPoint

    cairo = app.levels[1].cities["CITY.06.CAIRO"]
    g = FocusPoint(app, cairo.puzzles[1])
    g.anim.on = False
    homes = g.data.homes
    while not g.solved:
        i = next(k for k in range(len(homes)) if not g.locked[k])
        j = g.where.index(homes[i])
        g.swap(i, j)
        assert g.locked[i]
    assert g.where == homes


def test_clicks_and_hint(app):
    from pbremaster.puzzles.focuspoint import FocusPoint

    cairo = app.levels[1].cities["CITY.06.CAIRO"]
    g = FocusPoint(app, cairo.puzzles[1])
    free = [k for k in range(len(g.where)) if not g.locked[k]]
    a, b = free[0], free[1]
    centre = lambda k: (g.origin[0] + g.where[k][0] + 2, g.origin[1] + g.where[k][1] + 2)
    pa, pb = centre(a), centre(b)
    g.mouse_down(pa)
    assert g.selected == a
    g.mouse_down(pb)
    assert g.selected is None and g.where[a] == g.data.slots[b]
    g.update(1.0)                                   # let the swap animation finish
    before = sum(g.locked)
    assert g.use_hint() and g.hint_mode
    k = next(k for k in range(len(g.where)) if not g.locked[k])
    g.mouse_down(centre(k))                         # click the piece to place
    assert g.locked[k] and g.hint_done and sum(g.locked) > before
    g.complete()
    assert g.solved
