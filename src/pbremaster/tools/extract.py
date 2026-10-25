"""pb-extract: unpack the original Pandora's Box data for study.

Writes everything under OUT (default ./extracted), which is git-ignored:
    PANDORA/..., SCREENS/...   every archive member, original names
    *.RIM.png                  decoded raw images next to the .RIM
    *.inflated                 decompressed payload of other defT files
    strings/<DLL>.json         string tables of the language DLLs
    catalogue.json             levels, cities and puzzles with their rewards
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..data import catalogue, deft, gamedir
from ..data.rof import ROF
from ..data.strings import load_strings

STRING_DLLS = ("LANGENU.DLL", "PUZENU.DLL", "NAMEENU.DLL", "STATENU.DLL")


def extract_rof(rof: ROF, out: Path, decode=True):
    from PIL import Image

    for name in rof.files:
        data = rof.read(name)
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        if not decode or not deft.is_deft(data) and not name.endswith(".RIM"):
            continue
        if name.endswith(".RIM"):
            Image.fromarray(deft.decode_rim(data)).save(dest.with_name(dest.name + ".png"))
        else:
            dest.with_name(dest.name + ".inflated").write_bytes(deft.inflate(data))


def catalogue_json(levels):
    def puzzle(p):
        return {"number": p.number, "kind": p.kind_name, "path": p.path, "piece": p.piece,
                "hint": p.hint, "wildcard": p.wildcard, "time_limit": p.time_limit}
    return [{"level": l.number, "trickster": l.trickster,
             "puzzles": [puzzle(p) for _, p in sorted(l.puzzles.items())],
             "cities": [{"id": c.id, "name": c.name, "path": c.path,
                         "puzzles": [puzzle(p) for _, p in sorted(c.puzzles.items())]}
                        for c in sorted(l.cities.values(), key=lambda c: c.id)]}
            for l in levels.values()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", help="folder with the original game (or its DATA folder)")
    ap.add_argument("--out", default="extracted")
    ap.add_argument("--no-decode", action="store_true", help="only copy archive members")
    args = ap.parse_args(argv)

    game = gamedir.find(args.data)
    out = Path(args.out)
    for arc in ("PANDORA.ROF", "SCREENS.ROF"):
        print(f"extracting {arc} ...")
        rof = ROF(game.file(arc))
        extract_rof(rof, out / arc.split(".")[0], decode=not args.no_decode)
        print(f"  {len(rof.files)} files")

    (out / "strings").mkdir(parents=True, exist_ok=True)
    for dll in STRING_DLLS:
        table = load_strings(game.file(dll))
        (out / "strings" / f"{dll.split('.')[0]}.json").write_text(
            json.dumps(table, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"strings {dll}: {len(table)}")

    rtr = game.file("TRICKS.RTR").read_bytes()
    (out / "TRICKS.RTR.inflated").write_bytes(deft.inflate(rtr))

    levels = catalogue.load(ROF(game.file("PANDORA.ROF")))
    (out / "catalogue.json").write_text(json.dumps(catalogue_json(levels), indent=1), encoding="utf-8")
    print(f"catalogue: {sum(len(c.puzzles) for l in levels.values() for c in l.cities.values())} city puzzles")


if __name__ == "__main__":
    main()
