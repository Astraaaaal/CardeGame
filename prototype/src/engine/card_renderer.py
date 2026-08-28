"""
CardRenderer — Rendu visuel des cartes avec Pillow.
Layout:
  - Haut-gauche: nom + spécialité (si pas Normal)
  - Haut-droit: type du personnage (badge encadré couleur)
  - Centre: image du personnage
  - Zone description (sous l'image, pas de fond semi-transparent)
  - Bas-gauche: rareté (badge encadré couleur)
  - Bas-droit: gen + set
  - Tout en bas centre: ID court

Bordure:
  - Couleur = couleur du type (Plantes=vert, etc.)
  - Jewelry override si pas "none"
  - full_art = pas de bordure

Effets:
  - Qualité → overlay PNG depuis assets/img/quality/{quality_id}.png
  - Spécialité → overlay PNG depuis assets/img/specialty/{specialty_id}.png
  - Jewelry → overlay PNG depuis assets/img/jewelry/{jewelry_id}.png
"""

import os
import hashlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from typing import Optional
from ..models.card import Card
from ..utils.constants import (
    CHARACTERS_IMG_DIR, BORDERS_IMG_DIR,
    QUALITY_IMG_DIR, SPECIALTY_IMG_DIR, JEWELRY_IMG_DIR,
    CARD_RENDER_WIDTH, CARD_RENDER_HEIGHT, SAVES_DIR
)

# Dossier de cache pour les images rendues
CACHE_DIR = os.path.join(SAVES_DIR, "card_cache")

# Couleurs des types de personnages
TYPE_COLORS = {
    "Plantes": (60, 180, 75),
    "Feu": (220, 60, 40),
    "Eau": (50, 120, 220),
    "Électrique": (255, 210, 50),
    "Ténèbres": (80, 50, 120),
    "Lumière": (255, 240, 180),
    "Glace": (150, 220, 255),
    "Roche": (160, 130, 90),
    "Vent": (170, 220, 200),
    "Poison": (170, 80, 200),
    "Métal": (160, 170, 185),
    "Psychique": (230, 100, 180),
    "Dragon": (100, 60, 200),
    "Fée": (255, 150, 200),
    "Combat": (180, 50, 30),
    "Normal": (150, 150, 150),
}


class CardRenderer:
    """Moteur de rendu des cartes."""

    def __init__(self):
        os.makedirs(CACHE_DIR, exist_ok=True)

    def render_card(self, card: Card) -> str:
        """
        Rend l'image finale d'une carte et retourne le chemin.
        Utilise un cache basé sur le hash des propriétés.
        """
        cache_key = self._get_cache_key(card)
        cache_path = os.path.join(CACHE_DIR, f"{cache_key}.png")

        if os.path.exists(cache_path):
            card.rendered_image_path = cache_path
            return cache_path

        # 1. Image de base avec personnage
        img = self._create_base_image(card)

        # 2. Bordure (type ou jewelry)
        img = self._apply_border(img, card)

        # 3. Overlay jewelry (PNG depuis assets/img/jewelry/)
        img = self._apply_jewelry_effect(img, card.jewelry_id)

        # 4. Overlay spécialité (PNG depuis assets/img/specialty/)
        img = self._apply_specialty_effect(img, card.specialty_id)

        # 5. Texte (layout) — avant la qualité pour que l'usure affecte tout
        img = self._draw_card_text(img, card)

        # 6. Overlay qualité (PNG depuis assets/img/quality/) — en dernier
        img = self._apply_quality_filter(img, card.quality_id)

        img.save(cache_path, "PNG")
        card.rendered_image_path = cache_path
        return cache_path

    def _get_cache_key(self, card: Card) -> str:
        """Génère une clé de cache unique pour la carte."""
        key_data = (
            f"{card.character_id}_{card.rarity_id}_"
            f"{card.quality_id}_{card.specialty_id}_{card.jewelry_id}"
        )
        return hashlib.md5(key_data.encode()).hexdigest()

    def _create_base_image(self, card: Card) -> Image.Image:
        """Crée l'image de base de la carte avec le personnage."""
        W, H = CARD_RENDER_WIDTH, CARD_RENDER_HEIGHT
        img = Image.new("RGBA", (W, H), (30, 30, 45, 255))

        char_img = self._load_character_image(card.image_file)
        if char_img:
            margin = 15
            img_area_w = W - margin * 2
            img_area_h = int(H * 0.55)

            if card.specialty_id == "full_art":
                char_img = char_img.convert("RGBA")
                char_img = char_img.resize((W, H), Image.Resampling.LANCZOS)
                img.paste(char_img, (0, 0), char_img)
            else:
                char_img = char_img.convert("RGBA")
                char_img.thumbnail((img_area_w, img_area_h), Image.Resampling.LANCZOS)
                x_offset = margin + (img_area_w - char_img.width) // 2
                y_offset = 30 + (img_area_h - char_img.height) // 2
                img.paste(char_img, (x_offset, y_offset), char_img)

        return img

    def _load_character_image(self, image_file: str) -> Optional[Image.Image]:
        """Charge l'image d'un personnage."""
        if not image_file:
            return None
        for folder in [CHARACTERS_IMG_DIR,
                       os.path.join(os.path.dirname(CHARACTERS_IMG_DIR), "images")]:
            path = os.path.join(folder, image_file)
            if os.path.exists(path):
                try:
                    return Image.open(path)
                except Exception as e:
                    print(f"[CardRenderer] Erreur chargement image {path}: {e}")
        return None

    def _apply_border(self, img: Image.Image, card: Card) -> Image.Image:
        """Bordure : full_art=aucune, jewelry override, sinon couleur du type."""
        if card.specialty_id == "full_art":
            return img

        W, H = img.size

        # Bordure personnalisée PNG
        border_file = card.jewelry_id if card.jewelry_id != "none" else card.character_type.lower()
        border_path = os.path.join(BORDERS_IMG_DIR, f"{border_file}.png")
        if os.path.exists(border_path):
            try:
                border = Image.open(border_path).convert("RGBA")
                border = border.resize((W, H), Image.Resampling.LANCZOS)
                img = Image.alpha_composite(img, border)
                return img
            except Exception:
                pass

        # Bordure générée par code
        draw = ImageDraw.Draw(img)
        border_width = 6

        if card.jewelry_id != "none":
            color = tuple(card.jewelry_color)
        else:
            color = TYPE_COLORS.get(card.character_type, (100, 100, 120))

        draw.rounded_rectangle(
            [0, 0, W - 1, H - 1], radius=12,
            outline=color, width=border_width
        )
        inner_color = tuple(min(255, c + 40) for c in color)
        draw.rounded_rectangle(
            [border_width, border_width,
             W - 1 - border_width, H - 1 - border_width],
            radius=8, outline=inner_color, width=2
        )
        return img

    def _apply_overlay(self, img: Image.Image,
                       folder: str, overlay_id: str) -> Image.Image:
        """Charge et applique un overlay PNG depuis un dossier donné."""
        overlay_path = os.path.join(folder, f"{overlay_id}.png")
        if os.path.exists(overlay_path):
            try:
                overlay = Image.open(overlay_path).convert("RGBA")
                overlay = overlay.resize(img.size, Image.Resampling.LANCZOS)
                img = Image.alpha_composite(img.convert("RGBA"), overlay)
            except Exception as e:
                print(f"[CardRenderer] Erreur overlay {overlay_path}: {e}")
        return img

    def _apply_jewelry_effect(self, img: Image.Image,
                               jewelry_id: str) -> Image.Image:
        """Applique un overlay jewelry depuis assets/img/jewelry/."""
        if jewelry_id == "none":
            return img
        return self._apply_overlay(img, JEWELRY_IMG_DIR, jewelry_id)

    def _apply_specialty_effect(self, img: Image.Image,
                                  specialty_id: str) -> Image.Image:
        """Applique un overlay spécialité depuis assets/img/specialty/."""
        if specialty_id == "normal":
            return img
        return self._apply_overlay(img, SPECIALTY_IMG_DIR, specialty_id)

    def _apply_quality_filter(self, img: Image.Image,
                               quality_id: str) -> Image.Image:
        """Applique un overlay qualité depuis assets/img/quality/."""
        if quality_id in ("mint", "excellent", "graded", "authentic"):
            return img
        return self._apply_overlay(img, QUALITY_IMG_DIR, quality_id)

    def _draw_card_text(self, img: Image.Image, card: Card) -> Image.Image:
        """
        Layout textuel:
        - Haut-gauche: nom (+spécialité si pas Normal)
        - Haut-droit: type (badge encadré couleur du type)
        - Description sous l'image (pas de fond semi-transparent)
        - Bas-gauche: rareté (badge encadré couleur)
        - Bas-droit: Gen X • Set
        - Bas centre: ID court
        """
        W, H = img.size
        draw = ImageDraw.Draw(img)

        try:
            font_name = ImageFont.truetype("arial.ttf", 13)
            font_medium = ImageFont.truetype("arial.ttf", 11)
            font_small = ImageFont.truetype("arial.ttf", 9)
            font_tiny = ImageFont.truetype("arial.ttf", 8)
        except (IOError, OSError):
            font_name = ImageFont.load_default()
            font_medium = font_name
            font_small = font_name
            font_tiny = font_name

        # Décalage global vers le bas pour le bandeau haut
        header_shift = 4
        margin_x = 16  # un peu plus de marge pour rapprocher du centre

        # --- Bandeau haut supprimé — texte directement sur la carte ---
        top_y = 12 + header_shift  # légèrement plus bas

        # --- Nom en haut-gauche ---
        name_text = card.name
        if card.specialty_id not in ("normal", "full_art"):
            name_text += f" ({card.specialty_name})"
        draw.text((margin_x, top_y), name_text,
                  fill=(255, 255, 255), font=font_name)

        # --- Type en haut-droit (badge encadré, un peu plus à gauche + même décalage bas) ---
        type_text = card.character_type
        type_color = TYPE_COLORS.get(card.character_type, (180, 180, 200))
        t_bbox = draw.textbbox((0, 0), type_text, font=font_medium)
        t_w = t_bbox[2] - t_bbox[0]
        t_h = t_bbox[3] - t_bbox[1]

        badge_padding = 4
        type_x = W - margin_x - t_w
        type_badge_rect = [
            type_x - badge_padding,
            top_y - badge_padding + 1,
            type_x + t_w + badge_padding,
            top_y + t_h + badge_padding + 1
        ]
        draw.rounded_rectangle(type_badge_rect, radius=4,
                               fill=(*type_color, 180))
        draw.text((type_x, top_y), type_text,
                  fill=(255, 255, 255), font=font_medium)

        # --- Zone description (bien descendue pour ne pas mordre sur l'image) ---
        desc_y = int(H * 0.68)

        if card.description and card.quality_id != "Unplayable":
            words = card.description.split()
            lines = []
            current_line = ""
            max_w = W - margin_x * 2
            for word in words:
                test_line = f"{current_line} {word}".strip()
                bbox = draw.textbbox((0, 0), test_line, font=font_small)
                if bbox[2] - bbox[0] <= max_w:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            for i, line in enumerate(lines[:3]):
                draw.text((margin_x, desc_y + i * 13), line,
                          fill=(180, 180, 200), font=font_small)

        # --- Bas de la carte ---
        bottom_y = H - 32  # légèrement plus bas (était -30)

        # Rareté en bas-gauche (badge encadré, légèrement plus à droite)
        rarity_text = card.rarity_name
        r_bbox = draw.textbbox((0, 0), rarity_text, font=font_medium)
        r_w = r_bbox[2] - r_bbox[0]
        r_h = r_bbox[3] - r_bbox[1]

        rarity_x = margin_x  # plus à droite qu'avant (était 10)
        badge_rect = [
            rarity_x - badge_padding,
            bottom_y - badge_padding,
            rarity_x + r_w + badge_padding,
            bottom_y + r_h + badge_padding + 2
        ]
        draw.rounded_rectangle(badge_rect, radius=4,
                               fill=(*card.rarity_color, 180))
        draw.text((rarity_x, bottom_y), rarity_text,
                  fill=(255, 255, 255), font=font_medium)

        # Gen + Set en bas-droit (légèrement plus à gauche)
        gen_set_text = f"Gen {card.gen} • {card.set_name}"
        gs_bbox = draw.textbbox((0, 0), gen_set_text, font=font_small)
        gs_w = gs_bbox[2] - gs_bbox[0]
        draw.text((W - margin_x - gs_w, bottom_y + 2), gen_set_text,
                  fill=(120, 120, 140), font=font_small)

        # ID de la carte en bas au centre (remonté)
        id_text = card.uid[:8]
        id_bbox = draw.textbbox((0, 0), id_text, font=font_tiny)
        id_w = id_bbox[2] - id_bbox[0]
        draw.text(((W - id_w) // 2, H - 18), id_text,
                  fill=(70, 70, 90), font=font_tiny)

        return img
