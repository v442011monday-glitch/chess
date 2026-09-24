"""Chess board state and legal move generation.

The board uses a simple 8x8 integer array:
    0   empty
    1-6 white pawn/knight/bishop/rook/queen/king
   -1..-6 black pawn/knight/bishop/rook/queen/king

Move tuples are ``(row, column, promotion_piece)``.  Promotion pieces are
2, 3, 4 or 5; otherwise the third value is ``None``.
"""

BOARD_SIZE = 8

WHITE = 1
BLACK = -1

PAWN = 1
KNIGHT = 2
BISHOP = 3
ROOK = 4
QUEEN = 5
KING = 6

PROMOTION_PIECES = (KNIGHT, BISHOP, ROOK, QUEEN)

INITIAL_STATE = (
    (-4, -2, -3, -5, -6, -3, -2, -4),
    (-1, -1, -1, -1, -1, -1, -1, -1),
    (0, 0, 0, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0, 0, 0),
    (1, 1, 1, 1, 1, 1, 1, 1),
    (4, 2, 3, 5, 6, 3, 2, 4),
)


class Board:
    def __init__(self):
        self.reset()

    def reset(self):
        """Restore the standard starting position and all game state."""
        self.state = [list(row) for row in INITIAL_STATE]

        # Castling rights are represented as "has this original king/rook moved?".
        self.white_king_moved = False
        self.black_king_moved = False
        self.white_rook_a_moved = False
        self.white_rook_h_moved = False
        self.black_rook_a_moved = False
        self.black_rook_h_moved = False

        # The square that may be captured en passant on the immediately
        # following move.  None means there is no en-passant opportunity.
        self.en_passant_target = None

    @staticmethod
    def _in_bounds(row, col):
        return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE

    @staticmethod
    def _team(piece):
        return WHITE if piece > 0 else BLACK

    def copy(self):
        """Return an independent copy of the board, including game state."""
        new_board = Board()
        new_board.state = [row[:] for row in self.state]
        new_board.white_king_moved = self.white_king_moved
        new_board.black_king_moved = self.black_king_moved
        new_board.white_rook_a_moved = self.white_rook_a_moved
        new_board.white_rook_h_moved = self.white_rook_h_moved
        new_board.black_rook_a_moved = self.black_rook_a_moved
        new_board.black_rook_h_moved = self.black_rook_h_moved
        new_board.en_passant_target = self.en_passant_target
        return new_board

    def make_move(self, row, column, new_row, new_column, promotion_piece=None):
        """Apply a move in-place and return an undo token for fast search."""
        piece = self.state[row][column]
        if piece == 0:
            raise ValueError("Cannot move an empty square")
        if promotion_piece is not None and promotion_piece not in PROMOTION_PIECES:
            raise ValueError("Invalid promotion piece")
        team = self._team(piece)
        old_ep = self.en_passant_target
        old_rights = (self.white_king_moved, self.black_king_moved, self.white_rook_a_moved, self.white_rook_h_moved, self.black_rook_a_moved, self.black_rook_h_moved)
        changes = []
        def set_square(r, c, value):
            changes.append((r, c, self.state[r][c]))
            self.state[r][c] = value
        target_piece = self.state[new_row][new_column]
        set_square(row, column, 0)
        is_castle = abs(piece) == KING and row == new_row and abs(new_column - column) == 2
        is_en_passant = abs(piece) == PAWN and old_ep == (new_row, new_column) and target_piece == 0 and column != new_column
        if is_en_passant:
            captured_pawn_row = new_row + 1 if team == WHITE else new_row - 1
            set_square(captured_pawn_row, new_column, 0)
        placed_piece = team * promotion_piece if promotion_piece is not None else piece
        set_square(new_row, new_column, placed_piece)
        if is_castle:
            rook_column, rook_destination = (7, 5) if new_column == 6 else (0, 3)
            rook = self.state[row][rook_column]
            set_square(row, rook_column, 0)
            set_square(row, rook_destination, rook)
        self.en_passant_target = None
        if abs(piece) == PAWN and abs(new_row - row) == 2:
            self.en_passant_target = ((row + new_row) // 2, column)
        if piece == 6:
            self.white_king_moved = True
        elif piece == -6:
            self.black_king_moved = True
        elif piece == 4 and (row, column) == (7, 0):
            self.white_rook_a_moved = True
        elif piece == 4 and (row, column) == (7, 7):
            self.white_rook_h_moved = True
        elif piece == -4 and (row, column) == (0, 0):
            self.black_rook_a_moved = True
        elif piece == -4 and (row, column) == (0, 7):
            self.black_rook_h_moved = True
        return changes, old_ep, old_rights

    def unmake_move(self, undo):
        changes, old_ep, old_rights = undo
        for row, col, old_value in reversed(changes):
            self.state[row][col] = old_value
        self.en_passant_target = old_ep
        (self.white_king_moved, self.black_king_moved, self.white_rook_a_moved, self.white_rook_h_moved, self.black_rook_a_moved, self.black_rook_h_moved) = old_rights

    def move_piece(self, row, column, new_row, new_column, promotion_piece=None):
        """Apply a move to the board. Public compatibility API."""
        self.make_move(row, column, new_row, new_column, promotion_piece)

    def long_range_recursion(self, row, column, dirx, diry, team):
        """Return sliding moves in one direction.

        Kept as a public helper for compatibility with the original project.
        """
        moves = []
        r, c = row + dirx, column + diry
        while self._in_bounds(r, c):
            piece = self.state[r][c]
            if piece == 0:
                moves.append((r, c, None))
            else:
                if self._team(piece) != team and abs(piece) != KING:
                    moves.append((r, c, None))
                break
            r += dirx
            c += diry
        return moves

    def is_square_attacked(self, row, col, by_team):
        """Return whether ``(row, col)`` is attacked by ``by_team``."""
        # Pawns attack toward the opponent's side of the board.
        pawn_row = row + 1 if by_team == WHITE else row - 1
        pawn = by_team * PAWN
        for pawn_col in (col - 1, col + 1):
            if self._in_bounds(pawn_row, pawn_col) and self.state[pawn_row][pawn_col] == pawn:
                return True

        # Knights.
        knight = by_team * KNIGHT
        knight_offsets = (
            (2, 1), (2, -1), (-2, 1), (-2, -1),
            (1, 2), (1, -2), (-1, 2), (-1, -2),
        )
        for dr, dc in knight_offsets:
            r, c = row + dr, col + dc
            if self._in_bounds(r, c) and self.state[r][c] == knight:
                return True

        # Kings.
        enemy_king = by_team * KING
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                r, c = row + dr, col + dc
                if self._in_bounds(r, c) and self.state[r][c] == enemy_king:
                    return True

        # Rooks/queens.
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            r, c = row + dr, col + dc
            while self._in_bounds(r, c):
                piece = self.state[r][c]
                if piece != 0:
                    if piece in (by_team * ROOK, by_team * QUEEN):
                        return True
                    break
                r += dr
                c += dc

        # Bishops/queens.
        for dr, dc in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            r, c = row + dr, col + dc
            while self._in_bounds(r, c):
                piece = self.state[r][c]
                if piece != 0:
                    if piece in (by_team * BISHOP, by_team * QUEEN):
                        return True
                    break
                r += dr
                c += dc

        return False

    def _find_king(self, team):
        king = team * KING
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if self.state[row][col] == king:
                    return row, col
        return None

    def in_check(self, team):
        """Return whether ``team``'s king is currently in check."""
        king_pos = self._find_king(team)
        if king_pos is None:
            # A valid chess position always has both kings.  Treating a missing
            # king as checked prevents illegal positions from becoming playable.
            return True
        return self.is_square_attacked(king_pos[0], king_pos[1], -team)

    def king_check_check(self):
        """Compatibility API: return both check states and checked king squares."""
        white_pos = self._find_king(WHITE)
        black_pos = self._find_king(BLACK)
        white_in_check = white_pos is not None and self.is_square_attacked(*white_pos, BLACK)
        black_in_check = black_pos is not None and self.is_square_attacked(*black_pos, WHITE)
        return (
            white_in_check,
            black_in_check,
            white_pos if white_in_check else None,
            black_pos if black_in_check else None,
        )

    def _pseudo_legal_moves(self, row, column, captures_only=False):
        """Generate movement-pattern-valid moves before king-safety filtering."""
        piece = self.state[row][column]
        if piece == 0:
            return []

        team = self._team(piece)
        piece_type = abs(piece)
        moves = []

        def add_step(r, c, promotion=None):
            if not self._in_bounds(r, c):
                return
            target = self.state[r][c]
            if target != 0 and self._team(target) == team:
                return
            if target != 0 and abs(target) == KING:
                return
            if captures_only and target == 0:
                return
            moves.append((r, c, promotion))

        if piece_type == PAWN:
            direction = -1 if team == WHITE else 1
            start_row = 6 if team == WHITE else 1
            promotion_row = 0 if team == WHITE else 7

            one_row = row + direction
            if self._in_bounds(one_row, column) and self.state[one_row][column] == 0:
                if one_row == promotion_row:
                    moves.extend((one_row, column, p) for p in PROMOTION_PIECES)
                elif not captures_only:
                    moves.append((one_row, column, None))

                two_row = row + 2 * direction
                if not captures_only and row == start_row and self.state[two_row][column] == 0:
                    moves.append((two_row, column, None))

            # Pawns capture diagonally only.
            for dc in (-1, 1):
                capture_col = column + dc
                if not self._in_bounds(one_row, capture_col):
                    continue
                target = self.state[one_row][capture_col]
                is_enemy = target != 0 and self._team(target) == -team and abs(target) != KING
                is_ep = self.en_passant_target == (one_row, capture_col) and target == 0
                if is_enemy or is_ep:
                    if one_row == promotion_row:
                        moves.extend((one_row, capture_col, p) for p in PROMOTION_PIECES)
                    else:
                        moves.append((one_row, capture_col, None))

        elif piece_type == KNIGHT:
            for dr, dc in ((2, 1), (2, -1), (-2, 1), (-2, -1),
                           (1, 2), (1, -2), (-1, 2), (-1, -2)):
                add_step(row + dr, column + dc)

        elif piece_type in (BISHOP, ROOK, QUEEN):
            directions = []
            if piece_type in (ROOK, QUEEN):
                directions.extend(((1, 0), (-1, 0), (0, 1), (0, -1)))
            if piece_type in (BISHOP, QUEEN):
                directions.extend(((1, 1), (1, -1), (-1, 1), (-1, -1)))
            for dr, dc in directions:
                moves.extend(self.long_range_recursion(row, column, dr, dc, team))

        elif piece_type == KING:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr or dc:
                        add_step(row + dr, column + dc)

            # Castling is a quiet move and is therefore excluded in capture-only mode.
            if not captures_only and team == WHITE and (row, column) == (7, 4) and not self.white_king_moved:
                if (
                    not self.white_rook_h_moved
                    and self.state[7][7] == 4
                    and self.state[7][5] == 0
                    and self.state[7][6] == 0
                    and not self.in_check(WHITE)
                    and not self.is_square_attacked(7, 5, BLACK)
                ):
                    moves.append((7, 6, None))
                if (
                    not self.white_rook_a_moved
                    and self.state[7][0] == 4
                    and self.state[7][1] == 0
                    and self.state[7][2] == 0
                    and self.state[7][3] == 0
                    and not self.in_check(WHITE)
                    and not self.is_square_attacked(7, 3, BLACK)
                ):
                    moves.append((7, 2, None))

            elif not captures_only and team == BLACK and (row, column) == (0, 4) and not self.black_king_moved:
                if (
                    not self.black_rook_h_moved
                    and self.state[0][7] == -4
                    and self.state[0][5] == 0
                    and self.state[0][6] == 0
                    and not self.in_check(BLACK)
                    and not self.is_square_attacked(0, 5, WHITE)
                ):
                    moves.append((0, 6, None))
                if (
                    not self.black_rook_a_moved
                    and self.state[0][0] == -4
                    and self.state[0][1] == 0
                    and self.state[0][2] == 0
                    and self.state[0][3] == 0
                    and not self.in_check(BLACK)
                    and not self.is_square_attacked(0, 3, WHITE)
                ):
                    moves.append((0, 2, None))

        return moves

    def get_legal_moves(self, row, column, captures_only=False):
        """Return moves that obey piece movement rules and leave own king safe."""
        if not self._in_bounds(row, column) or self.state[row][column] == 0:
            return []

        piece = self.state[row][column]
        team = self._team(piece)
        legal_moves = []

        for move in self._pseudo_legal_moves(row, column, captures_only):
            undo = self.make_move(row, column, move[0], move[1], move[2])
            legal = not self.in_check(team)
            self.unmake_move(undo)
            if legal:
                legal_moves.append(move)

        return legal_moves

    def get_all_legal_moves(self, team, captures_only=False):
        all_legal_moves = []
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if self.state[row][col] * team > 0:
                    for move in self.get_legal_moves(row, col, captures_only):
                        all_legal_moves.append((row, col, move[0], move[1], move[2]))
        return all_legal_moves

    def is_insufficient_material(self):
        """Return whether neither side has enough material to checkmate."""
        pieces = []
        for row in self.state:
            for piece in row:
                if piece != 0:
                    pieces.append(piece)

        # Any pawn, rook or queen means a mating material configuration exists.
        if any(abs(piece) in (PAWN, ROOK, QUEEN) for piece in pieces):
            return False

        non_kings = [piece for piece in pieces if abs(piece) != KING]
        if not non_kings:
            return True  # king vs king
        if len(non_kings) == 1 and abs(non_kings[0]) in (KNIGHT, BISHOP):
            return True  # K+B/K or K+N/K
        if all(abs(piece) == BISHOP for piece in non_kings):
            # K+B vs K+B is only automatically drawn when all bishops are on
            # the same colour.  This is the common sufficient-material test.
            colours = set()
            for row in range(BOARD_SIZE):
                for col in range(BOARD_SIZE):
                    if abs(self.state[row][col]) == BISHOP:
                        colours.add((row + col) % 2)
            return len(colours) == 1
        return False

    def check_for_win(self, team):
        """Compatibility API: checkmate=-winner, stalemate=0, otherwise None."""
        if self.is_insufficient_material():
            return 0

        if self.get_all_legal_moves(team):
            return None

        if self.in_check(team):
            return -team
        return 0
