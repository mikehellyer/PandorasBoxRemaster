from pbremaster.data import catalogue
from pbremaster.data.rof import ROF
from pbremaster.game.progress import Player


def _levels(game):
    return catalogue.load(ROF(game.file("PANDORA.ROF")))


def test_rewards_and_piece(game, tmp_path):
    levels = _levels(game)
    lv = levels[1]
    cairo = lv.cities["CITY.06.CAIRO"]
    p = Player("Tester")
    assert p.solve(cairo, cairo.puzzles[3]) == ["hint"]           # HINT.3
    assert p.hints == 1
    events = p.solve(cairo, cairo.puzzles[4])                       # PIECE.4
    assert events == ["piece"] and p.pieces == [cairo.path]
    for n in cairo.puzzles:
        p.solve(cairo, cairo.puzzles[n])
    assert p.total_solved == 10 and p.free >= 1 and p.toward_token == 0
    p.save(tmp_path)
    q = Player.load("Tester", tmp_path)
    assert q == p


def test_five_pieces_open_the_challenge(game):
    lv = _levels(game)[1]
    p = Player("T")
    events = []
    for city in lv.cities.values():
        piece = next(x for x in city.puzzles.values() if x.piece)
        events = p.solve(city, piece)
    assert events[-1] == "challenge"
    for pz in lv.puzzles.values():
        ev = p.solve_master(lv, pz)
    assert ev == ["captured"] and p.captured == [1]
