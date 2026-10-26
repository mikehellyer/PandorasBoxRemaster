"""Outer Layer puzzles (3DSKIN.SKI, C3DSkinObject).

3DSKIN.SKI is an INI file:
    [3DSkin]            ObjectCount, SegmentCount, InitialCamera (1-4), EnableRotation, ...
    [3DSkinSegmentN]    MinX/MinY/MaxX/MaxY: a rectangle of the texture (where pieces go)
    [3DSkinSpriteN]     HasMask, InitialXpos/Ypos/Angle, InitialTray (-1 = on the object,
                        0-3 = a stack on the left), InitialTrayOrder, InitialSegment,
                        FinalXpos/Ypos (top-left in the texture), FinalAngle (always 0)
3DSKIN_BACK.PNG is the bare texture (its size is the texture's), 3DSKIN_SPRn.PNG the
pieces. Each CAMERA<k>/ holds a 540x540 view: BACK.JPG (the scene with the object
blank), MULT.PNG (shading) and ADD.PNG (highlights), WARPER.MAP (defT) = two planes
of i16 [540][540], u then v, each stored as differences along the row: summed, a
pixel showing the object has u = 16384 + texture x and v = texture y (anything else
shows BACK). WARPER.DAT is a 62-byte header (u16 1, u16, u32 540, u32 540, bounds).
"""
from __future__ import annotations

import configparser
from dataclasses import dataclass

import numpy as np

from . import deft

ON_OBJECT = -1
TRAYS = 4


@dataclass
class SkiSprite:
    index: int                  # 1-based, as in 3DSKIN_SPR<n>.PNG
    start: tuple[int, int]
    start_angle: int
    tray: int
    tray_order: int
    final: tuple[int, int]
    final_angle: int


@dataclass
class SkiPuzzle:
    sprites: list[SkiSprite]
    segments: list[tuple[int, int, int, int]]
    camera: int                 # 0-based first view
    rotation: bool


def parse(data: bytes) -> SkiPuzzle:
    cp = configparser.ConfigParser(strict=False, interpolation=None)
    cp.optionxform = str
    cp.read_string(data.decode("latin-1"))
    main = cp["3DSkin"]
    segments = [tuple(int(cp[f"3DSkinSegment{k}"][x]) for x in ("MinX", "MinY", "MaxX", "MaxY"))
                for k in range(1, int(main["SegmentCount"]) + 1)]
    sprites = []
    for n in range(1, int(main["ObjectCount"]) + 1):
        s = cp[f"3DSkinSprite{n}"]
        sprites.append(SkiSprite(
            n, (int(s["InitialXpos"]), int(s["InitialYpos"])), int(float(s["InitialAngle"])) % 360,
            int(s["InitialTray"]), int(s["InitialTrayOrder"]),
            (int(s["FinalXpos"]), int(s["FinalYpos"])), int(float(s["FinalAngle"])) % 360))
    return SkiPuzzle(sprites, segments, max(0, int(main.get("InitialCamera", "1")) - 1),
                     main.get("EnableRotation", "1") != "0")


def warp(data: bytes):
    """WARPER.MAP -> (inside (540, 540) bool, x, y int arrays into the texture)."""
    raw = np.frombuffer(deft.inflate(data), "<i2").reshape(2, 540, 540).astype(np.int32)
    u = np.cumsum(raw[0], axis=1)
    v = np.cumsum(raw[1], axis=1)
    inside = (u >> 14) == 1
    return inside, np.where(inside, u - 16384, 0), np.where(inside, v, 0)
