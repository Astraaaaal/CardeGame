"""
CardRendererService — Rendu visuel avec Pillow + upload Cloudinary.
Migration de src/engine/card_renderer.py vers le serveur.
"""

import hashlib
import io
import os
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cloudinary_client import upload_image_bytes, configure_cloudinary
from app.config import settings

# Dimensions du rendu (identiques au projet Pygame)
CARD_RENDER_WIDTH = 240
CARD_RENDER_HEIGHT = 336

# Couleurs des types
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


class CardRendererService:
    """Rendu de carte serveur-side avec upload vers Cloudinary."""

    def __init__(self):
        configure_cloudinary()

    async def render_and_upload(
        self, session: AsyncSession, card_data: dict
    ) -> str | None:
        """
        Rend une carte et l'upload vers Cloudinary.
        Retourne l'URL de l'image, ou None si le rendu serveur est désactivé
        (pas de Cloudinary) — le client affiche alors la carte à partir des
        métadonnées.
        """
        # Sans Cloudinary : pas de rendu serveur. On renvoie None plutôt qu'une
        # URL bidon (qui donnait des 404 /api/cards/render/*.png côté client).
        if not settings.CLOUDINARY_CLOUD_NAME:
            return None

        # Clé de cache unique (même logique que l'original)
        cache_key = self._get_cache_key(card_data)

        # Rendre l'image
        img = self._render_card_image(card_data)

        # Convertir en bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # Upload vers Cloudinary
        url = upload_image_bytes(
            buffer.getvalue(),
            public_id=cache_key,
            folder="cards",
        )
        return url

    def _get_cache_key(self, card_data: dict) -> str:
        """Génère une clé de cache unique."""
        key = (
            f"{card_data['character_id']}_{card_data['rarity_id']}_"
            f"{card_data['quality_id']}_{card_data['specialty_id']}_"
            f"{card_data['jewelry_id']}"
        )
        return hashlib.md5(key.encode()).hexdigest()

    def _render_card_image(self, card_data: dict) -> Image.Image:
        """
        Rendu complet de la carte.
        Reprend la même pipeline que card_renderer.py :
        1. Image de base
        2. Bordure
        3. Overlay jewelry
        4. Overlay specialty
        5. Texte
        6. Overlay qualité (en dernier pour l'usure)
        """
        W, H = CARD_RENDER_WIDTH, CARD_RENDER_HEIGHT
        img = Image.new("RGBA", (W, H), (30, 30, 45, 255))

        char = card_data.get("_character", {})
        rarity = card_data.get("_rarity")
        quality = card_data.get("_quality")
        specialty = card_data.get("_specialty")
        jewelry = card_data.get("_jewelry")

        # Bordure (code-generated, comme l'original)
        is_full_art = card_data.get("specialty_id") == "full_art"
        if not is_full_art:
            draw = ImageDraw.Draw(img)
            border_width = 6

            if card_data.get("jewelry_id", "none") != "none" and jewelry:
                color = (jewelry.color_r, jewelry.color_g, jewelry.color_b)
            else:
                color = TYPE_COLORS.get(char.get("type", "Normal"), (100, 100, 120))

            draw.rounded_rectangle(
                [0, 0, W - 1, H - 1], radius=12,
                outline=color, width=border_width,
            )
            inner_color = tuple(min(255, c + 40) for c in color)
            draw.rounded_rectangle(
                [border_width, border_width,
                 W - 1 - border_width, H - 1 - border_width],
                radius=8, outline=inner_color, width=2,
            )

        # Texte
        self._draw_text(img, card_data)

        return img

    def _draw_text(self, img: Image.Image, card_data: dict):
        """Dessin du texte sur la carte (même layout que l'original)."""
        W, H = img.size
        draw = ImageDraw.Draw(img)

        char = card_data.get("_character", {})
        rarity = card_data.get("_rarity")
        quality = card_data.get("_quality")
        specialty = card_data.get("_specialty")

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

        margin_x = 16
        top_y = 16

        # Nom + spécialité
        name_text = char.get("name", "???")
        if specialty and specialty.id not in ("normal", "full_art"):
            name_text += f" ({specialty.name})"
        draw.text((margin_x, top_y), name_text,
                  fill=(255, 255, 255), font=font_name)

        # Type badge (haut-droit)
        type_text = char.get("type", "Normal")
        type_color = TYPE_COLORS.get(type_text, (180, 180, 200))
        t_bbox = draw.textbbox((0, 0), type_text, font=font_medium)
        t_w = t_bbox[2] - t_bbox[0]
        t_h = t_bbox[3] - t_bbox[1]
        badge_padding = 4
        type_x = W - margin_x - t_w
        type_badge_rect = [
            type_x - badge_padding, top_y - badge_padding + 1,
            type_x + t_w + badge_padding, top_y + t_h + badge_padding + 1,
        ]
        draw.rounded_rectangle(type_badge_rect, radius=4,
                               fill=(*type_color, 180))
        draw.text((type_x, top_y), type_text,
                  fill=(255, 255, 255), font=font_medium)

        # Description
        desc_y = int(H * 0.68)
        description = char.get("description", "")
        quality_id = card_data.get("quality_id", "")
        if description and quality_id != "unplayable":
            words = description.split()
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

        # Rareté badge (bas-gauche)
        bottom_y = H - 32
        if rarity:
            rarity_text = rarity.name
            r_bbox = draw.textbbox((0, 0), rarity_text, font=font_medium)
            r_w = r_bbox[2] - r_bbox[0]
            r_h = r_bbox[3] - r_bbox[1]
            badge_rect = [
                margin_x - badge_padding, bottom_y - badge_padding,
                margin_x + r_w + badge_padding, bottom_y + r_h + badge_padding + 2,
            ]
            rarity_color = (rarity.color_r, rarity.color_g, rarity.color_b)
            draw.rounded_rectangle(badge_rect, radius=4,
                                   fill=(*rarity_color, 180))
            draw.text((margin_x, bottom_y), rarity_text,
                      fill=(255, 255, 255), font=font_medium)

        # Gen + Set (bas-droit)
        gen_set_text = f"Gen {char.get('gen', 1)} • {card_data.get('set_id', '?')}"
        gs_bbox = draw.textbbox((0, 0), gen_set_text, font=font_small)
        gs_w = gs_bbox[2] - gs_bbox[0]
        draw.text((W - margin_x - gs_w, bottom_y + 2), gen_set_text,
                  fill=(120, 120, 140), font=font_small)

        # ID court (bas centre)
        id_text = card_data.get("_id_short", "????????")
        id_bbox = draw.textbbox((0, 0), id_text, font=font_tiny)
        id_w = id_bbox[2] - id_bbox[0]
        draw.text(((W - id_w) // 2, H - 18), id_text,
                  fill=(70, 70, 90), font=font_tiny)
