"""
BoosterShopScreen — Écran de la boutique de boosters.
Le joueur choisit quel pack acheter (x1, x5 avec -10%, x10 avec -15%).
"""

import math
import pygame
from .screen_manager import Screen
from ..utils.constants import *
from ..utils.helpers import draw_text, draw_rounded_rect, create_button_rect


class BoosterShopScreen(Screen):
    """Boutique où le joueur achète des boosters."""

    def __init__(self, screen_manager):
        super().__init__(screen_manager)
        self.booster_buttons = []  # boutons principaux (booster info)
        self.back_button = None
        self.hovered = None
        self.message = ""
        self.message_timer = 0
        self.message_color = COLOR_RED

    def on_enter(self):
        """Construit les boutons des boosters disponibles."""
        self.booster_buttons = []
        self.message = ""

        if not self.sm.game:
            return

        boosters = self.sm.game.data_manager.boosters
        start_y = 130
        center_x = SCREEN_WIDTH // 2

        for i, booster in enumerate(boosters):
            base_price = booster.get("price", 100)
            price_x5 = math.floor(base_price * 5 * 0.90)
            price_x10 = math.floor(base_price * 10 * 0.85)

            row_y = start_y + i * 120

            # Bouton principal (x1)
            btn_x1 = pygame.Rect(center_x - 175, row_y, 350, 55)
            # Boutons x5 et x10 sous le principal
            btn_x5 = pygame.Rect(center_x - 175, row_y + 58, 170, 30)
            btn_x10 = pygame.Rect(center_x + 5, row_y + 58, 170, 30)

            self.booster_buttons.append({
                "btn_x1": btn_x1,
                "btn_x5": btn_x5,
                "btn_x10": btn_x10,
                "booster": booster,
                "price_x1": base_price,
                "price_x5": price_x5,
                "price_x10": price_x10,
            })

        self.back_button = create_button_rect(
            center_x, SCREEN_HEIGHT - 40, 200, 40
        )

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = None
            for btn in self.booster_buttons:
                for key in ("btn_x1", "btn_x5", "btn_x10"):
                    if btn[key].collidepoint(event.pos):
                        self.hovered = (btn, key)
                        break
            if self.back_button and self.back_button.collidepoint(event.pos):
                self.hovered = "back"

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Bouton retour
            if self.back_button and self.back_button.collidepoint(event.pos):
                self.sm.switch_to("main_menu")
                return

            # Boutons boosters
            for btn in self.booster_buttons:
                if btn["btn_x1"].collidepoint(event.pos):
                    self._buy_booster(btn["booster"], 1, btn["price_x1"])
                    return
                elif btn["btn_x5"].collidepoint(event.pos):
                    self._buy_booster(btn["booster"], 5, btn["price_x5"])
                    return
                elif btn["btn_x10"].collidepoint(event.pos):
                    self._buy_booster(btn["booster"], 10, btn["price_x10"])
                    return

    def _buy_booster(self, booster: dict, quantity: int, total_price: int):
        """Achète et ouvre un ou plusieurs boosters."""
        if not self.sm.game:
            return

        player = self.sm.game.player

        if not player.can_afford(total_price):
            self.message = f"Pas assez de pièces ! (besoin de {total_price})"
            self.message_color = COLOR_RED
            self.message_timer = 2.0
            return

        # Payer
        player.spend(total_price)

        # Générer tous les packs
        all_packs = []
        for _ in range(quantity):
            cards = self.sm.game.card_generator.generate_pack(booster["id"])
            if not cards:
                self.message = "Aucune carte dans ce set !"
                self.message_color = COLOR_RED
                self.message_timer = 2.0
                player.earn(total_price)
                return
            # Rendre les cartes visuellement
            for card in cards:
                self.sm.game.card_renderer.render_card(card)
            all_packs.append(cards)

        # Stocker dans le pack_opening screen
        pack_screen = self.sm.screens.get("pack_opening")
        if pack_screen:
            first_pack = all_packs.pop(0)
            pack_screen.all_opened_cards = []
            pack_screen.set_cards(first_pack, pending_packs=all_packs)
            player.packs_opened += quantity
            player.total_cards_obtained += sum(len(p) for p in [first_pack] + all_packs)
            self.sm.switch_to("pack_opening")

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

    def draw(self):
        self.surface.fill(COLOR_BG)

        font_title = pygame.font.SysFont("Arial", FONT_SIZE_LARGE, bold=True)
        font_medium = pygame.font.SysFont("Arial", FONT_SIZE_MEDIUM)
        font_small = pygame.font.SysFont("Arial", FONT_SIZE_SMALL)
        font_tiny = pygame.font.SysFont("Arial", FONT_SIZE_TINY)
        font_btn = pygame.font.SysFont("Arial", FONT_SIZE_SMALL, bold=True)

        # Titre
        draw_text(self.surface, "Boutique de Boosters",
                  SCREEN_WIDTH // 2, 30, font_title, COLOR_ACCENT, center=True)

        # Pièces du joueur
        if self.sm.game and self.sm.game.player:
            draw_text(self.surface,
                      f"{self.sm.game.player.coins} pièces",
                      SCREEN_WIDTH // 2, 65, font_medium, COLOR_GOLD,
                      center=True)

        # Message d'erreur/info
        if self.message:
            draw_text(self.surface, self.message,
                      SCREEN_WIDTH // 2, 95, font_small,
                      self.message_color, center=True)

        # Boutons des boosters
        for entry in self.booster_buttons:
            booster = entry["booster"]
            btn_x1 = entry["btn_x1"]
            btn_x5 = entry["btn_x5"]
            btn_x10 = entry["btn_x10"]

            is_hovered_x1 = (self.hovered == (entry, "btn_x1"))
            is_hovered_x5 = (self.hovered == (entry, "btn_x5"))
            is_hovered_x10 = (self.hovered == (entry, "btn_x10"))

            # --- Bouton principal x1 ---
            border_col = COLOR_ACCENT_HOVER if is_hovered_x1 else COLOR_ACCENT
            draw_rounded_rect(self.surface, btn_x1, COLOR_BG_PANEL,
                              radius=10, border_color=border_col, border_width=2)

            # Nom du booster
            draw_text(self.surface, booster["name"],
                      btn_x1.x + 15, btn_x1.y + 8,
                      font_medium, COLOR_WHITE)

            # Description courte
            desc = booster.get("description", "")
            if len(desc) > 40:
                desc = desc[:37] + "..."
            draw_text(self.surface, desc,
                      btn_x1.x + 15, btn_x1.y + 30,
                      font_tiny, COLOR_GRAY)

            # Prix x1 à droite
            draw_text(self.surface, f"{entry['price_x1']}",
                      btn_x1.right - 60, btn_x1.y + 18,
                      font_btn, COLOR_GOLD)

            # --- Bouton x5 ---
            border_5 = COLOR_ACCENT_HOVER if is_hovered_x5 else (100, 160, 220)
            draw_rounded_rect(self.surface, btn_x5, COLOR_BG_PANEL,
                              radius=6, border_color=border_5, border_width=2)
            draw_text(self.surface,
                      f"x5  {entry['price_x5']} (-10%)",
                      btn_x5.centerx, btn_x5.centery,
                      font_tiny, (100, 180, 255), center=True)

            # --- Bouton x10 ---
            border_10 = COLOR_ACCENT_HOVER if is_hovered_x10 else (180, 120, 220)
            draw_rounded_rect(self.surface, btn_x10, COLOR_BG_PANEL,
                              radius=6, border_color=border_10, border_width=2)
            draw_text(self.surface,
                      f"x10  {entry['price_x10']} (-15%)",
                      btn_x10.centerx, btn_x10.centery,
                      font_tiny, (200, 140, 255), center=True)

        # Bouton retour
        if self.back_button:
            draw_rounded_rect(self.surface, self.back_button, COLOR_BG_PANEL,
                              radius=8, border_color=COLOR_RED, border_width=2)
            draw_text(self.surface, "Retour",
                      self.back_button.centerx, self.back_button.centery,
                      font_btn, COLOR_RED, center=True)
