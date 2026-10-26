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
    assert app.view.id == 250 and app.view.scene.page == 1   # the story's first page opens the level
    click(app, 251)                                   # close the book
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
    assert app.view.id == 250 and app.view.scene.page == 2   # the story goes on: where to look next
    click(app, 251)
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
    click(app, 251)                                   # close the story's first page
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


def test_success_view_shows_finished_puzzle(app):
    new_player(app)
    app.player_ready()
    level = app.levels[1]
    city = level.cities["CITY.06.CAIRO"]
    app.enter_city(city)
    puzzle = next(p for p in city.puzzles.values() if p.kind_name == "Rotascope" and not p.piece)
    app.open_puzzle(level, city, puzzle)
    puzzle_view = app.view
    ev(app, pygame.KEYDOWN, key=pygame.K_F9, unicode="", mod=0)
    tick(app, 20)
    assert app.active().id == 130 and app.view is puzzle_view      # box over the solved puzzle
    click(app, 130)                                                 # View
    assert not app.dialogs and app.view is puzzle_view and puzzle_view.scene.viewing
    tick(app, 5)
    assert app.view is puzzle_view                                  # stays until a click
    click_at(app, (400, 300))
    assert app.view.id == 500 and puzzle.number in app.player.solved[city.path]


def solve_speed_puzzle(app, city_name, hint=False):
    level = app.levels[2]
    city = level.cities[city_name]
    app.enter_city(city)
    puzzle = next(p for p in city.puzzles.values() if p.time_limit)
    slot = next(cid for cid, p in app.view.scene.slots.items() if p is puzzle)
    app.open_puzzle(level, city, puzzle, slot_id=slot)
    assert app.active().id == 900 and "speed puzzle" in " ".join(app.active().scene.lines)
    click(app, 1200)
    if hint:
        app.view.scene.used_hint = True
    ev(app, pygame.KEYDOWN, key=pygame.K_F9, unicode="", mod=0)
    tick(app, 20)
    click(app, 131)                                   # Continue on the success box
    return city


def test_speed_puzzle_bonuses(app):
    new_player(app)
    app.player_ready()
    app.player.level = 2

    city = solve_speed_puzzle(app, "CITY.13.LONDON")
    assert app.active().id == 900 and "location of the hidden object" in " ".join(app.active().scene.lines)
    assert city.path in app.player.revealed
    click(app, 1200)
    app.draw()                                        # the piece icon on the hiding puzzle's button

    lusaka = app.levels[2].cities["CITY.14.LUSAKA"]
    app.player.pieces.append(lusaka.path)             # piece already found: tokens instead
    free = app.player.free
    solve_speed_puzzle(app, "CITY.14.LUSAKA")
    assert "three Free Puzzle tokens" in " ".join(app.active().scene.lines)
    assert app.player.free == free + 3
    click(app, 1200)

    free = app.player.free
    city = solve_speed_puzzle(app, "CITY.24.PHILADELPHIA", hint=True)
    assert city.path not in app.player.revealed and app.player.free == free
    assert not app.dialogs or "beat the clock" not in " ".join(getattr(app.active().scene, "lines", []))


def test_story_book(app):
    new_player(app)
    app.player_ready()
    app.player.videos_seen.append(1)
    app.resume()
    book = app.view.scene
    assert app.view.id == 250 and len(book.book) == 1        # nothing found yet: one page
    assert not app.view[252].visible and not app.view[253].visible   # no page to turn to
    click(app, 251)
    app.player.pieces += [p.path for p in list(app.levels[1].cities.values())[:2]]
    click(app, 53)                                    # the Story button on the map
    book = app.view.scene
    assert app.view.id == 250 and book.pages == 3 and book.page == 3
    assert app.view[252].visible and not app.view[253].visible
    click(app, 252)                                   # back a page
    assert book.page == 2 and "1.2" in app.player.stories_seen
    click_at(app, (760, 565))                         # the arrow painted in the corner: forward
    assert book.page == 3
    ev(app, pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="", mod=0)
    assert app.view.id == 400


def test_story_book_keeps_finished_levels(app):
    new_player(app)
    app.player_ready()
    app.player.level, app.player.captured = 2, [1]
    app.player.videos_seen += [1, 2]
    app.show_map()
    click(app, 53)
    book = app.view.scene
    assert [(lv.number, k) for lv, k in book.book] == [(1, k) for k in range(1, 6)] + [(2, 1)]
    assert book.level.number == 2 and book.page == 1      # opens on the current level's page
    click(app, 252)                                   # back into Maui's story
    assert book.level.number == 1 and book.page == 5 and "Maui" in book.app.strings.get(430)
    for lv in range(1, 8):                            # every page fits the right page
        for page in range(1, 6):
            book.book = [(app.levels[lv], page)]
            book.at = 0
            book.layout()
            assert sum(book.line_h if l else book.line_h // 2 for l in book.lines) <= book.PAGE.h

def test_trickster_icons_on_the_map(app):
    new_player(app)
    app.player_ready()
    app.player.level, app.player.captured = 3, [1, 2]
    app.show_map()
    icons = app.view.scene.tricksters
    assert [state for _, state, *_ in icons] == ["captured", "captured", "current"] + ["hidden"] * 4
    assert icons[0][0].topleft == (7, 63) and icons[6][0].topleft == (7 + 73 * 6, 63)
    assert all(img is not None for _, _, img, _ in icons)
    click_at(app, icons[0][0].center)                  # a captured trickster: nothing to open
    assert app.view.id == 400
    click_at(app, icons[2][0].center)                  # the current one: the Challenge box
    assert app.view.id == 1800


def puzzle_of_each_type(app):
    found = {}
    for n, level in sorted(app.levels.items()):
        if n == 0:
            continue
        for city in level.cities.values():
            for p in city.puzzles.values():
                found.setdefault(p.kind_name, (level, city, p))
    return found


def test_half_finished_puzzles_are_kept(app):
    import json

    new_player(app)
    app.player_ready()
    kinds = puzzle_of_each_type(app)
    assert len(kinds) == 10
    for kind, (level, city, puzzle) in kinds.items():
        app.open_puzzle(level, city, puzzle)
        app.dialogs.clear()                            # a speed puzzle's message
        scene = app.view.scene
        scene.elapsed, scene.used_hint = 42.5, True
        before = json.loads(json.dumps(scene.game.save_state()))
        app.back()                                     # leave it unsolved
        assert app.player.partial[puzzle.path]["state"] == before, kind
        app.save_player()
        app.player = type(app.player).load(app.player.name)   # through the JSON file
        app.open_puzzle(level, city, puzzle)
        app.dialogs.clear()
        scene = app.view.scene
        assert json.loads(json.dumps(scene.game.save_state())) == before, kind
        assert scene.elapsed == 42.5 and scene.used_hint, kind

        # load_state really moves the pieces: a solved layout loads as solved
        scene.game.complete()
        for _ in range(600):
            if scene.game.solved:
                break
            scene.game.update(0.05)
        done = json.loads(json.dumps(scene.game.save_state()))
        scene.game.restart()
        assert not scene.game.solved, kind
        scene.game.load_state(done)
        assert scene.game.solved, kind
        scene.finished = True                          # leave without keeping it
        app.back()


def test_solving_forgets_the_half_finished_puzzle(app):
    new_player(app)
    app.player_ready()
    level, city, puzzle = puzzle_of_each_type(app)["Rotascope"]
    app.open_puzzle(level, city, puzzle)
    app.main_screen()                                  # Main Screen from the menu keeps it too
    assert puzzle.path in app.player.partial
    app.open_puzzle(level, city, puzzle)
    app.puzzle_solved(app.view.scene)
    assert puzzle.path not in app.player.partial


def key(app, k, mod=0):
    ev(app, pygame.KEYDOWN, key=k, unicode="", mod=mod)


def test_undo_and_redo_a_move(app):
    new_player(app)
    app.player_ready()
    level = app.levels[1]
    city = level.cities["CITY.06.CAIRO"]
    app.open_puzzle(level, city, city.puzzles[1])                # Focus Point
    app.dialogs.clear()
    scene = app.view.scene
    g = scene.game
    start = list(g.where)
    key(app, pygame.K_z, pygame.KMOD_CTRL)                       # nothing to undo yet
    assert g.where == start
    a, b = [k for k in range(len(g.where)) if not g.locked[k]][:2]
    centre = lambda k: (g.origin[0] + g.where[k][0] + 2, g.origin[1] + g.where[k][1] + 2)
    pa, pb = centre(a), centre(b)
    for p in (pa, pb):
        scene.mouse_down(p)
        scene.mouse_up(p)
    moved = list(g.where)
    assert moved != start and len(scene.history) == 2            # selecting alone isn't a move
    key(app, pygame.K_z, pygame.KMOD_CTRL)
    assert g.where == start and g.selected is None
    key(app, pygame.K_y, pygame.KMOD_CTRL)
    assert g.where == moved
    key(app, pygame.K_z, pygame.KMOD_CTRL | pygame.KMOD_SHIFT)   # redo again: nothing left
    assert g.where == moved
    scene.restart()
    assert len(scene.history) == 1 and not scene.future


def test_undo_works_for_every_type(app):
    import json

    new_player(app)
    app.player_ready()
    for kind, (level, city, puzzle) in puzzle_of_each_type(app).items():
        app.open_puzzle(level, city, puzzle)
        app.dialogs.clear()
        scene = app.view.scene
        g = scene.game
        if not g.UNDO:
            assert kind == "Image Hole"
            scene.finished = True
            app.back()
            continue
        start = scene.history[0]
        g.complete()
        for _ in range(600):
            if g.solved:
                break
            g.update(0.05)
        g.solved = False                         # as if the last piece were still to go
        scene.snapshot()
        assert len(scene.history) == 2, kind
        scene.undo()
        assert json.loads(json.dumps(g.save_state())) == start and not g.solved, kind
        scene.finished = True
        app.back()
