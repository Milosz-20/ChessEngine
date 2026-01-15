import unittest
from chess_engine import Bitboard  # Assuming your file is named chess_engine.py


class TestKnightMoves(unittest.TestCase):

    def setUp(self):
        self.board = Bitboard()
        # Clear the board for easier testing (remove default pieces)
        self.board.wp = 0
        self.board.wn = 0
        self.board.wb = 0
        self.board.wr = 0
        self.board.wq = 0
        self.board.wk = 0
        self.board.bp = 0
        self.board.bn = 0
        self.board.bb = 0
        self.board.br = 0
        self.board.bq = 0
        self.board.bk = 0

    def test_knight_center_empty_board(self):
        # Place Knight on d4 (index 27)
        # d4 is Rank 4 (index 3), File d (index 3) -> 3*8 + 3 = 27
        # Moves should be: c2, e2, b3, f3, b5, f5, c6, e6
        self.board.wn = (1 << 27)

        moves = self.board.get_knight_moves(27, is_white=True)

        # Count set bits (population count)
        count = bin(moves).count('1')
        self.assertEqual(count, 8, "Knight on d4 should have 8 moves on empty board")

    def test_knight_corner_a1(self):
        # Place Knight on a1 (index 0)
        # Moves should be: b3 (index 17), c2 (index 10)
        self.board.wn = (1 << 0)

        moves = self.board.get_knight_moves(0, is_white=True)

        expected_mask = (1 << 17) | (1 << 10)
        self.assertEqual(moves, expected_mask, "Knight on a1 should only move to b3 and c2")

    def test_knight_friendly_block(self):
        # Knight on d4 (27)
        # Friendly Pawn on e6 (44) -> This is normally a valid move (d4 -> e6)

        self.board.wn = (1 << 27)
        self.board.wp = (1 << 44)  # Block e6

        moves = self.board.get_knight_moves(27, is_white=True)

        # Check if bit 44 is set in moves (it should NOT be)
        is_e6_allowed = (moves >> 44) & 1
        self.assertEqual(is_e6_allowed, 0, "Knight should not capture friendly piece on e6")

        # We expect 7 moves now (8 total - 1 blocked)
        self.assertEqual(bin(moves).count('1'), 7)

    def test_knight_enemy_capture(self):
        # Knight on d4 (27)
        # Enemy Pawn on e6 (44) -> Should be a valid capture

        self.board.wn = (1 << 27)
        self.board.bp = (1 << 44)  # Enemy on e6

        moves = self.board.get_knight_moves(27, is_white=True)

        # Check if bit 44 is set (it SHOULD be)
        is_e6_allowed = (moves >> 44) & 1
        self.assertEqual(is_e6_allowed, 1, "Knight should be able to capture enemy on e6")


class TestKingMoves(unittest.TestCase):

    def setUp(self):
        self.board = Bitboard()
        # Clear the board
        self.board.wp = 0
        self.board.wn = 0
        self.board.wb = 0
        self.board.wr = 0
        self.board.wq = 0
        self.board.wk = 0
        self.board.bp = 0
        self.board.bn = 0
        self.board.bb = 0
        self.board.br = 0
        self.board.bq = 0
        self.board.bk = 0

    def test_king_center_empty_board(self):
        # Place King on e4 (index 36)
        self.board.wk = (1 << 36)

        moves = self.board.get_king_moves(36, is_white=True)

        # Count set bits (population count)
        count = bin(moves).count('1')
        self.assertEqual(count, 8, "King on e4 should have 8 moves on empty board")

    def test_king_corner_h8(self):
        # Place King on h8 (index 63)
        # Moves should be: g8 (62), g7 (54), h7 (55)
        self.board.wk = (1 << 63)

        moves = self.board.get_king_moves(63, is_white=True)

        expected_mask = (1 << 62) | (1 << 54) | (1 << 55)
        self.assertEqual(moves, expected_mask, "King on h8 should only have 3 moves")
        self.assertEqual(bin(moves).count('1'), 3)


class TestInputValidation(unittest.TestCase):

    def setUp(self):
        self.board = Bitboard()

    def test_knight_invalid_square_negative(self):
        with self.assertRaises(ValueError):
            self.board.get_knight_moves(-1, is_white=True)

    def test_knight_invalid_square_too_large(self):
        with self.assertRaises(ValueError):
            self.board.get_knight_moves(64, is_white=True)

    def test_king_invalid_square_negative(self):
        with self.assertRaises(ValueError):
            self.board.get_king_moves(-1, is_white=True)

    def test_king_invalid_square_too_large(self):
        with self.assertRaises(ValueError):
            self.board.get_king_moves(64, is_white=True)


if __name__ == '__main__':
    unittest.main()