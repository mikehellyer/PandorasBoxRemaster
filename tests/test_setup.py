"""Finding the player's own game files: checks, copy, saved choice, setup screen.
Uses a fake game folder, so it runs without the original files (e.g. in CI)."""
import os

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pbremaster.data import gamedir


@pytest.fixture
def fake_cd(tmp_path):
    data = tmp_path / "cd" / "DATA"
    data.mkdir(parents=True)
    for name in gamedir.NEEDED:
        (data / name).write_bytes(b"x" * 1000)
    (data / "MUSIC").mkdir()
    (data / "MUSIC" / "INTRO.WAV").write_bytes(b"y" * 5000)
    return tmp_path / "cd"


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "xdg"))
    monkeypatch.delenv("PANDORA_DIR", raising=False)
    return tmp_path / "xdg"


def test_check(fake_cd):
    c = gamedir.check(fake_cd)
    assert c.ok and c.data == fake_cd / "DATA" and not c.missing
    assert "voices" in c.lacking and "music" not in c.lacking
    assert gamedir.check(fake_cd / "DATA").ok                  # its DATA folder works too
    (fake_cd / "DATA" / "PUZENU.DLL").unlink()
    c = gamedir.check(fake_cd)
    assert not c.ok and c.missing == ["PUZENU.DLL"]


def test_copy_and_cancel(fake_cd, home):
    seen = []
    out = gamedir.copy_data(fake_cd / "DATA", progress=lambda d, t: seen.append((d, t)))
    assert out == gamedir.copied_dir() / "DATA"
    assert (out / "MUSIC" / "INTRO.WAV").read_bytes() == b"y" * 5000
    assert seen[-1][0] == seen[-1][1]
    assert gamedir.check(gamedir.copied_dir()).ok
    with pytest.raises(InterruptedError):
        gamedir.copy_data(fake_cd / "DATA", home / "other", cancelled=lambda: True)
    assert not (home / "other" / "DATA").exists() and not (home / "other" / "DATA.partial").exists()


def test_saved_choice_is_used(fake_cd, home):
    assert gamedir.find(saved=str(fake_cd)).data == fake_cd / "DATA"


def typing(text):
    return [pygame.event.Event(pygame.TEXTINPUT, text=ch) for ch in text]


def test_setup_screen_picks_folder(fake_cd, home):
    from pbremaster.ui.setup import SetupScreen

    pygame.init()
    window = pygame.display.set_mode((800, 600))
    s = SetupScreen(window, current="")
    for ev in typing(str(fake_cd)):
        s.handle(ev)
    assert s.check.ok and s.play.enabled is not None
    s.copy_first = False
    s.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0))
    assert s.result == str(fake_cd)
    s = SetupScreen(window, current=str(fake_cd / "nowhere"))
    s.present()
    assert not s.check.ok
    s.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0))
    assert s.result is None
    pygame.quit()


def test_setup_screen_copies_first(fake_cd, home):
    from pbremaster.ui.setup import SetupScreen

    pygame.init()
    window = pygame.display.set_mode((800, 600))
    s = SetupScreen(window, current=str(fake_cd))
    s.copy_first = True
    s.choose()
    assert s.copying
    picked = s.run()                                   # finishes the copy, then returns
    assert picked == str(gamedir.copied_dir())
    assert gamedir.check(picked).ok
    found = gamedir.detect()
    assert found and found[0].data == gamedir.copied_dir() / "DATA"     # offered first next time
    pygame.quit()
