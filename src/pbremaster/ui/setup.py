"""The setup screen: point the remaster at the player's own Pandora's Box files.

Shown on the first run, when the saved folder has gone (say the CD was taken out),
and from Options > Game files. It lists copies found in the usual places
(gamedir.detect), lets the player browse or paste a folder, checks it, and can copy
the data to this computer first so the CD isn't needed. Nothing from the original
can be used to draw it (that is what it is looking for), so it has its own plain
look in the game's colours and pygame's built-in font.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pygame

from ..data import gamedir

WIDTH, HEIGHT = 800, 600
BG, PANEL, EDGE = (30, 12, 4), (52, 24, 8), (150, 82, 30)
TEXT, DIM, GOOD, BAD = (236, 220, 190), (170, 140, 105), (150, 210, 110), (240, 120, 90)
GOLD = (248, 176, 100)


def choose_folder(initial: str | None = None) -> str | None:
    """The system's folder picker: zenity or kdialog on Linux, else Tk's."""
    start = initial if initial and Path(initial).is_dir() else str(Path.home())
    if sys.platform.startswith("linux"):
        for cmd in (["zenity", "--file-selection", "--directory", "--title=Choose the Pandora's Box folder",
                     f"--filename={start.rstrip('/')}/"],
                    ["kdialog", "--getexistingdirectory", start, "--title", "Choose the Pandora's Box folder"]):
            if shutil.which(cmd[0]):
                try:
                    out = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                except (OSError, subprocess.SubprocessError):
                    continue
                return out.stdout.strip() or None
    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(initialdir=start, title="Choose the Pandora's Box folder")
        root.destroy()
        return path or None
    except Exception:                       # no Tk: the player can still paste a path
        return None


class Button:
    def __init__(self, text, rect, primary=False):
        self.text, self.rect, self.primary = text, pygame.Rect(rect), primary
        self.enabled = True

    def draw(self, surf, font, mouse):
        hover = self.enabled and self.rect.collidepoint(mouse)
        fill = (120, 60, 18) if self.primary else PANEL
        if hover:
            fill = tuple(min(255, c + 30) for c in fill)
        pygame.draw.rect(surf, fill if self.enabled else (40, 20, 8), self.rect, border_radius=6)
        pygame.draw.rect(surf, GOLD if hover else EDGE, self.rect, 2, border_radius=6)
        img = font.render(self.text, True, TEXT if self.enabled else DIM)
        surf.blit(img, img.get_rect(center=self.rect.center))

    def hit(self, pos):
        return self.enabled and self.rect.collidepoint(pos)


class SetupScreen:
    """run() -> the chosen game data folder, or None if the player quit / went back."""

    def __init__(self, window, message: str = "", current: str | None = None, can_go_back=False):
        self.window = window
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.font = pygame.font.Font(None, 24)
        self.small = pygame.font.Font(None, 20)
        self.big = pygame.font.Font(None, 40)
        self.message = message
        self.found = []
        self.path = current or ""
        self.result = None
        self.copying = None             # {"done", "total", "error", "finished", "cancel"}
        self.copy_first = False
        self.back = Button("Back" if can_go_back else "Quit", (40, 540, 150, 40))
        self.browse = Button("Browse...", (590, 300, 170, 36))
        self.search = Button("Search again", (590, 252, 170, 36))
        self.play = Button("Play", (610, 540, 150, 40), primary=True)
        self.cancel = Button("Cancel copy", (325, 470, 150, 36))
        self.copy_box = pygame.Rect(40, 432, 22, 22)
        self.rescan()
        if not self.path and self.found:
            self.set_path(str(self.found[0].folder))
        else:
            self.set_path(self.path)

    # ------------------------------------------------------------ state
    def rescan(self):
        self.found = gamedir.detect()[:5]

    def set_path(self, path):
        self.path = path
        self.check = gamedir.check(path) if path.strip() else None
        self.copy_first = bool(self.check and self.check.ok and self.check.removable)

    def start_copy(self):
        state = {"done": 0, "total": 1, "error": None, "finished": None, "cancel": False}
        src = self.check.data

        def work():
            try:
                state["finished"] = gamedir.copy_data(
                    src, progress=lambda d, t: state.update(done=d, total=t), cancelled=lambda: state["cancel"])
            except (OSError, InterruptedError) as e:
                state["error"] = str(e)

        self.copying = state
        threading.Thread(target=work, daemon=True).start()

    def choose(self):
        if not (self.check and self.check.ok):
            return
        if self.copy_first and self.check.data.resolve() != (gamedir.copied_dir() / "DATA").resolve():
            self.start_copy()
        else:
            self.result = str(self.check.folder)

    # ------------------------------------------------------------ loop
    def run(self):
        clock = pygame.time.Clock()
        pygame.key.start_text_input()
        while self.result is None:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return None
                if self.handle(ev) == "quit":
                    return None
            if self.copying and self.copying["finished"]:
                self.result = str(self.copying["finished"].parent)
            elif self.copying and self.copying["error"]:
                self.message = self.copying["error"]
                self.copying = None
            self.present()
            clock.tick(30)
        return self.result

    def to_canvas(self, pos):
        ww, wh = self.window.get_size()
        scale = min(ww / WIDTH, wh / HEIGHT)
        return int((pos[0] - (ww - WIDTH * scale) / 2) / scale), int((pos[1] - (wh - HEIGHT * scale) / 2) / scale)

    def handle(self, ev):
        if self.copying:
            if ev.type == pygame.MOUSEBUTTONUP and self.cancel.hit(self.to_canvas(ev.pos)):
                self.copying["cancel"] = True
            return None
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            pos = self.to_canvas(ev.pos)
            if self.back.hit(pos):
                return "quit"
            if self.play.hit(pos):
                self.choose()
            elif self.browse.hit(pos):
                picked = choose_folder(self.path)
                pygame.event.clear()
                if picked:
                    self.set_path(picked)
            elif self.search.hit(pos):
                self.rescan()
            elif self.copy_box.inflate(400, 6).move(200, 0).collidepoint(pos) and self.check and self.check.ok:
                self.copy_first = not self.copy_first
            else:
                for k, c in enumerate(self.found):
                    if self.row(k).collidepoint(pos):
                        self.set_path(str(c.folder))
        elif ev.type == pygame.TEXTINPUT:
            self.set_path(self.path + ev.text)
        elif ev.type == pygame.KEYDOWN:
            ctrl = ev.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)
            if ev.key == pygame.K_BACKSPACE:
                self.set_path(self.path[:-1])
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.choose()
            elif ev.key == pygame.K_ESCAPE:
                return "quit"
            elif ctrl and ev.key == pygame.K_v:
                text = pygame.scrap.get_text() if hasattr(pygame.scrap, "get_text") else ""
                if text:
                    self.set_path(text.strip().strip('"'))
            elif ctrl and ev.key == pygame.K_u:
                self.set_path("")
        return None

    # ------------------------------------------------------------ drawing
    def row(self, k):
        return pygame.Rect(40, 222 + k * 30, 530, 26)

    def present(self):
        surf = self.canvas
        surf.fill(BG)
        pygame.draw.rect(surf, EDGE, surf.get_rect().inflate(-16, -16), 2, border_radius=10)
        mouse = self.to_canvas(pygame.mouse.get_pos())
        surf.blit(self.big.render("Pandora's Box Remaster", True, GOLD), (40, 34))
        lines = ["This remaster plays on your own copy of Microsoft Pandora's Box (1999).",
                 "Insert the CD, or choose the folder that holds the game's files",
                 "(the CD itself, its DATA folder, or where the original was installed)."]
        for i, line in enumerate(lines):
            surf.blit(self.font.render(line, True, TEXT), (40, 84 + i * 24))
        if self.message:
            surf.blit(self.small.render(self.message, True, BAD), (40, 164))
        surf.blit(self.font.render("Found on this computer:", True, GOLD), (40, 194))
        if not self.found:
            surf.blit(self.small.render("Nothing yet. Insert the CD and click Search again, or Browse.",
                                        True, DIM), (48, 226))
        for k, c in enumerate(self.found):
            r = self.row(k)
            picked = self.check and c.folder == self.check.folder
            if picked or r.collidepoint(mouse):
                pygame.draw.rect(surf, PANEL, r, border_radius=4)
            where = ("copied to this computer" if c.data.parent == gamedir.copied_dir()
                     else "CD / removable drive" if c.removable else "folder")
            surf.blit(self.small.render(self.fit(str(c.folder), 380), True, TEXT), (r.x + 8, r.y + 6))
            surf.blit(self.small.render(where, True, DIM), (r.x + 400, r.y + 6))
        surf.blit(self.font.render("Folder:", True, GOLD), (40, 382 - 26))
        box = pygame.Rect(40, 382, 720, 32)
        pygame.draw.rect(surf, PANEL, box, border_radius=4)
        pygame.draw.rect(surf, EDGE, box, 1, border_radius=4)
        caret = "|" if pygame.time.get_ticks() // 500 % 2 and not self.copying else ""
        surf.blit(self.font.render(self.fit(self.path, 700, self.font) + caret, True, TEXT), (box.x + 8, box.y + 8))
        self.draw_status(surf)
        self.play.enabled = bool(self.check and self.check.ok) and not self.copying
        for b in (self.back, self.browse, self.search, self.play):
            b.enabled = b.enabled if b is self.play else not self.copying
            b.draw(surf, self.font, mouse)
        if self.copying:
            shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 140))
            surf.blit(shade, (0, 0))
            self.draw_progress(surf, mouse)
        ww, wh = self.window.get_size()
        scale = min(ww / WIDTH, wh / HEIGHT)
        size = (int(WIDTH * scale), int(HEIGHT * scale))
        self.window.fill((0, 0, 0))
        self.window.blit(pygame.transform.smoothscale(surf, size), ((ww - size[0]) // 2, (wh - size[1]) // 2))
        pygame.display.flip()

    def draw_status(self, surf):
        c = self.check
        y = 420
        if c is None:
            return
        if not c.ok:
            text = ("That folder doesn't exist." if not c.folder.exists()
                    else "No Pandora's Box files there (missing " + ", ".join(c.missing[:3]) +
                    ("..." if len(c.missing) > 3 else "") + ").")
            surf.blit(self.small.render(text, True, BAD), (40, y))
            return
        mb = c.size() >> 20 if c.removable else 0
        surf.blit(self.small.render("Pandora's Box found." + (
            "  Missing: " + ", ".join(c.lacking) + " (the game runs without them)." if c.lacking else ""),
            True, GOOD), (40, y))
        if c.data.parent == gamedir.copied_dir():
            return
        pygame.draw.rect(surf, PANEL, self.copy_box, border_radius=3)
        pygame.draw.rect(surf, EDGE, self.copy_box, 1, border_radius=3)
        if self.copy_first:
            pygame.draw.lines(surf, GOLD, False, [(44, 443), (50, 450), (59, 436)], 3)
        label = "Copy the game files to this computer first, so the CD isn't needed"
        surf.blit(self.small.render(label + (f" ({mb} MB)" if mb else ""), True, TEXT), (72, 437))

    def draw_progress(self, surf, mouse):
        st = self.copying
        frac = min(1.0, st["done"] / max(1, st["total"]))
        panel = pygame.Rect(150, 230, 500, 180)
        pygame.draw.rect(surf, BG, panel, border_radius=8)
        pygame.draw.rect(surf, GOLD, panel, 2, border_radius=8)
        surf.blit(self.font.render("Copying the game files...", True, GOLD), (panel.x + 20, panel.y + 20))
        bar = pygame.Rect(panel.x + 20, panel.y + 70, panel.w - 40, 24)
        pygame.draw.rect(surf, PANEL, bar, border_radius=4)
        pygame.draw.rect(surf, (200, 120, 40), (bar.x, bar.y, int(bar.w * frac), bar.h), border_radius=4)
        pygame.draw.rect(surf, EDGE, bar, 1, border_radius=4)
        txt = f"{st['done'] >> 20} of {st['total'] >> 20} MB"
        surf.blit(self.small.render(txt, True, TEXT), (bar.x, bar.bottom + 8))
        self.cancel.rect.midbottom = (panel.centerx, panel.bottom - 14)
        self.cancel.draw(surf, self.font, mouse)

    def fit(self, text, width, font=None):
        font = font or self.small
        if font.size(text)[0] <= width:
            return text
        while text and font.size("..." + text)[0] > width:
            text = text[1:]
        return "..." + text
