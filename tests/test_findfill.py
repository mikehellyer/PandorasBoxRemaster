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


def findfills(app):
    return [p for lv in app.levels.values()
            for p in list(lv.puzzles.values()) + [q for c in lv.cities.values() for q in c.puzzles.values()]
            if p.kind_name == "Find and Fill"]


def test_every_findfill_loads(app):
    from pbremaster.puzzles.findfill import FindAndFill

    puzzles = findfills(app)
    assert len(puzzles) == 45
    for p in puzzles:
        g = FindAndFill(app, p)
        assert len(g.data.objects) >= 3
        assert all(g.owned), p.files                 # every object has areas to fill
        assert g.region_count > len(g.owned)         # outlines cross: more areas than objects
        assert not g.solved
        g.draw(app.canvas)


def show(g, x, y):
    """Scroll board point (x, y) into view, as the arrows would."""
    g.scroll_by(x - 100 - g.scroll_x, y - 100 - g.scroll)


def screen(g, x, y):
    from pbremaster.puzzles.findfill import VIEW
    return VIEW.x + g.origin[0] + x - g.scroll_x, VIEW.y + g.origin[1] + y - g.scroll


def solve_by_filling(g):
    """Fill each object's areas with one colour, as a player would."""
    for k, regions in enumerate(g.owned):
        if g.found[k]:
            continue
        *rest, last = sorted(regions - g.locked)
        for r in rest:                                  # fill directly, then click the last area
            g.fill[r] = k % 4
        ys, xs = (g.labels == last).nonzero()
        y, x = int(ys[0]), int(xs[0])
        show(g, x, y)
        g.colour = k % 4
        assert g.mouse_down(screen(g, x, y))
        assert g.found[k]


def test_filling_finds_objects(app):
    from pbremaster.puzzles.findfill import FindAndFill

    for p in findfills(app):
        g = FindAndFill(app, p)
        solve_by_filling(g)
        assert g.solved


def test_wrong_colour_mix_does_not_find(app):
    from pbremaster.puzzles.findfill import FindAndFill

    g = FindAndFill(app, findfills(app)[0])
    big = max(range(len(g.owned)), key=lambda k: len(g.owned[k]))
    regions = sorted(g.owned[big])
    if len(regions) > 1:
        g.fill = {r: 0 for r in regions}
        g.fill[regions[0]] = 1
        g.evaluate()
        assert not g.found[big]


def test_hint_reveals_outline_and_complete(app):
    from pbremaster.puzzles.findfill import FindAndFill

    g = FindAndFill(app, findfills(app)[0])
    assert g.use_hint() and g.hint_mode
    r = next(iter(g.owned[0]))
    ys, xs = (g.labels == r).nonzero()
    show(g, int(xs[0]), int(ys[0]))
    g.mouse_down(screen(g, int(xs[0]), int(ys[0])))
    assert g.hint_done and g.revealed and not g.hint_mode
    g.complete()
    assert g.solved


def test_object_inside_another_can_still_be_found(app):
    from pbremaster.puzzles.findfill import FindAndFill

    p = next(p for p in findfills(app) if "SYDNEY/PUZZLE.02" in p.files[-1])
    g = FindAndFill(app, p)
    outer, inner = 1, 2
    assert g.owned[inner] <= g.owned[outer]
    for r in g.owned[outer]:
        g.fill[r] = 0
    g.evaluate()
    assert g.found[outer] and not g.found[inner]
    assert not (g.owned[inner] & g.locked)            # still open to fill
    for r in g.owned[inner]:
        g.fill[r] = 1
    g.evaluate()
    assert g.found[inner]
