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
Marker art: `401B` ball (piece not found), `403B` star (found), `402` a halo drawn half-transparent
under the current city's ball or star, as the legend's icon shows; legend LANGENU 450-452. The current
location is the city last entered (`Player.last_city`, kept after going back to the map and cleared on
a new level), separate from `Player.city`, which only says the game should resume inside a city.

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
of picture cells; select (SHIFT adds, or drag a box from empty tray space over several, as the quick help
says), drag (snaps to cells), right-click or the Rotate button turns a
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

### Lens Bender ✅ (CBumpyGlassObject, `src/pbremaster/puzzles/lensbender.py`)
Texts LANGENU 11950-11954 (tutorial), hint 11924, tooltip STATENU 11111 "Rotate piece. Or right-click
to rotate." Each outer lens k holds a stack; its top piece shows through the lens table turned to
Angle + 60k. Drag a top piece to another lens (top of that stack); a lens's arrow attaches its top
piece to the middle when it faces 0 and touches (Adjacency) a piece already there (BG_RIGHT, else
BG_WRONG / BG_NO). The tutorial (Level 0) plays out exactly under these rules: attach from the
second-smallest lens, move the next piece to the smallest lens, one piece won't attach until its
neighbour is in. Solved when every piece is in the middle.
**Interpretation:** Rotate / right-click cycles the selected lens's stack (turning a piece freely
would make the lenses pointless); Difficulty 0-3 -> TUTOR/EASY/MEDIUM/HARD tables; pieces are scaled
to fit their lens (by their diagonal) and the solution to the middle's canvas; hint moves the clicked
piece to the lens where it faces right; selection ring.

### Outer Layer ✅ (C3DSkinObject, `src/pbremaster/puzzles/outerlayer.py`)
Texts LANGENU 6204-6212 (tutorial), hint 6206, buttons Next/Previous piece 6601/6602, Rotate 6666,
Go left/right 6667/6668, camera hotspots STATENU 6250-6253. Four stacks on the left (3DSKIN/302.PNG
column, UPARROW/DNARROW step a stack); drag a piece onto the object and the point you hold it by
lands on the texture point under the cursor (from the warp map); dropped within a fifth of a piece of
its place and upright it snaps and stays. Pieces on the object can be picked up again the same way.
Right-click / ROTATE turns 90 degrees. Solved when every piece is in place.
**Interpretation:** stack layout and arrow positions, the snap distance, REVLF/REVRT and keys 1-4 for the
cameras (the original also lets you click the N/E/S/W arrows painted on the table; hotspots not found),
the hint placing the clicked piece, BRACKET0-3 round the selected stack piece, generic click sounds
(3DSKIN has no WAVs).

### Quick help ✅ (`App.quick_help`, `campaign.HelpScene`)
The "?" button (action 2) posts 0x8065; the screen opens HELP/PANDORA.M20 at its SCREEN.DAT help topic.
Shown in the code-built message box (900.RIM, OK 1200): title centred, short headings bold, bullets;
the font steps down 17 -> 12 px until the topic fits. **Interpretation:** the original's viewer layout.

### Hints
Hints are earned (HINT.n puzzles); the Hint button (307) asks LANGENU 1002 and, on Yes, starts the
puzzle's hint mode; one is charged when the hint is used. With none the original only plays the "no"
click (STATENU 307: "If you have earned Hints, click to receive a Hint"). **Modern addition:** with no
Hints the remaster shows a short message (campaign.NO_HINTS) saying so and how Hints are earned.

### Free Puzzle tokens
Free (306, handler 0x436430) asks LANGENU 1001 and solves the puzzle for one token. In the Challenge
(mode 4, the screen built by 0x438960 on the gold-trimmed 300F.RIM) it costs three: LANGENU 1041 asks,
and with fewer than three 1042 says to earn more in this level's cities. **Modern addition:** with no
tokens on a normal puzzle the remaster shows campaign.NO_TOKENS instead of only the "no" click.

### Puzzles Only, saved games, display
- Puzzles Only (150): a type button fills the list (165) with every puzzle of that type, Scalawag's bonus
  puzzles included; Play (169) opens the selected one outside the campaign (no pieces, tokens or Hints;
  a Free token still costs one) and returns to the list when it is solved.
- Save (menu 40004, dialog 102: name box 741, list 701, Save 707, Delete 704) and Load (106, dialog 101:
  list 702, Load 706, Delete 704): named snapshots of the player's progress (game/saves.py, JSON under
  the data folder). Progress itself is still saved automatically. Load puts the player back on the map.
  **Interpretation:** saves are per player; overwrite and delete ask first.
- **Modern:** ui/display.py draws the 800x600 frame in a GPU window, sharp ("sharp bilinear": whole-number
  nearest scaling, then linear to fit) or smooth, 4:3 with borders; window sized to about 85% of the
  desktop and remembered; starts full screen by default; F11 / Alt+Enter switch it.
- **Modern:** Options > Settings, a page built like the Options dialog (700.RIM, its switches): Full
  screen, Sharp scaling, Check for updates (all apply at once and are saved), and Game files.
- Gallery (600, gallery.rtf): type buttons 650-661 (command 650), list 601 of the type's puzzles with your
  best time beside the best time ever on this computer (with who set it) or another player's; the arrow
  (606, command 605) switches. Times are recorded when a puzzle is solved without a Free token
  (Player.best, game/besttimes.py in the data folder; the original's DATA/BESTTIME.DAT only holds three
  leftover test entries and is never written). **Interpretation:** row layout; a puzzle is listed when
  either column has a time.
- Success box (130, successdlg.bmp): shown over the solved puzzle. View (result 1) closes it and leaves
  the finished puzzle on screen until a click, key or Back; Continue (result 0) goes straight on. Either
  way the rewards and next steps follow. **Interpretation:** the "Click to continue" caption.

### Tutorial instructions (ui/tutorial.py)
The practice puzzles (LEVEL.0, via Tutorial) show the original's step texts, one LANGENU block per type
(Image Hole 2053-2057, Focus Point 3313-3316, Rotascope 4308-4311, Overlap 5414-5419, Outer Layer
6208-6212, Jesse's Strips 8007-8015, Slices 10900-10905, Lens Bender 11950-11954, Interlock 12900-12903,
Find and Fill 13126-13130). The original draws them in a text bubble (0x46fe90 / 0x46ff10) and advances
from inside each puzzle; here a step ends when the puzzle reports the action it asks for (puzzle sounds
are events via PuzzleGame.emit, plus Outer Layer's view/place/stack/rotate and Jesse's move_tray), and
Jesse's "press 4" steps wait for that tray. Image Hole's strike text 2057 shows after a strike.
**Interpretation:** the triggers, and the panel at the bottom of the play area with back/next/close.
Jesse's Strips opens on the last tray with strips (the tutorial's "then return to tray 5"; campaign
puzzles leave tray 1 empty).

### Speed puzzles (TIME.<n>.<secs>, one per campaign city)
Opening one shows LANGENU 1035 ("To earn a bonus, solve this speed puzzle in under %s. If you use a Hint
or Free Puzzle token, you will not receive a bonus."); the timer counts down. Solved within the limit
without a Hint or Free token (and for the first time), the bonus (0x403fe9) is: if the city's piece is
neither found nor already shown, the city is marked revealed (player set at +0xdd8) and 1036 says the
hidden object's location is shown on a puzzle button; otherwise Free Puzzle tokens (+0xee8) and 1037
("three Free Puzzle tokens"). **Interpretation:** the revealed marker (the city's piece icon as a badge
on the piece puzzle's button), and three tokens as 1037 says (only one increment was traced).

### Story book (screen 250, button 53)
Each level's story is five pages, LANGENU 1900 + 10 * level + page (1911-1975), read aloud by
VO/SX_<trickster><page>.WAV (PANDORA.MGD "Story" event: Piece=n plays StoryVOColl n). Page 1 opens the
level and names the first piece to find; page n+1 follows the nth piece found. Screen 250 is code-drawn
on 250.RIM (an open book) with buttons 252/253 (page back/on) and 251 (close); the Story button 53
(53u/53d, top bar at 542,4) is added in code (the main menu setup at 0x41ab10 places it too). The book
opens at the level's start (page 1) and after each found piece (the next page), then the piece message.
**Interpretation:** the text on the blank right page, the painted corner arrows also turning pages,
pages limited to those unlocked, and the book on the map and city screens (not the main menu).
The remaster used to play voice-over n after the nth piece, one page behind; fixed.

### Trickster portraits on the world map
The map setup (0x41f180) puts seven 64x64 portraits in the dark strip across the top of 400.RIM, from a
static table at 0x5ba798 (0x24 bytes per trickster: images 44xU, 44xD, the shared 440UA mask, and a
rect; left 7 + 73k, top 63). Levels before the current one show 44xS (gold frame: captured); the
current trickster is a button (44xU / 44xD, the 68x68 440UA alpha mask giving its frame shadow) that
opens the Challenge box (STATENU 1720 "Click the box to see your progress."); later ones show 447.RIM,
an empty frame. Names LANGENU 430-436. **Interpretation:** the hover caption, and the remaster's
"Level n - Capture X" title moved beside WORLD MAP so the row is clear.

