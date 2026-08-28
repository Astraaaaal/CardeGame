"""
ScreenManager — Gère la navigation entre les différents écrans du jeu.
"""

import pygame
from typing import Dict, Optional


class Screen:
    """Classe de base pour tous les écrans."""

    def __init__(self, screen_manager: "ScreenManager"):
        self.sm = screen_manager
        self.surface = screen_manager.display

    def on_enter(self):
        """Appelé quand on entre dans cet écran."""
        pass

    def on_exit(self):
        """Appelé quand on quitte cet écran."""
        pass

    def handle_event(self, event: pygame.event.Event):
        """Gère les événements."""
        pass

    def update(self, dt: float):
        """Met à jour la logique (dt en secondes)."""
        pass

    def draw(self):
        """Dessine l'écran."""
        pass


class ScreenManager:
    """Gestionnaire des écrans avec navigation."""

    def __init__(self, display: pygame.Surface):
        self.display = display
        self.screens: Dict[str, Screen] = {}
        self.current_screen: Optional[Screen] = None
        self.current_screen_name: str = ""
        self.game = None  # Référence au Game, définie après init

    def register(self, name: str, screen: Screen):
        """Enregistre un écran."""
        self.screens[name] = screen

    def switch_to(self, name: str):
        """Change d'écran."""
        if name not in self.screens:
            print(f"[ScreenManager] Écran '{name}' introuvable!")
            return

        if self.current_screen:
            self.current_screen.on_exit()

        self.current_screen = self.screens[name]
        self.current_screen_name = name
        self.current_screen.on_enter()

    def handle_event(self, event: pygame.event.Event):
        """Passe l'événement à l'écran actuel."""
        if self.current_screen:
            self.current_screen.handle_event(event)

    def update(self, dt: float):
        """Met à jour l'écran actuel."""
        if self.current_screen:
            self.current_screen.update(dt)

    def draw(self):
        """Dessine l'écran actuel."""
        if self.current_screen:
            self.current_screen.draw()
