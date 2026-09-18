import pytest

from chess_engine import Bitboard
from move import Move


def snapshot(board):
    """Captures every piece of mutable state make/unmake is responsible for."""
    return {
        'wp': board.wp, 'wn': board.wn, 'wb': board.wb,
        'wr': board.wr, 'wq': board.wq, 'wk': board.wk,
        'bp': board.bp, 'bn': board.bn, 'bb': board.bb,
        'br': board.br, 'bq': board.bq, 'bk': board.bk,
        'side_to_move': board.side_to_move,
        'castling_rights': dict(board.castling_rights),
        'en_passant_square': board.en_passant_square,
        'halfmove_clock': board.halfmove_clock,
    }


def assert_round_trip(board, move):
    """make_move followed by unmake_move must restore the exact prior state."""
    before = snapshot(board)
    history_depth_before = len(board.history)

    board.make_move(move)
    board.unmake_move(move)

    after = snapshot(board)
    assert before == after, f"State mismatch after make/unmake of {move}"
    assert len(board.history) == history_depth_before, "history stack is not balanced after make/unmake"


@pytest.fixture
def board():
    return Bitboard()


def test_quiet_knight_move_updates_bitboard(board):
    move = Move(from_sq=1, to_sq=18, piece='wn')  # Nb1-c3
    before_wn = board.wn

    board.make_move(move)
    assert board.wn == (before_wn & ~(1 << 1)) | (1 << 18)
    assert not board.side_to_move  # turn passed to black

    board.unmake_move(move)


def test_quiet_knight_move_round_trip(board):
    move = Move(from_sq=1, to_sq=18, piece='wn')  # Nb1-c3
    assert_round_trip(board, move)


def test_pawn_double_push_round_trip(board):
    move = Move(from_sq=12, to_sq=28, piece='wp', is_double_push=True)  # e2-e4
    assert_round_trip(board, move)


def test_capture_removes_captured_piece(board):
    # White rook on d4 (27), black knight on d5 (35)
    board.wr = 1 << 27
    board.bn = 1 << 35
    move = Move(from_sq=27, to_sq=35, piece='wr', captured_piece='bn')

    board.make_move(move)
    assert board.wr == 1 << 35
    assert board.bn == 0

    board.unmake_move(move)
    assert board.wr == 1 << 27
    assert board.bn == 1 << 35


def test_capture_round_trip(board):
    board.wr = 1 << 27
    board.bn = 1 << 35
    move = Move(from_sq=27, to_sq=35, piece='wr', captured_piece='bn')
    assert_round_trip(board, move)


def test_promotion_replaces_pawn_with_promoted_piece(board):
    board.wp = 1 << 48  # a7
    board.wq = 0  # isolate: ignore the queen already on d1 at game start
    move = Move(from_sq=48, to_sq=56, piece='wp', promotion_piece='wq')  # a7-a8=Q

    board.make_move(move)
    assert board.wp == 0
    assert board.wq == 1 << 56

    board.unmake_move(move)
    assert board.wp == 1 << 48
    assert board.wq == 0


def test_promotion_round_trip(board):
    board.wp = 1 << 48
    move = Move(from_sq=48, to_sq=56, piece='wp', promotion_piece='wq')
    assert_round_trip(board, move)


def test_promotion_with_capture_round_trip(board):
    board.wp = 1 << 52  # e7
    board.br = 1 << 61  # f8 rook, to be captured on promotion
    move = Move(from_sq=52, to_sq=61, piece='wp', captured_piece='br', promotion_piece='wq')
    assert_round_trip(board, move)


def test_en_passant_capture_removes_correct_pawn(board):
    # White pawn on e5 (36); black pawn just double-pushed to d5 (35).
    # En passant target square is d6 (43) - the square the black pawn "skipped".
    board.wp = 1 << 36
    board.bp = 1 << 35
    board.en_passant_square = 43
    move = Move(from_sq=36, to_sq=43, piece='wp', captured_piece='bp', is_en_passant=True)

    board.make_move(move)
    assert board.wp == 1 << 43
    assert board.bp == 0, "captured pawn must be removed from square 35, not 43"

    board.unmake_move(move)
    assert board.wp == 1 << 36
    assert board.bp == 1 << 35


def test_en_passant_round_trip(board):
    board.wp = 1 << 36
    board.bp = 1 << 35
    board.en_passant_square = 43
    move = Move(from_sq=36, to_sq=43, piece='wp', captured_piece='bp', is_en_passant=True)
    assert_round_trip(board, move)


def test_generator_round_trip_from_start_position(board):
    """
    Every pseudo-legal move for white from the starting position must be
    perfectly reversible - this exercises the generator and make/unmake together.
    """
    original = snapshot(board)
    moves = board.generate_pseudo_legal_moves(is_white=True)
    assert len(moves) > 0

    for move in moves:
        board.make_move(move)
        board.unmake_move(move)
        assert snapshot(board) == original, f"round trip failed for generated move {move}"
