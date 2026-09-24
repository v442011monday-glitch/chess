import unittest

from board import Board
from search import MATE_SCORE, Search


class TestSearch(unittest.TestCase):
    def test_search_returns_legal_move(self):
        board = Board()
        search = Search(depth=2)
        score, move = search.minmax(board, -1)
        self.assertIsNotNone(move)
        legal = board.get_all_legal_moves(-1)
        self.assertIn(move, legal)
        self.assertIsInstance(score, (int, float))


    def test_search_finds_mate_in_one(self):
        board = Board()
        board.state = [[0 for _ in range(8)] for _ in range(8)]
        board.state[0][7] = -6  # black king h8
        board.state[2][5] = 6   # white king f6
        board.state[2][6] = 5   # white queen g6
        search = Search(depth=2, quiescence_depth=2)
        score, move = search.minmax(board, 1)
        self.assertEqual(move, (2, 6, 1, 6, None))  # Qg7#
        self.assertGreaterEqual(score, MATE_SCORE - 2)

    def test_search_detects_checkmate_terminal(self):
        board = Board()
        board.state = [[0 for _ in range(8)] for _ in range(8)]
        board.state[0][7] = -6
        board.state[1][6] = 5
        board.state[2][5] = 6
        search = Search(depth=2)
        score, move = search.minmax(board, -1)
        self.assertIsNone(move)
        self.assertEqual(score, MATE_SCORE + 2)


if __name__ == "__main__":
    unittest.main()
