"""Drive the menu screens with synthetic events on a headless display."""
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


def click(app, cid):
    pos = app.active()[cid].rect.center
    app.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)))
    app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
    app.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))


def type_text(app, text):
    for ch in text:
        app.handle(pygame.event.Event(pygame.KEYDOWN, key=ord(ch.lower()), unicode=ch, mod=0))


def test_needs_a_player_name(app):
    click(app, 102)                       # TUTORIAL
    assert app.view.id == 100
    type_text(app, "Mike")
    click(app, 102)
    assert app.view.id == 501
    assert app.settings.players == ["Mike"]


def test_back_and_menu(app):
    type_text(app, "Mike")
    click(app, 104)                       # PUZZLES ONLY
    assert app.view.id == 150
    click(app, 52)                        # Back
    assert app.view.id == 100
    click(app, 103)                       # GALLERY
    click(app, 54)                        # Menu
    assert app.menu is not None
    app.menu_pick(40001)                  # Main Screen
    assert app.view.id == 100 and app.menu is None


def city_puzzles(app, kind):
    return sum(p.kind_name == kind for lv in app.levels.values()
               for c in lv.cities.values() for p in c.puzzles.values())


def test_puzzle_type_radio(app):
    type_text(app, "Mike")
    click(app, 104)
    assert app.view[150].on
    assert len(app.view[165].items) == city_puzzles(app, "Image Hole") == 41
    click(app, 158)                       # SLICES
    assert app.view[158].on and not app.view[150].on
    assert len(app.view[165].items) == city_puzzles(app, "Slices")


def test_options_dialog(app):
    click(app, 105)
    dlg = app.active()
    assert dlg.id == 103 and dlg[721].on
    click(app, 721)                       # sound off
    click(app, 705)                       # Cancel keeps the setting
    assert app.settings.sound and not app.dialogs
    click(app, 105)
    click(app, 722)                       # music off
    click(app, 703)                       # Apply
    assert not app.settings.music and not app.dialogs


def test_every_screen_draws(app):
    from pbremaster.ui import widgets

    for sid in app.ui.layout.screens:
        app.stack.append(widgets.ScreenView(app.ui, sid))
        app.draw()
