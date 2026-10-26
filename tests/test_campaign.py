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
    # back on the map Cairo is the current location (the ringed 402 marker), yet a
    # resumed game still starts on the map rather than inside Cairo
    states = {m.city.id: app.view.scene.state(m) for m in app.view.scene.markers}
    assert states[6] == "current" and list(states.values()).count("current") == 1
    assert app.player.city is None and app.player.last_city == "CITY.06.CAIRO"


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


def test_hint_with_none_explains(app):
    new_player(app)
    app.player_ready()
    level = app.levels[1]
    city = level.cities["CITY.06.CAIRO"]
    puzzle = next(p for p in city.puzzles.values() if p.kind_name == "Rotascope")
    app.player.hints = 0
    app.open_puzzle(level, city, puzzle)
    click(app, 307)                                   # Hint with none: a short explanation
    assert app.dialogs and app.active().id == 900
    assert "no Hints" in " ".join(app.active().scene.lines)
    click(app, 1200)                                  # OK
    assert not app.dialogs and not app.view.scene.game.hint_mode
    app.player.hints = 1                              # with one: the original's question
    click(app, 307)
    click(app, 1201)                                  # Yes
    assert app.view.scene.game.hint_mode


def test_free_with_none_explains(app):
    new_player(app)
    app.player_ready()
    level = app.levels[1]
    city = level.cities["CITY.06.CAIRO"]
    app.player.free = 0
    app.open_puzzle(level, city, next(iter(city.puzzles.values())))
    click(app, 306)                                   # Free with none: a short explanation
    assert app.dialogs and "no Free Puzzle tokens" in " ".join(app.active().scene.lines)
    click(app, 1200)
    assert not app.dialogs


def test_challenge_free_costs_three(app):
    new_player(app)
    app.player_ready()
    level = app.levels[1]
    app.player.free = 2
    app.start_master(level)
    scene = app.view.scene
    assert scene.master
    plain = app.ui.assets.image("SCREENS/300.RIM")
    assert app.view.background.get_at((60, 300)) != plain.get_at((60, 300))     # the 300F frame
    click(app, 306)                                   # two tokens: "You need three ..."
    assert app.dialogs and "three" in " ".join(app.active().scene.lines)
    click(app, 1200)
    app.player.free = 4
    click(app, 306)
    assert "three" in " ".join(app.active().scene.lines)
    click(app, 1201)                                  # Yes: use them
    tick(app, 20)
    assert app.player.free == 1


def test_puzzles_only_plays_any_puzzle(app):
    new_player(app)
    click(app, 104)                                   # PUZZLES ONLY
    assert app.view.id == 150
    click(app, 151)                                   # Focus Point
    k = next(i for i, (lv, _, _) in enumerate(app.listed) if lv.number == 8)   # a Scalawag bonus puzzle
    app.view[165].selected = k
    before = (app.player.free, app.player.hints, list(app.player.pieces))
    click(app, 169)                                   # Play
    scene = app.view.scene
    assert scene.only and scene.level.number == 8 and scene.puzzle.kind_name == "Focus Point"
    ev(app, pygame.KEYDOWN, key=pygame.K_F9, unicode="", mod=0)
    tick(app, 20)
    assert app.active().id == 130                     # Congratulations
    click(app, 131)
    assert app.view.id == 150 and not app.dialogs     # straight back to the list
    assert (app.player.free, app.player.hints, list(app.player.pieces)) == before


def test_save_and_load_games(app):
    from pbremaster.ui.app import LOAD_DLG, MENU_SAVE, SAVE_DLG

    new_player(app)
    app.player_ready()
    app.player.hints = 3
    app.show_map()
    app.open_menu(app.view[54])
    assert app.menu.enabled[MENU_SAVE]                 # Save is offered once a player is playing
    app.menu_pick(MENU_SAVE)
    assert app.active().id == SAVE_DLG and "Level 1" in app.active()[741].value
    app.active()[741].value = "Before Cairo"
    click(app, 707)                                    # Save
    assert app.active().id == 900                      # "Game saved as ..."
    click(app, 1200)
    app.player.hints = 0                               # play on and lose the hints

    app.dialog(LOAD_DLG)
    assert app.active()[702].items == ["Before Cairo"]
    tick(app, 1)
    app.dialogs[-1][0][702].selected = 0
    click(app, 706)                                    # Load: back to that point, on the map
    assert app.player.hints == 3 and app.view.id in (40, 400)

    app.dialog(SAVE_DLG)
    view = app.active()
    view[701].selected = 0
    click(app, 704)                                    # Delete, then Yes
    click(app, 1201)
    assert view[701].items == []


def test_gallery_shows_best_times(app):
    new_player(app)
    app.player_ready()
    level = app.levels[1]
    city = level.cities["CITY.06.CAIRO"]
    puzzle = next(p for p in city.puzzles.values() if p.kind_name == "Rotascope")
    app.open_puzzle(level, city, puzzle)
    app.view.scene.elapsed = 83.4
    ev(app, pygame.KEYDOWN, key=pygame.K_F9, unicode="", mod=0)
    tick(app, 20)
    click(app, 131)                                   # Continue
    while app.dialogs:
        app.end_dialog(1)
    assert app.player.best[puzzle.path] > 83
    app.main_screen()
    click(app, 103)                                   # GALLERY
    gallery = app.view.scene
    assert app.view.id == 600 and gallery.rows == []  # Image Hole: nothing solved yet
    click(app, 652)                                   # Rotascope
    assert len(gallery.rows) == 1
    name, mine, best = gallery.rows[0]
    assert mine == app.player.best[puzzle.path] and best[1] == "Tester"
    tick(app, 1)
