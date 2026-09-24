"""Pygame user interface for the chess engine."""

from pathlib import Path

import pygame

from board import Board
from search import Search


class Game:
    # Easy to change display & search configuration
    BOARD_PIXELS = 500
    WINDOW_WIDTH = 650
    WINDOW_HEIGHT = 650
    ENGINE_DEPTH = 3
    ENGINE_TIME_LIMIT = 29.0
    FPS = 60

    LIGHT_SQUARE = (238, 238, 210)
    DARK_SQUARE = (118, 150, 86)
    BACKGROUND = (28, 30, 31)
    PANEL = (39, 42, 43)
    TEXT = (240, 240, 240)
    MUTED_TEXT = (190, 195, 195)
    ACCENT = (92, 145, 85)
    SELECTED = (255, 215, 55)
    LAST_MOVE = (245, 210, 65)
    MOVE_DOT = (45, 45, 45)
    CAPTURE_RING = (190, 60, 60)
    CHECK = (220, 70, 70)
    BUTTON = (65, 69, 71)
    BUTTON_HOVER = (83, 88, 90)

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Chess Engine")
        self.screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()

        self.base_dir = Path(__file__).resolve().parent
        self.board = Board()
        self.search = Search(depth=self.ENGINE_DEPTH, time_limit=self.ENGINE_TIME_LIMIT)

        self.board_size = 8
        self.square_size = self.BOARD_PIXELS // self.board_size
        self.board_x = (self.WINDOW_WIDTH - self.BOARD_PIXELS) // 2
        self.board_y = 65

        self.title_font = pygame.font.Font(None, 34)
        self.status_font = pygame.font.Font(None, 27)
        self.button_font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 18)
        self.overlay_title_font = pygame.font.Font(None, 48)
        self.overlay_font = pygame.font.Font(None, 30)

        self.running = True
        self.active_team = 1  # Human = White, engine = Black.
        self.selected_square = None
        self.last_move = None

        self.game_over = False
        self.result_text = None
        self.confirmation = None  # "resign" or "new_game"

        self.promotion_possible = False
        self.promotion_moves = []
        self.promotion_rects = {}

        self.buttons = {}
        self.piece_images = self._load_piece_images()

    def _load_piece_images(self):
        """Load the repository's existing piece assets and scale them once."""
        piece_files = {
            1: "w_pawn_png_1024px.png",
            2: "w_knight_png_1024px.png",
            3: "w_bishop_png_1024px.png",
            4: "w_rook_png_1024px.png",
            5: "w_queen_png_1024px.png",
            6: "w_king_png_1024px.png",
            -1: "b_pawn_png_1024px.png",
            -2: "b_knight_png_1024px.png",
            -3: "b_bishop_png_1024px.png",
            -4: "b_rook_png_1024px.png",
            -5: "b_queen_png_1024px.png",
            -6: "b_king_png_1024px.png",
        }
        size = int(self.square_size * 0.84)
        images = {}
        for piece, filename in piece_files.items():
            image = pygame.image.load(self.base_dir / filename).convert_alpha()
            images[piece] = pygame.transform.smoothscale(image, (size, size))
        return images

    def reset_game(self):
        self.board.reset()
        self.search = Search(depth=self.ENGINE_DEPTH, time_limit=self.ENGINE_TIME_LIMIT)
        self.active_team = 1
        self.selected_square = None
        self.last_move = None
        self.game_over = False
        self.result_text = None
        self.confirmation = None
        self.promotion_possible = False
        self.promotion_moves = []
        self.promotion_rects = {}

    def _square_rect(self, row, col):
        return pygame.Rect(
            self.board_x + col * self.square_size,
            self.board_y + row * self.square_size,
            self.square_size,
            self.square_size,
        )

    def _mouse_square(self, pos):
        x, y = pos
        col = (x - self.board_x) // self.square_size
        row = (y - self.board_y) // self.square_size
        if 0 <= row < 8 and 0 <= col < 8:
            return row, col
        return None

    def _button_rect(self, name):
        return self.buttons[name]

    def _set_game_over(self, text):
        self.game_over = True
        self.result_text = text
        self.selected_square = None
        self.promotion_possible = False
        self.promotion_moves = []

    def _update_game_state_after_move(self):
        """Switch turn and determine checkmate/stalemate/draw status."""
        self.active_team *= -1

        if self.board.is_insufficient_material():
            self._set_game_over("Draw - Insufficient Material")
            return

        result = self.board.check_for_win(self.active_team)
        if result == -1:
            self._set_game_over("Checkmate - Black Wins")
        elif result == 1:
            self._set_game_over("Checkmate - White Wins")
        elif result == 0:
            self._set_game_over("Draw - Stalemate")

    def _apply_move(self, move):
        self.board.move_piece(move[0], move[1], move[2], move[3], move[4])
        self.last_move = move[:4]
        self.selected_square = None
        self.promotion_possible = False
        self.promotion_moves = []
        self._update_game_state_after_move()

    def _handle_board_click(self, square):
        if self.game_over or self.confirmation or self.promotion_possible or self.active_team != 1:
            return

        row, col = square
        piece = self.board.state[row][col]

        if self.selected_square is None:
            if piece > 0:
                self.selected_square = square
            return

        # Clicking another white piece changes selection.
        if piece > 0:
            self.selected_square = square
            return

        moves = self.board.get_legal_moves(*self.selected_square)
        matching = [
            (self.selected_square[0], self.selected_square[1], move[0], move[1], move[2])
            for move in moves
            if move[0] == row and move[1] == col
        ]

        if not matching:
            # Clear selection after an invalid destination click, but leave the
            # board otherwise unchanged so an illegal move can never be applied.
            self.selected_square = None
            return

        if len(matching) > 1:
            self.promotion_possible = True
            self.promotion_moves = matching
            return

        self._apply_move(matching[0])

    def _handle_promotion_click(self, pos):
        for promotion_piece, rect in self.promotion_rects.items():
            if rect.collidepoint(pos):
                for move in self.promotion_moves:
                    if move[4] == promotion_piece:
                        self._apply_move(move)
                        return

    def _handle_button_click(self, pos):
        if self.confirmation or self.promotion_possible:
            return

        if self.buttons["new_game"].collidepoint(pos):
            if self.game_over:
                self.reset_game()
            else:
                self.confirmation = "new_game"
        elif self.buttons["resign"].collidepoint(pos) and not self.game_over:
            self.confirmation = "resign"

    def _handle_confirmation_click(self, pos):
        confirm_rect = self._confirmation_button_rect(True)
        cancel_rect = self._confirmation_button_rect(False)
        if confirm_rect.collidepoint(pos):
            if self.confirmation == "resign":
                self._set_game_over("White Resigned - Black Wins")
            elif self.confirmation == "new_game":
                self.reset_game()
            self.confirmation = None
        elif cancel_rect.collidepoint(pos):
            self.confirmation = None

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue

            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            if self.game_over:
                if self.buttons.get("overlay_new") and self.buttons["overlay_new"].collidepoint(event.pos):
                    self.reset_game()
                elif self.buttons.get("overlay_quit") and self.buttons["overlay_quit"].collidepoint(event.pos):
                    self.running = False
                continue

            if self.confirmation:
                self._handle_confirmation_click(event.pos)
                continue

            if self.promotion_possible:
                self._handle_promotion_click(event.pos)
                continue

            button_hit = False
            for rect in self.buttons.values():
                if rect.collidepoint(event.pos):
                    button_hit = True
                    break
            if button_hit:
                self._handle_button_click(event.pos)
                continue

            square = self._mouse_square(event.pos)
            if square is not None:
                self._handle_board_click(square)

    def update(self):
        if self.game_over or self.confirmation or self.promotion_possible:
            return

        if self.active_team == -1:
            _, move = self.search.minmax(self.board, -1)
            if move is None:
                # This is normally caught immediately after the player's move.
                self._update_game_state_after_move()
                return
            self._apply_move(move)

    def _draw_button(self, name, label, enabled=True):
        rect = self.buttons[name]
        mouse_over = rect.collidepoint(pygame.mouse.get_pos())
        color = self.BUTTON_HOVER if mouse_over and enabled else self.BUTTON
        if not enabled:
            color = (55, 57, 58)
        pygame.draw.rect(self.screen, color, rect, border_radius=8)
        pygame.draw.rect(self.screen, (105, 109, 110), rect, 1, border_radius=8)
        surface = self.button_font.render(label, True, self.TEXT if enabled else self.MUTED_TEXT)
        self.screen.blit(surface, surface.get_rect(center=rect.center))

    def draw(self):
        self.screen.fill(self.BACKGROUND)

        title = self.title_font.render("Chess Engine", True, self.TEXT)
        self.screen.blit(title, (self.board_x, 20))

        turn_text = "White to move" if self.active_team == 1 else "Black to move"
        if self.game_over:
            turn_text = "Game over"
        elif self.board.in_check(self.active_team):
            turn_text += " - CHECK"
        status = self.status_font.render(turn_text, True, self.CHECK if "CHECK" in turn_text else self.MUTED_TEXT)
        self.screen.blit(status, (self.board_x + 180, 23))

        self._draw_board()
        self._draw_controls()

        if self.promotion_possible:
            self._draw_promotion_dialog()
        if self.confirmation:
            self._draw_confirmation_dialog()
        if self.game_over:
            self._draw_game_over_overlay()

    def _draw_board(self):
        legal_destinations = set()
        capture_destinations = set()
        if self.selected_square and not self.game_over:
            for move in self.board.get_legal_moves(*self.selected_square):
                legal_destinations.add((move[0], move[1]))
                target = self.board.state[move[0]][move[1]]
                is_ep = self.board.en_passant_target == (move[0], move[1]) and target == 0
                if target != 0 or is_ep:
                    capture_destinations.add((move[0], move[1]))

        for row in range(8):
            for col in range(8):
                rect = self._square_rect(row, col)
                color = self.LIGHT_SQUARE if (row + col) % 2 == 0 else self.DARK_SQUARE
                pygame.draw.rect(self.screen, color, rect)

                if self.last_move and (row, col) in ((self.last_move[0], self.last_move[1]), (self.last_move[2], self.last_move[3])):
                    # Strong, easy-to-see last-move marker. Draw it before the
                    # pieces so the piece remains crisp while the square still
                    # has a clearly visible highlight around it.
                    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                    overlay.fill((*self.LAST_MOVE, 145))
                    self.screen.blit(overlay, rect)
                    pygame.draw.rect(self.screen, self.LAST_MOVE, rect, 4)

                if self.selected_square == (row, col):
                    # A bright, thick border makes the selected piece obvious
                    # even against both board colours.
                    pygame.draw.rect(self.screen, self.SELECTED, rect, 6)

                if (row, col) in legal_destinations:
                    center = rect.center
                    if (row, col) in capture_destinations:
                        pygame.draw.circle(self.screen, self.CAPTURE_RING, center, self.square_size // 3, 4)
                    else:
                        pygame.draw.circle(self.screen, self.MOVE_DOT, center, self.square_size // 9)

                if (row, col) in self._checked_squares():
                    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                    overlay.fill((*self.CHECK, 85))
                    self.screen.blit(overlay, rect)
                    pygame.draw.rect(self.screen, self.CHECK, rect, 4)

                piece = self.board.state[row][col]
                if piece:
                    image = self.piece_images[piece]
                    image_rect = image.get_rect(center=rect.center)
                    self.screen.blit(image, image_rect)

        pygame.draw.rect(
            self.screen,
            (20, 20, 20),
            pygame.Rect(self.board_x - 2, self.board_y - 2, self.BOARD_PIXELS + 4, self.BOARD_PIXELS + 4),
            2,
        )

    def _checked_squares(self):
        white_check, black_check, white_pos, black_pos = self.board.king_check_check()
        checked = set()
        if white_check and white_pos:
            checked.add(white_pos)
        if black_check and black_pos:
            checked.add(black_pos)
        return checked

    def _draw_controls(self):
        y = self.board_y + self.BOARD_PIXELS + 18
        self.buttons["new_game"] = pygame.Rect(self.board_x, y, 180, 48)
        self.buttons["resign"] = pygame.Rect(self.board_x + 195, y, 180, 48)
        self._draw_button("new_game", "New Game")
        self._draw_button("resign", "Resign", enabled=not self.game_over)

        hint = "You are White" if self.active_team == 1 and not self.game_over else "Engine is Black"
        hint_surface = self.status_font.render(hint, True, self.MUTED_TEXT)
        self.screen.blit(hint_surface, (self.board_x + 390, y + 12))

    def _draw_promotion_dialog(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 115))
        self.screen.blit(overlay, (0, 0))

        dialog = pygame.Rect(self.board_x + 70, self.board_y + 275, self.BOARD_PIXELS - 140, 170)
        pygame.draw.rect(self.screen, self.PANEL, dialog, border_radius=12)
        pygame.draw.rect(self.screen, (120, 125, 126), dialog, 2, border_radius=12)
        text = self.overlay_font.render("Choose promotion", True, self.TEXT)
        self.screen.blit(text, text.get_rect(center=(dialog.centerx, dialog.y + 35)))

        self.promotion_rects = {}
        pieces = (2, 3, 4, 5)
        labels = {2: "Knight", 3: "Bishop", 4: "Rook", 5: "Queen"}
        for index, piece in enumerate(pieces):
            rect = pygame.Rect(dialog.x + 25 + index * 92, dialog.y + 65, 70, 80)
            self.promotion_rects[piece] = rect
            pygame.draw.rect(self.screen, self.BUTTON, rect, border_radius=8)
            image = self.piece_images[piece]
            image_rect = image.get_rect(center=(rect.centerx, rect.y + 31))
            self.screen.blit(image, image_rect)
            label = self.small_font.render(labels[piece], True, self.MUTED_TEXT)
            self.screen.blit(label, label.get_rect(center=(rect.centerx, rect.bottom - 11)))

    def _confirmation_button_rect(self, confirm):
        center_x = self.WINDOW_WIDTH // 2
        y = self.WINDOW_HEIGHT // 2 + 35
        return pygame.Rect(center_x - (125 if confirm else -5), y, 110, 42)

    def _draw_confirmation_dialog(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        self.screen.blit(overlay, (0, 0))

        dialog = pygame.Rect(105, 325, self.WINDOW_WIDTH - 210, 190)
        pygame.draw.rect(self.screen, self.PANEL, dialog, border_radius=12)
        pygame.draw.rect(self.screen, (120, 125, 126), dialog, 2, border_radius=12)

        message = "Resign this game?" if self.confirmation == "resign" else "Start a new game?"
        text = self.overlay_font.render(message, True, self.TEXT)
        self.screen.blit(text, text.get_rect(center=(dialog.centerx, dialog.y + 50)))

        confirm = self._confirmation_button_rect(True)
        cancel = self._confirmation_button_rect(False)
        for rect, label in ((confirm, "Confirm"), (cancel, "Cancel")):
            pygame.draw.rect(self.screen, self.BUTTON, rect, border_radius=7)
            surface = self.button_font.render(label, True, self.TEXT)
            self.screen.blit(surface, surface.get_rect(center=rect.center))

    def _draw_game_over_overlay(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 125))
        self.screen.blit(overlay, (0, 0))

        dialog = pygame.Rect(85, 295, self.WINDOW_WIDTH - 170, 235)
        pygame.draw.rect(self.screen, self.PANEL, dialog, border_radius=14)
        pygame.draw.rect(self.screen, self.ACCENT, dialog, 2, border_radius=14)

        title = self.overlay_title_font.render("Game Over", True, self.TEXT)
        result = self.overlay_font.render(self.result_text, True, self.TEXT)
        self.screen.blit(title, title.get_rect(center=(dialog.centerx, dialog.y + 55)))
        self.screen.blit(result, result.get_rect(center=(dialog.centerx, dialog.y + 105)))

        new_rect = pygame.Rect(dialog.centerx - 145, dialog.bottom - 65, 130, 44)
        quit_rect = pygame.Rect(dialog.centerx + 15, dialog.bottom - 65, 130, 44)
        self.buttons["overlay_new"] = new_rect
        self.buttons["overlay_quit"] = quit_rect
        for rect, label in ((new_rect, "New Game"), (quit_rect, "Quit")):
            pygame.draw.rect(self.screen, self.BUTTON, rect, border_radius=7)
            surface = self.button_font.render(label, True, self.TEXT)
            self.screen.blit(surface, surface.get_rect(center=rect.center))

    def run(self):
        while self.running:
            self.handle_events()

            # Render immediately after input. This is important because the
            # engine search is synchronous and can take noticeable time.
            # Without this intermediate frame, the human move would not become
            # visible until after the engine has finished thinking.
            self.draw()
            pygame.display.flip()

            # Search only after the player's move has already been displayed.
            # The final engine position is rendered again when the search ends.
            if self.running and not self.game_over and not self.confirmation and not self.promotion_possible:
                if self.active_team == -1:
                    self.update()
                    self.draw()
                    pygame.display.flip()

            self.clock.tick(self.FPS)

        pygame.quit()


if __name__ == "__main__":
    Game().run()
