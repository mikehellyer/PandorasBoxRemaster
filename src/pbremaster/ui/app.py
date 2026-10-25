"""pbremaster: the game window.

Milestone 0 only proves the pipeline: the splash screen, then the main menu
backdrop, drawn from the original files at the original 800x600 and scaled
to the window.  Esc quits, F11 toggles full screen, any key/click skips the splash.
"""
from __future__ import annotations

import argparse
import sys

import pygame

from .. import __version__
from ..data import gamedir
from ..data.assets import Assets
from ..data.strings import load_strings

WIDTH, HEIGHT = 800, 600


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pbremaster")
    ap.add_argument("--data", help="folder with the original Pandora's Box files")
    ap.add_argument("--screenshot", help="render the main menu to this PNG and exit")
    args = ap.parse_args(argv)

    try:
        game = gamedir.find(args.data)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1

    pygame.init()
    strings = load_strings(game.file("LANGENU.DLL"))
    pygame.display.set_caption(f"{strings.get(56, 'Pandora' + chr(39) + 's Box')} Remaster {__version__}")
    window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    canvas = pygame.Surface((WIDTH, HEIGHT))
    assets = Assets(game)

    splash = assets.loose_image("SPLASH.PNG")
    menu = assets.image("SCREENS/100.RIM")

    if args.screenshot:
        canvas.blit(menu, (0, 0))
        pygame.image.save(canvas, args.screenshot)
        return 0

    clock = pygame.time.Clock()
    scene, scene_time = "splash", 0
    fullscreen = False
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                pygame.quit()
                return 0
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_F11:
                fullscreen = not fullscreen
                window = pygame.display.set_mode((0, 0) if fullscreen else (WIDTH, HEIGHT),
                                                 pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE)
            elif ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN) and scene == "splash":
                scene = "menu"

        scene_time += clock.tick(60)
        if scene == "splash" and scene_time > 4000:
            scene = "menu"

        canvas.fill((0, 0, 0))
        if scene == "splash":
            canvas.blit(splash, splash.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        else:
            canvas.blit(menu, (0, 0))
        present(window, canvas)


def present(window, canvas):
    """Scale the 800x600 canvas into the window, keeping the aspect ratio."""
    ww, wh = window.get_size()
    scale = min(ww / WIDTH, wh / HEIGHT)
    size = (int(WIDTH * scale), int(HEIGHT * scale))
    window.fill((0, 0, 0))
    window.blit(pygame.transform.smoothscale(canvas, size),
                ((ww - size[0]) // 2, (wh - size[1]) // 2))
    pygame.display.flip()


if __name__ == "__main__":
    sys.exit(main())
