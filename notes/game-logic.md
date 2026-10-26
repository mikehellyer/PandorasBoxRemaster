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
