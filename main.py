from chess_engine import Bitboard, get_rook_mask, get_bishop_mask

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



    # board.print_full_board()