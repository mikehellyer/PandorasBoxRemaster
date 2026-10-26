# Plan

Same approach as UltimaOneRemaster: the engine reads the original files at runtime and never ships them;
game rules come from disassembling the unprotected `PANDORA.EUL`. Mike reviews each step before the next.

1. **Formats** ✅ (first pass): `notes/file-formats.md`.
2. **Extraction** ✅: `pb-extract` unpacks both archives, decodes RIM images, string tables, campaign catalogue.
3. **Engine** (pygame-ce, 800x600 canvas scaled to the window):
   - M0 ✅ window, splash, main menu backdrop from the original files.
   - M1 ✅ SCREEN.DAT layouts: every screen drawn, buttons with hover/press/toggle/radio states, captions,
     sounds, Book Antiqua text, the game cursor, Menu pop-up, Options (saved to settings.json), player
     names, Puzzles Only type picker + picture list, Credits/About text. Still to do on the menus: the
     Load/Save dialogs (need save games), quick help (the RTFs are not on the CD), and the PLAY flow.
   - M3a ✅ (ahead of M2) campaign shell: story movies (PyAV), world map with markers, cities with
     picture/trickster/tiles/counters, rewards (tokens, hints, pieces), piece-found and city-done
     messages, Challenge box, capture and next level, Credits/About on their real frames, music per
     PANDORA.MGD, saves per player (JSON). Puzzles show their picture and can be finished with a Free
     Puzzle token or F9 until each type is written. Since done: Load/Save, Gallery, Puzzles Only play
     (Scalawag is bonus puzzles, not a level), tutorial instructions, speed-puzzle bonuses, Story book, trickster portraits on the map: everything from the
     original is now in (some details interpreted, see game-logic.md).
   - M2 puzzle types: Focus Point ✅ (71), Rotascope ✅ (55), Image Hole ✅ (42), Jesse's Strips ✅ (43), Overlap ✅ (63), Interlock ✅ (12), Find and Fill ✅ (45), Slices ✅ (29), Lens Bender ✅ (22), Outer Layer ✅ (29): all ten types playable
   - M2 (was) one puzzle type end to end (Slices or Lens Bender: the most data is already readable), then the other nine.
   - M3 the world map, cities, rewards (piece / hint / wildcard / timed), tricksters, save games, best times.
   - M4 videos (intro + story AVIs via PyAV), music, gallery, puzzles-only mode, tutorial.
4. **Modern improvements**: sharp scaling, GPU window and Options > Display ✅; no-Hints / no-tokens
   messages ✅. Next ideas: keep half-finished puzzles, undo, keyboard shortcuts, high-resolution text,
   a widescreen frame.
5. **Builds** 🟡: Linux and Windows only. Done locally: first-run setup screen (`ui/setup.py`: detect CD /
   install / Wine / copied data, browse via zenity/kdialog/Tk, check, optional copy to the data folder,
   saved as `Settings.game_dir`, Options > Game files), update check (`update.py`, notice on the main
   menu), own icon, PyInstaller spec, `.deb`, AppImage and Inno Setup scripts, GitHub workflows. The
   Linux onedir build and `.deb` are tested locally; the AppImage and Windows installer only build in
   CI. Waiting on: a GitHub repo (mikehellyer/PandorasBoxRemaster, as `update.py` expects).
