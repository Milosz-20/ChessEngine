# Constant helpers (files)
# 0x0101010101010101 is a vertical line at file A
FILE_A = 0x0101010101010101
FILE_B = FILE_A << 1
FILE_G = FILE_A << 6
FILE_H = FILE_A << 7

# Combined masks (needed for knights)
# Knight moving two tiles to the left cannot stand on either A or B
NOT_FILE_A = ~FILE_A & 0xFFFFFFFFFFFFFFFF
NOT_FILE_B = ~FILE_B & 0xFFFFFFFFFFFFFFFF
NOT_FILE_G = ~FILE_G & 0xFFFFFFFFFFFFFFFF
NOT_FILE_H = ~FILE_H & 0xFFFFFFFFFFFFFFFF

NOT_FILE_AB = NOT_FILE_A & NOT_FILE_B
NOT_FILE_GH = NOT_FILE_G & NOT_FILE_H


def _init_knight_moves():
    moves_list = [0] * 64

    for square in range(64):
        moves = 0
        position = 1 << square  # Bitboard with only the knight on the specific square

        # General rule: cannot exceed the board (0 <= index < 64)

        # 1. Adding (moving up)

        # Moves 'up up right' (index +17)
        # Rule: cannot be on file H
        if (square + 17) < 64 and (position & NOT_FILE_H):
            moves |= (1 << (square + 17))

        # Moves 'up up left' (index +15)
        # Rule: cannot be on file A
        if (square + 15) < 64 and (position & NOT_FILE_A):
            moves |= (1 << (square + 15))

        # Moves 'up right right' (index +10)
        # Rule: cannot be on file G or H
        if (square + 10) < 64 and (position & NOT_FILE_GH):
            moves |= (1 << (square + 10))

        # Moves 'up left left' (index +6)
        # Rule: cannot be on file A or B
        if (square + 6) < 64 and (position & NOT_FILE_AB):
            moves |= (1 << (square + 6))

        # 2. Subtracting (moving down)

        # Moves 'down down right' (index -15)
        # Rule: cannot be on file H
        if (square - 15) >= 0 and (position & NOT_FILE_H):
            moves |= (1 << (square - 15))

        # Moves 'down down left' (index -17)
        # Rule: cannot be on file A
        if (square - 17) >= 0 and (position & NOT_FILE_A):
            moves |= (1 << (square - 17))

        # Moves 'down right right' (index -6)
        # Rule: cannot be on file G or H
        if (square - 6) >= 0 and (position & NOT_FILE_GH):
            moves |= (1 << (square - 6))

        # Moves 'down left left' (index -10)
        # Rule: cannot be on file A or B
        if (square - 10) >= 0 and (position & NOT_FILE_AB):
            moves |= (1 << (square - 10))

        moves_list[square] = moves

    return moves_list


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

        self.knight_table = _init_knight_moves() # Full board of available knight moves

    def get_knight_moves(self, square, isWhite):
        possible_moves = self.knight_table[square]

        if isWhite: # Check to not step on your own piece
            own_pieces = self.wp | self.wn | self.wb | self.wr | self.wq | self.wk
        else:
            own_pieces = self.bp | self.bn | self.bb | self.br | self.bq | self.bk

        valid_moves =  possible_moves & ~own_pieces
        return valid_moves

    # Helper function to display bitboard of valid moves for some piece
    def print_bb(self, bb):
        print("  a b c d e f g h")
        for r in range(7, -1, -1):
            line = f"{r+1} "
            for f in range(8):
                idx = r*8 + f
                if (bb >> idx) & 1:
                    line += "X "
                else:
                    line += ". "
            print(line)

    def print_full_board(self):
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
