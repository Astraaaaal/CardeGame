"""
Constantes globales du jeu CardeGame.
"""

import os

# --- Chemins ---
# __file__ = <repo>/prototype/src/utils/constants.py  →  4 remontées = racine du dépôt.
# assets/ et saves/ sont partagés à la racine (pas dans prototype/).
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(ASSETS_DIR, "data")
IMG_DIR = os.path.join(ASSETS_DIR, "img")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
SAVES_DIR = os.path.join(BASE_DIR, "saves")

# Sous-dossiers images
CHARACTERS_IMG_DIR = os.path.join(IMG_DIR, "characters")
BORDERS_IMG_DIR = os.path.join(IMG_DIR, "borders")
OVERLAYS_IMG_DIR = os.path.join(IMG_DIR, "overlays")
QUALITY_IMG_DIR = os.path.join(IMG_DIR, "quality")
SPECIALTY_IMG_DIR = os.path.join(IMG_DIR, "specialty")
JEWELRY_IMG_DIR = os.path.join(IMG_DIR, "jewelry")
BACKS_IMG_DIR = os.path.join(IMG_DIR, "backs")
UI_IMG_DIR = os.path.join(IMG_DIR, "ui")

# --- Écran (ratio 9:16 type téléphone) ---
SCREEN_WIDTH = 405
SCREEN_HEIGHT = 720
FPS = 60

# --- Taille des cartes ---
CARD_WIDTH = 120
CARD_HEIGHT = 168
CARD_RENDER_WIDTH = 240   # Taille de rendu interne (haute qualité)
CARD_RENDER_HEIGHT = 336

# --- Couleurs ---
COLOR_BG = (25, 25, 35)
COLOR_BG_LIGHT = (35, 35, 50)
COLOR_BG_PANEL = (40, 40, 60)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GRAY = (150, 150, 150)
COLOR_DARK_GRAY = (80, 80, 80)
COLOR_ACCENT = (80, 160, 255)
COLOR_ACCENT_HOVER = (100, 180, 255)
COLOR_GOLD = (255, 200, 50)
COLOR_GREEN = (80, 200, 120)
COLOR_RED = (220, 60, 60)

# --- Textes ---
GAME_TITLE = "CardeGame"
FONT_SIZE_TITLE = 36
FONT_SIZE_LARGE = 24
FONT_SIZE_MEDIUM = 18
FONT_SIZE_SMALL = 14
FONT_SIZE_TINY = 11

# --- Pack ---
CARDS_PER_PACK = 5

# --- Animation ---
ANIM_CARD_FLIP_SPEED = 8     # Vitesse de retournement
ANIM_CARD_REVEAL_DELAY = 300  # ms entre chaque carte révélée
