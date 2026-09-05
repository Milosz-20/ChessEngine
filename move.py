class Move:
    def __init__(self, from_sq, to_sq, piece, captured_piece=None,
                 promotion_piece=None, is_double_push=False,
                 is_en_passant=False, is_castling=False):
        self.from_sq = from_sq
        self.to_sq = to_sq
        self.piece = piece
        self.captured_piece = captured_piece
        self.promotion_piece = promotion_piece
        self.is_double_push = is_double_push
        self.is_en_passant = is_en_passant
        self.is_castling = is_castling

    def __eq__(self, other):
        if not isinstance(other, Move):
            return False
        return ((self.from_sq, self.to_sq, self.piece, self.promotion_piece) == 
                (other.from_sq, other.to_sq, other.piece, other.promotion_piece))

    def __repr__(self):
        return f"Move({self.piece} {self.from_sq}->{self.to_sq})"