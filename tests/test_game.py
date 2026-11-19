import pytest

from game import (Game, IllegalMove, START_FEN, WHITE_WINS, BLACK_WINS, DRAW, CHECKMATE,
                  STALEMATE, REPETITION, FIFTY_MOVES, INSUFFICIENT, build_pgn)


def play(game, *ucis):
    return [game.push_uci(u) for u in ucis]


def test_start_position_fen_round_trip():
    game = Game()
    assert game.fen() == START_FEN
    assert len(game.legal_uci_moves()) == 20


@pytest.mark.parametrize("fen", [
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
])
def test_fen_export_matches_loaded_fen(fen):
    assert Game(fen).fen() == fen


def test_fen_after_double_push_has_en_passant_square():
    game = Game()
    play(game, "e2e4")
    assert game.fen() == "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"


def test_illegal_and_malformed_moves_rejected():
    game = Game()
    for bad in ["e2e5", "e7e5", "zz", "e2e4q", None, "i9i9"]:
        with pytest.raises(IllegalMove):
            game.push_uci(bad)
    assert game.uci_moves == []


def test_fools_mate():
    game = Game()
    sans = play(game, "f2f3", "e7e5", "g2g4", "d8h4")
    assert sans == ["f3", "e5", "g4", "Qh4#"]
    assert game.outcome() == (BLACK_WINS, CHECKMATE)


def test_scholars_mate_white_wins():
    game = Game()
    play(game, "e2e4", "e7e5", "f1c4", "b8c6", "d1h5", "g8f6", "h5f7")
    assert game.san_moves[-1] == "Qxf7#"
    assert game.outcome() == (WHITE_WINS, CHECKMATE)


def test_stalemate():
    game = Game("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    assert game.outcome() == (DRAW, STALEMATE)


def test_threefold_repetition():
    game = Game()
    play(game, "g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1")
    assert game.outcome() is None
    play(game, "f6g8")
    assert game.outcome() == (DRAW, REPETITION)


def test_fifty_move_rule():
    game = Game("7k/8/8/8/8/8/8/R6K w - - 99 80")
    assert game.outcome() is None
    play(game, "a1a2")
    assert game.outcome() == (DRAW, FIFTY_MOVES)


@pytest.mark.parametrize("fen, expected", [
    ("7k/8/8/8/8/8/8/7K w - - 0 1", True),               # K v K
    ("7k/8/8/8/8/8/8/6NK w - - 0 1", True),              # K+N v K
    ("7k/8/8/8/8/8/8/6BK w - - 0 1", True),              # K+B v K
    ("6bk/8/8/8/8/8/8/5B1K w - - 0 1", True),            # bishops on same colour
    ("5b1k/8/8/8/8/8/8/5B1K w - - 0 1", False),          # bishops on opposite colours
    ("7k/8/8/8/8/8/8/5NNK w - - 0 1", False),
    ("7k/8/8/8/8/8/P7/7K w - - 0 1", False),
])
def test_insufficient_material(fen, expected):
    assert Game(fen).insufficient_material() is expected


def test_capture_into_insufficient_material_ends_game():
    game = Game("7k/8/8/8/8/8/8/r6K w - - 0 1")
    assert game.outcome() is None
    game = Game("7k/8/8/8/8/8/6r1/7K w - - 0 1")
    play(game, "h1g2")
    assert game.outcome() == (DRAW, INSUFFICIENT)


def test_san_castling_promotion_en_passant():
    game = Game("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    assert play(game, "e1g1", "e8c8") == ["O-O", "O-O-O"]

    game = Game("8/P6k/8/8/8/8/8/K7 w - - 0 1")
    assert play(game, "a7a8n") == ["a8=N"]

    game = Game("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    assert play(game, "e5d6") == ["exd6"]


def test_san_disambiguation():
    game = Game("4k3/8/8/8/8/8/8/N3K2N w - - 0 1")  # knights on a1 and h1 can't both reach
    assert game.san(game.parse_uci("a1b3")) == "Nb3"
    game = Game("4k3/8/8/8/8/8/8/1N1NK3 w - - 0 1")  # knights b1, d1 both reach c3
    assert game.san(game.parse_uci("b1c3")) == "Nbc3"
    game = Game("4k3/8/8/8/R7/8/8/R3K3 w - - 0 1")   # rooks a1, a4 both reach a2
    assert game.san(game.parse_uci("a4a2")) == "R4a2"


def test_promotion_requires_piece_choice():
    game = Game("8/P6k/8/8/8/8/8/K7 w - - 0 1")
    with pytest.raises(IllegalMove):
        game.push_uci("a7a8")
    assert "a7a8q" in game.legal_uci_moves()


def test_replay_from_uci_moves():
    game = Game.from_uci_moves(["e2e4", "c7c5", "g1f3"])
    assert game.san_moves == ["e4", "c5", "Nf3"]
    assert len(game.fens) == 4
    assert not game.white_to_move


def test_can_mate_for_timeout():
    assert not Game("7k/8/8/8/8/8/8/7K w - - 0 1").can_mate(True)
    assert not Game("7k/8/8/8/8/8/8/6NK w - - 0 1").can_mate(True)
    assert Game("7k/7p/8/8/8/8/8/6NK w - - 0 1").can_mate(True)
    assert Game("7k/8/8/8/8/8/8/6QK w - - 0 1").can_mate(True)


def test_pgn():
    pgn = build_pgn({"White": "a", "Black": "b", "Result": "0-1"}, ["f3", "e5", "g4", "Qh4#"], "0-1")
    assert pgn == '[White "a"]\n[Black "b"]\n[Result "0-1"]\n\n1. f3 e5 2. g4 Qh4# 0-1\n'
