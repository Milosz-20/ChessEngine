from chess_engine import Bitboard, get_rook_mask, get_bishop_mask, rook_attacks_on_the_fly, bishop_attacks_on_the_fly

if __name__ == "__main__":
    board = Bitboard()
    sq = 35
    print(f"List of moves for KNIGHT on square {sq}:\n(other pieces at start positions)")
    moves = board.get_knight_moves(sq, is_white=True)
    board.print_bb(moves)
    print()

    print(f"List of moves for KING on square {sq}:\n(other pieces at start positions)")
    moves = board.get_king_moves(sq, is_white=True)
    board.print_bb(moves)
    print()

    print(f"Rook mask on square {sq} (relevant occupancy bits):")
    moves = get_rook_mask(sq)
    board.print_bb(moves)
    print()

    print(f"Bishop mask on square {sq} (relevant occupancy bits):")
    moves = get_bishop_mask(sq)
    board.print_bb(moves)
    print()

    rook_blockers = (1 << 51) | (1 << 38)
    print("Rook blockers positions:")
    board.print_bb(rook_blockers)
    print()
    rook_moves = rook_attacks_on_the_fly(sq, rook_blockers)
    print("Resulting Rook possible attacks:")
    board.print_bb(rook_moves)
    print()

    bishop_blockers = (1 << 42) | (1 << 21)
    print("Bishop blockers positions:")
    board.print_bb(bishop_blockers)
    print()
    print("Resulting Bishop possible attacks:")
    bishop_moves = bishop_attacks_on_the_fly(sq, bishop_blockers)
    board.print_bb(bishop_moves)
    # board.print_full_board()