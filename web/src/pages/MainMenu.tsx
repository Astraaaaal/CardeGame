import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { playerApi } from "@/api/player";
import { friendsApi } from "@/api/friends";
import { progressionApi } from "@/api/progression";
import { useAuthStore } from "@/stores/authStore";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import Button from "@/components/ui/Button";
import CoinDisplay from "@/components/player/CoinDisplay";
import ResourceDisplay from "@/components/player/ResourceDisplay";
import StreakBadge from "@/components/player/StreakBadge";
import DailyRewardPopup from "@/components/player/DailyRewardPopup";
import FriendsPanel from "@/components/social/FriendsPanel";
import TradeRequestPopup from "@/components/social/TradeRequestPopup";
import ActiveTradeBanner from "@/components/trade/ActiveTradeBanner";

export default function MainMenu() {
  const navigate = useNavigate();
  const { user, setUser } = useAuthStore();
  // Rouvre automatiquement le panneau Amis au retour d'une sélection de
  // carte pour un cadeau (cf. FriendsPanel / MessagesInbox), quel que soit
  // l'onglet d'origine — FriendsPanel se replace lui-même sur le bon onglet.
  const [friendsOpen, setFriendsOpen] = useState(
    () => useCardSelectionStore.getState().result?.context?.purpose === "gift"
  );

  const { data: player } = useQuery({
    queryKey: ["player"],
    queryFn: playerApi.getMe,
    staleTime: 30_000,
  });

  const { data: friendRequests } = useQuery({
    queryKey: ["friend-requests"],
    queryFn: friendsApi.listRequests,
    staleTime: 30_000,
  });
  const pendingCount = friendRequests?.incoming.length ?? 0;

  const { data: levelStatus } = useQuery({
    queryKey: ["level-status"],
    queryFn: progressionApi.getLevel,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (player) setUser(player);
  }, [player, setUser]);

  const menuItems = [
    { label: "Boutique", path: "/shop" },
    { label: "Ma Collection", path: "/collection" },
    { label: "Classement", path: "/leaderboard" },
    { label: "Progression", path: "/progression" },
  ];

  return (
    <div className="min-h-screen bg-game-bg flex flex-col">
      <DailyRewardPopup />
      <TradeRequestPopup />

      <div className="px-4 pt-4 max-w-sm mx-auto w-full space-y-2">
        <div className="bg-game-surface/50 border border-white/5 rounded-2xl px-4 py-3 flex items-center justify-between">
          <button
            className="text-white font-bold text-lg hover:text-accent transition-colors text-left"
            onClick={() => navigate("/profile")}
            title="Vitrine et statistiques"
          >
            {user?.display_name || "Joueur"}
          </button>
          <StreakBadge streak={user?.login_streak ?? 0} />
        </div>

        <div className="flex items-center gap-2">
          <CoinDisplay coins={user?.coins ?? 0} />
          <ResourceDisplay amount={user?.resources?.[0]?.amount ?? 0} label={user?.resources?.[0]?.name} />
        </div>

        <button
          className="w-full bg-game-surface/50 border border-white/5 rounded-2xl px-4 py-3 flex items-center justify-center gap-2 hover:border-accent/40 transition-colors"
          onClick={() => navigate("/progression")}
        >
          <span className="text-white/40 text-xs uppercase tracking-wide">Niveau</span>
          <span className="text-accent font-extrabold text-lg">{levelStatus?.current_level ?? "—"}</span>
        </button>
      </div>

      <FriendsPanel open={friendsOpen} onClose={() => setFriendsOpen(false)} />
      <ActiveTradeBanner />

      {/* Content */}
      <main className="flex-1 flex flex-col items-center justify-center gap-6 px-4">
        <motion.h1
          className="text-3xl font-extrabold text-white text-center"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          Carde<span className="text-accent">Game</span>
        </motion.h1>

        <div className="w-full max-w-sm space-y-3">
          {menuItems.map((item, idx) => (
            <motion.div
              key={item.path}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 * (idx + 1) }}
            >
              <Button
                variant="secondary"
                size="lg"
                className="w-full justify-start"
                onClick={() => navigate(item.path)}
              >
                {item.label}
              </Button>
            </motion.div>
          ))}
        </div>
      </main>

      <footer className="flex items-center justify-between px-4 py-4">
        <button
          className="text-white/70 hover:text-white text-xl"
          onClick={() => navigate("/settings")}
          title="Réglages"
        >
          ⚙️
        </button>
        <button
          className="relative text-white/70 hover:text-white text-xl"
          onClick={() => setFriendsOpen(true)}
          title="Amis"
        >
          👥
          {pendingCount > 0 && (
            <span className="absolute -top-1 -right-1.5 inline-flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4">
              {pendingCount}
            </span>
          )}
        </button>
      </footer>
    </div>
  );
}
