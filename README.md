## Requirements

- Python 3.12.x
- Pygame 2.x

No additional Python packages are required beyond Pygame.

## Run

From the project directory:

```bash
python -m pip install pygame
python game.py
```

On systems where `python` maps to a different interpreter, use:

```bash
python3.12 -m pip install pygame
python3.12 game.py
```

## Tests

The chess-rule test suite uses only Python's standard library:

```bash
python -m unittest -v test_board.py
```

The tests cover pawn movement/captures, capture-only generation, en passant, promotion, sliding pieces, knights, king safety, pins, castling, check, checkmate, stalemate, insufficient material and engine mate finding.

## Engine configuration

The engine search depth is configured in `game.py`:

```python
ENGINE_DEPTH = 7
ENGINE_TIME_LIMIT = 29.0
```

Search depth is measured in plies. The GUI targets depth 7 and uses a 29-second hard search budget; if the target depth cannot finish in time, iterative deepening returns the best move from the deepest completed iteration. This keeps the UI responsive and prevents unexpectedly long engine turns.

The board/window dimensions are also configurable at the top of `game.py`:

```python
BOARD_PIXELS = 720
WINDOW_WIDTH = 760
WINDOW_HEIGHT = 850
```

## Project structure

- `board.py` — board state, legal move generation, check/checkmate/stalemate and special moves.
- `search.py` — iterative-deepening negamax with alpha-beta pruning, transposition-table bounds, move ordering, killer/history heuristics, late-move reductions and capture-only quiescence search.
- `evaluate.py` — fast material + piece-square evaluation with small pawn-structure, bishop-pair and rook-file terms.
- `game.py` — Pygame interface, controls and game-state presentation.
- `test_board.py` — automated chess-rule tests.
- `*_png_1024px.png` — existing piece image assets.
