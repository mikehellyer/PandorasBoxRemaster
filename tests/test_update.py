"""The update check: version compare, picking the asset, and the main-menu notice."""
import os

import pygame

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pbremaster import update

ASSETS = [("PandorasBoxRemaster-0.2.0-Windows-Setup.exe", "u/exe"),
          ("pbremaster_0.2.0_amd64.deb", "u/deb"),
          ("PandorasBoxRemaster-0.2.0-x86_64.AppImage", "u/appimage")]


def test_versions():
    assert update.is_newer("v0.2.0", "0.1.0")
    assert update.is_newer("v0.10.0", "0.9.3")
    assert not update.is_newer("v0.1.0", "0.1.0")


def test_asset_for_platform(monkeypatch):
    monkeypatch.setattr(update.sys, "platform", "win32")
    assert update.asset_for_this_platform(ASSETS) == "u/exe"
    monkeypatch.setattr(update.sys, "platform", "linux")
    monkeypatch.delenv("APPIMAGE", raising=False)
    assert update.asset_for_this_platform(ASSETS) == "u/deb"
    monkeypatch.setenv("APPIMAGE", "/tmp/x.AppImage")
    assert update.asset_for_this_platform(ASSETS) == "u/appimage"


def test_offline_means_no_update(monkeypatch):
    def boom(*a, **k):
        raise OSError("offline")
    monkeypatch.setattr(update.urllib.request, "urlopen", boom)
    assert update.check_for_update("0.1.0") is None


def test_notice_on_main_menu(game, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from pbremaster.settings import Settings
    from pbremaster.ui.app import App

    pygame.init()
    app = App(game, Settings.load())
    app.open_window()
    assert not app.update_notice.visible                  # nothing until a newer release is seen
    app.update_notice.info = update.UpdateInfo("v9.0.0", "page", ASSETS)
    app.draw()
    started = []
    monkeypatch.setattr(update, "download_asset", lambda url: started.append(url) or None)
    pos = app.update_notice.button.center
    app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
    assert app.update_notice.busy or app.update_notice.status
    pygame.quit()
