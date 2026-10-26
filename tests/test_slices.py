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


def test_every_slices_loads_and_joins(app):
    from pbremaster.puzzles.slices import Slices

    puzzles = [p for lv in app.levels.values()
               for p in list(lv.puzzles.values()) + [q for c in lv.cities.values() for q in c.puzzles.values()]
               if p.kind_name == "Slices"]
    assert len(puzzles) == 29
    for p in puzzles:
        g = Slices(app, p)
        assert not g.solved and len(g.groups) == len(g.data.pieces)
        g.draw(app.canvas)
        g.hint_join(g.groups[0], g.groups[0].members[0])     # a neighbour joins
        assert len(g.groups) == len(g.data.pieces) - 1
        g.complete()
        assert g.solved
        g.draw(app.canvas)


def sprite_point(g, group):
    """A screen point on one of the group's pieces that no other sprite covers."""
    for _, i, h, surf, mask, tl in g.placed_sprites():
        if h is not group:
            continue
        for y in range(0, surf.get_height(), 3):
            for x in range(0, surf.get_width(), 3):
                pos = (tl[0] + x, tl[1] + y)
                if mask.get_at((x, y)) and g.group_at(pos) is group:
                    return pos
    return None


def cairo(app):
    from pbremaster.puzzles.slices import Slices
    return Slices(app, app.levels[1].cities["CITY.06.CAIRO"].puzzles[2])


def test_drag_onto_neighbour_joins(app):
    g = cairo(app)
    a, b = g.groups[0], next(h for h in g.groups if h.members[0] in g.data.neighbours[0])
    g.turned(b, a.flip, a.turn)
    g.move_to(a, -6, 6)
    g.move_to(b, 6, -6)
    src, dst = sprite_point(g, b), sprite_point(g, a)
    assert g.mouse_down(src) and g.selected is b
    g.mouse_move(dst)
    g.mouse_up(dst)
    assert len(g.groups) == len(g.data.pieces) - 1 and set(b.members) <= set(a.members)


def test_wrong_facing_bounces_back(app):
    g = cairo(app)
    a, b = g.groups[0], next(h for h in g.groups if h.members[0] in g.data.neighbours[0])
    g.turned(b, a.flip ^ 1, a.turn)
    g.move_to(a, -6, 6)
    g.move_to(b, 6, -6)
    home = g.centre(b)
    src, dst = sprite_point(g, b), sprite_point(g, a)
    g.mouse_down(src)
    g.mouse_move(dst)
    g.mouse_up(dst)
    assert len(g.groups) == len(g.data.pieces)
    assert abs(g.centre(b)[0] - home[0]) < 1e-6 and abs(g.centre(b)[2] - home[2]) < 1e-6


def test_revolve_keeps_groups_whole(app):
    g = cairo(app)
    g.complete()
    before = g.placed_sprites()
    g.revolve(1)
    g.revolve(-1)
    after = g.placed_sprites()
    assert [t[5] for t in before] == [t[5] for t in after]
    assert g.solved
