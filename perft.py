def perft(board, depth, is_white):
    if depth == 0:
        return 1
    nodes = 0
    for move in board.generate_legal_moves(is_white):
        board.make_move(move)
        nodes += perft(board, depth-1, not is_white)
        board.unmake_move(move)
    return nodes