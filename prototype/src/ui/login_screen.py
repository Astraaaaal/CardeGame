"""
LoginScreen — Écran de connexion / inscription.
Permet de se connecter ou créer un compte.
"""

import pygame
from .screen_manager import Screen
from ..utils.constants import *
from ..utils.helpers import draw_text, draw_rounded_rect, create_button_rect


class LoginScreen(Screen):
    """Écran de connexion et d'inscription."""

    def __init__(self, screen_manager):
        super().__init__(screen_manager)

        # État
        self.mode = "login"  # "login" ou "register"
        self.username = ""
        self.password = ""
        self.active_field = "username"  # "username" ou "password"
        self.message = ""
        self.message_color = COLOR_RED
        self.message_timer = 0

        # Daily reward popup
        self.show_daily_popup = False
        self.daily_reward = 0
        self.daily_streak = 0
        self.daily_popup_timer = 0

        # Suppression continue
        self._delete_held = False
        self._delete_timer = 0
        self._delete_delay = 0.4  # délai initial avant répétition
        self._delete_repeat = 0.05  # intervalle de répétition

        # Boutons
        self.submit_button = None
        self.switch_mode_button = None
        self.username_rect = None
        self.password_rect = None
        self.daily_ok_button = None

    def on_enter(self):
        self.username = ""
        self.password = ""
        self.message = ""
        self.active_field = "username"
        self.show_daily_popup = False

        center_x = SCREEN_WIDTH // 2
        self.username_rect = pygame.Rect(center_x - 140, 260, 280, 40)
        self.password_rect = pygame.Rect(center_x - 140, 340, 280, 40)
        self.submit_button = create_button_rect(center_x, 430, 200, 45)
        self.switch_mode_button = create_button_rect(center_x, 490, 260, 35)
        self.daily_ok_button = create_button_rect(center_x, 480, 160, 40)

    def handle_event(self, event):
        if self.show_daily_popup:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.daily_ok_button and self.daily_ok_button.collidepoint(event.pos):
                    self.show_daily_popup = False
                    self.sm.switch_to("main_menu")
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Champs de saisie
            if self.username_rect and self.username_rect.collidepoint(event.pos):
                self.active_field = "username"
            elif self.password_rect and self.password_rect.collidepoint(event.pos):
                self.active_field = "password"
            # Bouton submit
            elif self.submit_button and self.submit_button.collidepoint(event.pos):
                self._submit()
            # Bouton switch mode
            elif self.switch_mode_button and self.switch_mode_button.collidepoint(event.pos):
                self.mode = "register" if self.mode == "login" else "login"
                self.message = ""

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                # Basculer entre les champs
                self.active_field = (
                    "password" if self.active_field == "username" else "username"
                )
            elif event.key == pygame.K_RETURN:
                self._submit()
            elif event.key == pygame.K_BACKSPACE:
                self._delete_one_char()
                self._delete_held = True
                self._delete_timer = self._delete_delay
            elif event.key == pygame.K_a and (event.mod & pygame.KMOD_CTRL):
                # Ctrl+A : sélectionner tout = vider le champ actif
                if self.active_field == "username":
                    self.username = ""
                else:
                    self.password = ""
            else:
                char = event.unicode
                if char and char.isprintable():
                    if self.active_field == "username":
                        if len(self.username) < 20:
                            self.username += char
                    else:
                        if len(self.password) < 30:
                            self.password += char

        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_BACKSPACE:
                self._delete_held = False

    def _delete_one_char(self):
        """Supprime un caractère du champ actif."""
        if self.active_field == "username":
            self.username = self.username[:-1]
        else:
            self.password = self.password[:-1]

    def _submit(self):
        """Soumet le formulaire (connexion ou inscription)."""
        if not self.sm.game:
            return

        account_mgr = self.sm.game.account_manager

        if self.mode == "register":
            success, msg = account_mgr.register(self.username, self.password)
            self.message = msg
            self.message_color = COLOR_GREEN if success else COLOR_RED
            self.message_timer = 3.0
            if success:
                # Auto-login après inscription
                self.mode = "login"
                self._do_login()
        else:
            self._do_login()

    def _do_login(self):
        """Effectue la connexion."""
        if not self.sm.game:
            return

        account_mgr = self.sm.game.account_manager
        success, msg = account_mgr.login(self.username, self.password)
        self.message = msg
        self.message_color = COLOR_GREEN if success else COLOR_RED
        self.message_timer = 3.0

        if success:
            # Charger le joueur
            username_lower = self.username.strip().lower()
            self.sm.game.login_player(username_lower)

            # Vérifier la récompense journalière
            reward, streak, is_new = account_mgr.check_daily_reward(username_lower)
            if is_new:
                self.sm.game.player.earn(reward)
                self.sm.game.player.save()
                self.daily_reward = reward
                self.daily_streak = streak
                self.show_daily_popup = True
            else:
                self.daily_reward = reward
                self.daily_streak = streak
                self.sm.switch_to("main_menu")

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

        # Suppression continue quand backspace est maintenu
        if self._delete_held:
            self._delete_timer -= dt
            if self._delete_timer <= 0:
                self._delete_one_char()
                self._delete_timer = self._delete_repeat

    def draw(self):
        self.surface.fill(COLOR_BG)

        font_title = pygame.font.SysFont("Arial", FONT_SIZE_TITLE, bold=True)
        font_large = pygame.font.SysFont("Arial", FONT_SIZE_LARGE, bold=True)
        font_medium = pygame.font.SysFont("Arial", FONT_SIZE_MEDIUM)
        font_small = pygame.font.SysFont("Arial", FONT_SIZE_SMALL)
        font_btn = pygame.font.SysFont("Arial", FONT_SIZE_MEDIUM, bold=True)
        font_tiny = pygame.font.SysFont("Arial", FONT_SIZE_TINY)

        # Titre
        draw_text(self.surface, "CardeGame",
                  SCREEN_WIDTH // 2, 80, font_title, COLOR_GOLD,
                  center=True, shadow=True)

        mode_title = "Connexion" if self.mode == "login" else "Inscription"
        draw_text(self.surface, mode_title,
                  SCREEN_WIDTH // 2, 140, font_large, COLOR_WHITE, center=True)

        # Message
        if self.message:
            draw_text(self.surface, self.message,
                      SCREEN_WIDTH // 2, 185, font_small,
                      self.message_color, center=True)

        # Champ pseudo
        draw_text(self.surface, "Pseudo :",
                  self.username_rect.x, self.username_rect.y - 22,
                  font_small, COLOR_GRAY)

        usr_border = COLOR_ACCENT if self.active_field == "username" else COLOR_DARK_GRAY
        draw_rounded_rect(self.surface, self.username_rect, COLOR_BG_LIGHT,
                          radius=8, border_color=usr_border, border_width=2)

        usr_display = self.username
        draw_text(self.surface, usr_display,
                  self.username_rect.x + 10, self.username_rect.y + 10,
                  font_medium, COLOR_WHITE)

        # Curseur
        if self.active_field == "username":
            cursor_x = self.username_rect.x + 10 + font_medium.size(usr_display)[0]
            pygame.draw.line(self.surface, COLOR_WHITE,
                             (cursor_x, self.username_rect.y + 8),
                             (cursor_x, self.username_rect.y + 32), 2)

        # Champ mot de passe
        draw_text(self.surface, "Mot de passe :",
                  self.password_rect.x, self.password_rect.y - 22,
                  font_small, COLOR_GRAY)

        pwd_border = COLOR_ACCENT if self.active_field == "password" else COLOR_DARK_GRAY
        draw_rounded_rect(self.surface, self.password_rect, COLOR_BG_LIGHT,
                          radius=8, border_color=pwd_border, border_width=2)

        pwd_display = "*" * len(self.password)
        draw_text(self.surface, pwd_display,
                  self.password_rect.x + 10, self.password_rect.y + 10,
                  font_medium, COLOR_WHITE)

        if self.active_field == "password":
            cursor_x = self.password_rect.x + 10 + font_medium.size(pwd_display)[0]
            pygame.draw.line(self.surface, COLOR_WHITE,
                             (cursor_x, self.password_rect.y + 8),
                             (cursor_x, self.password_rect.y + 32), 2)

        # Bouton submit
        if self.submit_button:
            btn_text = "Se connecter" if self.mode == "login" else "Créer le compte"
            draw_rounded_rect(self.surface, self.submit_button, COLOR_BG_PANEL,
                              radius=10, border_color=COLOR_ACCENT, border_width=3)
            draw_text(self.surface, btn_text,
                      self.submit_button.centerx, self.submit_button.centery,
                      font_btn, COLOR_ACCENT, center=True)

        # Bouton switch mode
        if self.switch_mode_button:
            switch_text = ("Pas de compte ? Créer un compte"
                           if self.mode == "login"
                           else "Déjà un compte ? Se connecter")
            draw_text(self.surface, switch_text,
                      self.switch_mode_button.centerx,
                      self.switch_mode_button.centery,
                      font_small, COLOR_GRAY, center=True)

        # Info stockage
        draw_text(self.surface, "Données: saves/<pseudo>/",
                  SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50,
                  font_tiny, COLOR_DARK_GRAY, center=True)
        draw_text(self.surface, "Mots de passe hashés (SHA-256 + salt)",
                  SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30,
                  font_tiny, COLOR_DARK_GRAY, center=True)

        # Popup de récompense journalière
        if self.show_daily_popup:
            self._draw_daily_popup(font_large, font_medium, font_small, font_btn)

    def _draw_daily_popup(self, font_large, font_medium, font_small, font_btn):
        """Dessine la popup de récompense journalière."""
        # Fond semi-transparent
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.surface.blit(overlay, (0, 0))

        # Panneau
        panel_w, panel_h = 320, 260
        panel_x = (SCREEN_WIDTH - panel_w) // 2
        panel_y = (SCREEN_HEIGHT - panel_h) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        draw_rounded_rect(self.surface, panel_rect, COLOR_BG_PANEL,
                          radius=15, border_color=COLOR_GOLD, border_width=3)

        cx = SCREEN_WIDTH // 2

        draw_text(self.surface, "Connexion Journalière !",
                  cx, panel_y + 30, font_large, COLOR_GOLD, center=True)

        draw_text(self.surface, f"Jour {self.daily_streak}",
                  cx, panel_y + 70, font_medium, COLOR_WHITE, center=True)

        draw_text(self.surface, f"+{self.daily_reward} pièces !",
                  cx, panel_y + 110, font_large, COLOR_GOLD,
                  center=True, shadow=True)

        # Explication
        if self.daily_streak > 1:
            bonus = (self.daily_streak - 1) * 100
            draw_text(self.surface,
                      f"(500 base + {bonus} bonus streak)",
                      cx, panel_y + 150, font_small, COLOR_GRAY, center=True)
        else:
            draw_text(self.surface, "(500 pièces de base)",
                      cx, panel_y + 150, font_small, COLOR_GRAY, center=True)

        draw_text(self.surface,
                  f"Demain: +{500 + self.daily_streak * 100} si consécutif !",
                  cx, panel_y + 180, font_small, COLOR_ACCENT, center=True)

        # Bouton OK
        if self.daily_ok_button:
            draw_rounded_rect(self.surface, self.daily_ok_button, COLOR_BG_PANEL,
                              radius=8, border_color=COLOR_GREEN, border_width=3)
            draw_text(self.surface, "OK !",
                      self.daily_ok_button.centerx,
                      self.daily_ok_button.centery,
                      font_btn, COLOR_GREEN, center=True)
