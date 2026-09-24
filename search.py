"""Fast minimax/alpha-beta chess search.

The search keeps the original Board/Evaluate architecture, but uses in-place
make/unmake moves, iterative deepening, transposition-table bounds, quiescence
search, killer moves and a history heuristic.  These are deliberately kept
explicit so the engine remains study-friendly.
"""

from board import Board
from evaluate import Evaluate
import time

MATE_SCORE = 1_000_000
INFINITY = 10_000_000
EXACT, LOWERBOUND, UPPERBOUND = 0, 1, 2


class SearchTimeout(Exception):
    """Internal signal used to stop a search at its configured time limit."""


class Search:
    def __init__(self, depth=3, quiescence_depth=2, time_limit=None):
        self.evaluate = Evaluate()
        self.depth = depth
        self.quiescence_depth = quiescence_depth
        self.time_limit = time_limit
        self.deadline = None
        self.transposition_table = {}
        self.nodes = 0
        self.qnodes = 0
        self.killers = {}
        self.history = {}
        self.pv_move = None

    def copy_board(self, board):
        return board.copy()

    @staticmethod
    def _position_key(board, team):
        rights = (
            board.white_king_moved, board.black_king_moved,
            board.white_rook_a_moved, board.white_rook_h_moved,
            board.black_rook_a_moved, board.black_rook_h_moved,
        )
        flat = bytes(piece + 6 for row in board.state for piece in row)
        return (flat, team, rights, board.en_passant_target)

    @staticmethod
    def _move_key(move):
        return move

    def move_order_score(self, board, move, ply=0):
        fr, fc, tr, tc, promotion = move
        moving = abs(board.state[fr][fc])
        target = board.state[tr][tc]
        score = 0

        if self.pv_move == move:
            score += 2_000_000
        if promotion is not None:
            score += 1_000_000 + promotion * 100

        if target != 0:
            # MVV-LVA, with a large tactical priority.
            score += 500_000 + abs(target) * 1_000 - moving * 10
        elif moving == 1 and board.en_passant_target == (tr, tc) and fc != tc:
            score += 500_000

        killers = self.killers.get(ply, ())
        if move in killers:
            score += 100_000 if move == killers[0] else 90_000

        score += self.history.get((fr, fc, tr, tc, promotion), 0)

        # Small positional ordering hints help the first few moves.
        if moving == 6 and abs(tc - fc) == 2:
            score += 2_000
        if tr in (3, 4) and tc in (3, 4):
            score += 100
        return score

    def minmax(self, board, team, depth=None, alpha=-INFINITY, beta=INFINITY):
        """Return (score, best_move). Depth is measured in plies."""
        target_depth = self.depth if depth is None else depth
        self.nodes = 0
        self.qnodes = 0
        self.transposition_table = {}
        self.killers = {}
        self.history = {}
        self.pv_move = None
        self.deadline = time.perf_counter() + self.time_limit if self.time_limit is not None else None

        # Handle a terminal root before iterative deepening so mate scores are
        # stable and do not depend on the first shallow iteration.
        root_moves = board.get_all_legal_moves(team)
        if not root_moves:
            if board.in_check(team):
                return (-MATE_SCORE - target_depth if team == 1 else MATE_SCORE + target_depth), None
            return 0, None

        # Iterative deepening gives better move ordering at every deeper ply.
        best_score, best_move = 0, None
        for current_depth in range(1, target_depth + 1):
            try:
                score, move = self._negamax_root(board, team, current_depth)
            except SearchTimeout:
                break
            if move is None:
                return score, None
            best_score, best_move = score, move
            self.pv_move = move
        return best_score, best_move

    def _check_time(self):
        # Checking every node is measurable overhead in Python.  The search
        # counter is used as a cheap sampling clock.
        if self.deadline is not None and (self.nodes & 2047) == 0 and time.perf_counter() >= self.deadline:
            raise SearchTimeout

    def _negamax_root(self, board, team, depth):
        legal_moves = board.get_all_legal_moves(team)
        if not legal_moves:
            if board.in_check(team):
                return (-MATE_SCORE - depth if team == 1 else MATE_SCORE + depth), None
            return 0, None

        tt = self.transposition_table.get(self._position_key(board, team))
        tt_move = tt[3] if tt is not None and len(tt) > 3 else None
        old_pv = self.pv_move
        self.pv_move = tt_move or old_pv
        legal_moves.sort(key=lambda m: self.move_order_score(board, m, 0), reverse=True)

        best = -INFINITY
        best_move = legal_moves[0]
        alpha, beta = -INFINITY, INFINITY
        for move in legal_moves:
            undo = board.make_move(*move)
            try:
                score = -self._negamax(board, -team, depth - 1, -beta, -alpha, 1)
            finally:
                board.unmake_move(undo)
            if score > best:
                best, best_move = score, move
            if score > alpha:
                alpha = score
        self.pv_move = old_pv
        return best, best_move

    def _negamax(self, board, team, depth, alpha, beta, ply):
        self.nodes += 1
        self._check_time()
        alpha_orig = alpha
        key = self._position_key(board, team)
        entry = self.transposition_table.get(key)
        tt_move = None
        if entry is not None:
            tt_depth, tt_score, flag, tt_move = entry
            if tt_depth >= depth:
                if flag == EXACT:
                    return tt_score
                if flag == LOWERBOUND:
                    alpha = max(alpha, tt_score)
                elif flag == UPPERBOUND:
                    beta = min(beta, tt_score)
                if alpha >= beta:
                    return tt_score

        if depth <= 0:
            score = self._quiescence(board, team, alpha, beta, self.quiescence_depth, ply)
            self.transposition_table[key] = (0, score, EXACT, tt_move)
            return score

        legal_moves = board.get_all_legal_moves(team)
        if not legal_moves:
            if board.in_check(team):
                # Score from the side-to-move perspective: getting mated is bad.
                return -MATE_SCORE + ply
            return 0

        old_pv = self.pv_move
        self.pv_move = tt_move
        legal_moves.sort(key=lambda m: self.move_order_score(board, m, ply), reverse=True)

        best = -INFINITY
        best_move = legal_moves[0]
        for index, move in enumerate(legal_moves):
            undo = board.make_move(*move)
            try:
                # Late-move reduction: quiet moves late in the ordering get a small
                # reduced search, then a full re-search if they improve alpha.
                is_quiet = self._is_quiet_before_move(board, move)
                if index >= 4 and depth >= 3 and is_quiet:
                    score = -self._negamax(board, -team, depth - 2, -alpha - 1, -alpha, ply + 1)
                    if score > alpha:
                        score = -self._negamax(board, -team, depth - 1, -beta, -alpha, ply + 1)
                else:
                    score = -self._negamax(board, -team, depth - 1, -beta, -alpha, ply + 1)
            finally:
                board.unmake_move(undo)

            if score > best:
                best = score
                best_move = move
            if score > alpha:
                alpha = score
            if alpha >= beta:
                # Quiet beta-cutoffs are excellent candidates for future ordering.
                if self._is_quiet_move(board, move):
                    killers = self.killers.setdefault(ply, [])
                    if move not in killers:
                        killers.insert(0, move)
                        del killers[2:]
                    self.history[move] = min(self.history.get(move, 0) + depth * depth, 1_000_000)
                break

        if best <= alpha_orig:
            flag = UPPERBOUND
        elif best >= beta:
            flag = LOWERBOUND
        else:
            flag = EXACT
        self.transposition_table[key] = (depth, best, flag, best_move)
        self.pv_move = old_pv
        return best

    @staticmethod
    def _is_quiet_move(board, move):
        fr, fc, tr, tc, promotion = move
        if promotion is not None:
            return False
        if board.state[tr][tc] != 0:
            return False
        return not (abs(board.state[fr][fc]) == 1 and board.en_passant_target == (tr, tc) and fc != tc)

    def _is_quiet_before_move(self, board, move):
        return self._is_quiet_move(board, move)

    def _quiescence(self, board, team, alpha, beta, depth, ply):
        """Capture-only extension at the leaf.

        The main legal-move generator already guarantees king safety.  Keeping
        quiescence capture-only is intentional: it avoids exploding the node
        count while still resolving most hanging-piece/tactical sequences.
        """
        self.qnodes += 1
        if self.deadline is not None and (self.qnodes & 2047) == 0 and time.perf_counter() >= self.deadline:
            raise SearchTimeout
        stand_pat = self.evaluate.evaluate(board)
        if team == -1:
            stand_pat = -stand_pat

        if stand_pat >= beta:
            return stand_pat
        if stand_pat > alpha:
            alpha = stand_pat
        if depth == 0:
            return stand_pat

        captures = board.get_all_legal_moves(team, captures_only=True)
        captures.sort(key=lambda m: self.move_order_score(board, m, ply), reverse=True)

        for move in captures:
            undo = board.make_move(*move)
            try:
                score = -self._quiescence(board, -team, -beta, -alpha, depth - 1, ply + 1)
            finally:
                board.unmake_move(undo)
            if score >= beta:
                return score
            if score > alpha:
                alpha = score
        return alpha
