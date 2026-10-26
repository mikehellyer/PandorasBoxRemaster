import os

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture(scope="module")
def app(game, tmp_path_factory):
    os.environ["XDG_DATA_HOME"] = str(tmp_path_factory.mktemp("xdg"))
    from pbremaster.settings import Settings
    from pbremaster.ui.app import App

    pygame.init()
    a = App(game, Settings.load())
    a.open_window()
    yield a
    pygame.quit()


def lensbenders(app):
    return [p for lv in app.levels.values()
            for p in list(lv.puzzles.values()) + [q for c in lv.cities.values() for q in c.puzzles.values()]
            if p.kind_name == "Lens Bender"]


def move(g, i, lens):
    for s in g.stacks:
        if i in s:
            s.remove(i)
    g.stacks[lens].insert(0, i)
    g.views.clear()


def test_every_puzzle_solvable_by_the_rules(app):
    from pbremaster.puzzles.lensbender import LensBender

    puzzles = lensbenders(app)
    assert len(puzzles) == 22
    for p in puzzles:
        g = LensBender(app, p)
        g.draw(app.canvas)
        assert g.placed and not g.solved
        while not g.solved:
            ready = [s for s in g.data.sprites if s.index not in g.placed and s.adjacent & g.placed]
            assert ready, p.files[0]
            s = ready[0]
            move(g, s.index, s.final_stack)
            assert g.attach(s.final_stack)
        g.draw(app.canvas)


def tutorial(app):
    from pbremaster.puzzles.lensbender import LensBender
    return LensBender(app, next(p for p in lensbenders(app) if p.files[0].startswith("LEVEL.0/")))


def test_tutorial_steps(app):
    g = tutorial(app)
    assert g.attach(3)                       # "the arrow button on the second lens"
    assert not g.attach(3)                   # next piece faces the wrong way there
    move(g, g.stacks[3][0], 2)               # "try the smallest lens"
    assert g.attach(2)
    assert not g.attach(3)                   # "must have somewhere to connect"


def test_drag_between_lenses(app):
    g = tutorial(app)
    top = g.stacks[3][0]
    g.mouse_down(g.centres[3])
    g.mouse_move(g.centres[2])
    g.mouse_up(g.centres[2])
    assert g.stacks[2][0] == top and top not in g.stacks[3]


def test_hint_and_complete(app):
    g = tutorial(app)
    assert g.use_hint()
    g.mouse_down(g.centres[3])
    assert g.hint_done and not g.hint_mode
    g.complete()
    assert g.solved
