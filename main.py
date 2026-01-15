from chess_engine import Bitboard

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

    # board.print_full_board()