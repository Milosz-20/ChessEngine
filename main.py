from chess_engine import Bitboard
from helpers import get_rook_mask, get_bishop_mask, rook_attacks_on_the_fly, bishop_attacks_on_the_fly

if __name__ == "__main__":
    board = Bitboard()
    sq = 35
    print(f"List of moves for KNIGHT on square {sq}:\n(other pieces at start positions)")
    moves = board.get_knight_moves(sq, is_white=True)
    board.print_bitboard(moves)
    print()

    print(f"List of moves for KING on square {sq}:\n(other pieces at start positions)")
    moves = board.get_king_moves(sq, is_white=True)
    board.print_bitboard(moves)
    print()

    print(f"Rook mask on square {sq} (relevant occupancy bits):")
    moves = get_rook_mask(sq)
    board.print_bitboard(moves)
    print()

    print(f"Bishop mask on square {sq} (relevant occupancy bits):")
    moves = get_bishop_mask(sq)
    board.print_bitboard(moves)
    print()

    rook_blockers = (1 << 51) | (1 << 38)
    print("Rook blockers positions:")
    board.print_bitboard(rook_blockers)
    print()
    rook_moves = rook_attacks_on_the_fly(sq, rook_blockers)
    print("Resulting Rook possible attacks:")
    board.print_bitboard(rook_moves)
    print()

    bishop_blockers = (1 << 42) | (1 << 21)
    print("Bishop blockers positions:")
    board.print_bitboard(bishop_blockers)
    print()
    print("Resulting Bishop possible attacks:")
    bishop_moves = bishop_attacks_on_the_fly(sq, bishop_blockers)
    board.print_bitboard(bishop_moves)
    # board.print_full_board()

    sq = 35
    print(f"--- TESTING SQUARE {sq} ---")

    # Test Magic Lookups (Fast!)
    # Let's verify Magic Bitboards work by setting some fake blockers
    print("\n[MAGIC LOOKUP TEST]")
    # Rook on D5 (35), blockers on D7 (51) and C5 (34)
    blockers = (1 << 51) | (1 << 34)

    print("Blockers:")
    board.print_bitboard(blockers)

    # Use the Magic System (O(1) speed)
    magic_attacks = board.magics.get_rook_attacks(sq, blockers)

    print("Magic Generated Attacks:")
    board.print_bitboard(magic_attacks)

    # Verify against slow method
    slow_attacks = rook_attacks_on_the_fly(sq, blockers)
    if magic_attacks == slow_attacks:
        print("SUCCESS: Magic lookup matches calculated attacks.")
    else:
        print("FAILURE: Magic lookup incorrect.")