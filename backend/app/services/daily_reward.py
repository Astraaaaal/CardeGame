"""
DailyRewardService — Logique streak et récompense journalière.
Identique à la logique de account_manager.py mais côté serveur.
"""

from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.game_config import GameConfig
from app.services import guilds, quest_progress


class DailyRewardService:

    async def _tuning(self, session: AsyncSession) -> GameConfig:
        config = await session.get(GameConfig, 1)
        return config or GameConfig()  # filet de sécurité, la ligne est seedée au démarrage

    async def check_and_claim(
        self, session: AsyncSession, user: User
    ) -> dict:
        """
        Vérifie et attribue la récompense journalière.
        Retourne {reward, streak, is_new, total_coins}.
        """
        today = date.today()
        config = await self._tuning(session)

        if user.last_daily_claim:
            if user.last_daily_claim == today:
                # Déjà réclamé aujourd'hui
                reward = config.daily_base_reward + config.daily_streak_bonus * (
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

        reward = config.daily_base_reward + config.daily_streak_bonus * (
            user.login_streak - 1
        )

        # Guilde : +x % selon son niveau, et bonus temporaire éventuel.
        perks = await guilds.level_perks(session, user.id)
        reward = round(reward * (1 + perks["daily_bonus_pct"] / 100)
                       * (await guilds.buff_value(session, user.id, "daily_reward") or 1.0))
        user.best_login_streak = max(user.best_login_streak, user.login_streak)
        user.login_days_total += 1
        await quest_progress.increment(session, user.id, "daily_rewards_claimed", 1)
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
