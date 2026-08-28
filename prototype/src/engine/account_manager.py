"""
AccountManager — Gère les comptes joueur (inscription, connexion, hash mdp).
Les données sont stockées dans saves/accounts.json (mots de passe hashés SHA-256 + salt).
Chaque joueur a sa propre sauvegarde dans saves/<username>/player_save.json.
"""

import json
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from ..utils.constants import SAVES_DIR

ACCOUNTS_FILE = os.path.join(SAVES_DIR, "accounts.json")

# --- Récompenses journalières ---
DAILY_BASE_REWARD = 500
DAILY_STREAK_BONUS = 100


class AccountManager:
    """Gestionnaire de comptes avec hash de mot de passe et daily login."""

    def __init__(self):
        self.accounts: Dict[str, dict] = {}
        self._load_accounts()

    def _load_accounts(self):
        """Charge le fichier des comptes."""
        if os.path.exists(ACCOUNTS_FILE):
            try:
                with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                    self.accounts = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.accounts = {}
        else:
            self.accounts = {}

    def _save_accounts(self):
        """Sauvegarde le fichier des comptes."""
        os.makedirs(SAVES_DIR, exist_ok=True)
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.accounts, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Hash un mot de passe avec SHA-256 + salt."""
        return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

    def register(self, username: str, password: str) -> tuple[bool, str]:
        """
        Crée un nouveau compte.
        Retourne (succès, message).
        """
        # Validation
        username_lower = username.strip().lower()
        if not username_lower or len(username_lower) < 3:
            return False, "Le pseudo doit faire au moins 3 caractères."
        if len(username_lower) > 20:
            return False, "Le pseudo ne doit pas dépasser 20 caractères."
        if not username_lower.isalnum():
            return False, "Le pseudo ne doit contenir que des lettres et chiffres."
        if username_lower in self.accounts:
            return False, "Ce pseudo est déjà pris."
        if len(password) < 4:
            return False, "Le mot de passe doit faire au moins 4 caractères."

        # Créer le compte
        salt = secrets.token_hex(16)
        hashed = self._hash_password(password, salt)

        self.accounts[username_lower] = {
            "display_name": username.strip(),
            "salt": salt,
            "password_hash": hashed,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "login_streak": 0,
            "last_daily_claim": None,
        }

        # Créer le dossier de sauvegarde du joueur
        player_dir = os.path.join(SAVES_DIR, username_lower)
        os.makedirs(player_dir, exist_ok=True)

        self._save_accounts()
        return True, "Compte créé avec succès !"

    def login(self, username: str, password: str) -> tuple[bool, str]:
        """
        Vérifie les identifiants.
        Retourne (succès, message).
        """
        username_lower = username.strip().lower()
        if username_lower not in self.accounts:
            return False, "Pseudo introuvable."

        account = self.accounts[username_lower]
        salt = account["salt"]
        expected_hash = account["password_hash"]
        actual_hash = self._hash_password(password, salt)

        if actual_hash != expected_hash:
            return False, "Mot de passe incorrect."

        # Mettre à jour la date de connexion
        account["last_login"] = datetime.now().isoformat()
        self._save_accounts()

        return True, f"Bienvenue, {account['display_name']} !"

    def check_daily_reward(self, username: str) -> tuple[int, int, bool]:
        """
        Vérifie et attribue la récompense journalière.
        Retourne (montant, streak, est_nouveau_jour).
        """
        username_lower = username.strip().lower()
        if username_lower not in self.accounts:
            return 0, 0, False

        account = self.accounts[username_lower]
        today = datetime.now().date()
        last_claim_str = account.get("last_daily_claim")

        if last_claim_str:
            last_claim = datetime.fromisoformat(last_claim_str).date()

            if last_claim == today:
                # Déjà réclamé aujourd'hui
                streak = account.get("login_streak", 1)
                reward = DAILY_BASE_REWARD + DAILY_STREAK_BONUS * (streak - 1)
                return reward, streak, False

            if last_claim == today - timedelta(days=1):
                # Jour consécutif — on augmente le streak
                account["login_streak"] = account.get("login_streak", 0) + 1
            else:
                # Streak cassé — reset à 1
                account["login_streak"] = 1
        else:
            # Premier login
            account["login_streak"] = 1

        streak = account["login_streak"]
        reward = DAILY_BASE_REWARD + DAILY_STREAK_BONUS * (streak - 1)
        account["last_daily_claim"] = today.isoformat()
        self._save_accounts()

        return reward, streak, True

    def get_display_name(self, username: str) -> str:
        """Retourne le nom d'affichage du joueur."""
        username_lower = username.strip().lower()
        if username_lower in self.accounts:
            return self.accounts[username_lower].get("display_name", username)
        return username

    def get_player_save_dir(self, username: str) -> str:
        """Retourne le dossier de sauvegarde d'un joueur."""
        username_lower = username.strip().lower()
        player_dir = os.path.join(SAVES_DIR, username_lower)
        os.makedirs(player_dir, exist_ok=True)
        return player_dir

    def get_streak(self, username: str) -> int:
        """Retourne le streak actuel du joueur."""
        username_lower = username.strip().lower()
        if username_lower in self.accounts:
            return self.accounts[username_lower].get("login_streak", 0)
        return 0
