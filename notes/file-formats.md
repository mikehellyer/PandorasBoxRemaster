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
| Image Hole ✅ | IMH, IHL | `PUZZLE.IMH` + 650x540 picture .JPG + hole mask .PNG (.BMP on 4 Scalawag puzzles) | see below | imageqh.rtf | IMG/ |
| Focus Point ✅ | FPN, ZOO | `PUZZLE.ZOO` | Zoommess file, see below | focalpt.rtf | FPN/ |
| Rotascope ✅ | RTT, RTS | `PUZZLE.RTT` | `'Zero'` record (the tutorial wraps it in 'MAP'), see below | rotascop.rtf | RTT/ |
| Overlap ✅ | OVL, FSH | `PUZZLE.FSH` | see below | overlaps.rtf | OVER/ |
| Outer Layer ✅ | SKN, SKI | `3DSKIN.SKI` (INI) + `3DSKIN_BACK.PNG` + `3DSKIN_SPRn.PNG` + `CAMERAn/{BACK.JPG/PNG, ADD.PNG, MULT.PNG, WARPER.DAT, WARPER.MAP}` | see below | 3dskins.rtf | 3DSKIN/ |
| Jesse's Strips ✅ | JES, JESS | `PUZZLE.JES` + picture .JPG | see below | jesse.rtf | JES/ |
| Slices ✅ | SLC, SLICE | `STATE.TXT`, `OBJECT.WRL` (VRML 1.0), `<n>OBJ_<v>.PNG` + masks | see below | 3dslices.rtf | SLICE/ |
| Lens Bender ✅ | BGL | `PUZZLE.BGL` (INI) + `PUZZLE_SPRn.PNG` + masks + `TILE.PNG/BMP`; lens tables `BGL/<SET>_LENSn.RTRT/.RTRS`, layout `BGL/<SET>.INI` | see below | bumpy.rtf | BGL/ |
| Interlock ✅ | TRI, TAN | `PUZZLE.TRI` | see below | rigram.rtf | TRIGRAMS/ |
| Find and Fill ✅ | FNF, F&F | `PUZZLE.FNF` + photo .JPG; left column `FNF/301.RIM` | see below | findfill.rtf | FNF/ |

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

## ✅ PUZZLE.ZOO (Focus Point)

`src/pbremaster/data/zoo.py`, from the editor's save routine `0x4a2b80` ("Zoommess Ver.04, Microsoft (C)
1997, written by Kirill Ageev").
```
0x00  0x44-byte header template ('MAP' 01, GUID, "Puzzle Desc"...), sizes patched at 0x35
0x44  u32 desc_size = 0x160 + 36 * cells
0x48  char copyright[64]
0x88  params (0x120 bytes): cells, x, y, width, height, 1, 1, u32 (hi 0-6 / lo 0-1, unknown), zeros
0x1a8 cells x { home x+16, y+16, w, h;  slot x, y, w, h;  0 }   (i32)
then  the picture (JFIF JPEG), padding, 0x18-byte trailer
```
- Slots are a rearrangement of the homes: a fixed partition of the picture; the file's slot layout is
  the starting scramble; a piece is drawn stretched into the slot it occupies.
- x, y centre the board in the 650x540 play area at (75,42) (FPN/312.PNG matches 300.RIM there), except
  the tutorial and Athens 1, which store (16,16); the remaster always centres.
- Data quirks on the CD: Athens 1's header is overwritten with pixel bytes; three JPEGs are truncated
  (libjpeg/pygame still decode them); Scalawag "City Place" stores homes 1 px low (snapped to slots);
  Monkey level puzzle 2's JPEG is 12 px wider than the board.

## ✅ PUZZLE.RTT (Rotascope)

`src/pbremaster/data/rtt.py`; loader `0x4efea0`, layout grid load `0x4f06f0`.
```
'Zero', u32 version 3, name\0 ("New Puzzle")
u32 ?, u32 ?, COLORREF outline colour, u32 ?
64 x (u8 ring, u8 sector)   grid[ring][sector]: the piece in each ring section, (255,255) = gap
u8 ring, u8 sector          the piece in the centre                     } 10 bytes the Feb 2000
u32 ?, u32 ?                                                            } loader does not read
u32 start angle (degrees)   path\0   u32 jpeg size, JPEG
```
Disk configs (`0x5b2630`): 4 sectors x 2 rings, start 45, radius ratio 3; 5 x 3, 18, 2; 6 x 4, 30, 1.64.
Outer radius min(w,h)/2 - 1 (<= 250); radii shrink inward by the ratio; the innermost radius is the
centre disc (CCenterSection); ring sections are CRingSection(a0, a1, r_in, r_out) built at `0x4f0a00`.
All 55 files fit exactly one config. The tutorial file wraps the record in a 'MAP' container.

## ✅ PUZZLE.IMH (Image Hole)

`src/pbremaster/data/imh.py`; loader `0x4ace50`.
```
u32 ?, u32 version (1/2), u32 holes, COLORREF fill, COLORREF outline
title\0  picture.jpg\0  mask.bmp\0   (the CD ships the mask as .PNG on most puzzles)
holes x 58: u8 ?, f32 scale (0.5-1.4), f32 0, f32 speed (3-21), u8 starts-locked,
            RECT place, POINT home (= place top-left), POINT start, POINT direction, COLORREF mask key
version 2: u32 0
```
The JPG is the whole 650x540 play area (frame included); the mask image marks each hole's shape in its
own colour on blue.

## ✅ PUZZLE.JES (Jesse's Strips)

`src/pbremaster/data/jes.py`; loader `0x4b6e30`.
```
u32 ?, u32 version, i32 cell (30/25/20), i32 ?, i32 ?, i32 ?, u32 tray cols, u32 tray rows, u32 strips, u32 ?, u8 ?
"puzzle.jes"\0  picture\0
5 x u32 tray counts, then each tray's strip numbers (strips in no tray start in place)
strips x 57: start (x, y, dir), same again, solution (x, y, dir: 1 vertical, 2 horizontal), u8 ?,
             u32 length, RECT in the picture (px)
u32 n, n x (x, y): board cells shown from the start (marked at +0x26c)
```
Tray grids are 19x16 @30, 23x19 @25, 28x24 @20 (all ~570x480). The board offset (solution - rect/cell)
is the same for every strip of a puzzle (checked on all 43).

## ✅ PUZZLE.FSH (Overlap)

`src/pbremaster/data/fsh.py`; loader `0x4e1c30`, piece load `0x4e4960`, shape table built at `0x4e4780`.
A raw struct dump (0xCD = MSVC uninitialised fill):
```
'SFHP', u32 3, i32 cols, rows, cell, pieces, stacks, ?, ?, ?, ?
char picture_path[260], char background_path[260]  -> OVER/BG_<name>.PNG
u32 bits, bytes: CBitField of cells shown from the start
stacks x { u32 cap, cap x u32 (index 0 unused), u32 count, u32 ? }   (stale entries: use piece.stack)
pieces x { i32 x, y, shape, rotation, scramble, ?, stack, number }
u32 size, JPEG (one file: BMP)
```
Shapes: anchor + two steps; shape 0 straight, shape 1 L; steps by (rotation + scramble) % 4:
`0: (0,1)(0,1) | (-1,0)(-1,0) | (0,-1)(0,-1) | (1,0)(1,0)`,
`1: (0,1)(-1,0) | (-1,0)(0,-1) | (0,-1)(1,0) | (1,0)(0,1)`.
Shown cells + pieces cover every cell in all 63 files; pieces overlap; anchors outside the picture
show the background pattern.

## ✅ PUZZLE.TRI (Interlock)

`src/pbremaster/data/tri.py`; loader `0x5116e0`, shape `0x511e20`, piece `0x510eb0`.
```
'trgm', u32 1, u32 n + path[n] (picture), u32 shapes (1)
shape: u32 n + name[n], COLORREF piece colour,
       7 x { u32 type, u8 flip, i32 x, i32 y, i32 rotation }   solution
       i32 w, h, w*h bytes (always 0x0), i32 ?, i32 ?, u32 triangle size
7 x { u32 type, u8 flip, i32 x, i32 y, i32 rotation, i32 ?, i32 ?, u32 size }   start (newer than the Feb loader)
```
Equilateral triangle grid (0x511170): column step size/2, row height size*sqrt(3)/2; board triangle
(x, y) points down when x + y is even. Pieces: table at `0x5b440c`, (type*6 + rotation)*2 + flip ->
u8 w, u8 h, u8 first-points-down, w*h cells; dumped to `src/pbremaster/data/iamonds.py` by
`tools/re/dump_iamonds.py` (shapes of 5,4,5,5,4,5,4 triangles = 32).

## ✅ PUZZLE.FNF (Find and Fill)

`src/pbremaster/data/fnf.py`; loader `0x499eb0` (CFindNFillObject). Checked on all 45 files.
```
'fnf_', u32 1, u32 pictures, u32 first strip width, u32 121, u32 16
per picture:
    image   strip 121 high: the reference picture (140 px cell, magenta border), then one 140 px
            cell per object with its black silhouette
    u32     objects
    objects x { image (the object as cut from the picture, magenta 0x7C1F = transparent),
                u32 1, COLORREF, f64 angle (degrees), f64 -height/2, RECT in the source picture,
                i32, i32, outline chain codes / scanline records (no length), u32 n + name[n] }
u32 n + source path[n] ... (last one ends ".bmp")
f64 angle (radians), u32 layout (0, 1 = square pile; 2 = wide strip), u32 size, u32 W, u32 H
u16 board[H][W]       cell bit 4+k = object k covers it; bit 3 on some cells (unknown)
image = u32 w, u32 h, u32 bpp (16), RGB555 rows padded to 4 bytes
```
Later strips are found by their `w, 121, 16` header, objects by an image header followed by u32 1
and a RECT the image's size, the board by the first `.bmp` string followed by a plausible header.
Boards: 500x500 (11), 400x400, 350x350, 250x250 ... and strips up to 1256x430. Four files carry
stale bytes after the board (an older, larger save written over in place; Moscow 4: a 330x330 board,
then the tail of a 400x400 one). On the board each object is turned and scaled (area ratios 1 to 15);
neither per-object double predicts the turn, so the game fits it (see game-logic.md).

## ✅ Slices folder (CLambChopsObject)

`src/pbremaster/data/slc.py`; loader around `0x4c3950` (`object.wrl`, `state.txt`, `%dobj`, `wobj`).
```
OBJECT.WRL   VRML 1.0: 4 SpotLights; per piece DEF <n>obj Separator { MatrixTransform { matrix
             4x4 row vectors } Separator { Coordinate3 { point [8 box corners] } Normal ...
             IndexedFaceSet } }; last DEF wobj = box round the whole object
STATE.TXT    per piece: floor x, floor z, flip, turn (some entries give fewer numbers), name
<n>OBJ_<v>.PNG / <n>OBJ_<v>A.PNG   piece pre-rendered in view v = flip*4 + turn + 1, mask black = solid
WOBJ_<v>     the whole object; SLICE/BACKGROUND.PNG the 648x540 checkerboard table
```
Views: the object turned `turn` quarter turns about y, then if flipped half over about x. Camera
(mouse-to-floor pick at `0x4c5d00`): orthographic, view direction (-2,-1,-2)/3, up (-1,4,-1)/(3 sqrt 2),
view height 14 units per 480 px (`0x4c9778`: client height / 480 * 14), floor y = -0.48, floor x, z in
-10..10 mapped to a 10x10 grid. Sprites are centred on their box centre's projection: compositing the
pieces this way rebuilds WOBJ's silhouette at 0.985-0.99 overlap in all 8 views (Eris puzzle 1).
Every PNG has odd width and height (rendered round the centre). Boxes touching within 0.05 units link
every puzzle's pieces into one connected graph.

## ✅ PUZZLE.BGL and lens tables (Lens Bender)

`src/pbremaster/data/bgl.py`; sprite loader `0x478af0`, layout loader near `0x47bbae`.
```
[BumpyGlass]    ObjectCount, Difficulty 0-3, SolutionWidth/Height, LensDepth, LensIndex,
                AmbientK/DiffuseK/SpecularK/SpecularPower, FlashCount, Designer...
[BumpySpriteN]  Visible, FinalXpos/FinalYpos, InitialStack (0-5 lens, 6 = middle),
                InitialStackOrder (0 = top), FinalStack, Adjacency (letters = sprites),
                Angle (multiple of 60), CentroidX/Y and CenterX/Y (optional, designer)
PUZZLE_SPR<n-1>.PNG + ...A.PNG (mask, black = solid); TILE.PNG/BMP the lens background
BGL/<SET>.INI   [BumpyGlassLayout] LensCount=7, Lens1..7PosX/Y (centres in the 650x540
                area; 7 = middle), Button1..6PosX/Y (arrow centres; Button7 = 0,0)
BGL/<SET>_LENSk.RTRT/.RTRS   u32 w, u32 h, 50 bytes (01 01, zeros, 4 float bounds),
                i16 (src x, src y)[h][w] (-16383 = outside), u16 shade[h][w] (/65536)
```
Sets TUTOR, EASY, MEDIUM, HARD share sizes: lenses 0-5 are 175, 201, 75, 101, 125, 151 px, the
middle 315 (RTRS samples a 540x540 canvas, RTRT ~600x600; TUTOR has no RTRS). Outer tables only
magnify and bend (no turn). Angle + 60 * FinalStack = 0 (mod 360) for all 313 sprites; each puzzle
starts with 1-5 sprites in the middle. Difficulty rises with the level (0: Level 0/Coyote/Monkey,
1: Monkey, 2: Anansi, 3: Raven).

## ✅ 3DSKIN.SKI and camera warps (Outer Layer)

`src/pbremaster/data/ski.py`.
```
[3DSkin]            ObjectCount, SegmentCount, InitialCamera (1-4), EnableRotation, PositionSnap,
                    FlashCount, Designer, Debug, DrawManipulators
[3DSkinSegmentN]    MinX, MinY, MaxX, MaxY: rectangles of the texture (1-5 per puzzle)
[3DSkinSpriteN]     HasMask (always 0), InitialXpos/Ypos/Angle (0/90/180/270), InitialTray
                    (-1 on the object, 0-3 a stack), InitialTrayOrder, InitialSegment,
                    FinalXpos/Ypos (top-left in the texture), FinalAngle (always 0), FinalSegment
3DSKIN_BACK.PNG     the bare texture (its size: 400x200 .. 2000x200 / 800x800)
3DSKIN_SPRn.PNG     square pieces, 80-100 px
CAMERAk/            BACK (JPG, 20 cameras PNG) the scene with the object blank, MULT shading,
                    ADD highlights, all 540x540; WARPER.DAT 62-byte header (u16 1, u16, u32 540,
                    u32 540, float bounds); WARPER.MAP defT: i16 u-plane[540][540] then v-plane,
                    each as differences along the row. Summed: u = 16384 + texture x, v = texture y
                    where the object (or its reflection in the mirror) shows; anything else = BACK.
```
View pixel = texture[v][u - 16384] * MULT / 255 + ADD. 59 of the 1323 pieces have their middle hidden
from all four cameras, but every piece has some of its final square visible in one of them.

