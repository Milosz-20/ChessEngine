# Constant helpers (files)
# 0x0101010101010101 is a vertical line at file A
FILE_A = 0x0101010101010101
FILE_B = FILE_A << 1
FILE_G = FILE_A << 6
FILE_H = FILE_A << 7

# Full board mask (all 64 bits set)
FULL_BOARD_MASK = 0xFFFFFFFFFFFFFFFF

# Combined masks (needed for knights)
# Knight moving two tiles to the left cannot stand on either A or B
NOT_FILE_A = ~FILE_A & FULL_BOARD_MASK
NOT_FILE_B = ~FILE_B & FULL_BOARD_MASK
NOT_FILE_G = ~FILE_G & FULL_BOARD_MASK
NOT_FILE_H = ~FILE_H & FULL_BOARD_MASK

NOT_FILE_AB = NOT_FILE_A & NOT_FILE_B
NOT_FILE_GH = NOT_FILE_G & NOT_FILE_H

NORTH = 8
NORTH_EAST = 9
EAST = 1
SOUTH_EAST = -7
SOUTH = -8
SOUTH_WEST = -9
WEST = -1
NORTH_WEST = 7

def _init_king_moves():
    """
    Initialize lookup table for king moves from all 64 squares.

    King can move one square in any direction (8 possible moves).
    Moves are restricted by board edges and file boundaries.

    Returns:
        list: List of 64 integers (bitboards), where each represents
              all possible king moves from that square index.
    """
    moves_list = [0] * 64

    for square in range(64):
        moves = 0
        position = 1 << square

        # 1. North
        target = square + NORTH
        if 0 <= target < 64: moves |= (1 << target)

        # 2. East + diagonals
        if position & NOT_FILE_H:
            target = square + NORTH_EAST
            if 0 <= target < 64: moves |= (1 << target)

            target = square + EAST
            if 0 <= target < 64: moves |= (1 << target)

            target = square + SOUTH_EAST
            if 0 <= target < 64: moves |= (1 << target)

        # 3. South
        target = square + SOUTH
        if 0 <= target < 64: moves |= (1 << target)

        # 4. West + diagonals
        if position & NOT_FILE_A:
            target = square + SOUTH_WEST
            if 0 <= target < 64: moves |= (1 << target)

            target = square + WEST
            if 0 <= target < 64: moves |= (1 << target)

            target = square + NORTH_WEST
            if 0 <= target < 64: moves |= (1 << target)

        moves_list[square] = moves
    return moves_list

def _init_knight_moves():
    """
    Initialize lookup table for knight moves from all 64 squares.

    Knight moves in an L-shape: 2 squares in one direction and 1 square
    perpendicular (8 possible moves). Moves are restricted by board edges
    and file boundaries.

    Returns:
        list: List of 64 integers (bitboards), where each represents
              all possible knight moves from that square index.
    """
    moves_list = [0] * 64

    for square in range(64):
        moves = 0
        position = 1 << square  # Bitboard with only the knight on the specific square

        # 1. NORTH NORTH EAST
        target = square + 2*NORTH + EAST
        if 0 <= target < 64 and (position & NOT_FILE_H):
            moves |= (1 << target)

        # 2. NORTH NORTH WEST
        target = square + 2*NORTH + WEST
        if 0 <= target < 64 and (position & NOT_FILE_A):
            moves |= (1 << target)

        # 3. 'NORTH EAST EAST'
        target = square + NORTH + 2*EAST
        if 0 <= target < 64 and (position & NOT_FILE_GH):
            moves |= (1 << target)

        # 4. NORTH WEST WEST
        target = square + NORTH + 2*WEST
        if 0 <= target < 64 and (position & NOT_FILE_AB):
            moves |= (1 << target)

        # 5. SOUTH SOUTH EAST
        target = square + 2*SOUTH + EAST
        if 0 <= target < 64 and (position & NOT_FILE_H):
            moves |= (1 << target)

        # 6. SOUTH SOUTH WEST
        target = square + 2*SOUTH + WEST
        if 0 <= target < 64 and (position & NOT_FILE_A):
            moves |= (1 << target)

        # 7. SOUTH EAST EAST
        target = square + SOUTH + 2*EAST
        if 0 <= target < 64 and (position & NOT_FILE_GH):
            moves |= (1 << target)

        # 8. SOUTH WEST WEST
        target = square + SOUTH + 2*WEST
        if 0 <= target < 64 and (position & NOT_FILE_AB):
            moves |= (1 << target)

        moves_list[square] = moves

    return moves_list

def count_bits(bitboard):
    """
    Counts the number of set bits (1s) in a bitboard.

    Uses Brian Kernighan's algorithm to clear the least significant bit
    in each iteration, which is efficient for sparse bitboards.

    Args:
        bitboard: The integer (bitboard) to count bits in.

    Returns:
        int: The number of set bits.
    """
    count = 0
    while bitboard:
        count += 1
        bitboard &= bitboard - 1
    return count

def set_bit(bitboard, bit):
    """
    Sets the bit at the given index to 1 in the bitboard.

    How it works:
    1. (1 << bit) creates a mask with a single 1 at the specified index.
       e.g., if bit=2: 1 << 2 = 100 (binary)
    2. The bitwise OR (|) operator combines the bitboard with this mask.
       This ensures the bit at 'index' becomes 1, leaving others unchanged.

    Args:
        bitboard: The bitboard integer.
        bit: The index of the bit to set (0-63).

    Returns:
        int: The new bitboard with the bit set.
    """
    return bitboard | (1 << bit)

def get_rook_mask(square):
    """
    Generates a mask of relevant occupancy bits for a rook on the given square.

    This mask includes all squares that could potentially block a rook's movement,
    excluding the edges of the board. This is used for generating magic bitboards,
    where the occupancy of the edge squares does not affect the set of attacked squares
    behind them (since the piece stops at the edge anyway).

    Args:
        square: The square index (0-63) of the rook.

    Returns:
        int: Bitboard mask of relevant occupancy bits.
    """
    mask = 0
    rank, file = divmod(square, 8)

    # NORTH
    for r in range(rank + 1, 7): mask |= (1 << (r * 8 + file))

    # EAST
    for f in range(file + 1, 7): mask |= (1 << (rank * 8 + f))

    # SOUTH
    for r in range(rank - 1, 0, -1): mask |= (1 << (r * 8 + file))

    # WEST
    for f in range(file - 1, 0, -1): mask |= (1 << (rank * 8 + f))

    return mask

def get_bishop_mask(square):
    """
    Generates a mask of relevant occupancy bits for a bishop on the given square.

    Similar to get_rook_mask, this includes squares along the diagonals that could
    block the bishop, excluding the board edges. This reduced mask is used for
    magic bitboard table lookups to keep the table size manageable.

    Args:
        square: The square index (0-63) of the bishop.

    Returns:
        int: Bitboard mask of relevant occupancy bits.
    """
    mask = 0
    rank, file = divmod(square, 8)

    # NORTH-EAST
    r, f = rank + 1, file + 1
    while r < 7 and f < 7:
        mask |= (1 << (r * 8 + f))
        r += 1
        f += 1

    # SOUTH-EAST
    r, f = rank - 1, file + 1
    while r > 0 and f < 7:
        mask |= (1 << (r * 8 + f))
        r -= 1
        f += 1

    # SOUTH-WEST
    r, f = rank - 1, file - 1
    while r > 0 and f > 0:
        mask |= (1 << (r * 8 + f))
        r -= 1
        f -= 1

    # NORTH-WEST
    r, f = rank + 1, file -1
    while r < 7 and f > 0:
        mask |= (1 << (r * 8 + f))
        r += 1
        f -= 1

    return mask

def rook_attacks_on_the_fly(square, blockers):
    attacks = 0
    rank, file = divmod(square, 8)

    # NORTH
    for r in range(rank + 1, 8):
        target = r * 8 + file
        attacks |= (1 << target)
        if (1 << target) & blockers: break

    # EAST
    for f in range(file + 1, 8):
        target = rank * 8 + f
        attacks |= (1 << target)
        if (1 << target) & blockers: break

    # SOUTH
    for r in range(rank - 1, -1, -1):
        target = r * 8 + file
        attacks |= (1 << target)
        if (1 << target) & blockers: break

    # WEST
    for f in range(file - 1, -1, -1):
        target = rank * 8 + f
        attacks |= (1 << target)
        if (1 << target) & blockers: break

    return attacks

def bishop_attacks_on_the_fly(square, blockers):
    attacks = 0
    rank, file = divmod(square, 8)

    # NORTH-EAST
    r, f = rank + 1, file + 1
    while r < 8 and f < 8:
        target = r * 8 + f
        attacks |= (1 << target)
        if (1 << target) & blockers: break
        r += 1
        f += 1

    # SOUTH-EAST
    r, f = rank - 1, file + 1
    while r >= 0 and f < 8:
        target = r * 8 + f
        attacks |= (1 << target)
        if (1 << target) & blockers: break
        r -= 1
        f += 1

    # SOUTH-WEST
    r, f = rank - 1, file - 1
    while r >= 0 and f >= 0:
        target = r * 8 + f
        attacks |= (1 << target)
        if (1 << target) & blockers: break
        r -= 1
        f -= 1

    # NORTH-WEST
    r, f = rank + 1, file - 1
    while r < 8 and f >= 0:
        target = r * 8 + f
        attacks |= (1 << target)
        if (1 << target) & blockers: break
        r += 1
        f -= 1

    return attacks

# Initialize move tables once at module level for better performance
KNIGHT_MOVES_TABLE = _init_knight_moves()
KING_MOVES_TABLE = _init_king_moves()

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

    def print_bb(self, bb):
        """
        Display a bitboard in a visual chess board format.

        Args:
            bb: Bitboard to display (64-bit integer)
        """
        for r in range(7, -1, -1):
            line = f"{r+1} "
            for f in range(8):
                idx = r*8 + f
                if (bb >> idx) & 1:
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
