"""
DailyRewardService — Logique streak et récompense journalière.
Identique à la logique de account_manager.py mais côté serveur.
"""

from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.config import settings


class DailyRewardService:

    async def check_and_claim(
        self, session: AsyncSession, user: User
    ) -> dict:
        """
        Vérifie et attribue la récompense journalière.
        Retourne {reward, streak, is_new, total_coins}.
        """
        today = date.today()

        if user.last_daily_claim:
            if user.last_daily_claim == today:
                # Déjà réclamé aujourd'hui
                reward = settings.DAILY_BASE_REWARD + settings.DAILY_STREAK_BONUS * (
                    user.login_streak - 1
                )
                return {
                    "reward": reward,
                    "streak": user.login_streak,
                    "is_new": False,
                    "total_coins": user.coins,
                }

            if user.last_daily_claim == today - timedelta(days=1):
                # Jour consécutif
                user.login_streak += 1
            else:
                # Streak cassé
                user.login_streak = 1
        else:
            # Premier login
            user.login_streak = 1

        reward = settings.DAILY_BASE_REWARD + settings.DAILY_STREAK_BONUS * (
            user.login_streak - 1
        )

        user.coins += reward
        user.last_daily_claim = today
        await session.commit()
        await session.refresh(user)

        return {
            "reward": reward,
            "streak": user.login_streak,
            "is_new": True,
            "total_coins": user.coins,
        }
