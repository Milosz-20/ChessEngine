"""A full game of chess on top of the bitboard engine.

`Bitboard` knows the rules of a single move. `Game` adds everything needed to play
a whole game between two people: parsing moves sent by a client (UCI strings such as
"e2e4" or "e7e8q"), algebraic notation (SAN) for the move list, FEN export, and
detecting how the game ended (mate, stalemate, repetition, fifty moves, material).
"""
from chess_engine import Bitboard
from helpers import get_set_bits, count_bits

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
PIECE_ATTRS = ('wp', 'wn', 'wb', 'wr', 'wq', 'wk', 'bp', 'bn', 'bb', 'br', 'bq', 'bk')
FILES = "abcdefgh"

# Results and the reason the game ended
WHITE_WINS, BLACK_WINS, DRAW = "1-0", "0-1", "1/2-1/2"
CHECKMATE, STALEMATE = "checkmate", "stalemate"
REPETITION, FIFTY_MOVES, INSUFFICIENT = "repetition", "fifty_moves", "insufficient_material"


class IllegalMove(ValueError):
    pass


def square_name(square):
    return FILES[square % 8] + str(square // 8 + 1)


def parse_square(name):
    if len(name) != 2 or name[0] not in FILES or name[1] not in "12345678":
        raise ValueError(f"Bad square: {name!r}")
    return (int(name[1]) - 1) * 8 + FILES.index(name[0])


def move_to_uci(move):
    uci = square_name(move.from_sq) + square_name(move.to_sq)
    if move.promotion_piece:
        uci += move.promotion_piece[1]
    return uci


class Game:
    def __init__(self, fen=START_FEN):
        self.board = Bitboard()
        self.board.load_fen(fen)
        self.start_fen = fen
        self._legal_cache = None
        self.moves = []          # Move objects actually played
        self.uci_moves = []
        self.san_moves = []
        self.fens = [self.fen()]  # position after every ply, fens[0] = start
        self.position_counts = {}
        self._count_position()

    # ---------- queries ----------

    @property
    def white_to_move(self):
        return self.board.side_to_move

    def legal_moves(self):
        if self._legal_cache is None:
            self._legal_cache = self.board.generate_legal_moves(self.board.side_to_move)
        return self._legal_cache

    def legal_uci_moves(self):
        return [move_to_uci(m) for m in self.legal_moves()]

    def is_check(self):
        return self.board.is_in_check(self.board.side_to_move)

    def king_square(self, is_white):
        bb = self.board.wk if is_white else self.board.bk
        return get_set_bits(bb)[0]

    def piece_placement(self):
        rows = []
        for rank in range(7, -1, -1):
            row, empty = "", 0
            for file in range(8):
                piece = self.board.get_piece_at(rank * 8 + file)
                if piece is None:
                    empty += 1
                    continue
                if empty:
                    row += str(empty)
                    empty = 0
                row += piece[1].upper() if piece[0] == 'w' else piece[1]
            if empty:
                row += str(empty)
            rows.append(row)
        return "/".join(rows)

    def _castling_field(self):
        field = "".join(r for r in "KQkq" if self.board.castling_rights[r])
        return field or "-"

    def _relevant_ep_field(self):
        # The en passant square only matters (for repetition) if a capture is really possible
        ep = self.board.en_passant_square
        if ep is None:
            return "-"
        if any(m.is_en_passant for m in self.legal_moves()):
            return square_name(ep)
        return "-"

    def fen(self):
        b = self.board
        ep = "-" if b.en_passant_square is None else square_name(b.en_passant_square)
        return " ".join([self.piece_placement(), "w" if b.side_to_move else "b",
                         self._castling_field(), ep, str(b.halfmove_clock), str(b.fullmove_number)])

    def position_key(self):
        # Two positions are "the same" for threefold repetition when pieces, side to move,
        # castling rights and en passant possibility all match (FIDE art. 9.2)
        return " ".join([self.piece_placement(), "w" if self.board.side_to_move else "b",
                         self._castling_field(), self._relevant_ep_field()])

    def _count_position(self):
        key = self.position_key()
        self.position_counts[key] = self.position_counts.get(key, 0) + 1

    # ---------- moves ----------

    def parse_uci(self, uci):
        if not isinstance(uci, str) or len(uci) not in (4, 5):
            raise IllegalMove(f"Bad move format: {uci!r}")
        try:
            from_sq, to_sq = parse_square(uci[0:2]), parse_square(uci[2:4])
        except ValueError:
            raise IllegalMove(f"Bad move format: {uci!r}")
        promo = uci[4].lower() if len(uci) == 5 else None
        for move in self.legal_moves():
            if move.from_sq != from_sq or move.to_sq != to_sq:
                continue
            move_promo = move.promotion_piece[1] if move.promotion_piece else None
            if move_promo == promo:
                return move
        raise IllegalMove(f"Illegal move: {uci}")

    def san(self, move):
        """Standard Algebraic Notation for a legal move in the current position."""
        if move.is_castling:
            text = "O-O" if move.to_sq % 8 == 6 else "O-O-O"
        else:
            piece_type = move.piece[1]
            is_capture = move.captured_piece is not None
            target = square_name(move.to_sq)
            if piece_type == 'p':
                text = (FILES[move.from_sq % 8] + "x" if is_capture else "") + target
                if move.promotion_piece:
                    text += "=" + move.promotion_piece[1].upper()
            else:
                # Disambiguate when another piece of the same type can reach the same square
                rivals = [m for m in self.legal_moves()
                          if m.piece == move.piece and m.to_sq == move.to_sq and m.from_sq != move.from_sq]
                disambig = ""
                if rivals:
                    same_file = any(m.from_sq % 8 == move.from_sq % 8 for m in rivals)
                    same_rank = any(m.from_sq // 8 == move.from_sq // 8 for m in rivals)
                    if not same_file:
                        disambig = FILES[move.from_sq % 8]
                    elif not same_rank:
                        disambig = str(move.from_sq // 8 + 1)
                    else:
                        disambig = square_name(move.from_sq)
                text = piece_type.upper() + disambig + ("x" if is_capture else "") + target

        # Check or mate suffix
        mover_white = move.piece[0] == 'w'
        self.board.make_move(move)
        if self.board.is_in_check(not mover_white):
            replies = self.board.generate_legal_moves(not mover_white)
            text += "#" if not replies else "+"
        self.board.unmake_move(move)
        return text

    def push_uci(self, uci):
        move = self.parse_uci(uci)
        san = self.san(move)
        self.board.make_move(move)
        self._legal_cache = None
        self.moves.append(move)
        self.uci_moves.append(move_to_uci(move))
        self.san_moves.append(san)
        self.fens.append(self.fen())
        self._count_position()
        return san

    # ---------- game end ----------

    def _material(self, is_white):
        p = 'w' if is_white else 'b'
        return {t: getattr(self.board, p + t) for t in 'pnbrq'}

    def insufficient_material(self):
        """Neither side can possibly checkmate: K v K, K+minor v K, K+B v K+B with
        all bishops on the same square colour."""
        white, black = self._material(True), self._material(False)
        for side in (white, black):
            if side['p'] or side['r'] or side['q']:
                return False
        minors = [count_bits(white['n']) + count_bits(white['b']),
                  count_bits(black['n']) + count_bits(black['b'])]
        if sum(minors) <= 1:
            return True
        if white['n'] or black['n']:
            return False
        bishops = get_set_bits(white['b'] | black['b'])
        colours = {(sq // 8 + sq % 8) % 2 for sq in bishops}
        return len(colours) == 1

    def can_mate(self, is_white):
        """Rough test used when a clock runs out: if the side that did NOT flag has
        only a king (or king + single minor piece against a bare king), the game is a
        draw instead of a win (FIDE art. 6.9)."""
        own = self._material(is_white)
        other = self._material(not is_white)
        if own['p'] or own['r'] or own['q']:
            return True
        minors = count_bits(own['n']) + count_bits(own['b'])
        if minors == 0:
            return False
        if minors == 1:
            # A lone minor can only mate with help from the opponent's own pieces
            return any(other[t] for t in 'pnbrq')
        return True

    def outcome(self):
        """(result, reason) if the game is over by the rules, otherwise None."""
        if not self.legal_moves():
            if self.is_check():
                return (BLACK_WINS if self.white_to_move else WHITE_WINS), CHECKMATE
            return DRAW, STALEMATE
        if self.insufficient_material():
            return DRAW, INSUFFICIENT
        if self.position_counts.get(self.position_key(), 0) >= 3:
            return DRAW, REPETITION
        if self.board.halfmove_clock >= 100:
            return DRAW, FIFTY_MOVES
        return None

    @classmethod
    def from_uci_moves(cls, uci_moves, fen=START_FEN):
        game = cls(fen)
        for uci in uci_moves:
            game.push_uci(uci)
        return game


def build_pgn(headers, san_moves, result):
    """PGN text: header tags, then numbered SAN moves ending with the result."""
    lines = [f'[{key} "{value}"]' for key, value in headers.items()]
    tokens = []
    for i, san in enumerate(san_moves):
        if i % 2 == 0:
            tokens.append(f"{i // 2 + 1}.")
        tokens.append(san)
    tokens.append(result or "*")
    body, line = [], ""
    for token in tokens:  # wrap at 80 columns like most PGN writers
        if line and len(line) + 1 + len(token) > 80:
            body.append(line)
            line = token
        else:
            line = f"{line} {token}" if line else token
    body.append(line)
    return "\n".join(lines) + "\n\n" + "\n".join(body) + "\n"
