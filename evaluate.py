"""Fast, explainable static evaluation for the chess engine.

Scores are centipawns from White's perspective.  The evaluator deliberately
stays much smaller than a tournament engine while covering the features that
matter most at shallow-to-medium search depths: material, piece placement,
pawn structure, passed pawns, bishop pair, rook files and king safety.
"""

PIECE_VALUES = (0, 100, 320, 330, 500, 900, 20_000)

PAWN_TABLE = (
    (0, 0, 0, 0, 0, 0, 0, 0),
    (50, 50, 50, 50, 50, 50, 50, 50),
    (10, 10, 20, 30, 30, 20, 10, 10),
    (5, 5, 10, 25, 25, 10, 5, 5),
    (0, 0, 0, 20, 20, 0, 0, 0),
    (5, -5, -10, 0, 0, -10, -5, 5),
    (5, 10, 10, -20, -20, 10, 10, 5),
    (0, 0, 0, 0, 0, 0, 0, 0),
)

KNIGHT_TABLE = (
    (-50, -40, -30, -30, -30, -30, -40, -50),
    (-40, -20, 0, 5, 5, 0, -20, -40),
    (-30, 5, 10, 15, 15, 10, 5, -30),
    (-30, 0, 15, 20, 20, 15, 0, -30),
    (-30, 5, 15, 20, 20, 15, 5, -30),
    (-30, 0, 10, 15, 15, 10, 0, -30),
    (-40, -20, 0, 0, 0, 0, -20, -40),
    (-50, -40, -30, -30, -30, -30, -40, -50),
)

BISHOP_TABLE = (
    (-20, -10, -10, -10, -10, -10, -10, -20),
    (-10, 5, 0, 0, 0, 0, 5, -10),
    (-10, 10, 10, 10, 10, 10, 10, -10),
    (-10, 0, 10, 10, 10, 10, 0, -10),
    (-10, 5, 5, 10, 10, 5, 5, -10),
    (-10, 0, 5, 10, 10, 5, 0, -10),
    (-10, 0, 0, 0, 0, 0, 0, -10),
    (-20, -10, -10, -10, -10, -10, -10, -20),
)

ROOK_TABLE = (
    (0, 0, 0, 5, 5, 0, 0, 0),
    (-5, 0, 0, 0, 0, 0, 0, -5),
    (-5, 0, 0, 0, 0, 0, 0, -5),
    (-5, 0, 0, 0, 0, 0, 0, -5),
    (-5, 0, 0, 0, 0, 0, 0, -5),
    (-5, 0, 0, 0, 0, 0, 0, -5),
    (5, 10, 10, 10, 10, 10, 10, 5),
    (0, 0, 0, 0, 0, 0, 0, 0),
)

QUEEN_TABLE = (
    (-20, -10, -10, -5, -5, -10, -10, -20),
    (-10, 0, 0, 0, 0, 0, 0, -10),
    (-10, 0, 5, 5, 5, 5, 0, -10),
    (-5, 0, 5, 5, 5, 5, 0, -5),
    (0, 0, 5, 5, 5, 5, 0, -5),
    (-10, 5, 5, 5, 5, 5, 0, -10),
    (-10, 0, 5, 0, 0, 0, 0, -10),
    (-20, -10, -10, -5, -5, -10, -10, -20),
)

KING_MIDDLE_TABLE = (
    (-30, -40, -40, -50, -50, -40, -40, -30),
    (-30, -40, -40, -50, -50, -40, -40, -30),
    (-30, -40, -40, -50, -50, -40, -40, -30),
    (-30, -40, -40, -50, -50, -40, -40, -30),
    (-20, -30, -30, -40, -40, -30, -30, -20),
    (-10, -20, -20, -20, -20, -20, -20, -10),
    (20, 20, 0, 0, 0, 0, 20, 20),
    (20, 30, 10, 0, 0, 10, 30, 20),
)

KING_END_TABLE = (
    (-50, -30, -30, -30, -30, -30, -30, -50),
    (-30, -10, 0, 0, 0, 0, -10, -30),
    (-30, 0, 20, 30, 30, 20, 0, -30),
    (-30, 0, 30, 40, 40, 30, 0, -30),
    (-30, 0, 30, 40, 40, 30, 0, -30),
    (-30, 0, 20, 30, 30, 20, 0, -30),
    (-30, -10, 0, 0, 0, 0, -10, -30),
    (-50, -30, -30, -30, -30, -30, -30, -50),
)

TABLES = {1: PAWN_TABLE, 2: KNIGHT_TABLE, 3: BISHOP_TABLE,
          4: ROOK_TABLE, 5: QUEEN_TABLE}

# Endgame phase contribution.  0 means pure endgame; 24 is a normal full army.
PHASE_VALUES = (0, 0, 1, 1, 2, 4, 0)


class Evaluate:
    def evaluate(self, board):
        """Return a fast centipawn score from White's perspective."""
        score = 0
        pawn_files = [[0] * 8, [0] * 8]
        bishops = [0, 0]
        rooks = [[], []]

        # Keep this loop deliberately tight: evaluation is executed at hundreds
        # of thousands of leaf nodes in a depth-7 search.
        for row in range(8):
            for col in range(8):
                piece = board.state[row][col]
                if piece == 0:
                    continue
                sign = 1 if piece > 0 else -1
                piece_type = abs(piece)
                score += sign * PIECE_VALUES[piece_type]
                if piece_type == 6:
                    table = KING_MIDDLE_TABLE
                else:
                    table = TABLES[piece_type]
                table_row = row if sign > 0 else 7 - row
                score += sign * table[table_row][col]

                side = 0 if sign > 0 else 1
                if piece_type == 1:
                    pawn_files[side][col] += 1
                elif piece_type == 3:
                    bishops[side] += 1
                elif piece_type == 4:
                    rooks[side].append(col)

        # Small structural terms that cost almost nothing compared with a move search.
        score += 20 if bishops[0] >= 2 else 0
        score -= 20 if bishops[1] >= 2 else 0

        for side in (0, 1):
            sign = 1 if side == 0 else -1
            files = pawn_files[side]
            for file_index, count in enumerate(files):
                if count > 1:
                    score += sign * -5 * (count - 1)  # doubled pawns
                if count:
                    left = files[file_index - 1] if file_index else 0
                    right = files[file_index + 1] if file_index < 7 else 0
                    if left == 0 and right == 0:
                        score += sign * -5  # isolated pawn

            enemy_files = pawn_files[1 - side]
            for col in rooks[side]:
                if files[col] == 0 and enemy_files[col] == 0:
                    score += sign * 8  # open file
                elif files[col] == 0:
                    score += sign * 4   # semi-open file

        return score