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


def jesse(app):
    return [p for lv in app.levels.values()
            for p in list(lv.puzzles.values()) + [q for c in lv.cities.values() for q in c.puzzles.values()]
            if p.kind_name == "Jesse's Strips"]


def screen_of(g, cell):
    c = g.data.cell
    return (g.origin[0] + cell[0] * c + c // 2, g.origin[1] + cell[1] * c + c // 2)


def test_every_jesse_loads(app):
    from pbremaster.puzzles.jesse import JessesStrips

    puzzles = jesse(app)
    assert len(puzzles) == 43
    for p in puzzles:
        g = JessesStrips(app, p)
        assert not g.solved
        g.draw(app.canvas)


def test_drag_rotate_place(app):
    from pbremaster.puzzles.jesse import JessesStrips

    g = JessesStrips(app, app.levels[2].cities["CITY.13.LONDON"].puzzles[3])
    p = next(q for q in g.loose())
    g.mouse_down(screen_of(g, p.cell))
    assert g.selected == [p]
    while p.turns:                                   # rotate it upright
        g.rotate_selected()
    x, y, w, h = p.footprint()
    g.mouse_down(screen_of(g, (x, y)))
    g.mouse_move(screen_of(g, p.strip.home))
    g.mouse_up(screen_of(g, p.strip.home))
    assert p.placed


def test_trays_and_hint(app):
    from pbremaster.puzzles.jesse import TABS, JessesStrips

    g = JessesStrips(app, app.levels[2].cities["CITY.13.LONDON"].puzzles[3])
    g.mouse_down(TABS[2].center)
    assert g.tray == 2 and all(p.tray == 2 for p in g.loose())
    p = g.loose()[0]
    assert g.use_hint()
    x, y, w, h = p.footprint()
    g.mouse_down(screen_of(g, (x, y)))
    assert p.placed and g.hint_done
    g.complete()
    assert g.solved
