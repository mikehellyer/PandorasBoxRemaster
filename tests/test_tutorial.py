"""The Tutorial's step-by-step instructions (ui/tutorial.py)."""
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
    for ch in "Learner":
        a.handle(pygame.event.Event(pygame.KEYDOWN, key=ord(ch.lower()), unicode=ch, mod=0))
    a.player_ready()
    a.open_practice()
    yield a
    pygame.quit()


def practice(app, kind):
    lv = app.levels[0]
    app.open_puzzle(lv, app.view.scene.city, next(p for p in lv.puzzles.values() if p.kind_name == kind))
    return app.view.scene


def test_every_type_has_its_steps(app):
    from pbremaster.ui.tutorial import STEPS

    for kind, steps in STEPS.items():
        scene = practice(app, kind)
        assert scene.tutorial and scene.tutorial.text_id == steps[0][0]
        assert all(app.strings.get(s[0]) for s in steps)          # every step has its text
        scene.draw_front(app.canvas)
        app.back()


def test_slices_moves_on_when_a_piece_is_selected(app):
    scene = practice(app, "Slices")
    g, t = scene.game, scene.tutorial
    _, _, grp, surf, mask, tl = g.placed_sprites()[0]
    x, y = next((x, y) for y in range(surf.get_height()) for x in range(surf.get_width()) if mask.get_at((x, y)))
    scene.mouse_down((tl[0] + x, tl[1] + y))
    assert t.index == 1 and t.text_id == 10901                   # "Drag the selected piece..."


def test_lens_bender_script(app):
    scene = practice(app, "Lens Bender")
    g, t = scene.game, scene.tutorial
    assert g.attach(3) and t.text_id == 11951                    # attached from the second lens
    i = g.stacks[3][0]
    g.stacks[3].pop(0)
    g.stacks[2].insert(0, i)
    assert g.attach(2) and t.text_id == 11952
    assert not g.attach(3) and t.text_id == 11953                # "won't attach"


def test_jesse_tray_steps_wait_for_the_right_tray(app):
    scene = practice(app, "Jesse's Strips")
    g, t = scene.game, scene.tutorial
    g.switch(1)
    assert t.text_id == 8007                                     # not tray 5 yet
    g.switch(4)
    assert t.text_id == 8008


def test_panel_arrows_and_close(app):
    scene = practice(app, "Interlock")
    t = scene.tutorial
    scene.draw_front(app.canvas)
    scene.mouse_down(t.rects["next"].center)
    assert t.index == 1
    scene.draw_front(app.canvas)
    scene.mouse_down(t.rects["back"].center)
    assert t.index == 0
    scene.draw_front(app.canvas)
    scene.mouse_down(t.rects["close"].center)
    assert t.closed and not t.visible()


def test_no_tutorial_in_the_campaign(app):
    level = app.levels[1]
    city = level.cities["CITY.06.CAIRO"]
    app.open_puzzle(level, city, next(iter(city.puzzles.values())))
    assert app.view.scene.tutorial is None
