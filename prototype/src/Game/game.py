"""
Game — Classe principale qui orchestre tout le jeu.
Initialise Pygame, charge les données, gère la boucle principale.
"""

import pygame
import sys
from ..utils.constants import *
from ..models.player import Player
from ..engine.data_manager import DataManager
from ..engine.card_generator import CardGenerator
from ..engine.card_renderer import CardRenderer
from ..engine.account_manager import AccountManager
from ..ui.screen_manager import ScreenManager
from ..ui.login_screen import LoginScreen
from ..ui.main_menu import MainMenuScreen
from ..ui.booster_shop import BoosterShopScreen
from ..ui.pack_opening import PackOpeningScreen
from ..ui.collection_screen import CollectionScreen


class Game:
    """Classe principale du jeu CardeGame."""

    def __init__(self):
        # Initialiser Pygame
        pygame.init()
        pygame.display.set_caption(GAME_TITLE)

        self.display = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT)
        )
        self.clock = pygame.time.Clock()
        self.running = True

        # Charger les données
        print("[Game] Chargement des données...")
        self.data_manager = DataManager()
        self.data_manager.load_all()

        # Moteurs
        self.card_generator = CardGenerator(self.data_manager)
        self.card_renderer = CardRenderer()

        # Gestionnaire de comptes
        self.account_manager = AccountManager()

        # Le joueur sera chargé après le login
        self.player = None
        self.current_username = None

        # Écrans
        self.screen_manager = ScreenManager(self.display)
        self.screen_manager.game = self
        self._register_screens()

        # Démarrer sur l'écran de login
        self.screen_manager.switch_to("login")

        print("[Game] Prêt ! ")

    def _register_screens(self):
        """Enregistre tous les écrans du jeu."""
        self.screen_manager.register(
            "login", LoginScreen(self.screen_manager)
        )
        self.screen_manager.register(
            "main_menu", MainMenuScreen(self.screen_manager)
        )
        self.screen_manager.register(
            "booster_shop", BoosterShopScreen(self.screen_manager)
        )
        self.screen_manager.register(
            "pack_opening", PackOpeningScreen(self.screen_manager)
        )
        self.screen_manager.register(
            "collection", CollectionScreen(self.screen_manager)
        )

    def login_player(self, username: str):
        """Charge le profil du joueur après connexion."""
        self.current_username = username
        save_dir = self.account_manager.get_player_save_dir(username)
        display_name = self.account_manager.get_display_name(username)

        self.player = Player.load(save_dir=save_dir)
        self.player.name = display_name
        self.player._save_dir = save_dir

        print(f"[Game] Joueur connecté: {display_name} | "
              f" {self.player.coins} money | "
              f" {self.player.collection.count()} cartes")

    def logout(self):
        """Déconnecte le joueur et retourne au login."""
        if self.player:
            self.player.save()
        self.player = None
        self.current_username = None
        self.screen_manager.switch_to("login")

    def run(self):
        """Boucle principale du jeu."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # Delta time en secondes

            # Événements
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                self.screen_manager.handle_event(event)

            # Mise à jour
            self.screen_manager.update(dt)

            # Rendu
            self.screen_manager.draw()
            pygame.display.flip()

        # Sauvegarder avant de quitter
        print("[Game] Sauvegarde automatique...")
        if self.player:
            self.player.save()
        pygame.quit()
        sys.exit()
