"""The campaign screens: story videos, world map, cities, puzzles, the trickster's Challenge.

Each is a SCREEN.DAT screen (or a code-built one) plus a Scene that draws what the
original draws in code and handles its buttons. Asset numbering, from PANDORA.EUL
and the SCREENS archive:
    1600 + city id          city picture (516x381 at 142,25, blue colour key)
    521 + level             trickster portrait in the city's right panel (522 Maui ... 528 Raven)
    510 + type index        city puzzle tile, 16 flip frames; the R strip is the solved side
    401B / 403B / 402       map marker: piece not found / piece found / current city
    1800 + level - 1        the box on the Challenge screen
    15<level-1><k>          piece k of a level: F (found) / NF strips of 4, A mask
    1701 + level - 1        the trickster, full screen, when captured
"""
from __future__ import annotations

import dataclasses
import re

import pygame

from ..data import screens as sd
from ..game import world
from ..game.progress import MASTER_FREE_COST
from . import widgets
from .video import RECT as VIDEO_RECT
from .video import Video

TEXT = (248, 176, 100)
DARK = (63, 15, 0)

CITY_SLOTS = [504, 505, 506, 507, 508, 509, 510, 511, 512, 513]
PRACTICE_SLOTS = [504, 505, 506, 507, 508, 514, 510, 515, 512, 513]


def shadow_text(surf, font, text, pos, colour=TEXT, centre=False, shade=(0, 0, 0)):
    img = font.render(text, True, colour)
    x, y = pos
    if centre:
        x -= img.get_width() // 2
    surf.blit(font.render(text, True, shade), (x + 2, y + 2))
    surf.blit(img, (x, y))
    return img.get_size()


def wrap(font, text, width):
    lines = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            trial = f"{line} {word}".strip()
            if font.size(trial)[0] > width and line:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
    return lines


class Scene:
    def __init__(self, app, view):
        self.app, self.view, self.ui = app, view, app.ui
        view.scene = self

    def img(self, name, key=True):
        rim = sd.rim_name(name)
        return self.app.assets.image(rim, colorkey=key) if self.app.assets.has(rim) else None

    def frames(self, name, count, key=True):
        strip = self.img(name, key)
        if strip is None:
            return []
        w = strip.get_width() // count
        return [strip.subsurface((i * w, 0, w, strip.get_height())) for i in range(count)]

    def enter(self):
        pass

    def draw_back(self, surf):
        pass

    def draw_front(self, surf):
        pass

    def update(self, dt):
        pass

    def mouse_move(self, pos):
        return False

    def mouse_down(self, pos):
        return False

    def mouse_up(self, pos):
        return False

    def command(self, cid, button):
        return False

    def key(self, ev):
        return False


# --------------------------------------------------------------------- video
class VideoScene(Scene):
    """Screen 40: a movie over AVIBACK.PNG; any click or key skips it."""

    def __init__(self, app, path, then):
        super().__init__(app, widgets.ScreenView(app.ui, 40, controls=[]))
        self.back = app.assets.image("SCREENS/AVIBACK.PNG")
        self.video = Video(path, sound_on=app.settings.sound)
        self.then = then

    def enter(self):
        self.app.music.play_loop(None)

    def draw_back(self, surf):
        surf.blit(self.back, (0, 0))
        if self.video.frame is not None:
            surf.blit(self.video.frame, VIDEO_RECT)

    def update(self, dt):
        self.video.update(dt)
        if self.video.done:
            self.finish()

    def finish(self):
        if self.then:
            then, self.then = self.then, None
            self.video.stop()
            then()

    def mouse_up(self, pos):
        self.finish()
        return True

    def key(self, ev):
        self.finish()
        return True


# ----------------------------------------------------------------- world map
class Marker:
    SIZE = 15

    def __init__(self, city, pos):
        self.city = city
        self.rect = pygame.Rect(pos, (self.SIZE, self.SIZE))
        self.hover = False


class MapScene(Scene):
    """Screen 400. Markers for the current level's five cities (STATENU 400-402)."""

    def __init__(self, app, view):
        super().__init__(app, view)
        self.found = self.frames("401b.bmp", 4)          # orange ball: piece not found
        self.star = self.frames("403b.bmp", 4)           # star: piece found
        self.current = self.img("402.bmp")              # halo round the current city's marker
        if self.current:
            self.current = self.current.copy()
            self.current.set_alpha(160)                  # as the legend's "Current location" shows it
        self.font = app.fonts.get(14)
        self.title_font = app.fonts.get(18)
        old = {}
        for sid in range(461, 495):                      # the older city list the markers follow
            name = app.status.get(sid, "").replace("Solve puzzles in ", "").rstrip(".")
            old.setdefault(name, sid - 60)               # STATENU 461 -> control 401
        self.markers = []
        level = app.levels[app.player.level]
        for city in sorted(level.cities.values(), key=lambda c: c.id):
            name = app.city_name(city)
            if name in world.EXTRA_MARKERS:
                pos = world.EXTRA_MARKERS[name]
            elif name in old and old[name] in app.ui.layout.controls:
                pos = app.ui.layout.controls[old[name]].pos
            else:
                continue
            self.markers.append(Marker(city, pos))

    def enter(self):
        self.app.music.play_loop("MUSIC/MAP.WAV")

    def state(self, m):
        p = self.app.player
        here = p.city or p.last_city
        if here and m.city.path.endswith("/" + here):
            return "current"
        return "found" if m.city.path in p.pieces else "not found"

    def draw_front(self, surf):
        p, s = self.app.player, self.app.strings
        level_text = s.get(440 + p.level, "")
        shadow_text(surf, self.title_font, level_text, (10, 50))
        for i, sid in enumerate((450, 451, 452)):
            surf.blit(self.font.render(s.get(sid, "").strip(), True, DARK), (510, 456 + i * 24))
        if len(p.level_pieces(self.app.levels[p.level].path)) >= 5:
            label = s.get(1220 + p.level, "")
            self.challenge_rect = pygame.Rect(0, 0, *self.title_font.size(label))
            self.challenge_rect.midtop = (575, 532)
            shadow_text(surf, self.title_font, label, self.challenge_rect.midtop, centre=True)
        else:
            self.challenge_rect = None
        for m in self.markers:
            if self.state(m) == "current" and self.current:
                surf.blit(self.current, self.current.get_rect(center=m.rect.center))
            frames = self.star if m.city.path in p.pieces else self.found
            if frames:
                surf.blit(frames[2 if m.hover else 0], m.rect)
        for m in self.markers:
            if m.hover:
                st = {"current": 450, "not found": 451, "found": 452}[self.state(m)]
                lines = [self.app.city_name(m.city), s.get(st, "").strip()]
                w = max(self.font.size(t)[0] for t in lines) + 12
                box = pygame.Rect(0, 0, w, 18 * len(lines) + 6)
                box.midtop = (m.rect.centerx, m.rect.bottom + 4)
                box.clamp_ip(surf.get_rect())
                pygame.draw.rect(surf, (40, 18, 6), box)
                pygame.draw.rect(surf, TEXT, box, 1)
                for i, line in enumerate(lines):
                    img = self.font.render(line, True, TEXT)
                    surf.blit(img, (box.centerx - img.get_width() // 2, box.y + 3 + 18 * i))

    def mouse_move(self, pos):
        for m in self.markers:
            inside = m.rect.inflate(8, 8).collidepoint(pos)
            if inside and not m.hover:
                self.app.sounds.play(self.app.sounds.MOUSE_OVER)
            m.hover = inside
        return False

    def mouse_up(self, pos):
        for m in self.markers:
            if m.rect.inflate(8, 8).collidepoint(pos):
                self.app.sounds.play("DOORCITY")
                self.app.enter_city(m.city)
                return True
        if self.challenge_rect and self.challenge_rect.collidepoint(pos):
            self.app.open_challenge()
            return True
        return False


# ---------------------------------------------------------------------- city
class CityScene(Scene):
    FLIP = 0.8          # seconds for a tile to turn over

    def __init__(self, app, view, level, city):
        super().__init__(app, view)
        self.level, self.city = level, city
        self.practice = view.id == 501
        slots = PRACTICE_SLOTS if self.practice else CITY_SLOTS
        numbers = sorted(city.puzzles)
        self.slots = {cid: city.puzzles[n] for cid, n in zip(slots, numbers) if cid in view.by_id}
        self.picture = self.img(f"{1600 + city.id}.bmp") if not self.practice else self.img("1600.bmp")
        self.tiles = {}
        self.flipping = {}       # slot id -> seconds into the flip
        if not self.practice and 518 in view.by_id:
            view[518].image = self.img(f"{521 + level.number}.bmp")
        name = app.city_name(city)
        for cid in (522, 525):
            if cid in view.by_id:
                view[cid].set_text(name)
        if 517 in view.by_id:
            view[517].set_text("")

    def tile_frames(self, puzzle):
        idx = world.KIND_INDEX.get(puzzle.kind_name, 0)
        key = 510 + idx
        if key not in self.tiles:
            self.tiles[key] = (self.frames(f"{key}.bmp", 16), self.frames(f"{key}r.bmp", 16))
        return self.tiles[key]

    def enter(self):
        region = world.REGIONS.get(self.city.id)
        stem = world.REGION_MUSIC.get(region)
        self.app.music.play_loop(f"MUSIC/{stem}.WAV" if stem else "MUSIC/MAP.WAV")
        self.refresh()

    def refresh(self):
        p = self.app.player
        for cid, value in ((501, p.toward_token), (502, p.hints), (503, p.free)):
            if cid in self.view.by_id:
                self.view[cid].set_text(f"{value:02d}")

    def solved(self, puzzle):
        return self.app.is_solved(self.city, puzzle)

    def flip(self, slot_id):
        self.flipping[slot_id] = 0.0

    def update(self, dt):
        for k in list(self.flipping):
            self.flipping[k] += dt
            if self.flipping[k] >= self.FLIP:
                del self.flipping[k]

    def draw_back(self, surf):
        if self.picture:
            surf.blit(self.picture, (142, 25))
        for cid, pz in self.slots.items():
            front, back = self.tile_frames(pz)
            if not front:
                continue
            rect = self.view[cid].rect
            if cid in self.flipping:
                t = self.flipping[cid] / self.FLIP * 32
                frame = front[min(15, int(t))] if t < 16 else back[max(0, 31 - int(t))]
            else:
                frame = back[0] if self.solved(pz) and back else front[0]
            surf.blit(frame, frame.get_rect(center=rect.center))
            if self.view[cid].hover:
                pygame.draw.rect(surf, TEXT, rect.inflate(2, 2), 1)

    def draw_front(self, surf):
        p = self.app.player
        if not self.practice and self.city.path in p.pieces:
            slot = self.view.by_id.get(519)
            k = self.app.city_slot(self.level, self.city)
            frames = self.frames(f"150{self.level.number - 1}{k}f.bmp", 4)
            if slot and frames:
                piece = frames[3]
                w = slot.rect.w - 6
                h = int(piece.get_height() * w / piece.get_width())
                img = pygame.transform.smoothscale(piece, (w, h))
                surf.blit(img, img.get_rect(center=slot.rect.center))

    def command(self, cid, button):
        if cid == 504 and button.id in self.slots:
            self.app.open_puzzle(self.level, self.city, self.slots[button.id], slot_id=button.id)
            return True
        if cid == 519:
            self.app.open_challenge()
            return True
        if cid == 52:
            if self.practice:
                self.app.main_screen()
            else:
                self.app.player.city = None
                self.app.save_player()
                self.app.show_map()
            return True
        return False


# -------------------------------------------------------------------- puzzle
class PuzzleScene(Scene):
    """A puzzle screen (2000 Image Hole ... 13000 Find and Fill) around a game from
    pbremaster.puzzles. Types without a game yet show their picture and can be
    finished with a Free Puzzle token or (for testing) F9."""
    AREA = pygame.Rect(75, 42, 650, 540)
    SOLVED_PAUSE = 1.5          # seconds to admire the finished picture

    def __init__(self, app, view, level, city, puzzle, master=False, slot_id=None, only=False):
        super().__init__(app, view)
        from ..puzzles import game_for
        self.level, self.city, self.puzzle = level, city, puzzle
        self.master, self.slot_id = master, slot_id
        self.only = only                # from Puzzles Only: no campaign rewards
        self.elapsed = 0.0
        self.paused = False
        self.used_free = False
        self.done_for = None
        cls = game_for(puzzle.kind_name)
        self.game = cls(app, puzzle) if cls else None
        self.picture = None if self.game else self._picture()
        self.font = app.fonts.get(16)
        self.limit = puzzle.time_limit

    def _picture(self):
        best = None
        for f in self.puzzle.files:
            if f.endswith((".JPG", ".PNG", ".BMP")) and "/CAMERA" not in f:
                size = self.app.assets.pandora.files[f].size
                if best is None or size > best[0]:
                    best = (size, f)
        if not best:
            return None
        img = self.app.assets.image(best[1])
        scale = min(self.AREA.w / img.get_width(), self.AREA.h / img.get_height(), 1.0)
        return pygame.transform.smoothscale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))

    def enter(self):
        region = world.REGIONS.get(self.city.id) if self.city else None
        stem = world.REGION_MUSIC.get(region)
        self.app.music.play_loop(f"MUSIC/{stem}_P.WAV" if stem else "MUSIC/CHMODE.WAV")

    def update(self, dt):
        if self.game:
            self.game.update(dt)
            if self.game.hint_done:
                self.game.hint_done = False
                self.app.player.hints -= 1
                self.app.save_player()
                self.app.sounds.play("USEHINT")
            if self.game.solved:
                self.done_for = (self.done_for or 0.0) + dt
                if self.done_for >= self.SOLVED_PAUSE:
                    self.app.puzzle_solved(self, used_free=self.used_free)
                return
        if not self.paused and not self.app.dialogs:
            self.elapsed += dt

    def draw_back(self, surf):
        if self.game:
            self.game.draw(surf)
        elif self.picture:
            surf.blit(self.picture, self.picture.get_rect(center=self.AREA.center))

    def draw_front(self, surf):
        if self.app.settings.timer:
            secs = int(self.elapsed)
            if self.limit:
                secs = max(0, self.limit - secs)
            img = self.font.render(f"{secs // 60}:{secs % 60:02d}", True, TEXT)   # region 302
            surf.blit(img, img.get_rect(midleft=(704, 91)))
        if not self.game:
            msg = ("This puzzle type is not playable yet. Use a Free Puzzle token, "
                   "or press F9 to mark it solved.")
            box = pygame.Rect(0, 0, 520, 52)
            box.midbottom = (self.AREA.centerx, self.AREA.bottom - 8)
            pygame.draw.rect(surf, (30, 12, 4), box)
            pygame.draw.rect(surf, TEXT, box, 1)
            for i, line in enumerate(wrap(self.app.fonts.get(14), msg, box.w - 20)):
                img = self.app.fonts.get(14).render(line, True, TEXT)
                surf.blit(img, (box.x + 10, box.y + 6 + i * 18))
        if self.paused:
            shadow_text(surf, self.app.fonts.get(30), self.app.strings.get(303, "Pause"),
                        (self.AREA.centerx, self.AREA.centery - 20), centre=True)

    # game input
    def busy(self):
        return self.paused or (self.game and self.game.solved)

    def mouse_move(self, pos):
        if self.game and not self.busy():
            self.game.mouse_move(pos)
        return False

    def mouse_down(self, pos):
        return bool(self.game and not self.busy() and self.game.mouse_down(pos))

    def mouse_up(self, pos):
        return bool(self.game and not self.busy() and self.game.mouse_up(pos))

    def command(self, cid, button):
        app = self.app
        if cid == 52:
            app.leave_puzzle(self)
        elif cid == 303:
            self.paused = button.on
            if self.game:
                self.game.paused = self.paused
            app.sounds.play("PAUSE")
        elif cid == 304:
            app.confirm(app.strings.get(1030, ""), self.restart)
        elif cid == 306:
            free = app.player.free
            if self.busy():
                app.sounds.play(app.sounds.NO_CLICK)
            elif self.master:                          # 0x436430 in mode 4: three tokens
                if free >= MASTER_FREE_COST:
                    app.confirm(app.strings.get(1041, ""), self.use_free)
                else:
                    app.message(app.strings.get(1042, ""))
            elif free > 0:
                app.confirm(app.strings.get(1001, ""), self.use_free)
            else:
                app.message(NO_TOKENS)                 # modern: the original only clicks "no"
        elif cid == 307:
            button.on = False
            if self.game and self.game.hint_mode:          # pressed again: cancel
                self.game.hint_mode = False
            elif self.game and app.player.hints > 0 and not self.busy():
                app.confirm(app.strings.get(1002, ""), self.game.use_hint)
            elif self.game and not self.busy():
                app.message(NO_HINTS)                  # modern: the original only clicks "no"
            else:
                app.sounds.play(app.sounds.NO_CLICK)
        else:
            return False
        return True

    def use_free(self):
        self.used_free = True
        if self.game:
            self.game.complete()
        else:
            self.app.puzzle_solved(self, used_free=True)

    def restart(self):
        self.elapsed = 0.0
        if self.game:
            self.game.restart()
        self.app.sounds.play("RESTART")

    def right_click(self, pos):
        if self.game and not self.busy():
            self.game.right_click(pos)

    def wheel(self, dy):
        if self.game and not self.busy():
            self.game.wheel(dy)

    def key(self, ev):
        if self.game and not self.busy() and self.game.key(ev):
            return True
        if ev.key == pygame.K_F9 and not (self.game and self.game.solved):
            if self.game:
                self.game.complete()
            else:
                self.app.puzzle_solved(self)
            return True
        return False


# ------------------------------------------------------------ success dialog
class SuccessScene(Scene):
    """Screen 130 (SUCCESSDLG): Congratulations, the time and the picture's credits
    (PUZENU '%nTitle %aArtist %tTime %rRights')."""

    def __init__(self, app, view, puzzle, elapsed):
        super().__init__(app, view)
        credits = app.puzzle_credits(puzzle)
        secs = int(elapsed)
        values = {133: f"{secs // 60}:{secs % 60:02d}", 134: credits.get("n", ""),
                  135: credits.get("a", ""), 136: credits.get("r", "")}
        for cid, text in values.items():
            if cid in view.by_id:
                view[cid].set_text(text)


def success_view(ui):
    controls = [ui.layout.controls[c] for c in (130, 131, 132, 133, 134, 135, 136)]
    return widgets.ScreenView(ui, 130, controls=controls)


# --------------------------------------------------------------- message box
# Not in the original (it only plays the "no" click); the wording follows its quick help.
NO_TOKENS = ("You have no Free Puzzle tokens yet.\n"
             "Earn one for every 10 puzzles you solve; more are hidden behind random puzzles. "
             "Then click Free to solve a puzzle automatically.")
NO_HINTS = ("You have no Hints yet.\n"
            "Hints are hidden behind random puzzles. Keep solving puzzles to find them, "
            "then click Hint to place a piece automatically.")


class MessageScene(Scene):
    """Message boxes are built in code on 900.RIM with buttons 1200-1208."""
    TEXT_AREA = pygame.Rect(36, 96, 410, 290)

    def __init__(self, app, view, text):
        super().__init__(app, view)
        self.lines = wrap(app.fonts.get(20), text, self.TEXT_AREA.w)

    def draw_front(self, surf):
        font = self.app.fonts.get(20)
        area = self.TEXT_AREA.move(self.view.origin)
        y = area.y + max(0, (area.h - len(self.lines) * 26) // 2)
        for line in self.lines:
            shadow_text(surf, font, line, (area.centerx, y), centre=True)
            y += 26


class HelpScene(MessageScene):
    """Quick help: a topic of HELP/PANDORA.M20 (data.m20) in the message box.
    The title is centred, headings (short lines without a full stop) are bold,
    bullets hang; the font shrinks until the topic fits."""
    TEXT_AREA = pygame.Rect(30, 92, 422, 312)

    def __init__(self, app, view, paragraphs):
        Scene.__init__(self, app, view)
        self.paragraphs = paragraphs
        for size in (17, 16, 15, 14, 13, 12):
            self.size = size
            self.layout = self.lay_out(size)
            if self.layout and self.layout[-1][2] + self.line_h(size) <= self.TEXT_AREA.h:
                break

    @staticmethod
    def line_h(size):
        return size + 3

    def lay_out(self, size):
        """(text, font, y, x, centre) lines inside TEXT_AREA."""
        width, lh = self.TEXT_AREA.w, self.line_h(size)
        out, y = [], 0
        for k, para in enumerate(self.paragraphs):
            if k == 0:
                font = self.app.fonts.get(size + 3, bold=True)
                for line in wrap(font, para, width):
                    out.append((line, font, y, 0, True))
                    y += lh + 3
                y += 4
                continue
            bullet = para.startswith("\u2022 ")
            heading = not bullet and len(para) < 40 and not para.endswith((".", ":"))
            font = self.app.fonts.get(size, bold=heading)
            if heading and k > 1:
                y += lh // 3
            indent = font.size("\u2022 ")[0] if bullet else 0
            text = para[2:] if bullet else para
            for i, line in enumerate(wrap(font, text, width - indent)):
                if bullet and i == 0:
                    out.append(("\u2022", font, y, 0, False))
                out.append((line, font, y, indent, False))
                y += lh
        return out

    def draw_front(self, surf):
        area = self.TEXT_AREA.move(self.view.origin)
        total = (self.layout[-1][2] + self.line_h(self.size)) if self.layout else 0
        top = area.y + max(0, (area.h - total) // 2)
        for text, font, y, x, centre in self.layout:
            if centre:
                shadow_text(surf, font, text, (area.centerx, top + y), centre=True)
            else:
                shadow_text(surf, font, text, (area.x + x, top + y))


def message_view(ui, buttons):
    """buttons: control ids such as 1200 OK, 1201 Yes, 1202 No, 1204 Map, 1205 Stay, 1206 Capture."""
    controls = []
    n = len(buttons)
    for i, cid in enumerate(buttons):
        c = ui.layout.controls[cid]
        x = int((482 - n * 147) / (n + 1) * (i + 1) + 147 * i)
        controls.append(dataclasses.replace(c, rect=(x, 468 - 31 - 30, 0, 0)))
    return widgets.ScreenView(ui, 900, background="900.bmp", controls=controls)


# ----------------------------------------------------------------- gallery
GALLERY_TYPES = {650: "Image Hole", 651: "Focus Point", 652: "Rotascope", 653: "Overlap",
                 654: "Outer Layer", 656: "Jesse's Strips", 658: "Slices", 659: "Lens Bender",
                 660: "Interlock", 661: "Find and Fill"}


def clock(seconds):
    s = int(round(seconds))
    return f"{s // 60}:{s % 60:02d}"


class GalleryScene(Scene):
    """Screen 600, the gallery of best times (gallery.rtf): pick a type; the list (601)
    shows each puzzle of it you have solved with your best time, beside the best time
    ever on this computer or another player's (the arrow, 606, switches; labels 607 and
    608 name the two columns). **Interpretation:** the row layout and that a puzzle is
    listed once either side has a time for it."""
    ROW = 20

    def __init__(self, app, view):
        super().__init__(app, view)
        self.kind = "Image Hole"
        self.compare = 0
        self.scroll = 0
        self.font = app.fonts.get(15)

    def enter(self):
        self.view.select_radio(650)
        self.kind = "Image Hole"
        self.refresh()

    def targets(self):
        """What the right column compares with: the best ever, then the other players."""
        me = self.app.player.name if self.app.player else ""
        return [None] + [n for n in self.app.settings.players if n != me]

    def refresh(self):
        from ..game import besttimes
        from ..game.progress import Player
        p = self.app.player
        mine = p.best if p else {}
        target = self.targets()[self.compare % len(self.targets())]
        if target is None:
            theirs = {k: v for k, v in besttimes.load().items()}
            right = self.app.status.get(611, "Best Times")
        else:
            other = Player.load(target)
            theirs = {k: (v, target) for k, v in other.best.items()}
            right = target
        rows = []
        for lv in self.app.levels.values():
            for city in lv.cities.values():
                for pz in city.puzzles.values():
                    if pz.kind_name == self.kind and (pz.path in mine or pz.path in theirs):
                        name = self.app.names.get(pz.name_id, f"{city.name.title()} {pz.number}")
                        rows.append((name, mine.get(pz.path), theirs.get(pz.path)))
            for pz in lv.puzzles.values():
                if pz.kind_name == self.kind and (pz.path in mine or pz.path in theirs):
                    rows.append((self.app.names.get(pz.name_id, pz.path), mine.get(pz.path), theirs.get(pz.path)))
        self.rows = sorted(rows, key=lambda r: r[0].lower())
        self.scroll = 0
        for cid, text in ((607, p.name if p else ""), (608, right)):
            if cid in self.view.by_id:
                self.view[cid].set_text(text)

    def command(self, cid, button):
        if cid == 650:
            self.kind = GALLERY_TYPES.get(button.id, self.kind)
            self.refresh()
            return True
        if cid == 605:
            self.compare = (self.compare + 1) % len(self.targets())
            self.refresh()
            return True
        return False

    def wheel(self, dy):
        area = self.view[601].inner
        most = max(0, len(self.rows) - area.h // self.ROW)
        self.scroll = max(0, min(most, self.scroll - dy))

    def draw_front(self, surf):
        area = self.view[601].inner.inflate(-8, -6)
        clip = surf.get_clip()
        surf.set_clip(area)
        if not self.rows:
            msg = "Solve a puzzle of this type to see your time here."
            surf.blit(self.font.render(msg, True, (248, 176, 100)), (area.x + 4, area.y + 4))
        for i, (name, mine, theirs) in enumerate(self.rows[self.scroll:]):
            y = area.y + 2 + i * self.ROW
            if y > area.bottom:
                break
            surf.blit(self.font.render(name, True, (236, 220, 190)), (area.x + 4, y))
            right = area.right - 4
            if theirs:
                text = clock(theirs[0]) + (f"  {theirs[1]}" if self.compare == 0 else "")
                img = self.font.render(text, True, (255, 110, 60))
                surf.blit(img, (right - img.get_width(), y))
            if mine is not None:
                img = self.font.render(clock(mine), True, (255, 170, 80))
                surf.blit(img, (area.x + area.w * 0.62 - img.get_width(), y))
        surf.set_clip(clip)


# ---------------------------------------------------------------- challenge
class ChallengeScene(Scene):
    """The box with the level's five pieces; with all five, the centre starts
    the trickster's Challenge (the level's own puzzles)."""
    BOX = pygame.Rect(142, 25, 516, 381)

    def __init__(self, app, view, level):
        super().__init__(app, view)
        self.level = level
        n = level.number
        self.box = self.img(f"{1799 + n}.bmp")
        self.trickster = self.img(f"{1720 + n}.bmp")
        self.icons = []
        for k in range(1, 6):
            self.icons.append((self.img(f"15{n}{k}.bmp"), self.img(f"15{n}{k}d.bmp")))
        self.ready = len(app.player.level_pieces(level.path)) >= 5
        label = app.strings.get(1850 + n, "") if self.ready else app.status.get(1700 + 10 * n, "")
        for cid in (1851, 1852):
            if cid in view.by_id:
                view[cid].set_text(label)

    def enter(self):
        self.app.music.play_loop("MUSIC/CHMODE.WAV" if self.ready else "MUSIC/MAP.WAV")

    def draw_back(self, surf):
        if self.box:
            surf.blit(self.box, self.BOX)
        if self.trickster:
            surf.blit(self.trickster, (658, 43))
        # 15<level><k>D is a found piece; the plain image is its highlighted look.
        found = self.app.found_slots(self.level)
        mouse = self.app.mouse_pos()
        for k, (lit, normal) in enumerate(self.icons):
            if k not in found:
                continue
            rect = pygame.Rect(24, 80 + 63 * k, 89, 63)
            img = lit if rect.collidepoint(mouse) else normal
            if img:
                surf.blit(img, rect)

    def mouse_up(self, pos):
        if self.ready and self.BOX.inflate(-200, -120).collidepoint(pos):
            self.app.start_master(self.level)
            return True
        return False

    def command(self, cid, button):
        if cid == 52:
            self.app.back()
            return True
        return False


def challenge_view(ui):
    keep = [ui.layout.controls[c] for c in (54, 52, 50, 1852, 1851)]
    return widgets.ScreenView(ui, 1800, background="500.bmp", controls=keep)


# ------------------------------------------------------------------ captured
class CapturedScene(Scene):
    """The captured trickster (1701 + level - 1), C_<name>.WAV, 'You captured X.'"""

    def __init__(self, app, level, then):
        super().__init__(app, widgets.ScreenView(app.ui, 1700, controls=[]))
        self.image = self.img(f"{1700 + level.number}.bmp", key=False)
        self.text = app.status.get(439 + level.number, "")
        self.then = then
        self.trickster = world.TRICKSTERS[level.number - 1]

    def enter(self):
        self.app.music.play_loop("MUSIC/LEVEND.WAV")
        self.app.music.play_once(f"MUSIC/C_{self.trickster.upper()}.WAV")

    def draw_back(self, surf):
        if self.image:
            surf.blit(self.image, (0, 0))
        shadow_text(surf, self.app.fonts.get(30), self.text, (400, 540), centre=True)

    def mouse_up(self, pos):
        then, self.then = self.then, None
        if then:
            then()
        return True

    def key(self, ev):
        return self.mouse_up(None)


def parse_credits(text):
    """'%nTitle: X %aArtist: Y %tTime: %c %rRights' -> {'n': 'X', 'a': 'Y', 'r': ...}"""
    out = {}
    for code, value in re.findall(r"%([natr])([^%]*)", text):
        value = value.strip()
        value = re.sub(r"^(Title|Artist|Time):\s*", "", value)
        out[code] = value
    return out
