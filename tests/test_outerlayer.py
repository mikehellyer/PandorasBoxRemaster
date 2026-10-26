import os

import numpy as np
import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture(scope="module")
def app(game, tmp_path_factory):
    os.environ["XDG_DATA_HOME"] = str(tmp_path_factory.mktemp("xdg"))
    from pbremaster.settings import Settings
    from pbremaster.ui.app import App

    pygame.init()
    a = App(game, Settings.load())
    a.open_window()
    yield a
    pygame.quit()


def outer_layers(app):
    return [p for lv in app.levels.values()
            for p in list(lv.puzzles.values()) + [q for c in lv.cities.values() for q in c.puzzles.values()]
            if p.kind_name == "Outer Layer"]


def screen_for(g, point):
    """A camera and screen position showing this texture point (closest match)."""
    from pbremaster.puzzles.outerlayer import VIEW
    best = None
    for c, (inside, x, y, *_) in enumerate(g.cameras):
        d = np.where(inside, np.abs(x - point[0]) + np.abs(y - point[1]), 1 << 30)
        k = int(d.argmin())
        if best is None or d.flat[k] < best[0]:
            best = (int(d.flat[k]), c, (VIEW.x + k % 540, VIEW.y + k // 540))
    return best


def visible_spot(g, piece):
    """A camera, screen position and grab point that lay the piece in its place."""
    from pbremaster.puzzles.outerlayer import VIEW
    w, h = piece.image.get_size()
    fx, fy = piece.sprite.final
    best = (None, None, None, 1 << 30)
    for c, (inside, x, y, *_) in enumerate(g.cameras):
        on = inside & (x >= fx + 2) & (x < fx + w - 2) & (y >= fy + 2) & (y < fy + h - 2)
        if not on.any():
            continue
        d = np.where(on, np.abs(x - fx - w // 2) + np.abs(y - fy - h // 2), 1 << 30)
        k = int(d.argmin())
        if d.flat[k] < best[3]:
            vy, vx = divmod(k, 540)
            best = (c, (VIEW.x + vx, VIEW.y + vy), (int(x[vy, vx]) - fx, int(y[vy, vx]) - fy), d.flat[k])
    return best[:3]


def test_every_puzzle_solvable_by_dragging(app):
    from pbremaster.puzzles.outerlayer import THUMB, OuterLayer

    puzzles = outer_layers(app)
    assert len(puzzles) == 29
    for p in puzzles:
        g = OuterLayer(app, p)
        g.draw(app.canvas)
        assert not g.solved
        for piece in [q for q in g.pieces if not q.placed]:
            w, h = piece.image.get_size()
            fx, fy = piece.sprite.final
            cam, pos, grab = visible_spot(g, piece)
            assert cam is not None, (p.files[0], piece.sprite.index)
            g.camera = cam
            g.take(piece)
            g.stacks[0].insert(0, piece)
            piece.angle = piece.sprite.final_angle
            r = pygame.Rect(0, 0, THUMB, THUMB)
            r.center = g.tray_box(0).center
            hold = (r.x + (grab[0] * THUMB + w - 1) // w, r.y + (grab[1] * THUMB + h - 1) // h)
            assert g.mouse_down(hold)
            g.mouse_move(pos)
            g.mouse_up(pos)
            assert piece.placed, (p.files[0], piece.sprite.index)
        assert g.solved
        g.draw(app.canvas)


def tutorial(app):
    from pbremaster.puzzles.outerlayer import OuterLayer
    return OuterLayer(app, next(p for p in outer_layers(app) if p.files[0].startswith("LEVEL.0/")))


def test_wrong_angle_does_not_stick(app):
    g = tutorial(app)
    piece = g.stacks[0][0]
    piece.angle = 90
    w, h = piece.image.get_size()
    _, cam, pos = screen_for(g, (piece.sprite.final[0] + w // 2, piece.sprite.final[1] + h // 2))
    g.camera = cam
    g.mouse_down(g.tray_box(0).center)
    g.mouse_up(pos)
    assert piece.pos is not None and not piece.placed
    g.right_click(pos)                          # still selected: turn it upright in place
    g.right_click(pos)
    g.right_click(pos)
    assert piece.angle == 0


def test_cameras_hint_complete(app):
    g = tutorial(app)
    start = g.camera
    g.toggled(g.go_right)
    assert g.camera == (start + 1) % 4
    assert g.use_hint()
    g.mouse_down(g.tray_box(0).center)
    assert g.hint_done and any(p.placed and p.sprite.tray >= 0 for p in g.pieces)
    g.complete()
    assert g.solved
