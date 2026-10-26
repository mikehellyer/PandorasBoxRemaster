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


def interlocks(app):
    return [p for lv in app.levels.values()
            for p in list(lv.puzzles.values()) + [q for c in lv.cities.values() for q in c.puzzles.values()]
            if p.kind_name == "Interlock"]


def amsterdam(app):
    from pbremaster.puzzles.interlock import Interlock
    return Interlock(app, app.levels[6].cities["CITY.01.AMSTERDAM"].puzzles[8])


def test_every_interlock_loads(app):
    from pbremaster.puzzles.interlock import Interlock, board_down

    puzzles = interlocks(app)
    assert len(puzzles) == 12
    for p in puzzles:
        g = Interlock(app, p)
        sol = g.data.solution
        assert sorted(s.type for s in sol) == list(range(7))
        assert all(s.down == board_down(s.x, s.y) for s in sol)          # solutions sit on the lattice
        assert sum(len(s.cells()) for s in sol) == len(g.holes) == 32     # no overlaps
        g.draw(app.canvas)


def test_turning_and_placing(app):
    from pbremaster.data import tri

    g = amsterdam(app)
    p = g.pieces[0]
    h = p.home
    p.at = tri.Placement(h.type, h.flip ^ 1, h.x, h.y, h.rotation)
    assert not g.try_place(p)
    g.turn(p, rotate=False)                       # flip back -> fits
    assert p.placed


def test_drag_onto_home(app):
    g = amsterdam(app)
    p = next(q for q in g.pieces if q.at.flip == q.home.flip and q.at.rotation == q.home.rotation)
    poly = g.piece_polys(p.at)[0]
    grab = (sum(x for x, _ in poly) / 3, sum(y for _, y in poly) / 3)
    g.mouse_down(grab)
    assert g.held
    _, (ox, oy) = g.held
    target = g.tri_points(p.home.x - ox, p.home.y - oy, True)
    # move the grab point to the same triangle of the home placement
    hp = g.piece_polys(p.home)[0]
    dest = (sum(x for x, _ in hp) / 3, sum(y for _, y in hp) / 3)
    g.mouse_move(dest)
    g.mouse_up(dest)
    assert p.placed


def test_hint_and_complete(app):
    g = amsterdam(app)
    p = g.pieces[3]
    assert g.use_hint()
    poly = g.piece_polys(p.at)[0]
    g.mouse_down((sum(x for x, _ in poly) / 3, sum(y for _, y in poly) / 3))
    assert p.placed and g.hint_done
    g.complete()
    assert g.solved
