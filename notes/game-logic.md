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
