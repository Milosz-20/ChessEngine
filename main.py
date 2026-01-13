from chess_engine import Bitboard

if __name__ == "__main__":
    board = Bitboard()

    sq = 27
    print(f"List of moves for knight on square {sq} (in start position):")
    moves = board.get_knight_moves(sq, isWhite=True)
    board.print_bb(moves)

    # board.print_full_board()