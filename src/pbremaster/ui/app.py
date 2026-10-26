"""pbremaster: the game window and the menu screens.

Navigation follows PANDORA.EUL: buttons run the command registered for their
id (table at 0x5d4100, extracted by tools/re/commands.py), show a screen, or end
a dialog. Screens the remaster does not play yet (world map, cities, puzzles)
are shown with working Back / Menu / Quick Help buttons.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pygame

from .. import __version__
from ..data import catalogue, cursors, gamedir
from ..data import screens as sd
from ..data.assets import Assets
from ..data.rof import ROF
from ..data.strings import load_strings
from ..settings import Settings
from . import widgets
from .media import Fonts, Sounds

WIDTH, HEIGHT = 800, 600

# Screen ids (SCREEN.DAT)
MAIN, LOAD_DLG, SAVE_DLG, OPTIONS_DLG = 100, 101, 102, 103
PUZZLES_ONLY, WORLD_MAP, CITY, PRACTICE_CITY, GALLERY = 150, 400, 500, 501, 600
CREDITS, ABOUT = 1998, 1202

# Puzzle-type radio buttons on the Puzzles Only screen (150-161) -> kind name.
TYPE_BUTTONS = {150: "Image Hole", 151: "Focus Point", 152: "Rotascope", 153: "Overlap",
                154: "Outer Layer", 156: "Jesse's Strips", 158: "Slices", 159: "Lens Bender",
                160: "Interlock", 161: "Find and Fill"}

# Drop-down menu (LANGENU menu 105) command ids.
MENU_MAIN_SCREEN, MENU_SAVE, MENU_MINIMIZE, MENU_OPTIONS, MENU_EXIT = 40001, 40004, 40002, 40007, 40008


class DropMenu:
    """The Menu button's pop-up (a Win32 menu in the original)."""
    ITEMS = [(MENU_MAIN_SCREEN, "Main Screen..."), (MENU_SAVE, "Save..."), (MENU_MINIMIZE, "Minimize"),
             (MENU_OPTIONS, "Options..."), (None, None), (MENU_EXIT, "Exit Pandora's Box")]
    BG, FG, HI, DIM = (236, 220, 190), (30, 10, 0), (120, 50, 10), (150, 130, 110)

    def __init__(self, fonts, anchor, enabled):
        self.font = fonts.get(14)
        self.enabled = enabled
        w = max(self.font.size(t)[0] for _, t in self.ITEMS if t) + 40
        self.rows = []
        y = 0
        for cid, text in self.ITEMS:
            h = 8 if cid is None else 22
            self.rows.append((cid, text, pygame.Rect(0, y, w, h)))
            y += h
        self.rect = pygame.Rect(0, 0, w, y + 4)
        self.rect.topright = anchor
        self.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))
        self.hover = None

    def item_at(self, pos):
        for cid, _, r in self.rows:
            if cid and r.move(self.rect.x, self.rect.y + 2).collidepoint(pos):
                return cid
        return None

    def draw(self, surf):
        pygame.draw.rect(surf, self.BG, self.rect)
        pygame.draw.rect(surf, self.FG, self.rect, 1)
        for cid, text, r in self.rows:
            r = r.move(self.rect.x, self.rect.y + 2)
            if cid is None:
                pygame.draw.line(surf, self.DIM, (r.x + 4, r.centery), (r.right - 4, r.centery))
                continue
            on = self.enabled.get(cid, True)
            if on and cid == self.hover:
                pygame.draw.rect(surf, self.HI, r.inflate(-4, 0))
            colour = (255, 255, 255) if on and cid == self.hover else (self.FG if on else self.DIM)
            surf.blit(self.font.render(text, True, colour), (r.x + 14, r.y + 3))


class TextScreen:
    """Credits / About: the PNG backdrops named in SCREEN.DAT are not on the CD,
    so the text is drawn on a plain dialog frame with the screen's OK button."""

    def __init__(self, view: widgets.ScreenView, lines, fonts):
        self.view, self.lines, self.fonts = view, lines, fonts
        self.box = pygame.Rect(0, 0, 520, 520)
        self.box.center = (WIDTH // 2, HEIGHT // 2)
        for w in view.widgets:
            w.rect.topleft = (self.box.centerx - w.rect.w // 2, self.box.bottom - w.rect.h - 14)

    def draw(self, surf):
        pygame.draw.rect(surf, (40, 18, 6), self.box)
        pygame.draw.rect(surf, (248, 176, 100), self.box, 2)
        y = self.box.y + 18
        for line in self.lines:
            bold = line.startswith("%B")
            text = line.replace("%B", "")
            f = self.fonts.get(15, bold=bold)
            colour = (248, 176, 100) if bold else (236, 220, 190)
            if text:
                img = f.render(text, True, colour)
                surf.blit(img, (self.box.centerx - img.get_width() // 2, y))
            y += 18 if text else 8
            if y > self.box.bottom - 70:
                break
        for w in self.view.widgets:
            w.draw(surf)


class App:
    def __init__(self, game: gamedir.GameDir, settings: Settings):
        self.game, self.settings = game, settings
        self.window = None
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.assets = Assets(game)
        self.fonts = Fonts(game)
        self.sounds = Sounds(game, settings)
        self.strings = load_strings(game.file("LANGENU.DLL"))
        self.names = load_strings(game.file("NAMEENU.DLL"))
        layout = sd.parse(self.assets.raw("SCREENS/SCREEN.DAT"))
        self.ui = widgets.UI(self.assets, self.fonts, self.sounds, self.strings, layout)
        self.levels = catalogue.load(ROF(game.file("PANDORA.ROF")))
        self.stack: list[widgets.ScreenView] = []
        self.dialogs: list[tuple[widgets.ScreenView, callable]] = []
        self.menu: DropMenu | None = None
        self.text_screen: TextScreen | None = None
        self.running = True
        self.show(MAIN)

    # ---------------------------------------------------------------- screens
    @property
    def view(self) -> widgets.ScreenView:
        return self.stack[-1]

    def show(self, screen_id):
        self.stack.append(widgets.ScreenView(self.ui, screen_id))
        self.enter(self.view)

    def back(self):
        if len(self.stack) > 1:
            self.stack.pop()
            self.enter(self.view)

    def main_screen(self):
        self.stack = self.stack[:1]
        self.enter(self.view)

    def enter(self, view):
        if view.id == MAIN:
            self.refresh_players(view)
        elif view.id == PUZZLES_ONLY:
            view.select_radio(150)
            self.fill_puzzle_list(view, 150)

    def dialog(self, screen_id, on_result=None):
        view = widgets.ScreenView(self.ui, screen_id)
        self.dialogs.append((view, on_result))
        if screen_id == OPTIONS_DLG:
            for cid, on in ((721, self.settings.sound), (722, self.settings.music), (723, self.settings.timer)):
                view[cid].on = on
        return view

    def end_dialog(self, result):
        view, cb = self.dialogs.pop()
        if cb:
            cb(view, result)

    def active(self) -> widgets.ScreenView:
        if self.text_screen:
            return self.text_screen.view
        return self.dialogs[-1][0] if self.dialogs else self.view

    # ----------------------------------------------------------- main menu
    def refresh_players(self, view):
        view[108].items = list(self.settings.players)
        view[108].selected = 0 if self.settings.players else -1
        view[107].value = self.settings.players[0] if self.settings.players else ""
        # Label 109 says whether PLAY resumes or starts a game (LANGENU 109/110).
        view[109].set_text(self.strings.get(110, ""))

    def player_ready(self) -> bool:
        """0x41c520: the name typed in the main menu becomes the current player."""
        name = self.stack[0][107].value.strip()
        if not name:
            self.sounds.play(Sounds.NO_CLICK)
            return False
        self.settings.use_player(name)
        self.settings.save()
        return True

    # ------------------------------------------------------------ commands
    def command(self, cid, button):
        if cid == 101:                      # PLAY -> story / world map (campaign not done yet)
            if self.player_ready():
                self.show(WORLD_MAP)
        elif cid == 102:                    # TUTORIAL -> practice city (0x41c4d0)
            if self.player_ready():
                self.show(PRACTICE_CITY)
        elif cid == 103:                    # GALLERY (0x41c3b0)
            if self.player_ready():
                self.show(GALLERY)
        elif cid == 104:                    # PUZZLES ONLY (0x41c500)
            if self.player_ready():
                self.show(PUZZLES_ONLY)
        elif cid == 105:                    # OPTIONS dialog (0x414cf0)
            self.dialog(OPTIONS_DLG, self.options_closed)
        elif cid == 106:                    # LOAD dialog (0x41c3e0)
            if self.player_ready():
                self.dialog(LOAD_DLG)
        elif cid == 52:
            self.back()
        elif cid == 54:
            self.open_menu(button)
        elif cid == 703:                    # Options: Apply
            self.end_dialog(1)
        elif cid == 716:
            self.show_text(CREDITS, self.game.file("CREDITS.DAT").read_text("latin-1").splitlines())
        elif cid == 717:
            self.show_text(ABOUT, [f"%BPandora's Box Remaster {__version__}", "",
                                   "Runs on the original Microsoft Pandora's Box files.",
                                   "", "%BGame Designer", "Alexey Pajitnov"])
        elif cid == 150:                    # puzzle type picked on Puzzles Only
            self.fill_puzzle_list(self.view, button.id)
        else:
            # Load / Save / Delete / Play puzzle and the in-game commands come
            # with the save games and puzzles.
            self.sounds.play(Sounds.NO_CLICK)

    def options_closed(self, view, result):
        if result == 1:
            self.settings.sound, self.settings.music, self.settings.timer = (
                view[721].on, view[722].on, view[723].on)
            self.settings.save()

    def show_text(self, screen_id, lines):
        self.text_screen = TextScreen(widgets.ScreenView(self.ui, screen_id), lines, self.fonts)

    def fill_puzzle_list(self, view, type_button):
        kind = TYPE_BUTTONS.get(type_button)
        items = []
        for lv in self.levels.values():
            for city in sorted(lv.cities.values(), key=lambda c: c.id):
                for p in sorted(city.puzzles.values(), key=lambda p: p.number):
                    if p.kind_name == kind:
                        items.append(self.names.get(p.name_id, f"{city.name.title()} {p.number}"))
        view[165].items = items
        view[165].selected = 0 if items else -1

    # ---------------------------------------------------------------- menu
    def open_menu(self, button):
        on_main = self.view.id == MAIN and not self.dialogs
        enabled = {MENU_MAIN_SCREEN: not on_main, MENU_SAVE: False, MENU_OPTIONS: not self.dialogs}
        self.menu = DropMenu(self.fonts, (button.rect.right, button.rect.bottom + 2), enabled)

    def menu_pick(self, cid):
        self.menu = None
        if cid == MENU_MAIN_SCREEN:
            self.dialogs.clear()
            self.main_screen()
        elif cid == MENU_MINIMIZE:
            pygame.display.iconify()
        elif cid == MENU_OPTIONS:
            self.dialog(OPTIONS_DLG, self.options_closed)
        elif cid == MENU_EXIT:
            self.running = False

    # -------------------------------------------------------------- events
    def click(self, button: widgets.Button):
        c = button.ctl
        if c.action == sd.ACT_COMMAND:
            self.command(c.arg, button)
        elif c.action == sd.ACT_SCREEN:
            self.show(c.arg)
        elif c.action == sd.ACT_END_DIALOG:
            if self.text_screen:
                self.text_screen = None
            elif self.dialogs:
                self.end_dialog(c.arg)
        elif c.action == sd.ACT_HELP:
            # The quick-help RTFs named in SCREEN.DAT are not on the CD.
            self.sounds.play(Sounds.HELP)
        elif c.action == sd.ACT_QUIT:
            self.running = False

    def handle(self, ev):
        if ev.type == pygame.QUIT:
            self.running = False
            return
        if ev.type == pygame.KEYDOWN:
            self.key(ev)
            return
        if ev.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            return
        pos = self.to_canvas(ev.pos)
        if self.menu:
            self.menu_mouse(ev, pos)
            return
        view = self.active()
        if ev.type == pygame.MOUSEMOTION:
            view.mouse_move(pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            hit = view.mouse_down(pos)
            if hit and hit[0] == "list" and hit[2] >= 0:
                lst = hit[1]
                lst.selected = hit[2]
                if lst.id == 108:            # pick a player
                    view[107].value = lst.items[hit[2]]
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            b = view.mouse_up(pos)
            if b:
                self.click(b)

    def key(self, ev):
        if ev.key == pygame.K_F11:
            self.toggle_fullscreen()
        elif ev.key == pygame.K_ESCAPE:
            if self.menu:
                self.menu = None
            elif self.text_screen:
                self.text_screen = None
            elif self.dialogs:
                self.end_dialog(2)
            else:
                self.back()
        else:
            view = self.active()
            if view.focus is None:
                return
            if ev.key == pygame.K_RETURN and view.id == MAIN:
                self.command(101, None)
            else:
                view.focus.key(ev)

    def menu_mouse(self, ev, pos):
        if ev.type == pygame.MOUSEMOTION:
            self.menu.hover = self.menu.item_at(pos)
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            cid = self.menu.item_at(pos)
            if cid and self.menu.enabled.get(cid, True):
                self.menu_pick(cid)
            elif not self.menu.rect.collidepoint(pos):
                self.menu = None

    # ------------------------------------------------------------- drawing
    def draw(self):
        c = self.canvas
        c.fill((0, 0, 0))
        self.view.draw(c)
        for view, _ in self.dialogs:
            view.draw(c)
        if self.text_screen:
            self.text_screen.draw(c)
        if self.menu:
            self.menu.draw(c)
        return c

    def to_canvas(self, pos):
        ww, wh = self.window.get_size()
        scale = min(ww / WIDTH, wh / HEIGHT)
        ox, oy = (ww - WIDTH * scale) / 2, (wh - HEIGHT * scale) / 2
        return int((pos[0] - ox) / scale), int((pos[1] - oy) / scale)

    def toggle_fullscreen(self):
        self.settings.fullscreen = not self.settings.fullscreen
        self.open_window()
        self.settings.save()

    def open_window(self):
        if self.settings.fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

    def set_cursor(self):
        """The game's own arrow (cursor 109 in PANDORA.EUL), if the EUL is there."""
        try:
            rgba, hot = cursors.load(self.game.file("PANDORA.EUL"))
        except (FileNotFoundError, KeyError, ValueError):
            return
        surf = pygame.image.frombuffer(np.ascontiguousarray(rgba).tobytes(), rgba.shape[1::-1], "RGBA")
        pygame.mouse.set_cursor(pygame.cursors.Cursor(hot, surf.copy()))


def present(window, canvas):
    """Scale the 800x600 canvas into the window, keeping the aspect ratio."""
    ww, wh = window.get_size()
    scale = min(ww / WIDTH, wh / HEIGHT)
    size = (int(WIDTH * scale), int(HEIGHT * scale))
    window.fill((0, 0, 0))
    window.blit(pygame.transform.smoothscale(canvas, size), ((ww - size[0]) // 2, (wh - size[1]) // 2))
    pygame.display.flip()


def splash(app, clock):
    """SPLASH.PNG for up to 4 seconds; any key or click skips it."""
    image = app.assets.loose_image("SPLASH.PNG")
    shown = 0
    while shown < 4000:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                shown = 4000
        app.canvas.fill((0, 0, 0))
        app.canvas.blit(image, image.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        present(app.window, app.canvas)
        shown += clock.tick(60)
    pygame.event.clear()
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pbremaster")
    ap.add_argument("--data", help="folder with the original Pandora's Box files")
    ap.add_argument("--screenshot", metavar="PNG", help="render a screen to PNG and exit")
    ap.add_argument("--screen", type=int, default=MAIN, help="screen id for --screenshot")
    ap.add_argument("--dialog", type=int, help="dialog screen id drawn on top for --screenshot")
    ap.add_argument("--hover", type=int, help="control id shown hovered for --screenshot")
    args = ap.parse_args(argv)

    try:
        game = gamedir.find(args.data)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1

    pygame.mixer.pre_init(22050, -16, 2, 512)
    pygame.init()
    settings = Settings.load()
    strings = load_strings(game.file("LANGENU.DLL"))
    pygame.display.set_caption(f"{strings.get(56, 'Pandora' + chr(39) + 's Box')} Remaster {__version__}")

    if args.screenshot:
        pygame.display.set_mode((WIDTH, HEIGHT))
        app = App(game, settings)
        if args.screen != MAIN:
            app.show(args.screen)
        if args.dialog:
            app.dialog(args.dialog)
        if args.hover:
            app.active()[args.hover].hover = True
        pygame.image.save(app.draw(), args.screenshot)
        return 0

    app = App(game, settings)
    app.open_window()
    app.set_cursor()
    clock = pygame.time.Clock()
    if not splash(app, clock):
        return 0
    while app.running:
        for ev in pygame.event.get():
            app.handle(ev)
        present(app.window, app.draw())
        clock.tick(60)
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
