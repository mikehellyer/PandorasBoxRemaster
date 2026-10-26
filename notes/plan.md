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
   - M2 one puzzle type end to end (Slices or Lens Bender: the most data is already readable), then the other nine.
   - M3 the world map, cities, rewards (piece / hint / wildcard / timed), tricksters, save games, best times.
   - M4 videos (intro + story AVIs via PyAV), music, gallery, puzzles-only mode, tutorial.
4. **Modern improvements**: resolution scaling / HD filters, widescreen frame, QoL (undo, hint tweaks), etc.
5. **Builds**: Linux and Windows only (PyInstaller, as with the Simple-* apps).
