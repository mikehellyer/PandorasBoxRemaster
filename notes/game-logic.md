# Pandora's Box: game logic from PANDORA.EUL

Addresses are in the unprotected `DATA/PANDORA.EUL`. Tools: `tools/re/pe.py` (disassembly, xrefs,
`asm` dumps the whole .text to `extracted/re/pandora.asm` for grep), `tools/re/reads.py` (reduces a
Load method to its stream reads), `tools/re/commands.py` (the command table below).

## UI buttons (class vtable 0x58c3cc)

- Constructor `0x4ffc30` sets "play sounds" (`+0x29d`) and "show caption" (`+0x2de`) for every button.
- Hover plays sound 20 `MO.WAV` (`0x500ee2`); click plays 21 `CLICK.WAV` (`0x500186`).
  UI sound ids (`0x4f89e8`): 20 MO, 21 CLICK, 22 ALERT, 23 NOCLICK, 24 HELP.
  Sound only plays when the Options "Sound" flag (`0x5ba65d`) is set (`0x43c6c8`).
- Label (`0x5017e2`): Book Antiqua 16 px (weight 500, antialiased; font made from LANGENU 31-36 at
  `0x50284c`), `TA_CENTER|TA_BASELINE` at (w/2, h/2 + 1), drawn in `#F8B064` at +1,+1 then `#3F0F00`;
  +1,+1 more while down.
- No label: the id's LANGENU string is a 14 px caption under the button while hovered (`0x5018a2`).

## Text labels (class vtable 0x58c33c)

Draw `0x4fea70`: baseline = rect bottom - 5; x = left / right / centre for align 0 / 1 / 2.
Init `0x4fe8f0`: if bottom is 0 the rect comes from `GetTextExtentPoint32` (`0x4feb40`).

## Command table (map 0x5d4100, registered at 0x442550)

| id | handler | does |
|---|---|---|
| 54 Menu | 0x414290 | Win32 pop-up from LANGENU menu 105: Main Screen (40001), Save (40004), Minimize (40002), Options (40007), Exit (40008) |
| 52 Back | 0x413fd0 | previous screen |
| 101 PLAY | 0x414c30 -> 0x41bc90 | player check, then story video / world map (campaign) |
| 102 TUTORIAL | 0x414c70 -> 0x41c4d0 | player check, load tutorial, screen 501 (practice city) |
| 103 GALLERY | 0x414dd0 -> 0x41c3b0 | player check, screen 600 |
| 104 PUZZLES ONLY | 0x414cb0 -> 0x41c500 | player check, screen 150 |
| 105 OPTIONS | 0x414cf0 | dialog 103 (controller 0x427480) |
| 106 LOAD | 0x414d90 -> 0x41c3e0 | player check, dialog 101 |
| 303 Pause, 304 Restart, 305, 306 Free, 307 Hint, 309 Continue | 0x414e10 ... | in-puzzle |
| 150, 650 | 0x414ef0, 0x4152f0 | puzzle-type radio groups (Puzzles Only, Gallery) |
| 169 Play | 0x414f40 | play the puzzle picked in Puzzles Only |
| 400, 504, 518, 519, 599, 605, 1800, 1801 | 0x414f80 ... | map / city / gallery |
| 255, 703 Apply, 704 Delete, 706 Load, 707 Save, 715 Eula, 716 Credits, 717 About | 0x4151e0 ... | dialogs |

"Player check" is `0x41c520`: the name in the main menu's edit box (107) becomes the current player
profile (a 0xf30-byte object); list 108 shows the existing players.

## Options dialog (0x427480)

Toggles 721 Sound / 722 Music / 723 Timer are set from `0x5ba65d` / ... via `SetChecked` (`0x4ff660`);
checked shows the down frame (the X).

## Campaign flow

- **PLAY** (`0x41bc90`): checks the player, then by the player's saved screen (`+0xeec`): new game -> the
  level's movie on screen 40, then the map (400); otherwise back to the map / city. Player fields: level
  `+0xedc`, city `+0xed8`, current puzzle `+0xef0` (= level*10000 + city*100 + puzzle), per-level
  "movie seen" flags `+0xeb8`.
- **Movies** (screen 40, `0x419270`): `AVIBACK.PNG` with the 448x336 video at (176,132). Table at
  `0x5ba490`: OPEN.AVI before level 1, INT01 before level 2 ... INT07 after level 7. Indeo 5 + PCM.
- **City -> music region** table at `0x5a9dd0` (id 500+city, name, region); see `game/world.py`.
  It already uses the archive's city numbers (1 Amsterdam ... 35 Vienna, 36 Workshop).
- **Rules** (STATENU 306/501-503, LANGENU 1001-1042): 10 solved puzzles = a Free Puzzle token;
  HINT.n / WILDCARD.n puzzles give a Hint / token; PIECE.n holds the city's piece; five pieces open the
  trickster's Challenge (the level's own puzzles); beating a timed puzzle reveals the piece or gives 3
  tokens; leaving a city resets half-done puzzles.
- **PUZZLE.DAT** is only a cache the game writes by scanning PANDORA.ROF (`0x431030`: `Level.*`,
  `City.*`, `Puzzle.*`, then `time.* hint.* wildcard.* piece.* story.*`); the remaster reads the archive.

## World map markers (approximation)

The map controls 401-434 in SCREEN.DAT sit at the places of an **older city list** (STATENU 461-494:
1 Acapulco, 6 Budapest, 8 Cairo, 10 Cheyenne ...), while the data and the code (`0x41fc00`:
`AddControl(400 + city)`) use the new numbering, so taken literally Cairo would sit in Hungary. The
shipped PANDORA.EXE is SafeDisc-encrypted and cannot be checked. The remaster matches cities to the old
markers by name and places the nine renamed ones (Amsterdam, Honolulu, Mexico City, Milan, Moscow,
Philadelphia, San Francisco, Tokyo, Vienna) itself from the map's scale (`world.EXTRA_MARKERS`).
Marker art: `401B` ball (piece not found), `403B` star (found), `402` big ball (current city); legend
LANGENU 450-452.

## Screen art numbering (SCREENS.ROF)

| Image | Use |
|---|---|
| 1600 + city id (1600 = tutorial) | city picture, 516x381 at (142,25) |
| 521 + level | trickster portrait in the city's right panel (picture 518) |
| 510..521 (+R) | city puzzle tiles in Puzzles Only order, 16 flip frames; R = the solved side |
| 15<level-1><k> F / NF / A / T / S | the level's k-th box piece (found / not found / mask / turning) |
| 15<level><k> / D | piece icons on the Challenge screen (D normal, plain highlighted) |
| 1800 + level - 1 | the box on the Challenge screen |
| 1701 + level - 1 | the trickster full screen; 1711-1717 and MASTER are unused placeholders |
| 900 | message box frame (buttons 1200-1208 placed by code) |
| CREDITS1, ABOUT1, INTRODLG | dialog frames; their text is drawn by code |
| 250, 251-254 | the Story book (button 53) |

## Music: DATA/MUSIC/PANDORA.MGD

A "MediaGraph" script (plain text). LocationCF cross-fades 0 silence, 1 city region track,
2 MAP.WAV, 3 the region's `_P` track in a puzzle, 4 LEVEND.WAV. INTRO.WAV plays at start-up, then MAP.
One-shots: `S_<region>` success, CHWIN challenge won, CHMODE challenge, `C_<trickster>`,
story voice-overs `VO/SX_<MAUI|PUCK|ERIS|COYO|MONK|ANAN|RAVE><piece>.WAV`. See `ui/music.py`.

## Puzzles (play area 650x540 at (75,42) of every puzzle screen)

Classes (RTTI): CImageHoleObject, CFocalPointObject, CRotoscopeObject, COverlapseObject, C3DSkinObject,
CJesseStripsObject, CLambChopsObject (Slices), CBumpyGlassObject, CTrigramsObject (tangram), CFindNFillObject.
How each plays is described in HELP/PANDORA.M20 (WinHelp; `strings` shows the text).

### Focus Point ✅ (CFocalPointObject, `src/pbremaster/puzzles/focuspoint.py`)
Click a piece, then another, to swap them; a piece in its own slot locks. Buttons made in code
(`0x4a12e9`): animation toggle id 3201 at (743,409), outline toggle 3202 at (743,467) - FPN/ANIM_*, GRID_*.
Hint = place one piece; Free token = solve. Sounds FPN/FP_SEL, FP_DESEL, FP_MOVE, FP_LOCK, FP_MO are
named in the June 2000 data, not in the Feb 2000 EUL, so when each plays is inferred.

### Rotascope ✅ (CRotoscopeObject, `src/pbremaster/puzzles/rotascope.py`)
Click a piece next to the gap to slide it in: neighbouring sector in the ring, same sector one ring
in/out, or centre <-> any innermost sector. Pieces are drawn by mapping their home section of the
picture onto the section they occupy, so they rotate and stretch. Solved: all home, gap in the centre
(the centre of the picture is never shown). The board graph has triangles (centre + two inner sectors),
so by Wilson's theorem every arrangement is solvable and hint swaps are safe. Hint (LANGENU 4312-4315):
click a piece to send it home. Sounds RTT/RO_SPIN, RO_SB, RO_BS, RO_CLICK (when each plays is inferred).
Interactive tutorial texts are LANGENU 4308-4311 (not used yet).

### Image Hole ✅ (CImageHoleObject, `src/pbremaster/puzzles/imagehole.py`)
Texts LANGENU 2052-2057, 2002 (three strikes restart), sounds IMG/IM_SEL, IM_MOVE, IM_RIGHT, IM_X, IM_FAIL
(LANGENU 2015-2019). Controls placed at `0x4a8f30`: strike icon (737,348), strike holes (740,404), pegs at
x 739/760/781, one speed cycle button (slow/medium/fast, LANGENU 2600-2602) at (748,429).
**Interpretation (not traced in code):** the picture is shown with every unlocked hole's place filled
with the fill colour; holes are outlined windows onto the picture drifting around; select a hole,
click the background to send it, click it again to lock. Lock succeeds within 10 px of its place's
centre; hole speed = speed x 6 px/s x (0.5/1/2). These three numbers are guesses to check against the
original.

### Hints (all types)
Hint arms a hint mode; the next click on a piece/hole places it (LANGENU 2052, 3318, 4313); clicking
Hint again cancels without using it. Focus Point also uses this now.

### Jesse's Strips ✅ (CJesseStripsObject, `src/pbremaster/puzzles/jesse.py`)
Tutorial texts LANGENU 8007-8015, hint 8006, buttons "Grid" 8990 / "Rotate" 8991. Strips are 1 x n runs
of picture cells; select (SHIFT adds), drag (snaps to cells), right-click or the Rotate button turns a
quarter, tabs or keys 1-5 switch trays, holding a dragged strip over a tab moves it there.
**Interpretation:** the board (picture area with its given cells) is drawn on every tray and each tray
keeps its own loose strips; a strip sticks when dropped on its own place upright; trays get a light
tint of their tab colour; tab hold 0.6 s; rotation is clockwise. No Grid toggle yet (no art for it).
Tall pictures (12x18 cells) overhang the 16-row grid; the remaster clips the board to the grid.

### Overlap ✅ (COverlapseObject, `src/pbremaster/puzzles/overlap.py`)
Texts LANGENU 5414-5421. OVER/BACKGROUND.PNG is 725x540: a stack column (4 compartments at y 0/130/270/400)
and the 540x540 board, picture centred on the BG pattern. Drag the top piece of a stack to the board;
right-click / Rotate turns it; it sticks on its anchor with no scramble left; dropped on a stack it
moves there; arrows (OVER/BUTTONS.PNG) look through a stack. Sounds OVER/OL_SEL, OL_ROTAT, OL_RIGHT,
OL_WRONG, OL_REORD, OL_DC.
**Interpretation:** compartment/arrow placement and thumbnail size are measured from the art; the
drop tolerance is "nearest cell".

### Interlock ✅ (CTrigramsObject, `src/pbremaster/puzzles/interlock.py`)
Texts LANGENU 12900-12903, hint 12950, buttons Flip 12101 / Rotate 12102. Pieces turn in 60 degree
steps and flip; a piece sticks when it covers exactly its solution triangles. The picture is centred
in the play area with the solution triangles blacked out (on Amsterdam 8 they cut out the lute player,
which supports this reading); unplaced pieces use the file's colour.
**Interpretation:** grid origin at the play area's corner, button positions.

### Find and Fill ✅ (CFindNFillObject, `src/pbremaster/puzzles/findfill.py`)
Texts LANGENU 13126-13132 (13128: "fill it with a single color. Make sure you don't fill any extra
spaces!"; 13129: two images at once with different colours; 13130: images may be rotated or upside
down), solved 13118, scroll tips STATENU 13133/13134. The board is the file's cell grid: lines are the
boundaries between cells covered by different sets of objects (2 px, so areas never touch
diagonally) and the areas between them are filled by clicking with the selected colour (FNF/BLUE,
YLLW, RED, GRN textures from FNF/PATTERNS.PNG rows 0-3; row 4 is the empty wood). FILL (black) or a
right-click erases one area, ERASE clears all. An object is found when one colour covers exactly its
still-open areas and no other open area; its picture then shows in place and its areas lock, except
those an unfound object still needs (five puzzles have an object wholly inside another; locking them
would make it unfindable). Hint: click an area to outline one unfound object covering it.
Sounds FNF/FF_COLOR, FF_FILL, FF_ERASE, OUTLINE, SUCCESS, BADCLICK.
**Interpretation:** layout (left column of reference pictures with their silhouettes, black until
found, pictures whose objects are all found drop out; palette and arrow positions; left/right arrows
are UPARROW turned), boards that fit are scaled up to fill the 540x540 view, larger ones scroll
(arrows, wheel, shift+wheel), outline colour, and the found picture: the sprite turned and scaled by
a fit to its cells (whole degrees, scale from the extent), as the file's fields didn't give it.

### Slices ✅ (CLambChopsObject, `src/pbremaster/puzzles/slices.py`)
Texts LANGENU 10900-10905 (select, drag, drag onto another piece to connect: both must face the same
direction; right-click rotates; flip), hint 10910, buttons Flip 10100 / Rotate 10101-10102 / Animate
10103. Pieces stand on the checkerboard in the original's camera (file-formats.md); a group keeps its
pieces' places in the assembled object and is drawn far-to-near by depth along (2,1,2). Drop a group
on another facing the same way and they join if one piece of each touches in the object; otherwise
SL_WRONG and it goes back. Right-click / ROTATEP turns a quarter, FLIPP flips, REVLF/REVRT turn the
whole table, ANIM spins the selected (or solved) group. Solved when one group holds every piece.
**Interpretation:** the touching rule (the original may join any two pieces facing the same way),
turning about the group's centre, groups standing on the floor by their lowest box, hint = bring one
touching piece into the clicked piece's group, button positions, HI_SQUARE_1 under the selection.
