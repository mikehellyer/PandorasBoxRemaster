"""Step-by-step instructions in the Tutorial's practice puzzles (LEVEL.0).

The texts are the original's (LANGENU, one block per puzzle type, written for the
tutorial's own pictures: "Try the pharaoh's head"). The original shows them in a
text bubble (0x46fe90) and moves on from inside each puzzle's code; here a step
moves on when the puzzle reports the action it asks for. Puzzles report actions
through PuzzleGame.emit: every puzzle sound is an event (SL_SEL, BG_RIGHT, ...),
plus a few named ones where a type has no sound of its own (Outer Layer's
"view"/"place"/"stack"/"rotate", Jesse's Strips' "move_tray").
**Interpretation:** which action ends each step, the panel at the bottom of the play
area with back/next arrows and a close button.
"""
from __future__ import annotations

import pygame

from .campaign import wrap

STEP = 0      # (text id, events that end it[, condition on the game])
MOVE_RO = ("RO_SPIN", "RO_SB", "RO_BS")
RINGS = ("RO_SB", "RO_BS")

STEPS = {
    "Image Hole": [(2053, ("IM_SEL",)), (2054, ("IM_MOVE",)), (2055, ("IM_RIGHT",)), (2056, ())],
    "Focus Point": [(3313, ("FP_MOVE",)), (3314, ("FP_MOVE",)), (3315, ("FP_MOVE",)), (3316, ())],
    "Rotascope": [(4308, MOVE_RO), (4309, RINGS), (4310, RINGS), (4311, ())],
    "Overlap": [(5414, ("OL_RIGHT",)), (5415, ("OL_RIGHT",)), (5416, ("OL_RIGHT",)),
                (5417, ("OL_RIGHT",)), (5418, ("OL_RIGHT", "OL_REORD")), (5419, ())],
    "Outer Layer": [(6208, ("view",)), (6209, ("place",)), (6210, ("place",)),
                    (6211, ("stack", "place")), (6212, ())],
    "Jesse's Strips": [(8007, ("JS_TAB",), lambda g: g.tray == 4), (8008, ("JS_RIGHT",)),
                       (8009, ("JS_TAB",), lambda g: g.tray == 3), (8010, ("JS_RIGHT",)),
                       (8011, ("JS_TAB",), lambda g: g.tray == 2), (8012, ("move_tray",)),
                       (8013, ("JS_RIGHT",)), (8014, ("JS_TAB",), lambda g: g.tray == 0), (8015, ())],
    "Slices": [(10900, ("SL_SEL",)), (10901, ("SL_MOVE", "SL_RIGHT")), (10902, ("SL_RIGHT",)),
               (10903, ("SL_ROTAT",)), (10904, ("SL_FLIP",)), (10905, ())],
    "Lens Bender": [(11950, ("BG_RIGHT",)), (11951, ("BG_RIGHT",)), (11952, ("BG_WRONG",)),
                    (11953, ("BG_RIGHT",)), (11954, ())],
    "Interlock": [(12900, ("TG_DROPI",)), (12901, ("TG_DROPI",)), (12902, ("TG_DROPI",)), (12903, ())],
    "Find and Fill": [(13126, ("FF_FILL",)), (13127, ("FF_ERASE",)), (13128, ("SUCCESS",)),
                      (13129, ("SUCCESS",)), (13130, ())],
}
# Shown for a moment when something goes wrong, then back to the current step.
ASIDES = {"Image Hole": {"IM_X": 2057}}

PANEL_BG, PANEL_EDGE, TEXT, DIM = (24, 10, 3, 225), (200, 130, 60), (236, 220, 190), (190, 150, 110)


class Tutorial:
    def __init__(self, app, kind, game, area: pygame.Rect):
        self.app, self.game, self.area = app, game, area
        self.steps = STEPS[kind]
        self.asides = ASIDES.get(kind, {})
        self.index = 0
        self.aside = None
        self.closed = False
        self.font = app.fonts.get(15)
        self.rects = {}
        game.on_event = self.event

    @property
    def text_id(self):
        return self.aside or self.steps[self.index][0]

    def event(self, name):
        if name in self.asides:
            self.aside = self.asides[name]
            return
        step = self.steps[self.index]
        if name in step[1] and (len(step) < 3 or step[2](self.game)):
            self.aside = None
            self.go(self.index + 1)

    def go(self, index):
        index = max(0, min(len(self.steps) - 1, index))
        if index != self.index:
            self.index = index
            self.aside = None
            self.closed = False

    # ------------------------------------------------------------- panel
    def visible(self):
        return not self.closed and not self.game.hint_mode and not self.game.solved and not self.game.paused

    def draw(self, surf):
        self.rects = {}
        if not self.visible():
            return
        text = self.app.strings.get(self.text_id, "")
        width = self.area.w - 80
        lines = [line for para in text.replace("\r\n", "\r").split("\r") for line in wrap(self.font, para, width)]
        h = 18 * len(lines) + 28
        panel = pygame.Rect(self.area.x + 10, self.area.bottom - h - 8, self.area.w - 20, h)
        bg = pygame.Surface(panel.size, pygame.SRCALPHA)
        bg.fill(PANEL_BG)
        surf.blit(bg, panel)
        pygame.draw.rect(surf, PANEL_EDGE, panel, 1, border_radius=6)
        for i, line in enumerate(lines):
            surf.blit(self.font.render(line, True, TEXT), (panel.x + 12, panel.y + 8 + 18 * i))
        small = self.app.fonts.get(13)
        count = small.render(f"Tip {self.index + 1} of {len(self.steps)}", True, DIM)
        surf.blit(count, (panel.x + 12, panel.bottom - 18))
        x = panel.right - 12
        for key, label in (("close", "x"), ("next", ">"), ("back", "<")):
            img = self.font.render(label, True, TEXT)
            r = pygame.Rect(0, 0, 22, 20)
            r.topright = (x, panel.y + 6)
            if key == "close" or (key == "next" and self.index < len(self.steps) - 1) or (key == "back" and self.index > 0):
                pygame.draw.rect(surf, PANEL_EDGE, r, 1, border_radius=4)
                surf.blit(img, img.get_rect(center=r.center))
                self.rects[key] = r
            x -= 26
        self.rects["panel"] = panel

    def click(self, pos) -> bool:
        """True if the click was on the panel (so the puzzle doesn't get it)."""
        if "panel" not in self.rects or not self.rects["panel"].collidepoint(pos):
            return False
        if self.rects.get("close", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            self.closed = True
        elif self.rects.get("next", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            self.go(self.index + 1)
        elif self.rects.get("back", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            self.go(self.index - 1)
        return True
