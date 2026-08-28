"""
PackOpeningScreen — Écran d'ouverture de pack.
Affiche la carte en cours en grand au centre avec animation de révélation.
Supporte l'ouverture de plusieurs packs en séquence (multi-booster).
Bouton skip pour voir la carte la plus rare et passer au suivant.
"""

import os
import pygame
from typing import List, Optional
from .screen_manager import Screen
from ..models.card import Card
from ..utils.constants import *
from ..utils.helpers import (
    draw_text, draw_rounded_rect, create_button_rect,
    ease_out_cubic, scale_image
)


class PackOpeningScreen(Screen):
    """Écran d'ouverture de pack — une carte à la fois en grand."""

    def __init__(self, screen_manager):
        super().__init__(screen_manager)
        # Pack courant
        self.cards: List[Card] = []
        self.card_surfaces: List[Optional[pygame.Surface]] = []
        self.current_card_index: int = 0
        self.animation_timer: float = 0
        self.state: str = "waiting"  # waiting, revealing, shown, skipped
        self.reveal_progress: float = 0
        self.collect_button = None
        self.next_button = None
        self.skip_button = None

        # Multi-packs : liste de packs restants à ouvrir
        self.pending_packs: List[List[Card]] = []
        self.all_opened_cards: List[Card] = []  # toutes les cartes de tous les packs

    def set_cards(self, cards: List[Card],
                  pending_packs: List[List[Card]] = None):
        """Définit les cartes du pack en cours + packs restants."""
        self.cards = cards
        self.card_surfaces = []
        self.current_card_index = 0
        self.state = "waiting"
        self.reveal_progress = 0
        self.pending_packs = pending_packs or []

        # Si c'est le premier pack, initialiser la liste globale
        if not self.all_opened_cards:
            self.all_opened_cards = []

        # Charger les images rendues des cartes
        for card in cards:
            if card.rendered_image_path and os.path.exists(card.rendered_image_path):
                try:
                    img = pygame.image.load(card.rendered_image_path).convert_alpha()
                    self.card_surfaces.append(img)
                except Exception:
                    self.card_surfaces.append(None)
            else:
                self.card_surfaces.append(None)

    def on_enter(self):
        center_x = SCREEN_WIDTH // 2
        self.collect_button = create_button_rect(
            center_x, SCREEN_HEIGHT - 50, 280, 45
        )
        self.next_button = create_button_rect(
            center_x, SCREEN_HEIGHT - 50, 280, 45
        )
        self.skip_button = create_button_rect(
            center_x, SCREEN_HEIGHT - 105, 200, 35
        )

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state == "waiting":
                # Vérifier le bouton skip (seulement avant la 1ère carte)
                if (self.current_card_index == 0 and
                        self.skip_button and
                        self.skip_button.collidepoint(event.pos)):
                    self._skip_pack()
                    return
                # Cliquer pour révéler la carte en cours
                self.state = "revealing"
                self.reveal_progress = 0
                self.animation_timer = 0

            elif self.state == "shown":
                # Carte suivante ou collecter
                if self.current_card_index < len(self.cards) - 1:
                    if self.next_button and self.next_button.collidepoint(event.pos):
                        self.current_card_index += 1
                        self.state = "waiting"
                        self.reveal_progress = 0
                else:
                    if self.collect_button and self.collect_button.collidepoint(event.pos):
                        self._finish_current_pack()

            elif self.state == "skipped":
                # Après le skip, clic pour continuer
                if self.collect_button and self.collect_button.collidepoint(event.pos):
                    self._finish_current_pack()

    def _skip_pack(self):
        """Skip le pack : montre la carte avec la plus faible probabilité."""
        self.state = "skipped"
        # Trouver la carte la plus rare (proba la plus faible)
        if self.cards:
            rarest = min(self.cards, key=lambda c: c.drop_probability)
            rarest_idx = self.cards.index(rarest)
            self.current_card_index = rarest_idx

    def _finish_current_pack(self):
        """Termine le pack en cours : collecte les cartes et passe au suivant."""
        if self.sm.game and self.sm.game.player:
            self.sm.game.player.collection.add_cards(self.cards)
            self.all_opened_cards.extend(self.cards)

        if self.pending_packs:
            # Il reste des packs à ouvrir
            next_pack = self.pending_packs.pop(0)
            self.set_cards(next_pack, self.pending_packs)
        else:
            # Tous les packs sont ouverts — sauvegarder et retourner au shop
            if self.sm.game and self.sm.game.player:
                self.sm.game.player.save()
            self.all_opened_cards = []
            self.sm.switch_to("booster_shop")

    def update(self, dt):
        if self.state == "revealing":
            self.animation_timer += dt
            self.reveal_progress = min(1.0, self.animation_timer / 0.6)

            if self.reveal_progress >= 1.0:
                self.state = "shown"

    def draw(self):
        self.surface.fill(COLOR_BG)

        font_title = pygame.font.SysFont("Arial", FONT_SIZE_LARGE, bold=True)
        font_medium = pygame.font.SysFont("Arial", FONT_SIZE_MEDIUM)
        font_small = pygame.font.SysFont("Arial", FONT_SIZE_SMALL)
        font_tiny = pygame.font.SysFont("Arial", FONT_SIZE_TINY)
        font_btn = pygame.font.SysFont("Arial", FONT_SIZE_MEDIUM, bold=True)

        idx = self.current_card_index
        total = len(self.cards)
        card = self.cards[idx] if idx < total else None
        packs_left = len(self.pending_packs)

        # Titre avec compteur
        if self.state == "skipped":
            title = ""
        else:
            title = f"Carte {idx + 1} / {total}"
        if packs_left > 0:
            title += f"  (encore {packs_left} pack{'s' if packs_left > 1 else ''})"
        draw_text(self.surface, title,
                  SCREEN_WIDTH // 2, 25, font_title, COLOR_WHITE, center=True)

        if not card:
            return

        # Zone centrale pour la carte en grand (agrandie)
        big_w = CARD_RENDER_WIDTH + 60
        big_h = CARD_RENDER_HEIGHT + 60
        big_x = (SCREEN_WIDTH - big_w) // 2
        big_y = 50

        if self.state == "waiting":
            # Carte face cachée — grande
            rect = pygame.Rect(big_x, big_y, big_w, big_h)
            draw_rounded_rect(self.surface, rect, (45, 45, 70), radius=12,
                              border_color=(100, 100, 140), border_width=3)
            font_q = pygame.font.SysFont("Arial", 48, bold=True)
            draw_text(self.surface, "?", rect.centerx, rect.centery,
                      font_q, COLOR_GRAY, center=True)
            draw_text(self.surface, "Cliquez pour révéler",
                      rect.centerx, rect.centery + 50,
                      font_small, COLOR_DARK_GRAY, center=True)

            # Bouton skip (seulement avant la 1ère carte)
            if self.skip_button and self.current_card_index == 0:
                draw_rounded_rect(self.surface, self.skip_button,
                                  COLOR_BG_PANEL, radius=8,
                                  border_color=COLOR_GRAY, border_width=2)
                draw_text(self.surface, "Skip >>",
                          self.skip_button.centerx,
                          self.skip_button.centery,
                          font_small, COLOR_GRAY, center=True)

        elif self.state == "revealing":
            # Animation de révélation
            progress = ease_out_cubic(self.reveal_progress)
            scale = 0.3 + 0.7 * progress
            alpha = int(255 * progress)

            sw = int(big_w * scale)
            sh = int(big_h * scale)
            sx = big_x + (big_w - sw) // 2
            sy = big_y + (big_h - sh) // 2

            # Glow de la rareté
            glow_rect = pygame.Rect(sx - 4, sy - 4, sw + 8, sh + 8)
            glow_color = tuple(int(c * progress) for c in card.rarity_color)
            draw_rounded_rect(self.surface, glow_rect, (30, 30, 50),
                              radius=14, border_color=glow_color,
                              border_width=4)

            # Image de la carte avec scale
            if idx < len(self.card_surfaces) and self.card_surfaces[idx]:
                scaled_img = pygame.transform.smoothscale(
                    self.card_surfaces[idx], (sw, sh)
                )
                scaled_img.set_alpha(alpha)
                self.surface.blit(scaled_img, (sx, sy))
            else:
                rect = pygame.Rect(sx, sy, sw, sh)
                draw_rounded_rect(self.surface, rect, COLOR_BG_PANEL,
                                  radius=10, border_color=glow_color,
                                  border_width=3)

        elif self.state in ("shown", "skipped"):
            # Carte révélée en grand
            if idx < len(self.card_surfaces) and self.card_surfaces[idx]:
                big_img = pygame.transform.smoothscale(
                    self.card_surfaces[idx], (big_w, big_h)
                )
                self.surface.blit(big_img, (big_x, big_y))
            else:
                rect = pygame.Rect(big_x, big_y, big_w, big_h)
                draw_rounded_rect(self.surface, rect, COLOR_BG_PANEL,
                                  radius=10,
                                  border_color=card.rarity_color,
                                  border_width=3)
                draw_text(self.surface, card.name,
                          rect.centerx, rect.centery,
                          font_medium, COLOR_WHITE, center=True)

            # Bouton suivant / collecter / pack suivant
            if self.state == "shown" and idx < total - 1:
                draw_rounded_rect(self.surface, self.next_button,
                                  COLOR_BG_PANEL, radius=10,
                                  border_color=COLOR_ACCENT, border_width=3)
                draw_text(self.surface,
                          f"Carte suivante ({idx + 2}/{total})",
                          self.next_button.centerx,
                          self.next_button.centery,
                          font_btn, COLOR_ACCENT, center=True)
            else:
                # Dernière carte ou skip
                if packs_left > 0:
                    btn_text = f"Pack suivant ({packs_left} restant{'s' if packs_left > 1 else ''})"
                    btn_color = COLOR_ACCENT
                else:
                    btn_text = "Collecter et retour au shop"
                    btn_color = COLOR_GREEN
                draw_rounded_rect(self.surface, self.collect_button,
                                  COLOR_BG_PANEL, radius=10,
                                  border_color=btn_color, border_width=3)
                draw_text(self.surface, btn_text,
                          self.collect_button.centerx,
                          self.collect_button.centery,
                          font_btn, btn_color, center=True)
