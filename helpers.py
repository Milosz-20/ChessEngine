# Constant helpers (files)
# 0x0101010101010101 is a vertical line at file A
FILE_A = 0x0101010101010101
FILE_B = FILE_A << 1
FILE_G = FILE_A << 6
FILE_H = FILE_A << 7

# Starting ranks for pawns (used to allow double pushes)
RANK_2 = 0x000000000000FF00
RANK_7 = 0x00FF000000000000

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
    # Lookup table of king moves from all 64 squares
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
    # Lookup table of knight moves from all 64 squares
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

def _init_white_pawn_attacks():
    # Lookup table of white pawn diagonal captures from all 64 squares
    moves_list = [0] * 64

    for square in range(64):
        moves = 0
        position = 1 << square

        if position & NOT_FILE_A:
            target = square + NORTH_WEST
            if 0 <= target < 64: moves |= (1 << target)

        if position & NOT_FILE_H:
            target = square + NORTH_EAST
            if 0 <= target < 64: moves |= (1 << target)

        moves_list[square] = moves

    return moves_list

def _init_black_pawn_attacks(): 
    # Lookup table of black pawn diagonal captures from all 64 squares
    moves_list = [0] * 64

    for square in range(64):
        moves = 0
        position = 1 << square

        if position & NOT_FILE_A:
            target = square + SOUTH_WEST
            if 0 <= target < 64: moves |= (1 << target)

        if position & NOT_FILE_H:
            target = square + SOUTH_EAST
            if 0 <= target < 64: moves |= (1 << target)

        moves_list[square] = moves

    return moves_list

def count_bits(bitboard):
    # Count set bits with Kernighan's algorithm (clear the lowest set bit each iteration)
    count = 0
    while bitboard:
        count += 1
        bitboard &= bitboard - 1
    return count

def set_bit(bitboard, bit):
    # Set the bit at the given index (0-63) to 1
    return bitboard | (1 << bit)

def get_set_bits(bitboard):
    # Return indices (0-63) of all set bits in the bitboard
    indices = []
    while bitboard:
        lsb = bitboard & -bitboard
        index = lsb.bit_length() - 1
        indices.append(index)
        bitboard &= (bitboard - 1)
    return indices

def generate_occupancy_variations(mask):
    # Generate all possible sub-masks (occupancies) of a given mask
    variations = []
    subset = 0
    while True:
        variations.append(subset)
        subset = (subset - mask) & mask
        if subset == 0: break
    return variations

def get_rook_mask(square):
    # Relevant occupancy mask for a rook: squares that can block it, edges excluded
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
    # Relevant occupancy mask for a bishop: squares that can block it, edges excluded
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