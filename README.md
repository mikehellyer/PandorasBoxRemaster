# Pandora's Box Remaster

A modern, cross-platform (Linux, Windows) remake of Microsoft Pandora's Box (1999) that runs on the
original game data. You need your own copy of the game; nothing from it is included here.

```bash
python3 -m venv venv && venv/bin/pip install -e ".[dev]"
venv/bin/pbremaster --data ~/Projects/Pandoras_Box_Original     # or set PANDORA_DIR
venv/bin/pb-extract --out extracted                               # unpack the data for study
venv/bin/pytest
```

- `src/pbremaster/data/`: readers for the original formats (ROF archives, defT/RIM images, string DLLs, campaign).
- `src/pbremaster/ui/`: the pygame-ce game.
- `tools/re/`: reverse-engineering helpers (`pe.py` disassembles PANDORA.EUL, `resources.py` dumps DLL resources).
- `notes/`: file formats and the plan.
