import os
import random

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


def all_rotascopes(app):
    return [p for lv in app.levels.values()
            for p in list(lv.puzzles.values()) + [q for c in lv.cities.values() for q in c.puzzles.values()]
            if p.kind_name == "Rotascope"]


def test_every_rotascope_loads(app):
    from pbremaster.puzzles.rotascope import Rotascope

    puzzles = all_rotascopes(app)
    assert len(puzzles) == 55
    for p in puzzles:
        g = Rotascope(app, p)
        assert not g.solved
        g.draw(app.canvas)


def test_moves_and_solving(app):
    from pbremaster.data.rtt import GAP
    from pbremaster.puzzles.rotascope import CENTRE, Rotascope

    cairo = app.levels[1].cities["CITY.06.CAIRO"]
    g = Rotascope(app, cairo.puzzles[3])
    g.anim.on = False
    g.complete()
    assert g.solved and g.at[CENTRE] == GAP
    # only neighbours of the gap can move
    assert set(g.neighbours(CENTRE)) == {(0, s) for s in range(4)}
    rng = random.Random(1)
    history = []
    for _ in range(40):
        gap = g.gap()
        pos = rng.choice(g.neighbours(gap))
        g.move(pos)
        history.append(gap)                 # moving back from the old gap undoes it
    assert not g.solved
    for pos in reversed(history):
        g.move(pos)
    assert g.solved


def test_click_and_hint(app):
    from pbremaster.puzzles.rotascope import Rotascope

    cairo = app.levels[1].cities["CITY.06.CAIRO"]
    g = Rotascope(app, cairo.puzzles[3])
    for pos in g.positions():                       # pos_at agrees with each section's middle
        s = g.shape(pos)
        import math
        if pos == "centre":
            pt = g.centre
        else:
            r, a = (s.r0 + s.r1) / 2, math.radians((s.a0 + s.a1) / 2)
            pt = (g.centre[0] + r * math.cos(a), g.centre[1] - r * math.sin(a))
        assert g.pos_at(pt) == pos
    wrong = next(p for p in g.positions() if g.at[p] not in ((255, 255), p))
    piece = g.at[wrong]
    assert g.use_hint() and g.hint_mode
    g.hint_at(wrong)
    assert g.at[piece] == piece and not g.hint_mode
