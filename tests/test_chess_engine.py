import unittest

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


class TestMakeUnmakeMove(unittest.TestCase):
    def setUp(self):
        self.board = Bitboard()

    def assert_round_trip(self, move):
        """make_move followed by unmake_move must restore the exact prior state."""
        before = snapshot(self.board)
        history_depth_before = len(self.board.history)

        self.board.make_move(move)
        self.board.unmake_move(move)

        after = snapshot(self.board)
        self.assertEqual(before, after, f"State mismatch after make/unmake of {move}")
        self.assertEqual(len(self.board.history), history_depth_before,
                          "history stack is not balanced after make/unmake")

    def test_quiet_knight_move_updates_bitboard(self):
        move = Move(from_sq=1, to_sq=18, piece='wn')  # Nb1-c3
        before_wn = self.board.wn

        self.board.make_move(move)
        self.assertEqual(self.board.wn, (before_wn & ~(1 << 1)) | (1 << 18))
        self.assertFalse(self.board.side_to_move)  # turn passed to black

        self.board.unmake_move(move)

    def test_quiet_knight_move_round_trip(self):
        move = Move(from_sq=1, to_sq=18, piece='wn')  # Nb1-c3
        self.assert_round_trip(move)

    def test_pawn_double_push_round_trip(self):
        move = Move(from_sq=12, to_sq=28, piece='wp', is_double_push=True)  # e2-e4
        self.assert_round_trip(move)

    def test_capture_removes_captured_piece(self):
        # White rook on d4 (27), black knight on d5 (35)
        self.board.wr = 1 << 27
        self.board.bn = 1 << 35
        move = Move(from_sq=27, to_sq=35, piece='wr', captured_piece='bn')

        self.board.make_move(move)
        self.assertEqual(self.board.wr, 1 << 35)
        self.assertEqual(self.board.bn, 0)

        self.board.unmake_move(move)
        self.assertEqual(self.board.wr, 1 << 27)
        self.assertEqual(self.board.bn, 1 << 35)

    def test_capture_round_trip(self):
        self.board.wr = 1 << 27
        self.board.bn = 1 << 35
        move = Move(from_sq=27, to_sq=35, piece='wr', captured_piece='bn')
        self.assert_round_trip(move)

    def test_promotion_replaces_pawn_with_promoted_piece(self):
        self.board.wp = 1 << 48  # a7
        self.board.wq = 0  # isolate: ignore the queen already on d1 at game start
        move = Move(from_sq=48, to_sq=56, piece='wp', promotion_piece='wq')  # a7-a8=Q

        self.board.make_move(move)
        self.assertEqual(self.board.wp, 0)
        self.assertEqual(self.board.wq, 1 << 56)

        self.board.unmake_move(move)
        self.assertEqual(self.board.wp, 1 << 48)
        self.assertEqual(self.board.wq, 0)

    def test_promotion_round_trip(self):
        self.board.wp = 1 << 48
        move = Move(from_sq=48, to_sq=56, piece='wp', promotion_piece='wq')
        self.assert_round_trip(move)

    def test_promotion_with_capture_round_trip(self):
        self.board.wp = 1 << 52  # e7
        self.board.br = 1 << 61  # f8 rook, to be captured on promotion
        move = Move(from_sq=52, to_sq=61, piece='wp', captured_piece='br', promotion_piece='wq')
        self.assert_round_trip(move)

    def test_en_passant_capture_removes_correct_pawn(self):
        # White pawn on e5 (36); black pawn just double-pushed to d5 (35).
        # En passant target square is d6 (43) - the square the black pawn "skipped".
        self.board.wp = 1 << 36
        self.board.bp = 1 << 35
        self.board.en_passant_square = 43
        move = Move(from_sq=36, to_sq=43, piece='wp', captured_piece='bp', is_en_passant=True)

        self.board.make_move(move)
        self.assertEqual(self.board.wp, 1 << 43)
        self.assertEqual(self.board.bp, 0, "captured pawn must be removed from square 35, not 43")

        self.board.unmake_move(move)
        self.assertEqual(self.board.wp, 1 << 36)
        self.assertEqual(self.board.bp, 1 << 35)

    def test_en_passant_round_trip(self):
        self.board.wp = 1 << 36
        self.board.bp = 1 << 35
        self.board.en_passant_square = 43
        move = Move(from_sq=36, to_sq=43, piece='wp', captured_piece='bp', is_en_passant=True)
        self.assert_round_trip(move)

    def test_generator_round_trip_from_start_position(self):
        """
        Every pseudo-legal move for white from the starting position must be
        perfectly reversible - this exercises the generator and make/unmake together.
        """
        original = snapshot(self.board)
        moves = self.board.generate_pseudo_legal_moves(is_white=True)
        self.assertTrue(len(moves) > 0)

        for move in moves:
            self.board.make_move(move)
            self.board.unmake_move(move)
            self.assertEqual(snapshot(self.board), original,
                              f"round trip failed for generated move {move}")


if __name__ == '__main__':
    unittest.main()
