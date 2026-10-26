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


def image_holes(app):
    return [p for lv in app.levels.values()
            for p in list(lv.puzzles.values()) + [q for c in lv.cities.values() for q in c.puzzles.values()]
            if p.kind_name == "Image Hole"]


def honolulu(app):
    from pbremaster.puzzles.imagehole import ImageHole
    return ImageHole(app, app.levels[1].cities["CITY.10.HONOLULU"].puzzles[5])


def test_every_image_hole_loads(app):
    from pbremaster.puzzles.imagehole import ImageHole

    puzzles = image_holes(app)
    assert len(puzzles) == 42
    for p in puzzles:
        g = ImageHole(app, p)
        assert g.holes and all(h.hit.count() > 0 for h in g.holes)
        for _ in range(5):
            g.update(0.1)
        g.draw(app.canvas)


def test_select_move_lock(app):
    from pbremaster.puzzles.base import AREA

    g = honolulu(app)
    h = g.holes[0]
    click = lambda p: g.mouse_down((AREA.x + p[0], AREA.y + p[1]))
    cx, cy = h.centre
    inside = next((int(h.x) + x, int(h.y) + y) for x, y in h.outline[:1])
    inside = (int(cx), int(cy)) if h.contains((int(cx), int(cy))) else inside
    click(inside)
    assert g.selected is h
    tx, ty = h.home_centre
    click((tx + 200 if tx < 300 else tx - 200, ty))          # send it somewhere wrong
    for _ in range(100):
        g.update(0.1)
    assert h.target is None
    cx, cy = h.centre
    click((int(cx), int(cy)) if h.contains((int(cx), int(cy))) else (int(h.x) + h.outline[0][0], int(h.y) + h.outline[0][1]))
    assert g.strikes == 1 and not h.locked
    # now send it home and lock it
    h.target = (tx - h.size[0] / 2, ty - h.size[1] / 2)
    for _ in range(100):
        g.update(0.1)
    g.try_lock(h)
    assert h.locked and g.strikes == 1


def test_three_strikes_restart(app):
    g = honolulu(app)
    h = g.holes[0]
    h.x, h.y = 0, 0
    for _ in range(3):
        g.try_lock(h)
    assert app.dialogs and app.dialogs[-1][0].id == 900
    app.end_dialog(1)
    assert g.strikes == 0


def test_hint_and_complete(app):
    from pbremaster.puzzles.base import AREA

    g = honolulu(app)
    assert g.use_hint() and g.hint_mode
    h = g.holes[1]
    h.x, h.y = 300, 250
    cx, cy = h.centre
    pt = (int(cx), int(cy)) if h.contains((int(cx), int(cy))) else (int(h.x) + h.outline[0][0], int(h.y) + h.outline[0][1])
    g.mouse_down((AREA.x + pt[0], AREA.y + pt[1]))
    assert h.locked and g.hint_done
    g.complete()
    assert g.solved
