"""pbremaster: the game window, the menus and the campaign flow.

Navigation follows PANDORA.EUL: buttons run the command registered for their
id (table at 0x5d4100, extracted by tools/re/commands.py), show a screen, or end
a dialog. Screens with code-drawn content get a Scene (ui/campaign.py).
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pygame

from .. import __version__
from ..data import catalogue, cursors, gamedir, m20
from ..data import screens as sd
from ..data.assets import Assets
from ..data.rof import ROF
from ..data.strings import load_strings
from ..game import world
from ..game.progress import Player
from ..settings import Settings
from . import campaign, widgets
from .media import Fonts, Sounds
from .music import Music

WIDTH, HEIGHT = 800, 600

# Screen ids (SCREEN.DAT)
MAIN, LOAD_DLG, SAVE_DLG, OPTIONS_DLG = 100, 101, 102, 103
PUZZLES_ONLY, WORLD_MAP, CITY, PRACTICE_CITY, GALLERY = 150, 400, 500, 501, 600
CREDITS, ABOUT = 1998, 1202
LAST_LEVEL = 7          # level 8 (Scalawag) is not wired up yet

# Dialog results (button action 15)
OK, CANCEL, YES, NO, MAP_, STAY, CAPTURE = 1, 2, 6, 7, 16, 17, 18

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


class TextScene(campaign.Scene):
    """Credits (CREDITS1, text from CREDITS.DAT, %B = bold) and About (ABOUT1):
    black framed pages whose text the game draws in code. Text that does not
    fit scrolls upwards above the box in the corner."""
    SPEED = 22          # pixels per second

    def __init__(self, app, view, lines):
        super().__init__(app, view)
        self.lines = lines
        self.offset = 0.0
        r = view.rect
        self.area = pygame.Rect(r.x + 20, r.y + 22, r.w - 40, r.h - 22 - 190)
        self.height = sum(18 if line.replace("%B", "") else 8 for line in lines)

    def update(self, dt):
        if self.height > self.area.h:
            self.offset = (self.offset + dt * self.SPEED) % (self.height + self.area.h)

    def draw_front(self, surf):
        clip = surf.get_clip()
        surf.set_clip(self.area)
        scrolling = self.height > self.area.h
        y = self.area.y + (self.area.h - self.offset if scrolling else 0)
        for line in self.lines:
            bold = "%B" in line
            text = line.replace("%B", "")
            if text:
                f = self.app.fonts.get(15, bold=bold)
                img = f.render(text, True, (248, 176, 100) if bold else (236, 220, 190))
                surf.blit(img, (self.area.centerx - img.get_width() // 2, y))
            y += 18 if text else 8
        surf.set_clip(clip)


class App:
    def __init__(self, game: gamedir.GameDir, settings: Settings):
        self.game, self.settings = game, settings
        self.window = None
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.assets = Assets(game)
        self.fonts = Fonts(game)
        self.sounds = Sounds(game, settings)
        self.music = Music(game, settings)
        self.strings = load_strings(game.file("LANGENU.DLL"))
        self.status = load_strings(game.file("STATENU.DLL"))
        self.names = load_strings(game.file("NAMEENU.DLL"))
        self.credits = load_strings(game.file("PUZENU.DLL"))
        layout = sd.parse(self.assets.raw("SCREENS/SCREEN.DAT"))
        self.ui = widgets.UI(self.assets, self.fonts, self.sounds, self.strings, layout)
        self.levels = catalogue.load(ROF(game.file("PANDORA.ROF")))
        self.player: Player | None = None
        self.stack: list[widgets.ScreenView] = []
        self.dialogs: list[tuple[widgets.ScreenView, callable]] = []
        self.menu: DropMenu | None = None
        self.running = True
        self.show(MAIN)

    # ---------------------------------------------------------------- screens
    @property
    def view(self) -> widgets.ScreenView:
        return self.stack[-1]

    def push(self, view):
        self.stack.append(view)
        self.enter(view)
        return view

    def replace(self, view):
        self.stack[-1] = view
        self.enter(view)
        return view

    def show(self, screen_id):
        return self.push(widgets.ScreenView(self.ui, screen_id))

    def back(self):
        if len(self.stack) > 1:
            self.stack.pop()
            self.enter(self.view)

    def main_screen(self):
        self.dialogs.clear()
        self.stack = self.stack[:1]
        self.enter(self.view)

    def enter(self, view):
        if view.scene:
            view.scene.enter()
        elif view.id == MAIN:
            self.refresh_players(view)
            self.music.theme("MUSIC/MAP.WAV")
        elif view.id == PUZZLES_ONLY:
            view.select_radio(150)
            self.fill_puzzle_list(view, 150)

    def dialog(self, view_or_id, on_result=None):
        view = view_or_id if isinstance(view_or_id, widgets.ScreenView) else widgets.ScreenView(self.ui, view_or_id)
        self.dialogs.append((view, on_result))
        if view.id == OPTIONS_DLG:
            for cid, on in ((721, self.settings.sound), (722, self.settings.music), (723, self.settings.timer)):
                view[cid].on = on
        if view.scene:
            view.scene.enter()
        return view

    def end_dialog(self, result):
        view, cb = self.dialogs.pop()
        if cb:
            cb(view, result)

    def active(self) -> widgets.ScreenView:
        return self.dialogs[-1][0] if self.dialogs else self.view

    def message(self, text, buttons=(1200,), on_result=None):
        view = campaign.message_view(self.ui, list(buttons))
        campaign.MessageScene(self, view, text)
        self.sounds.play(Sounds.ALERT)
        return self.dialog(view, (lambda v, r: on_result(r)) if on_result else None)

    def quick_help(self):
        """The screen's help topic (SCREEN.DAT help field) from HELP/PANDORA.M20, as the
        original's viewer (0x5075d0) shows it on message 0x8065."""
        self.sounds.play(Sounds.HELP)
        screen = self.ui.layout.screens.get(self.active().id)
        name = screen.help_rtf if screen else ""
        if not name:
            return None
        try:
            paragraphs = m20.topic(self.game.file("HELP", "PANDORA.M20").read_bytes(), name)
        except (FileNotFoundError, ValueError):
            paragraphs = None
        if not paragraphs:
            return None
        view = campaign.message_view(self.ui, [1200])
        campaign.HelpScene(self, view, paragraphs)
        return self.dialog(view)

    def confirm(self, text, on_yes):
        self.message(text, (1201, 1202), lambda r: on_yes() if r == YES else None)

    # ----------------------------------------------------------- main menu
    def refresh_players(self, view):
        view[108].items = list(self.settings.players)
        view[108].selected = 0 if self.settings.players else -1
        view[107].value = self.settings.players[0] if self.settings.players else ""
        self.update_resume_label(view)

    def update_resume_label(self, view=None):
        """Label 109: 'Resume game' (LANGENU 109) or 'Play new game' (110) for the typed player."""
        view = view or self.stack[0]
        name = view[107].value.strip()
        view[109].set_text(self.strings.get(109 if name and Player.exists(name) else 110, ""))

    def player_ready(self) -> bool:
        """0x41c520: the name typed in the main menu becomes the current player."""
        name = self.stack[0][107].value.strip()
        if not name:
            self.sounds.play(Sounds.NO_CLICK)
            return False
        self.settings.use_player(name)
        self.settings.save()
        if self.player is None or self.player.name != name:
            self.player = Player.load(name)
        return True

    def save_player(self):
        if self.player:
            self.player.save()

    # -------------------------------------------------------------- campaign
    def city_name(self, city) -> str:
        return self.strings.get(460 + city.id, city.name.title()) if city.id else self.strings.get(497, "Tutorial")

    def city_slot(self, level, city) -> int:
        """Which of the level's five pieces this city holds (cities in id order)."""
        return sorted(c.id for c in level.cities.values()).index(city.id)

    def found_slots(self, level):
        return {self.city_slot(level, c) for c in level.cities.values() if c.path in self.player.pieces}

    def is_solved(self, city, puzzle):
        return self.player.is_solved(city.path, puzzle.number) if self.player else False

    def puzzle_credits(self, puzzle):
        return campaign.parse_credits(self.credits.get(puzzle.name_id, ""))

    def play(self):
        """PLAY (0x41bc90): the level's story video once, then the map or the saved city."""
        p = self.player
        if p.finished:
            self.message(self.strings.get(1029, ""))
            return
        if p.level not in p.videos_seen:
            p.videos_seen.append(p.level)
            self.save_player()
            self.play_video(world.LEVEL_VIDEOS[p.level - 1], self.resume)
        else:
            self.resume()

    def resume(self):
        p = self.player
        self.stack = self.stack[:1]
        self.show_map()
        level = self.levels[p.level]
        if p.city and p.city in level.cities:
            self.enter_city(level.cities[p.city])

    def play_video(self, name, then):
        try:
            path = self.game.file(name)
        except FileNotFoundError:
            then()
            return
        scene = campaign.VideoScene(self, path, lambda: (self.stack.pop(), then()))
        self.push(scene.view)

    def show_map(self):
        view = widgets.ScreenView(self.ui, WORLD_MAP)
        campaign.MapScene(self, view)
        if self.view.id == WORLD_MAP:
            return self.replace(view)
        return self.push(view)

    def enter_city(self, city):
        level = self.levels[self.player.level]
        self.player.city = city.path.split("/")[-1]
        self.save_player()
        view = widgets.ScreenView(self.ui, CITY)
        campaign.CityScene(self, view, level, city)
        self.push(view)

    def open_practice(self):
        lv0 = self.levels[0]
        city = catalogue.City(lv0.path, 0, "TUTORIAL", lv0.puzzles)
        view = widgets.ScreenView(self.ui, PRACTICE_CITY)
        campaign.CityScene(self, view, lv0, city)
        self.push(view)

    def open_puzzle(self, level, city, puzzle, master=False, slot_id=None):
        screen = world.KIND_SCREEN.get(puzzle.kind_name, 2000)
        view = widgets.ScreenView(self.ui, screen)
        campaign.PuzzleScene(self, view, level, city, puzzle, master=master, slot_id=slot_id)
        self.push(view)

    def leave_puzzle(self, scene):
        self.back()

    def puzzle_solved(self, scene, used_free=False):
        p = self.player
        self.dialogs.clear()
        if scene.master:
            events = p.solve_master(scene.level, scene.puzzle, used_free)
        elif scene.level.number == 0:
            p.solved.setdefault(scene.city.path, [])
            if scene.puzzle.number not in p.solved[scene.city.path]:
                p.solved[scene.city.path].append(scene.puzzle.number)
            events = ["practice"]
        else:
            events = p.solve(scene.city, scene.puzzle, used_free)
        self.save_player()
        self.sounds.play("SUCCESS")
        region = world.REGIONS.get(scene.city.id) if scene.city else None
        stem = world.REGION_MUSIC.get(region)
        self.music.play_once("MUSIC/CHWIN.WAV" if scene.master else f"MUSIC/S_{stem or 'LEVEND'}.WAV")
        self.back()                                   # leave the puzzle screen
        if not scene.master and self.view.scene and hasattr(self.view.scene, "flip"):
            self.view.scene.flip(scene.slot_id)
            self.view.scene.refresh()
        view = campaign.success_view(self.ui)
        campaign.SuccessScene(self, view, scene.puzzle, scene.elapsed)
        self.dialog(view, lambda v, r: self.after_success(scene, events))

    def after_success(self, scene, events):
        """Reward messages and where to go next, one after another."""
        p = self.player
        if "practice" in events:
            self.message(self.strings.get(1029, ""))
            return
        for ev, sound in (("token", "INCWC1"), ("wildcard", "INCWC1"), ("hint", "INCHINT1")):
            if ev in events:
                self.sounds.play(sound)
        if self.view.scene and hasattr(self.view.scene, "refresh"):
            self.view.scene.refresh()
        if "captured" in events:
            self.captured(scene.level)
            return
        if scene.master:
            self.start_master(scene.level)
            return
        if "piece" in events:
            n = len(p.level_pieces(scene.level.path))
            stem = world.VO_STEMS[scene.level.number - 1]
            self.music.play_once(f"VO/SX_{stem}{n}.WAV")
            buttons = (1206, 1205) if "challenge" in events else (1204, 1205)
            self.message(self.status.get(210, ""), buttons, self.after_piece)
            return
        if "city_done" in events:
            self.message(self.strings.get(1011, ""), (1200,), lambda r: self.leave_city())

    def after_piece(self, result):
        if result == CAPTURE:
            self.open_challenge()
        elif result == MAP_:
            self.leave_city()

    def leave_city(self):
        self.player.city = None
        self.save_player()
        while len(self.stack) > 1 and self.view.id != WORLD_MAP:
            self.stack.pop()
        if self.view.id != WORLD_MAP:
            self.show_map()
        else:
            self.enter(self.view)

    def open_challenge(self):
        level = self.levels[self.player.level]
        view = campaign.challenge_view(self.ui)
        campaign.ChallengeScene(self, view, level)
        self.push(view)

    def start_master(self, level):
        done = self.player.master_solved.get(level.path, [])
        todo = [pz for n, pz in sorted(level.puzzles.items()) if n not in done]
        if todo:
            self.open_puzzle(level, None, todo[0], master=True)

    def captured(self, level):
        def next_level():
            self.player.next_level(LAST_LEVEL)
            self.save_player()
            self.stack = self.stack[:1]
            if self.player.finished:
                self.play_video(world.LEVEL_VIDEOS[LAST_LEVEL], self.main_screen)
            else:
                self.play()
        scene = campaign.CapturedScene(self, level, next_level)
        self.push(scene.view)

    # ------------------------------------------------------------ commands
    def command(self, cid, button):
        scene = self.active().scene
        if scene and scene.command(cid, button):
            return
        if cid == 101:                      # PLAY (0x41bc90)
            if self.player_ready():
                self.play()
        elif cid == 102:                    # TUTORIAL -> practice city (0x41c4d0)
            if self.player_ready():
                self.open_practice()
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
            self.end_dialog(OK)
        elif cid == 716:
            view = widgets.ScreenView(self.ui, CREDITS)
            TextScene(self, view, self.game.file("CREDITS.DAT").read_text("latin-1").splitlines())
            self.dialog(view)
        elif cid == 717:
            view = widgets.ScreenView(self.ui, ABOUT)
            TextScene(self, view, [f"%BPandora's Box Remaster {__version__}", "",
                                   self.strings.get(1050, ""), self.strings.get(1053, ""), "",
                                   "%BGame Designer", "Alexey Pajitnov", "",
                                   self.strings.get(1054, ""), self.strings.get(1071, "")])
            self.dialog(view)
        elif cid == 150:                    # puzzle type picked on Puzzles Only
            self.fill_puzzle_list(self.view, button.id)
        else:
            # Load / Save / Delete / Play puzzle come with save games and the puzzles.
            self.sounds.play(Sounds.NO_CLICK)

    def options_closed(self, view, result):
        if result == OK:
            self.settings.sound, self.settings.music, self.settings.timer = (
                view[721].on, view[722].on, view[723].on)
            self.settings.save()

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
            self.save_player()
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
            if self.dialogs:
                self.end_dialog(c.arg)
        elif c.action == sd.ACT_HELP:
            self.quick_help()
        elif c.action == sd.ACT_QUIT:
            self.running = False

    def handle(self, ev):
        if ev.type == pygame.QUIT:
            self.running = False
            return
        if ev.type == pygame.KEYDOWN:
            self.key(ev)
            return
        if ev.type == pygame.MOUSEWHEEL:
            scene = self.active().scene
            if scene and hasattr(scene, "wheel"):
                scene.wheel(ev.y)
            return
        if ev.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            return
        pos = self.to_canvas(ev.pos)
        if self.menu:
            self.menu_mouse(ev, pos)
            return
        view = self.active()
        scene = view.scene
        if ev.type == pygame.MOUSEMOTION:
            view.mouse_move(pos)
            if scene:
                scene.mouse_move(pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
            if scene and hasattr(scene, "right_click"):
                scene.right_click(pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if scene and scene.mouse_down(pos):
                return
            hit = view.mouse_down(pos)
            if hit and hit[0] == "list" and hit[2] >= 0:
                lst = hit[1]
                lst.selected = hit[2]
                if lst.id == 108:            # pick a player
                    view[107].value = lst.items[hit[2]]
                    self.update_resume_label(view)
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            if view.capture is None and scene and scene.mouse_up(pos):
                return
            b = view.mouse_up(pos)
            if b:
                self.click(b)

    def key(self, ev):
        if ev.key == pygame.K_F11:
            self.toggle_fullscreen()
            return
        view = self.active()
        if view.scene and view.scene.key(ev):
            return
        if ev.key == pygame.K_ESCAPE:
            if self.menu:
                self.menu = None
            elif self.dialogs:
                self.end_dialog(CANCEL)
            elif view.id != MAIN:
                b = view.by_id.get(52)
                if b:
                    self.click(b)
        elif view.focus is not None:
            if ev.key == pygame.K_RETURN and view.id == MAIN:
                self.command(101, None)
            else:
                view.focus.key(ev)
                if view.id == MAIN:
                    self.update_resume_label(view)

    def menu_mouse(self, ev, pos):
        if ev.type == pygame.MOUSEMOTION:
            self.menu.hover = self.menu.item_at(pos)
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            cid = self.menu.item_at(pos)
            if cid and self.menu.enabled.get(cid, True):
                self.menu_pick(cid)
            elif not self.menu.rect.collidepoint(pos):
                self.menu = None

    def update(self, dt):
        for view in [self.view] + [v for v, _ in self.dialogs]:
            if view.scene:
                view.scene.update(dt)
        self.music.update(dt)

    # ------------------------------------------------------------- drawing
    def draw(self):
        c = self.canvas
        c.fill((0, 0, 0))
        self.view.draw(c)
        for view, _ in self.dialogs:
            view.draw(c)
        if self.menu:
            self.menu.draw(c)
        return c

    def mouse_pos(self):
        return self.to_canvas(pygame.mouse.get_pos()) if self.window else (-1, -1)

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

    pygame.mixer.pre_init(22050, -16, 2, 1024)
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
    app.music.play_once("MUSIC/INTRO.WAV")
    if not splash(app, clock):
        return 0
    while app.running:
        for ev in pygame.event.get():
            app.handle(ev)
        app.update(clock.get_time() / 1000)
        present(app.window, app.draw())
        clock.tick(60)
    app.save_player()
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
