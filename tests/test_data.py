import struct
import zlib

import numpy as np

from pbremaster.data import catalogue, deft
from pbremaster.data.rof import ROF
from pbremaster.data.strings import load_strings


def test_deft_roundtrip():
    payload = struct.pack("<IIIi", 2, 2, 16, 4) + struct.pack("<4H", 0x7C00, 0x03E0, 0x001F, 0x7FFF)
    blob = b"defT" + struct.pack("<II", 80000, len(payload))
    comp = zlib.compress(payload)
    blob += struct.pack("<I", len(comp)) + comp
    rgb = deft.decode_rim(blob)
    assert rgb.shape == (2, 2, 3)
    assert rgb[0, 0].tolist() == [255, 0, 0]
    assert rgb[0, 1].tolist() == [0, 255, 0]
    assert rgb[1, 0].tolist() == [0, 0, 255]
    assert rgb[1, 1].tolist() == [255, 255, 255]


def test_rim_negative_stride_is_bottom_up():
    payload = struct.pack("<IIIi", 1, 2, 8, -4) + bytes([1, 0, 0, 0, 2, 0, 0, 0])
    assert deft.decode_rim(payload)[:, 0].tolist() == [2, 1]


def test_archives(game):
    pandora = ROF(game.file("PANDORA.ROF"))
    screens = ROF(game.file("SCREENS.ROF"))
    assert len(pandora.files) == 9538
    assert len(screens.files) == 729
    assert pandora.read("BGL/EASY.INI").startswith(b"[BumpyGlassLayout]")


def test_main_menu_image(game):
    img = deft.decode_rim(ROF(game.file("SCREENS.ROF")).read("SCREENS/100.RIM"))
    assert img.shape == (600, 800, 3) and img.dtype == np.uint8


def test_catalogue(game):
    levels = catalogue.load(ROF(game.file("PANDORA.ROF")))
    assert [l.trickster for l in levels.values()] == [
        None, "MAUI", "PUCK", "ERIS", "COYOTE", "MONKEY", "ANANSI", "RAVEN", "SCALAWAG"]
    for n in range(1, 8):
        assert len(levels[n].cities) == 5
        for city in levels[n].cities.values():
            assert len(city.puzzles) == 10
            assert sum(p.piece for p in city.puzzles.values()) == 1
    everything = [p for l in levels.values() for p in l.puzzles.values()] + [
        p for l in levels.values() for c in l.cities.values() for p in c.puzzles.values()]
    assert len(everything) == 411
    assert {p.kind_name for p in everything} == set(catalogue.DATA_KINDS.values())
    cairo = levels[1].cities["CITY.06.CAIRO"]
    assert cairo.puzzles[4].piece and cairo.puzzles[4].kind_name == "Overlap"


def test_strings(game):
    lang = load_strings(game.file("LANGENU.DLL"))
    assert lang[56] == "Pandora's Box"
    assert lang[150] == "IMAGE HOLE"
