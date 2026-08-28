"""
MainMenuScreen — Écran du menu principal.
"""

import pygame
from .screen_manager import Screen
from ..utils.constants import *
from ..utils.helpers import draw_text, draw_rounded_rect, create_button_rect


class MainMenuScreen(Screen):
    """Menu principal du jeu."""

    def __init__(self, screen_manager):
        super().__init__(screen_manager)
        self.buttons = []
        self._init_buttons()

    def _init_buttons(self):
        """Initialise les boutons du menu."""
        center_x = SCREEN_WIDTH // 2
        btn_w, btn_h = 250, 50
        start_y = 320

        self.buttons = [
            {
                "rect": create_button_rect(center_x, start_y, btn_w, btn_h),
                "text": " Ouvrir des Boosters",
                "action": "booster_shop",
                "color": COLOR_ACCENT,
                "hover_color": COLOR_ACCENT_HOVER,
            },
            {
                "rect": create_button_rect(center_x, start_y + 70, btn_w, btn_h),
                "text": " Ma Collection",
                "action": "collection",
                "color": COLOR_GREEN,
                "hover_color": (100, 220, 140),
            },
            {
                "rect": create_button_rect(center_x, start_y + 140, btn_w, btn_h),
                "text": " Déconnexion",
                "action": "logout",
                "color": COLOR_GRAY,
                "hover_color": (180, 180, 180),
            },
            {
                "rect": create_button_rect(center_x, start_y + 210, btn_w, btn_h),
                "text": " Quitter",
                "action": "quit",
                "color": COLOR_RED,
                "hover_color": (240, 80, 80),
            },
        ]
        self.hovered_button = None

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered_button = None
            for btn in self.buttons:
                if btn["rect"].collidepoint(event.pos):
                    self.hovered_button = btn
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.buttons:
                if btn["rect"].collidepoint(event.pos):
                    self._handle_action(btn["action"])
                    break

    def _handle_action(self, action: str):
        """Gère les actions des boutons."""
        if action == "booster_shop":
            self.sm.switch_to("booster_shop")
        elif action == "collection":
            self.sm.switch_to("collection")
        elif action == "logout":
            if self.sm.game:
                self.sm.game.logout()
        elif action == "quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def update(self, dt):
        pass

    def draw(self):
        self.surface.fill(COLOR_BG)

        # Titre
        font_title = pygame.font.SysFont("Arial", FONT_SIZE_TITLE, bold=True)
        font_sub = pygame.font.SysFont("Arial", FONT_SIZE_MEDIUM)
        font_btn = pygame.font.SysFont("Arial", FONT_SIZE_MEDIUM, bold=True)
        font_small = pygame.font.SysFont("Arial", FONT_SIZE_SMALL)

        draw_text(self.surface, " CardeGame", SCREEN_WIDTH // 2, 100,
                  font_title, COLOR_GOLD, center=True, shadow=True)

        draw_text(self.surface, "Collection & Trading Card Game",
                  SCREEN_WIDTH // 2, 150, font_sub, COLOR_GRAY, center=True)

        # Infos joueur
        if self.sm.game and self.sm.game.player:
            player = self.sm.game.player
            draw_text(self.surface, f"Bienvenue {player.name} !",
                      SCREEN_WIDTH // 2, 200, font_small, COLOR_WHITE, center=True)
            draw_text(self.surface, f" {player.coins} pièces",
                      SCREEN_WIDTH // 2, 230, font_sub, COLOR_GOLD, center=True)
            draw_text(self.surface, f" {player.collection.count()} cartes",
                      SCREEN_WIDTH // 2, 258, font_small, COLOR_WHITE, center=True)
            # Streak
            if self.sm.game.current_username:
                streak = self.sm.game.account_manager.get_streak(
                    self.sm.game.current_username
                )
                if streak > 0:
                    draw_text(self.surface, f" Streak: {streak} jour(s)",
                              SCREEN_WIDTH // 2, 280, font_small,
                              COLOR_ACCENT, center=True)

        # Boutons
        for btn in self.buttons:
            is_hovered = btn == self.hovered_button
            color = btn["hover_color"] if is_hovered else btn["color"]
            draw_rounded_rect(self.surface, btn["rect"], COLOR_BG_PANEL,
                              radius=12, border_color=color, border_width=3)
            draw_text(self.surface, btn["text"],
                      btn["rect"].centerx, btn["rect"].centery,
                      font_btn, color, center=True)

        # Version
        draw_text(self.surface, "v0.1.0 - Alpha", SCREEN_WIDTH // 2,
                  SCREEN_HEIGHT - 30, font_small, COLOR_DARK_GRAY, center=True)
