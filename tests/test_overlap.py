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


def overlaps(app):
    return [p for lv in app.levels.values()
            for p in list(lv.puzzles.values()) + [q for c in lv.cities.values() for q in c.puzzles.values()]
            if p.kind_name == "Overlap"]


def test_every_overlap_loads_and_covers(app):
    from pbremaster.data import fsh
    from pbremaster.puzzles.overlap import Overlap

    puzzles = overlaps(app)
    assert len(puzzles) == 63
    for p in puzzles:
        g = Overlap(app, p)
        d = g.data
        cells = set(d.shown)
        for pc in d.pieces:
            ax, ay = pc.anchor
            cells |= {(ax + x, ay + y) for x, y in fsh.shape_cells(pc.shape, pc.rotation)}
        assert {(x, y) for x in range(d.cols) for y in range(d.rows)} <= cells
        g.draw(app.canvas)


def drop_on_home(g, p):
    from pbremaster.puzzles.overlap import STACKS
    k = p.stack
    while g.showing(k) is not p:
        g.top[k] += 1
    g.mouse_down(STACKS[k].center)
    img, (mx, my) = g.piece_image(p)
    gx, gy = g.held[1]
    x, y = g.cell_xy((p.data.anchor[0] + mx, p.data.anchor[1] + my))
    g.mouse_up((x + gx, y + gy))


def test_rotate_and_place(app):
    from pbremaster.puzzles.overlap import Overlap

    g = Overlap(app, app.levels[1].cities["CITY.06.CAIRO"].puzzles[4])
    p = next(q for q in g.pieces if q.turns)
    drop_on_home(g, p)
    assert not p.placed                      # still turned
    while p.turns:
        g.turn(p)
    drop_on_home(g, p)
    assert p.placed


def test_move_between_stacks_and_hint(app):
    from pbremaster.puzzles.overlap import STACKS, Overlap

    g = Overlap(app, app.levels[1].cities["CITY.06.CAIRO"].puzzles[4])
    p = g.showing(0)
    g.mouse_down(STACKS[0].center)
    g.mouse_up(STACKS[3].center)
    assert p.stack == 3 and g.showing(3) is p
    assert g.use_hint()
    g.mouse_down(STACKS[3].center)
    assert p.placed and g.hint_done
    g.complete()
    assert g.solved
