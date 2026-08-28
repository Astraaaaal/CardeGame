"""
CollectionScreen — Écran d'inventaire du joueur.
Affiche toutes les cartes possédées avec filtrage et détails.
Les cartes identiques sont regroupées (même personnage + rareté + qualité + spécialité).
"""

import os
import pygame
from typing import List, Optional, Dict, Tuple
from .screen_manager import Screen
from ..models.card import Card
from ..utils.constants import *
from ..utils.helpers import (
    draw_text, draw_rounded_rect, create_button_rect, scale_image
)


def _card_group_key(card: Card) -> Tuple[str, str, str, str, str]:
    """Clé de regroupement : même personnage + rareté + qualité + spécialité + jewelry."""
    return (card.character_id, card.rarity_id, card.quality_id,
            card.specialty_id, card.jewelry_id)


class CollectionScreen(Screen):
    """Écran de la collection du joueur."""

    def __init__(self, screen_manager):
        super().__init__(screen_manager)
        self.displayed_cards: List[Card] = []  # une carte par groupe
        self.card_counts: Dict[Tuple, int] = {}  # clé → nombre d'exemplaires
        self.card_surfaces: dict = {}  # uid -> Surface
        self.scroll_offset: int = 0
        self.selected_card: Optional[Card] = None
        self.selected_surface: Optional[pygame.Surface] = None
        self.selected_count: int = 1
        self.back_button = None

        # Grille
        self.cols = 3
        self.card_w = CARD_WIDTH
        self.card_h = CARD_HEIGHT
        self.padding = 10
        self.grid_start_y = 100

        # Filtres
        self.current_filter = "all"
        self.filter_buttons = []
        self.sort_mode = "rarity"

    def on_enter(self):
        """Charge les cartes à afficher (regroupées)."""
        self.selected_card = None
        self.scroll_offset = 0

        if self.sm.game and self.sm.game.player:
            col = self.sm.game.player.collection
            # Trier d'abord
            if self.sort_mode == "rarity":
                sorted_cards = col.sort_by_rarity()
            elif self.sort_mode == "probability":
                sorted_cards = col.sort_by_probability()
            elif self.sort_mode == "quality":
                sorted_cards = col.sort_by_quality()
            elif self.sort_mode == "specialty":
                sorted_cards = col.sort_by_specialty()
            elif self.sort_mode == "jewelry":
                sorted_cards = col.sort_by_jewelry()
            else:
                sorted_cards = col.sort_by_name()

            # Regrouper les cartes identiques
            self._group_cards(sorted_cards)
        else:
            self.displayed_cards = []
            self.card_counts = {}

        # Charger les surfaces des cartes (une par groupe)
        self.card_surfaces = {}
        for card in self.displayed_cards:
            if (card.rendered_image_path and
                    os.path.exists(card.rendered_image_path)):
                try:
                    img = pygame.image.load(
                        card.rendered_image_path
                    ).convert_alpha()
                    self.card_surfaces[card.uid] = img
                except Exception:
                    pass

        # Boutons
        center_x = SCREEN_WIDTH // 2
        self.back_button = create_button_rect(
            center_x, SCREEN_HEIGHT - 30, 200, 36
        )

        # Boutons de filtre/tri
        self._build_filter_buttons()

    def _group_cards(self, sorted_cards: List[Card]):
        """Regroupe les cartes identiques, garde un représentant par groupe."""
        seen: Dict[Tuple, Card] = {}
        self.card_counts = {}

        for card in sorted_cards:
            key = _card_group_key(card)
            if key not in seen:
                seen[key] = card
                self.card_counts[key] = 1
            else:
                self.card_counts[key] += 1

        # L'ordre est préservé car on itère sur sorted_cards
        self.displayed_cards = list(seen.values())

    def _build_filter_buttons(self):
        """Construit les boutons de filtrage."""
        filters = [
            ("all", "Toutes"),
            ("rarity", "Rareté"),
            ("name", "Nom"),
            ("probability", "Proba"),
            ("quality", "Qualité"),
            ("specialty", "Spécia."),
            ("jewelry", "Jewelry"),
        ]
        self.filter_buttons = []
        btn_w = 53
        start_x = 3
        for i, (fid, fname) in enumerate(filters):
            rect = pygame.Rect(start_x + i * (btn_w + 3), 55, btn_w, 28)
            self.filter_buttons.append({
                "rect": rect,
                "filter_id": fid,
                "text": fname,
            })

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Bouton retour
                if (self.back_button and
                        self.back_button.collidepoint(event.pos)):
                    self.sm.switch_to("main_menu")
                    return

                # Si une carte est sélectionnée, cliquer n'importe où ferme
                if self.selected_card:
                    self.selected_card = None
                    self.selected_surface = None
                    return

                # Filtres
                for fb in self.filter_buttons:
                    if fb["rect"].collidepoint(event.pos):
                        self._apply_filter(fb["filter_id"])
                        return

                # Clic sur une carte
                self._check_card_click(event.pos)

            # Scroll
            elif event.button == 4:  # Scroll up
                self.scroll_offset = max(0, self.scroll_offset - 40)
            elif event.button == 5:  # Scroll down
                max_scroll = self._get_max_scroll()
                self.scroll_offset = min(max_scroll, self.scroll_offset + 40)

    def _apply_filter(self, filter_id: str):
        """Applique un filtre/tri."""
        if filter_id == "rarity":
            self.sort_mode = "rarity"
        elif filter_id == "name":
            self.sort_mode = "name"
        elif filter_id == "probability":
            self.sort_mode = "probability"
        elif filter_id == "quality":
            self.sort_mode = "quality"
        elif filter_id == "specialty":
            self.sort_mode = "specialty"
        elif filter_id == "jewelry":
            self.sort_mode = "jewelry"
        self.current_filter = filter_id
        self.on_enter()  # Recharger

    def _check_card_click(self, pos):
        """Vérifie si le clic est sur une carte."""
        for i, card in enumerate(self.displayed_cards):
            col = i % self.cols
            row = i // self.cols
            x = self.padding + col * (self.card_w + self.padding)
            y = (self.grid_start_y + row * (self.card_h + self.padding)
                 - self.scroll_offset)

            rect = pygame.Rect(x, y, self.card_w, self.card_h)
            if rect.collidepoint(pos) and y > 50 and y < SCREEN_HEIGHT - 60:
                self.selected_card = card
                key = _card_group_key(card)
                self.selected_count = self.card_counts.get(key, 1)
                if card.uid in self.card_surfaces:
                    self.selected_surface = self.card_surfaces[card.uid]
                else:
                    self.selected_surface = None
                break

    def _get_max_scroll(self) -> int:
        """Calcule le scroll maximum."""
        rows = (len(self.displayed_cards) + self.cols - 1) // self.cols
        total_h = rows * (self.card_h + self.padding) + self.grid_start_y
        return max(0, total_h - SCREEN_HEIGHT + 80)

    def update(self, dt):
        pass

    def draw(self):
        self.surface.fill(COLOR_BG)

        font_title = pygame.font.SysFont("Arial", FONT_SIZE_LARGE, bold=True)
        font_medium = pygame.font.SysFont("Arial", FONT_SIZE_MEDIUM)
        font_small = pygame.font.SysFont("Arial", FONT_SIZE_SMALL)
        font_tiny = pygame.font.SysFont("Arial", FONT_SIZE_TINY)
        font_btn = pygame.font.SysFont("Arial", FONT_SIZE_SMALL, bold=True)

        # Titre — nombre total (toutes cartes, pas groupées)
        total_count = sum(self.card_counts.values()) if self.card_counts else 0
        unique_count = len(self.displayed_cards)
        draw_text(self.surface,
                  f"Ma Collection ({total_count} | {unique_count} uniques)",
                  SCREEN_WIDTH // 2, 22, font_title, COLOR_WHITE, center=True)

        # Boutons de filtre
        for fb in self.filter_buttons:
            is_active = fb["filter_id"] == self.current_filter
            color = COLOR_ACCENT if is_active else COLOR_DARK_GRAY
            draw_rounded_rect(self.surface, fb["rect"], COLOR_BG_PANEL,
                              radius=6, border_color=color, border_width=2)
            draw_text(self.surface, fb["text"],
                      fb["rect"].centerx, fb["rect"].centery,
                      font_tiny, color, center=True)

        # Grille de cartes
        clip_rect = pygame.Rect(0, 90, SCREEN_WIDTH, SCREEN_HEIGHT - 150)
        self.surface.set_clip(clip_rect)

        for i, card in enumerate(self.displayed_cards):
            col_idx = i % self.cols
            row = i // self.cols
            x = self.padding + col_idx * (self.card_w + self.padding)
            y = (self.grid_start_y + row * (self.card_h + self.padding)
                 - self.scroll_offset)

            # Ne dessiner que les cartes visibles
            if y + self.card_h < 90 or y > SCREEN_HEIGHT - 60:
                continue

            if card.uid in self.card_surfaces:
                mini = pygame.transform.smoothscale(
                    self.card_surfaces[card.uid],
                    (self.card_w, self.card_h)
                )
                self.surface.blit(mini, (x, y))
            else:
                rect = pygame.Rect(x, y, self.card_w, self.card_h)
                draw_rounded_rect(self.surface, rect, COLOR_BG_PANEL,
                                  radius=6,
                                  border_color=card.rarity_color,
                                  border_width=2)
                draw_text(self.surface, card.name[:10],
                          rect.centerx, rect.centery,
                          font_tiny, COLOR_WHITE, center=True)

            # Badge de quantité si > 1
            key = _card_group_key(card)
            count = self.card_counts.get(key, 1)
            if count > 1:
                badge_text = f"x{count}"
                badge_w = font_tiny.size(badge_text)[0] + 8
                badge_rect = pygame.Rect(
                    x + self.card_w - badge_w - 2, y + 2,
                    badge_w, 18
                )
                pygame.draw.rect(self.surface, (0, 0, 0, 200), badge_rect,
                                 border_radius=4)
                draw_rounded_rect(self.surface, badge_rect, (30, 30, 50),
                                  radius=4, border_color=COLOR_GOLD,
                                  border_width=1)
                draw_text(self.surface, badge_text,
                          badge_rect.centerx, badge_rect.centery,
                          font_tiny, COLOR_GOLD, center=True)

        self.surface.set_clip(None)

        # Bouton retour
        if self.back_button:
            draw_rounded_rect(self.surface, self.back_button, COLOR_BG_PANEL,
                              radius=8, border_color=COLOR_RED, border_width=2)
            draw_text(self.surface, "Retour",
                      self.back_button.centerx, self.back_button.centery,
                      font_btn, COLOR_RED, center=True)

        # Popup de détail de carte
        if self.selected_card:
            self._draw_card_detail(font_medium, font_small, font_tiny)

    def _draw_card_detail(self, font_medium, font_small, font_tiny):
        """Dessine la popup de détail d'une carte sélectionnée."""
        card = self.selected_card

        # Fond semi-transparent
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.surface.blit(overlay, (0, 0))

        # Panneau
        panel_w, panel_h = 300, 570
        panel_x = (SCREEN_WIDTH - panel_w) // 2
        panel_y = (SCREEN_HEIGHT - panel_h) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        draw_rounded_rect(self.surface, panel_rect, COLOR_BG_PANEL,
                          radius=12, border_color=card.rarity_color,
                          border_width=3)

        # Image de la carte en grand
        img_w = CARD_RENDER_WIDTH
        img_h = CARD_RENDER_HEIGHT
        img_x = panel_x + (panel_w - img_w) // 2
        img_y = panel_y + 15

        if self.selected_surface:
            big = pygame.transform.smoothscale(
                self.selected_surface, (img_w, img_h)
            )
            self.surface.blit(big, (img_x, img_y))
        else:
            img_rect = pygame.Rect(img_x, img_y, img_w, img_h)
            draw_rounded_rect(self.surface, img_rect, COLOR_BG_LIGHT,
                              radius=8, border_color=card.rarity_color,
                              border_width=2)
            draw_text(self.surface, card.name,
                      img_rect.centerx, img_rect.centery,
                      font_medium, COLOR_WHITE, center=True)

        # Infos sous l'image
        info_y = img_y + img_h + 10
        center_x = panel_x + panel_w // 2

        draw_text(self.surface, card.name, center_x, info_y,
                  font_medium, COLOR_WHITE, center=True, shadow=True)
        draw_text(self.surface, card.rarity_name, center_x, info_y + 24,
                  font_small, card.rarity_color, center=True)
        draw_text(self.surface, f"{card.specialty_name}",
                  center_x, info_y + 44,
                  font_small, (200, 200, 220), center=True)
        # Jewelry (seulement si pas "none")
        jewelry_text = card.jewelry_name if card.jewelry_id != "none" else ""
        if jewelry_text:
            draw_text(self.surface, jewelry_text,
                      center_x, info_y + 62,
                      font_small, tuple(card.jewelry_color), center=True)
            next_y = info_y + 80
        else:
            next_y = info_y + 62
        draw_text(self.surface, f"{card.quality_name}",
                  center_x, next_y,
                  font_small, (160, 160, 180), center=True)
        draw_text(self.surface, f"{card.set_name}  {card.character_type}",
                  center_x, next_y + 22,
                  font_tiny, COLOR_GRAY, center=True)

        # Nombre d'exemplaires
        if self.selected_count > 1:
            draw_text(self.surface,
                      f"x{self.selected_count} exemplaires",
                      center_x, next_y + 44,
                      font_small, COLOR_GOLD, center=True)
        else:
            draw_text(self.surface, "x1 exemplaire",
                      center_x, next_y + 44,
                      font_small, COLOR_GRAY, center=True)

        # Probabilité d'obtention
        prob_text = f"Probabilité: {card.drop_probability:.4f}%"
        draw_text(self.surface, prob_text,
                  center_x, next_y + 66,
                  font_small, COLOR_ACCENT, center=True)

        draw_text(self.surface, "Cliquez pour fermer",
                  center_x, next_y + 90,
                  font_tiny, COLOR_DARK_GRAY, center=True)
