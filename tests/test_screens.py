from pbremaster.data import screens
from pbremaster.data.rof import ROF


def _layout(game):
    return screens.parse(ROF(game.file("SCREENS.ROF")).read("SCREENS/SCREEN.DAT"))


def test_screen_dat_parses_exactly(game):
    layout = _layout(game)
    assert len(layout.screens) == 39
    assert len(layout.controls) == 332


def test_main_menu(game):
    layout = _layout(game)
    main = layout.screens[100]
    assert main.background == "100.bmp" and main.help_rtf == "mainqh.rtf"
    play = layout.controls[101]
    assert isinstance(play, screens.Button)
    assert play.pos == (536, 263) and play.label_id == 101
    assert play.images == ["103u.bmp", "103d.bmp", "103uh.bmp", "103dh.bmp"]
    assert (play.action, play.arg) == (screens.ACT_COMMAND, 101)
    assert screens.rim_name(play.images[0]) == "SCREENS/103U.RIM"


def test_controls(game):
    layout = _layout(game)
    cancel = layout.controls[705]
    assert cancel.strip and (cancel.action, cancel.arg) == (screens.ACT_END_DIALOG, 2)
    title = layout.controls[454]
    assert isinstance(title, screens.Label)
    assert (title.string_id, title.size, title.align, title.color) == (454, 26, 0, (248, 176, 100))
    radio = layout.controls[150]
    assert radio.style == screens.STYLE_RADIO and len(radio.group) == 12
