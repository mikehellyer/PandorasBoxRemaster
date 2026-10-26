# Pandora's Box Remaster

A modern, cross-platform (Linux, Windows) remake of Microsoft Pandora's Box (1999) that runs on the
original game data. You need your own copy of the game; nothing from it is included here.

## Playing

Install the Windows setup `.exe`, the Linux `.deb` (Pop!_OS, Ubuntu, Debian) or the AppImage
(other distributions) from the GitHub Releases page.

On first start the game asks for your copy of Pandora's Box. Insert the CD (it is found
automatically) or click **Browse...** and choose the CD, its `DATA` folder, or the folder the
original was installed to. Tick **Copy the game files to this computer first** (about 520 MB) if
you'd rather not keep the CD in the drive. The choice is remembered; change it later under
**Options > Game files**.

Extras the original didn't have: a puzzle you leave half-finished is still as you left it next
time, Ctrl+Z / Ctrl+Y undo and redo moves (not in Image Hole), and R, F and H
press Rotate, Flip and Hint. Text is redrawn at your screen's resolution, so it stays sharp
when the game is scaled up, and a widescreen window gets wooden side panels instead of black bars.

The main menu tells you when a newer version is out; nothing is downloaded until you click Update.

## Developing

```bash
python3 -m venv venv && venv/bin/pip install -e ".[dev]"
venv/bin/pbremaster                                               # asks for the game files the first time
venv/bin/pbremaster --data ~/Projects/Pandoras_Box_Original     # or set PANDORA_DIR
venv/bin/pb-extract --out extracted                               # unpack the data for study
venv/bin/pytest                                                   # tests needing the game files skip without them
```

- `src/pbremaster/data/`: readers for the original formats (ROF archives, defT/RIM images, string DLLs,
  campaign, puzzle files) and `gamedir.py` (finding, checking and copying the player's files).
- `src/pbremaster/ui/`: the pygame-ce game; `setup.py` is the first-run screen.
- `src/pbremaster/update.py`: the GitHub Releases update check.
- `tools/re/`: reverse-engineering helpers (`pe.py` disassembles PANDORA.EUL, `resources.py` dumps DLL resources).
- `notes/`: file formats, game logic and the plan.

## Building

Tagging `vX.Y.Z` (matching `__version__`) runs `.github/workflows/release.yml`: PyInstaller with
Python 3.13 on Windows and Ubuntu 22.04, then Inno Setup (`packaging/windows/installer.iss`),
`packaging/linux/build-deb.sh` and `packaging/linux/build-appimage.sh`, and a GitHub Release with
the installers. Locally on Linux:

```bash
venv/bin/pip install pyinstaller
venv/bin/pyinstaller --noconfirm packaging/pyinstaller/pbremaster.spec
bash packaging/linux/build-deb.sh
```

The app icon is our own (`packaging/icons/generate_icon.py`), not the original's art.

## Disclaimer

This is an unofficial fan project, not affiliated with or endorsed by Microsoft. Microsoft and
Pandora's Box are trademarks of Microsoft Corporation. No part of the original game is included or
distributed: you need your own copy to play. The game's copy protection is not bypassed: the
remaster reads the unprotected data files and never uses the protected program.
