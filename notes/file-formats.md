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

## 🟡 SCREENS/SCREEN.DAT: UI layout

Loaded by `0x4fb7f0` in PANDORA.EUL. `u32 screen_count (39)`, then screen records (each read by a virtual
`Load`, background like `100.bmp` = `100.RIM`, quick-help RTF, list of control IDs); then `u32 control_count`
and control records; each starts with `u32 type` (1-6, jump table at `0x4fbe24`) that picks the control class.
Button images are named by control ID (`103u.bmp` -> `SCREENS/103U.RIM`). Control IDs match LANGENU string
IDs (101 PLAY, 102 TUTORIAL, 103 GALLERY ...). Next step: decode the six control `Load` methods.

## ✅ String tables: LANGENU / PUZENU / NAMEENU / STATENU .DLL

Resource-only DLLs, read with `src/pbremaster/data/strings.py`.
- LANGENU: UI text, puzzle type names, tricksters (430-436), cities (461-495).
- PUZENU: credits for each puzzle's artwork, `%nTitle %aArtist %tTime %rRights` format, ids like 1121.
- NAMEENU: short picture names, "Level 1: ..." (same ids as PUZENU).
- STATENU: status-bar tooltips.
The puzzle id scheme (1121 = level 1, ...) is not decoded yet. 🟡

## 🟡 Other files

| File | Notes |
|---|---|
| `PUZZLE.DAT` (71 KB) | u32 9, then records holding `LEVEL.0`, `LEVEL.01.MAUI`, ... + ints (10000 at 0x8c): probably the puzzle order / scoring table. ❓ |
| `BESTTIME.DAT` | u32 1, then 64-byte records: u32 puzzle id (0x138e5...), f64 time, char name[...] ("Dad"). Best-time table, written by the game. 🟡 |
| `CREDITS.DAT` | Plain text, `%B` toggles bold. ✅ |
| `TRICKS.RTR` + `TRICKS.BMP` | defT; payload starts 0x1d6 x 0x145 (470x325). Probably a ray-trace lookup table for the "tricks" (trickster) screen. ❓ |
| `BKANT.TTF` | Book Antiqua, the UI font (LANGENU 31). ✅ |
| `*.AVI` | `OPEN.AVI` (intro) and `INT01-07.AVI` (story per level). Video **Indeo 5 (IV50)**, PCM audio. PyAV's bundled FFmpeg decodes IV50. |
| `*.WAV` | Standard PCM. `MUSIC/` holds 22 kHz mono tracks per region (AFRICA, ASIA, ...) and `_P` variants. |
| `HELP/*.M20` | WinHelp (.HLP) files. |
