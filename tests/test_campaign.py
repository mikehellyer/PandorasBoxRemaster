"""Play through the campaign screens headlessly."""
import os

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture
def app(game, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from pbremaster.settings import Settings
    from pbremaster.ui.app import App

    pygame.init()
    a = App(game, Settings.load())
    a.open_window()
    yield a
    pygame.quit()


def ev(app, t, **k):
    app.handle(pygame.event.Event(t, **k))


def click_at(app, pos):
    ev(app, pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0))
    ev(app, pygame.MOUSEBUTTONDOWN, pos=pos, button=1)
    ev(app, pygame.MOUSEBUTTONUP, pos=pos, button=1)


def click(app, cid):
    click_at(app, app.active()[cid].rect.center)


def tick(app, n=3):
    for _ in range(n):
        app.update(0.1)
        app.draw()


def new_player(app, name="Tester"):
    for ch in name:
        ev(app, pygame.KEYDOWN, key=ord(ch.lower()), unicode=ch, mod=0)


def test_play_video_map_city_puzzle(app):
    new_player(app)
    click(app, 101)                                   # PLAY: story video first
    tick(app)
    assert app.view.id == 40 and app.view.scene.video.frame is not None
    click_at(app, (400, 300))                         # skip it
    assert app.view.id == 400
    names = {app.city_name(m.city) for m in app.view.scene.markers}
    assert names == {"Cairo", "Honolulu", "Madrid", "New York", "Paris"}
    cairo = next(m for m in app.view.scene.markers if m.city.id == 6)
    click_at(app, cairo.rect.center)
    assert app.view.id == 500 and app.player.city == "CITY.06.CAIRO"
    click(app, 507)                                   # PUZZLE.04, the piece
    assert app.view.id == 5000
    ev(app, pygame.KEYDOWN, key=pygame.K_F9, unicode="", mod=0)
    tick(app, 20)                                     # the finished picture shows first
    assert app.active().id == 130                     # Congratulations
    click(app, 131)                                   # Continue
    assert app.active().id == 900                     # "You found the piece in this city."
    assert app.player.pieces == ["LEVEL.01.MAUI/CITY.06.CAIRO"]
    click(app, 1204)                                  # Map
    assert app.view.id == 400 and not app.dialogs
    tick(app)


def test_free_token_and_resume(app, game):
    from pbremaster.game.progress import Player

    new_player(app)
    click(app, 101)
    click_at(app, (400, 300))
    app.player.free = 1
    m = app.view.scene.markers[0]
    click_at(app, m.rect.center)
    slot = next(iter(app.view.scene.slots))
    click(app, slot)
    click(app, 306)                                   # Free
    click(app, 1201)                                  # Yes
    tick(app, 20)                                     # a playable puzzle shows its picture first
    assert app.active().id == 130 and app.player.free == 0
    saved = Player.load("Tester")
    assert saved.total_solved == 1 and saved.city == m.city.path.split("/")[-1]
    # PLAY again resumes in that city without the video
    app.main_screen()
    click(app, 101)
    assert app.view.id == 500


def test_challenge_screen(app):
    new_player(app)
    click(app, 101)
    click_at(app, (400, 300))
    level = app.levels[1]
    for city in level.cities.values():
        app.player.solve(city, next(p for p in city.puzzles.values() if p.piece))
    app.open_challenge()
    assert app.view.scene.ready
    tick(app)
    click_at(app, (400, 215))                         # the box: first master puzzle
    assert app.view.scene.master
