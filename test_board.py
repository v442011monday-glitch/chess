import unittest

from board import Board


def empty_board():
    board = Board()
    board.state = [[0 for _ in range(8)] for _ in range(8)]
    board.en_passant_target = None
    board.white_king_moved = board.black_king_moved = False
    board.white_rook_a_moved = board.white_rook_h_moved = False
    board.black_rook_a_moved = board.black_rook_h_moved = False
    board.state[7][4] = 6
    board.state[0][4] = -6
    return board


class TestPawnRules(unittest.TestCase):
    def test_pawn_cannot_capture_forward(self):
        board = empty_board()
        board.state[5][3] = 1
        board.state[4][3] = -4
        moves = board.get_legal_moves(5, 3)
        self.assertNotIn((4, 3, None), moves)

    def test_pawn_captures_diagonally(self):
        board = empty_board()
        board.state[5][3] = 1
        board.state[4][4] = -2
        board.state[4][2] = -3
        moves = board.get_legal_moves(5, 3)
        self.assertIn((4, 4, None), moves)
        self.assertIn((4, 2, None), moves)

    def test_pawn_forward_move_requires_empty_square(self):
        board = Board()
        board.state[5][0] = -1
        board.state[6][0] = 1
        self.assertNotIn((5, 0, None), board.get_legal_moves(6, 0))

    def test_double_pawn_move_requires_both_squares_empty(self):
        board = Board()
        board.state[5][0] = -2
        self.assertNotIn((4, 0, None), board.get_legal_moves(6, 0))

    def test_en_passant(self):
        board = empty_board()
        board.state[3][4] = 1
        board.state[3][5] = -1
        board.en_passant_target = (2, 5)
        self.assertIn((2, 5, None), board.get_legal_moves(3, 4))
        board.move_piece(3, 4, 2, 5)
        self.assertEqual(board.state[3][5], 0)
        self.assertEqual(board.state[2][5], 1)


class TestPiecesAndKingSafety(unittest.TestCase):
    def test_bishop_cannot_jump(self):
        board = empty_board()
        board.state[4][4] = 3
        board.state[3][3] = 1
        self.assertNotIn((2, 2, None), board.get_legal_moves(4, 4))

    def test_rook_moves_straight_only(self):
        board = empty_board()
        board.state[4][4] = 4
        moves = board.get_legal_moves(4, 4)
        self.assertIn((4, 0, None), moves)
        self.assertIn((1, 4, None), moves)
        self.assertNotIn((3, 3, None), moves)

    def test_knight_jumps(self):
        board = empty_board()
        board.state[4][4] = 2
        board.state[3][4] = 1
        self.assertIn((2, 5, None), board.get_legal_moves(4, 4))

    def test_king_cannot_move_into_check(self):
        board = empty_board()
        board.state[6][4] = 6
        board.state[4][4] = -4
        moves = board.get_legal_moves(6, 4)
        self.assertNotIn((5, 4, None), moves)

    def test_pinned_piece_cannot_expose_king(self):
        board = empty_board()
        board.state[7][4] = 6
        board.state[6][4] = 1
        board.state[5][4] = -4
        board.state[7][4] = 6
        moves = board.get_legal_moves(6, 4)
        self.assertEqual(moves, [])

    def test_check_detection(self):
        board = empty_board()
        board.state[0][4] = -6
        board.state[4][4] = 4
        self.assertTrue(board.in_check(-1))
        self.assertFalse(board.in_check(1))

    def test_cannot_capture_enemy_king(self):
        board = empty_board()
        board.state[6][4] = 6
        board.state[5][4] = -6
        self.assertNotIn((5, 4, None), board.get_legal_moves(6, 4))

    def test_initial_position_perft_depth_two(self):
        def perft(board, depth, team):
            if depth == 0:
                return 1
            total = 0
            for move in board.get_all_legal_moves(team):
                child = board.copy()
                child.move_piece(move[0], move[1], move[2], move[3], move[4])
                total += perft(child, depth - 1, -team)
            return total

        board = Board()
        self.assertEqual(len(board.get_all_legal_moves(1)), 20)
        self.assertEqual(perft(board, 2, 1), 400)


    def test_capture_only_generation_excludes_quiet_moves(self):
        board = Board()
        self.assertEqual(board.get_all_legal_moves(1, captures_only=True), [])
        board.state[5][1] = -2
        captures = board.get_all_legal_moves(1, captures_only=True)
        self.assertIn((6, 0, 5, 1, None), captures)

    def test_en_passant_expires_after_one_move(self):
        board = Board()
        board.move_piece(6, 4, 4, 4)
        self.assertEqual(board.en_passant_target, (5, 4))
        board.move_piece(1, 0, 2, 0)
        self.assertIsNone(board.en_passant_target)



class TestSpecialMovesAndEndings(unittest.TestCase):
    def test_castling_requires_safe_transit_square(self):
        board = empty_board()
        board.state[7][7] = 4
        board.state[0][0] = -4
        board.state[5][5] = -4  # attacks f1
        self.assertNotIn((7, 6, None), board.get_legal_moves(7, 4))

    def test_castling_moves_rook(self):
        board = empty_board()
        board.state[7][7] = 4
        self.assertIn((7, 6, None), board.get_legal_moves(7, 4))
        board.move_piece(7, 4, 7, 6)
        self.assertEqual(board.state[7][6], 6)
        self.assertEqual(board.state[7][5], 4)

    def test_promotion_generates_four_choices(self):
        board = empty_board()
        board.state[1][0] = 1
        moves = board.get_legal_moves(1, 0)
        self.assertEqual({m[2] for m in moves if m[0] == 0}, {2, 3, 4, 5})

    def test_checkmate_and_stalemate(self):
        # Black king h8, white queen g7, white king f6 = checkmate.
        board = empty_board()
        board.state[0][4] = 0
        board.state[0][7] = -6
        board.state[1][6] = 5
        board.state[2][5] = 6
        self.assertEqual(board.check_for_win(-1), 1)

        # Black king h8, white queen f7, white king h6 = stalemate.
        board = empty_board()
        board.state[0][4] = 0
        board.state[0][7] = -6
        board.state[1][5] = 5
        board.state[2][7] = 6
        self.assertEqual(board.check_for_win(-1), 0)

    def test_insufficient_material(self):
        board = empty_board()
        self.assertTrue(board.is_insufficient_material())
        board.state[7][2] = 3
        self.assertTrue(board.is_insufficient_material())


if __name__ == "__main__":
    unittest.main()
