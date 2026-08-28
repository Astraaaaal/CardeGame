"""
Fonctions utilitaires.
"""

import pygame


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Limite une valeur entre min et max."""
    return max(min_val, min(max_val, value))


def lerp(a: float, b: float, t: float) -> float:
    """Interpolation linéaire entre a et b."""
    return a + (b - a) * clamp(t, 0.0, 1.0)


def ease_out_cubic(t: float) -> float:
    """Courbe d'easing out cubique pour animations fluides."""
    t = clamp(t, 0.0, 1.0)
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_quad(t: float) -> float:
    """Courbe d'easing in-out quadratique."""
    t = clamp(t, 0.0, 1.0)
    if t < 0.5:
        return 2 * t * t
    return 1 - (-2 * t + 2) ** 2 / 2


def draw_text(surface: pygame.Surface, text: str, x: int, y: int,
              font: pygame.font.Font, color=(255, 255, 255),
              center: bool = False, shadow: bool = False):
    """Dessine du texte avec option centrage et ombre."""
    if shadow:
        shadow_surf = font.render(text, True, (0, 0, 0))
        if center:
            shadow_rect = shadow_surf.get_rect(center=(x + 2, y + 2))
        else:
            shadow_rect = shadow_surf.get_rect(topleft=(x + 2, y + 2))
        surface.blit(shadow_surf, shadow_rect)

    text_surf = font.render(text, True, color)
    if center:
        text_rect = text_surf.get_rect(center=(x, y))
    else:
        text_rect = text_surf.get_rect(topleft=(x, y))
    surface.blit(text_surf, text_rect)
    return text_rect


def draw_rounded_rect(surface: pygame.Surface, rect: pygame.Rect,
                      color: tuple, radius: int = 10,
                      border_color: tuple = None, border_width: int = 0):
    """Dessine un rectangle arrondi."""
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border_color and border_width > 0:
        pygame.draw.rect(surface, border_color, rect, width=border_width,
                         border_radius=radius)


def create_button_rect(x: int, y: int, width: int, height: int) -> pygame.Rect:
    """Crée un rectangle de bouton centré sur x, y."""
    return pygame.Rect(x - width // 2, y - height // 2, width, height)


def is_point_in_rect(point: tuple, rect: pygame.Rect) -> bool:
    """Vérifie si un point est dans un rectangle."""
    return rect.collidepoint(point)


def scale_image(image: pygame.Surface, target_width: int,
                target_height: int) -> pygame.Surface:
    """Redimensionne une image en gardant la qualité."""
    return pygame.transform.smoothscale(image, (target_width, target_height))
