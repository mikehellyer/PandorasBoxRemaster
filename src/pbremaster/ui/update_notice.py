"""The 'new version available' notice on the main menu.

The check runs once in the background at start-up; if GitHub has a newer release,
a small panel with an Update button appears on the main menu. Nothing is
downloaded until Update is clicked; then the installer is fetched and handed to
the system (update.launch_installer) and the game closes so it can be replaced.
"""
from __future__ import annotations

import threading

import pygame

from .. import __version__, update

TEXT, EDGE, FILL, GOLD = (236, 220, 190), (150, 82, 30), (40, 18, 6), (248, 176, 100)


class UpdateNotice:
    RECT = pygame.Rect(248, 568, 304, 28)

    def __init__(self, app):
        self.app = app
        self.info: update.UpdateInfo | None = None
        self.status = ""
        self.busy = False
        self.quit_in = None               # seconds until the game closes for the installer
        self.button = pygame.Rect(0, 0, 70, 22)

    def start_check(self):
        def work():
            self.info = update.check_for_update(__version__)
        threading.Thread(target=work, daemon=True).start()

    @property
    def visible(self):
        return self.info is not None

    def update(self, dt):
        if self.quit_in is not None:
            self.quit_in -= dt
            if self.quit_in <= 0:
                self.app.running = False

    def draw(self, surf):
        if not self.visible:
            return
        r = self.RECT
        pygame.draw.rect(surf, FILL, r, border_radius=6)
        pygame.draw.rect(surf, EDGE, r, 1, border_radius=6)
        font = self.app.fonts.get(14)
        text = self.status or f"Version {self.info.version.lstrip('vV')} is available."
        surf.blit(font.render(text, True, TEXT), (r.x + 10, r.y + 6))
        if not self.busy and not self.status:
            self.button.midright = (r.right - 4, r.centery)
            hover = self.button.collidepoint(self.app.mouse_pos())
            pygame.draw.rect(surf, (120, 60, 18) if not hover else (150, 80, 25), self.button, border_radius=5)
            pygame.draw.rect(surf, GOLD, self.button, 1, border_radius=5)
            img = font.render("Update", True, TEXT)
            surf.blit(img, img.get_rect(center=self.button.center))

    def click(self, pos) -> bool:
        if not self.visible or self.busy or self.status or not self.button.collidepoint(pos):
            return False
        url = update.asset_for_this_platform(self.info.assets)
        if url is None:
            self.status = "No installer for this system: see the GitHub page."
            return True
        self.busy, self.status = True, "Downloading the update..."

        def work():
            path = update.download_asset(url)
            if path is None:
                self.busy, self.status = False, "Couldn't download the update. Try again later."
                return
            try:
                proc = update.launch_installer(path)
            except OSError:
                self.busy, self.status = False, f"Downloaded to {path}: open it to install."
                return
            if proc is None:
                appimage = update.running_appimage()
                self.status = ("Updated: restart the game to use the new version." if appimage
                               else "Installer started: closing the game...")
                self.busy = False
                self.quit_in = None if appimage else 1.5
                return
            self.status = "Installing the update..."
            code = proc.wait()                      # Linux: let the password prompt finish
            if code == 0:
                self.status, self.quit_in = "Updated: closing the game...", 1.5
            else:
                err = proc.stderr.read().strip() if proc.stderr else ""
                self.status = f"The update didn't install ({code}){': ' + err[:40] if err else ''}."
            self.busy = False

        threading.Thread(target=work, daemon=True).start()
        self.app.sounds.play(self.app.sounds.CLICK)
        return True
