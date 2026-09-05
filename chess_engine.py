import json
import os
from helpers import _init_knight_moves, _init_king_moves, _init_white_pawn_attacks, _init_black_pawn_attacks, \
    count_bits, generate_occupancy_variations, FULL_BOARD_MASK, RANK_2, RANK_7, \
    rook_attacks_on_the_fly, bishop_attacks_on_the_fly

# Initialize move tables once at module level for better performance
KNIGHT_MOVES_TABLE = _init_knight_moves()
KING_MOVES_TABLE = _init_king_moves()
WHITE_PAWN_ATTACKS_TABLE = _init_white_pawn_attacks()
BLACK_PAWN_ATTACKS_TABLE = _init_black_pawn_attacks()

class MagicManager:
    def __init__(self):
        self.rook_table = [None] * 64
        self.bishop_table = [None] * 64
        self.rook_magics = []
        self.bishop_magics = []

        if not os.path.exists("magic_numbers.json"):
            raise FileNotFoundError("Run generate_magics.py first!")

        print("Loading Magic Numbers...")
        with open("magic_numbers.json", 'r') as f:
            data = json.load(f)
            self.rook_magics = data["rook"]
            self.bishop_magics = data["bishop"]

        # 3. Initialize the lookup tables
        self._init_attacks_tables()

    def _init_attacks_tables(self):
        for sq in range(64):
            # Init Rook Table
            entry = self.rook_magics[sq]
            size = 1 << count_bits(entry["mask"])
            self.rook_table[sq] = [0] * size
            for occ in generate_occupancy_variations(entry["mask"]):
                idx = (occ * entry["magic"]) & FULL_BOARD_MASK
                idx >>= entry["shift"]
                self.rook_table[sq][idx] = rook_attacks_on_the_fly(sq, occ)

            # Init Bishop Table
            entry = self.bishop_magics[sq]
            size = 1 << count_bits(entry["mask"])
            self.bishop_table[sq] = [0] * size
            for occ in generate_occupancy_variations(entry["mask"]):
                idx = (occ * entry["magic"]) & FULL_BOARD_MASK
                idx >>= entry["shift"]
                self.bishop_table[sq][idx] = bishop_attacks_on_the_fly(sq, occ)

    def get_rook_attacks(self, square, occupancy):
        entry = self.rook_magics[square]
        idx = ((occupancy & entry["mask"]) * entry["magic"]) & FULL_BOARD_MASK
        return self.rook_table[square][idx >> entry["shift"]]

    def get_bishop_attacks(self, square, occupancy):
        entry = self.bishop_magics[square]
        idx = ((occupancy & entry["mask"]) * entry["magic"]) & FULL_BOARD_MASK
        return self.bishop_table[square][idx >> entry["shift"]]

class Bitboard:
    def __init__(self):
        self.wp = 0x000000000000FF00  # White Pawns
        self.wn = 0x0000000000000042  # White Knights
        self.wb = 0x0000000000000024  # White Bishops
        self.wr = 0x0000000000000081  # White Rooks
        self.wq = 0x0000000000000008  # White Queen
        self.wk = 0x0000000000000010  # White King

        self.bp = 0x00FF000000000000  # Black Pawns
        self.bn = 0x4200000000000000  # Black Knights
        self.bb = 0x2400000000000000  # Black Bishops
        self.br = 0x8100000000000000  # Black Rooks
        self.bq = 0x0800000000000000  # Black Queen
        self.bk = 0x1000000000000000  # Black King

        # Reference to pre-calculated move tables
        self.knight_table = KNIGHT_MOVES_TABLE
        self.king_table = KING_MOVES_TABLE
        self.white_pawn_attacks = WHITE_PAWN_ATTACKS_TABLE
        self.black_pawn_attacks = BLACK_PAWN_ATTACKS_TABLE

        self.magics = MagicManager()

    def get_occupancy(self, is_white):
        """
        Get bitboard of all pieces for a given color.

        Args:
            is_white: True for white pieces, False for black pieces

        Returns:
            int: Bitboard with all pieces of the specified color
        """
        if is_white:
            return self.wp | self.wn | self.wb | self.wr | self.wq | self.wk
        else:
            return self.bp | self.bn | self.bb | self.br | self.bq | self.bk

    def get_knight_moves(self, square, is_white):
        """
        Get valid knight moves from a given square.

        Args:
            square: Square index (0-63)
            is_white: True for white pieces, False for black

        Returns:
            int: Bitboard of valid knight moves

        Raises:
            ValueError: If square is out of range [0-63]
        """
        if not 0 <= square < 64:
            raise ValueError(f"Square {square} out of range [0-63]")

        possible_moves = self.knight_table[square]
        own_pieces = self.get_occupancy(is_white)
        valid_moves = possible_moves & ~own_pieces
        return valid_moves

    def get_king_moves(self, square, is_white):
        """
        Get valid king moves from a given square.

        Args:
            square: Square index (0-63)
            is_white: True for white pieces, False for black

        Returns:
            int: Bitboard of valid king moves

        Raises:
            ValueError: If square is out of range [0-63]
        """
        if not 0 <= square < 64:
            raise ValueError(f"Square {square} out of range [0-63]")

        possible_moves = self.king_table[square]
        own_pieces = self.get_occupancy(is_white)
        valid_moves = possible_moves & ~own_pieces
        return valid_moves

    def get_queen_moves(self, square, is_white):
        """
        Get valid queen moves from a given square: combines rook and
        bishop attacks (queen moves like both combined).

        Args:
            square: Square index (0-63)
            is_white: True for white pieces, False for black

        Returns:
            int: Bitboard of valid queen moves

        Raises:
            ValueError: If square is out of range [0-63]
        """
        if not 0 <= square < 64:
            raise ValueError(f"Square {square} out of range [0-63]")

        all_occupancy = self.get_occupancy(True) | self.get_occupancy(False)
        own_pieces = self.get_occupancy(is_white)

        rook_moves = self.magics.get_rook_attacks(square, all_occupancy)
        bishop_moves = self.magics.get_bishop_attacks(square, all_occupancy)

        possible_moves = rook_moves | bishop_moves
        valid_moves = possible_moves & ~own_pieces
        return valid_moves

    def get_pawn_moves(self, square, is_white):
        """
        Get valid pawn moves from a given square: single/double push and
        diagonal captures. Does not account for promotion or en passant.
        """

        if not 0 <= square < 64:
            raise ValueError(f"Square {square} out of range [0-63]")

        all_occupancy = self.get_occupancy(True) | self.get_occupancy(False)
        enemy_occupancy = self.get_occupancy(not is_white)

        moves = 0

        if is_white:
            single_push = (1 << (square + 8)) if square + 8 < 64 else 0
            single_push &= ~all_occupancy
            moves |= single_push

            if single_push and ((1 << square) & RANK_2):
                double_push = (1 << (square + 16)) & ~all_occupancy
                moves |= double_push

            moves |= self.white_pawn_attacks[square] & enemy_occupancy

        else:
            single_push = (1 << (square - 8)) if square - 8 >= 0 else 0
            single_push &= ~all_occupancy
            moves |= single_push

            if single_push and ((1 << square) & RANK_7):
                double_push = (1 << (square - 16)) & ~all_occupancy
                moves |= double_push

            moves |= self.black_pawn_attacks[square] & enemy_occupancy
        return moves
    
    def print_bitboard(self, bitboard):
        """
        Display a bitboard in a visual chess board format.

        Args:
            bitboard: Bitboard to display (64-bit integer)
        """
        for r in range(7, -1, -1):
            line = f"{r+1} "
            for f in range(8):
                idx = r*8 + f
                if (bitboard >> idx) & 1:
                    line += "X "
                else:
                    line += ". "
            print(line)
        print('  a b c d e f g h')

    def print_full_board(self):
        """
        Display the complete chess board with all pieces.

        White pieces: P (pawn), N (knight), B (bishop), R (rook), Q (queen), K (king)
        Black pieces: p, n, b, r, q, k (lowercase)
        Empty squares: .
        """
        piece_map = {
            'P': self.wp, 'N': self.wn, 'B': self.wb, 'R': self.wr, 'Q': self.wq, 'K': self.wk,
            'p': self.bp, 'n': self.bn, 'b': self.bb, 'r': self.br, 'q': self.bq, 'k': self.bk
        }

        board_output = "\n"
        for rank in range(7, -1, -1):
            board_output += f'{rank + 1} '
            for file in range(8):
                square = rank * 8 + file
                piece_found = "."

                for symbol, bb in piece_map.items():
                    if (bb >> square) & 1:
                        piece_found = symbol
                        break
                board_output += piece_found + " "
            board_output += f'\n'
        board_output += '  a b c d e f g h'
        print(board_output)
