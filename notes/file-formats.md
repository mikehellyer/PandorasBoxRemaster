# Pandora's Box: file formats

Source: Microsoft Pandora's Box (Alexey Pajitnov, 1999; this CD is v1.00.02, Sept 2000),
in `~/Projects/Pandoras_Box_Original`. **Those files are never modified, committed or shipped.**
Everything here was worked out from the data, plus disassembly of `DATA/PANDORA.EUL`.

Status: ✅ decoded and implemented · 🟡 partly understood · ❓ not yet looked at

## The executables

| File | What it is |
|---|---|
| `DATA/PANDORA.EXE` | The installed game. Encrypted by **SafeDisc** (`DRVMGT.DLL`, `CLCD16/32.DLL`, `00000001.LT1`, `02938F06.BIN`). We do **not** touch or decrypt it. |
| `DATA/PANDORA.EUL` | An **unprotected** PE32 build of Pandora.exe (Feb 2000, "Version: 1.00.02.0100"). It keeps MSVC RTTI class names (`CPuzzleScreen`, `CROFDirectory`, ...). This is our reference for game logic. Use `tools/re/pe.py` on it. |
| `DATA/DPLAYERX.DLL` | DirectPlay helper (multiplayer is not planned). |
| `SETUP.EXE`, `SETUPENU.DLL`, `EBUEULA.DLL`, `DIRECTX/`, `GOODIES/` | The installer, DirectX 7a and extras. Not needed. |

Imports of PANDORA.EUL: DDRAW (DirectDraw 7), WINMM + MSACM32 (wave audio), GDI/USER, ole32 (AVI playback).
It also links an IJG JPEG decoder and a PNG decoder.

## ✅ .ROF archives: `PANDORA.ROF` (231 MB, 9538 files) and `SCREENS.ROF` (70 MB, 729 files)

A tree of directory blocks, little-endian. Implemented in `src/pbremaster/data/rof.py`.

```
dir block:  u32 count, u32 names_size
            count x { u32 offset, u32 size, u32 kind, u32 name_len, u32 name_off }
            names (NUL-terminated, name_off relative to the start of this table)
kind 1 = sub-directory (offset -> its dir block, size 0); kind 0 = file (offset/size of data)
```
The root of PANDORA.ROF holds `3DSKIN BGL FNF FPN IMG JES OVER RTT SLICE TRIGRAMS` (shared puzzle art
and sounds per type) and `LEVEL.0`, `LEVEL.01.MAUI` ... `LEVEL.08.SCALAWAG`. SCREENS.ROF has a single `SCREENS/` folder.
The EXE also knows `CWADDirectory` / `CNOWADDirectory`: loose folders can stand in for an archive.

## ✅ defT containers (`.RIM`, `.RTR`, `WARPER.MAP`, `TRICKS.RTR`)

Chunked zlib. `src/pbremaster/data/deft.py`.
```
char[4] 'defT', u32 chunk_size (80000), u32 total_size
repeat: u32 comp_size, comp_size bytes of zlib  (each inflates to <= chunk_size)
```

## ✅ .RIM raw images (UI screens, buttons, the FNF board)

The payload of a defT container:
```
u32 width, u32 height, u32 bpp, i32 stride   (|stride| is 4-byte aligned; negative = rows stored bottom-up)
bpp 16 -> RGB555 colour;  bpp 8 -> alpha mask
```
Masks sit next to their image with an `A` suffix: `106U.RIM` + `106UA.RIM`.
Button states use suffixes `U` (up), `D` (down), `UH`/`DH` (hover). `100.RIM` is the 800x600 main menu.
The game runs at **800x600**.

## ✅ Images in the archives: PNG, JPG, BMP

All 8,344 PNGs, 317 JPGs and 25 BMPs are standard files (checked with Pillow). Sprites keep transparency
in a separate mask image: `1OBJ_1.PNG` + `1OBJ_1A.PNG`, `PUZZLE_SPR0.PNG` + `PUZZLE_SPR0A.PNG`.
Loose: `DATA/SPLASH.PNG`, `DATA/LOADBAR.PNG`, `DATA/TRICKS.BMP`.

## ✅ Campaign structure (directory tree of PANDORA.ROF)

`src/pbremaster/data/catalogue.py`. Puzzle folders: `PUZZLE.<n>.<kind>`. City rules are **empty marker files**:

| Marker | Meaning |
|---|---|
| `PIECE.<n>` | puzzle n holds this city's piece of the box (exactly 1 per city, levels 1-7) |
| `HINT.<n>` | solving puzzle n earns a hint |
| `WILDCARD.<n>` | solving puzzle n earns a free puzzle ("Free Puzzles", LANGENU 204) |
| `TIME.<n>.<secs>` | puzzle n is timed |

- `LEVEL.0`: the tutorial, one puzzle of each type (12 folders).
- Levels 1-7, one per trickster (Maui, Puck, Eris, Coyote, Monkey, Anansi, Raven): 5 cities x 10 puzzles,
  plus 1-3 level puzzles (`LEVEL.nn/PUZZLE.n.*`), presumably the master puzzle (LANGENU 30 "Master Puzzle").
- `LEVEL.08.SCALAWAG`: 20 "cities" x 2 puzzles (11, 12), folders named after the picture. Probably the
  final level / puzzles-only extras. 🟡
- 411 puzzles in total: Focus Point 71, Overlap 63, Rotascope 55, Find and Fill 45, Jesse's Strips 43,
  Image Hole 42, Outer Layer 29, Slices 29, Lens Bender 22, Interlock 12.

## 🟡 The ten puzzle types

Official names from LANGENU.DLL 150-161. "Help file" is the quick-help RTF named in SCREEN.DAT.

| Name | Folder suffix | Data file | Header / notes | Help file | Sounds |
|---|---|---|---|---|---|
| Image Hole | IMH, IHL | `PUZZLE.IMH` + photo .JPG + thumbnail .PNG | binary, ~230-350 bytes ❓ | imageqh.rtf | IMG/ |
| Focus Point | FPN, ZOO | `PUZZLE.ZOO` | `'MAP' 01` + 16-byte GUID ❓ | focalpt.rtf | FPN/ |
| Rotascope | RTT, RTS | `PUZZLE.RTT` | `'MAP' 01` + GUID, or `'Zero'` + "New Puzzle" ❓ (two variants) | rotascop.rtf | RTT/ |
| Overlap | OVL, FSH | `PUZZLE.FSH` | `'SFHP'`, u32 3, ... ❓ | overlaps.rtf | OVER/ |
| Outer Layer | SKN, SKI | `3DSKIN.SKI` (INI) + `3DSKIN_SPRn.PNG` + `CAMERAn/{BACK.JPG, ADD.PNG, MULT.PNG, WARPER.DAT, WARPER.MAP}` | pre-rendered 3D, warp maps ❓ | 3dskins.rtf | 3DSKIN/ |
| Jesse's Strips | JES, JESS | `PUZZLE.JES` + photo .JPG | binary, u32 size, u32 2, ... ❓ | jesse.rtf | JES/ |
| Slices | SLC, SLICE | `STATE.TXT` (text: per object `x y flip rot` + name), `OBJECT.WRL` (VRML 1.0), `nOBJ_m.PNG` + masks | 🟡 | 3dslices.rtf | SLICE/ |
| Lens Bender | BGL | `PUZZLE.BGL` (INI `[BumpyGlass]`) + `PUZZLE_SPRn.PNG` + `TILE.PNG`; lens shapes in `BGL/<DIFF>_LENSn.RTRT/.RTRS` (precomputed ray-trace tables), layouts in `BGL/<DIFF>.INI` | 🟡 | bumpy.rtf | BGL/ |
| Interlock | TRI, TAN | `PUZZLE.TRI` | `'trgm'` u32 1, ... (holds an author's D:\ path) ❓ | rigram.rtf | TRIGRAMS/ |
| Find and Fill | FNF, F&F | `PUZZLE.FNF` + photo .JPG; board `FNF/301.RIM` | `'fnf_'` u32 1, u32 1, ... (large: ~800 KB) ❓ | findfill.rtf | FNF/ |

Other help RTFs in SCREEN.DAT: `hiseler.rtf`, `sheet.rtf` (two more types that were cut?).

## ✅ SCREENS/SCREEN.DAT: UI layout

`src/pbremaster/data/screens.py`. Loader `0x4fb7f0`; screen `Load` `0x4fb590`; control loads via each
class's vtable slot 4 (base `0x507240`). All little-endian; parses to the last byte (39 screens, 332 controls).

```
u32 screen_count
Screen:  u32 id, char background[32], char help_rtf[28], u32 n, u32 control_id[n]
u32 control_count
Control: u32 kind, u32 id, i32 left, top, right, bottom, then by kind:
  1 Button  (244 bytes) +0 label string id | +8,+36,+64,+92 image names (28 bytes each: up, down,
            up-hover, down-hover; one name = a strip of the 4 states side by side) | +120 5th name (unused)
            | +148 12 x u32 radio group ids | +208 action | +212 argument | +240 style
  2 Picture (32)  image name[28], 4 unused
  3 Label   (48)  string id, font size (px), align (0 left, 1 right, 2 centre), ?, COLORREF, font name[28]
  4 Region  (8)   x, y: hot spots with a status-bar tip, content drawn by code
  5 List    (44)  image name[28], inner rect (4 x i32)
  6 Edit    (44)  same as List
```
- Background/image names say `.bmp` but are `SCREENS/<NAME>.RIM`. Images without an `A` mask use pure
  blue (RGB555 `0x001F`) as a colour key.
- right/bottom 0: a button takes its size from the image (a quarter of a strip); a label measures its text
  and treats (left, top) as top-left / bottom-right / centre for align 0 / 1 / 2.
- Button **style**: 1 push, 2 toggle (checked = down frame), 3 radio (the 12 group ids).
- Button **action** (jump table `0x500838`): 1 close screen, 2 quick help, 3 show screen `arg`,
  10 run the command registered for `arg` (map `0x5d4100`, see game-logic.md), 12 quit,
  14 notify the screen, 15 end the dialog with result `arg` (1 OK, 2 Cancel, 6 Yes, 7 No).
- Screens with no background (10, 40, 250, 900-903, 1200, 1204) are message boxes drawn by code.
  `credits1.png`, `about1.png`, `introdlg.png` and the quick-help `.rtf` files are not on the CD.
- Help RTFs for `Chiseler.rtf` (7000) and `sheet.rtf` (9000) belong to two puzzle types that were cut.

## ✅ Cursors (PANDORA.EUL resources)

`src/pbremaster/data/cursors.py`. 39 RT_CURSOR / 33 RT_GROUP_CURSOR; the normal pointer is group 109
(`LoadCursorA(0x6d)` at `0x4f8b10`).

## ✅ String tables: LANGENU / PUZENU / NAMEENU / STATENU .DLL

Resource-only DLLs, read with `src/pbremaster/data/strings.py`.
- LANGENU: UI text, puzzle type names, tricksters (430-436), cities (461-495).
- PUZENU: credits for each puzzle's artwork, `%nTitle %aArtist %tTime %rRights` format, ids like 1121.
- NAMEENU: short picture names, "Level 1: ..." (same ids as PUZENU).
- STATENU: status-bar tooltips.
Picture ids: `level*1000 + city_id*20 + puzzle` (Cairo is city 6: 1121-1130). All 390 city puzzles have
a name; tutorial and level (master) puzzles do not. ✅

## 🟡 Other files

| File | Notes |
|---|---|
| `PUZZLE.DAT` (71 KB) | u32 9, then records holding `LEVEL.0`, `LEVEL.01.MAUI`, ... + ints (10000 at 0x8c): probably the puzzle order / scoring table. ❓ |
| `BESTTIME.DAT` | u32 1, then 64-byte records: u32 puzzle id (0x138e5...), f64 time, char name[...] ("Dad"). Best-time table, written by the game. 🟡 |
| `CREDITS.DAT` | Plain text, `%B` toggles bold. ✅ |
| `TRICKS.RTR` + `TRICKS.BMP` | defT; payload starts 0x1d6 x 0x145 (470x325). Probably a ray-trace lookup table for the "tricks" (trickster) screen. ❓ |
| `BKANT.TTF` | Book Antiqua, the UI font (LANGENU 31). ✅ |
| `SCREENS/*.WAV` (folder `DATA/SCREENS`) | UI sounds: MO (mouse over), CLICK, ALERT, NOCLICK, HELP, BACK ... ✅ |
| `*.AVI` | `OPEN.AVI` (intro) and `INT01-07.AVI` (story per level). Video **Indeo 5 (IV50)**, PCM audio. PyAV's bundled FFmpeg decodes IV50. |
| `*.WAV` | Standard PCM. `MUSIC/` holds 22 kHz mono tracks per region (AFRICA, ASIA, ...) and `_P` variants. |
| `HELP/*.M20` | WinHelp (.HLP) files. |
