import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { playerApi } from "@/api/player";
import { friendsApi } from "@/api/friends";
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
import { useLogout } from "@/hooks/useAuth";

export default function MainMenu() {
  const navigate = useNavigate();
  const { user, setUser } = useAuthStore();
  const logout = useLogout();
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

  useEffect(() => {
    if (player) setUser(player);
  }, [player, setUser]);

  const menuItems = [
    { label: "Boutique", icon: "🛍️", path: "/shop", color: "bg-accent" },
    { label: "Ma Collection", icon: "📚", path: "/collection", color: "bg-purple-600" },
    { label: "Classement", icon: "🏆", path: "/leaderboard", color: "bg-purple-600" },
    { label: "Progression", icon: "⭐", path: "/progression", color: "bg-purple-600" },
  ];

  return (
    <div className="min-h-screen bg-game-bg flex flex-col">
      <DailyRewardPopup />
      <TradeRequestPopup />

      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
        <div>
          <button
            className="text-white font-bold text-lg hover:text-accent transition-colors"
            onClick={() => navigate("/profile")}
            title="Vitrine et statistiques"
          >
            {user?.display_name || "Joueur"}
          </button>
          <div className="flex items-center gap-2 mt-0.5">
            <CoinDisplay coins={user?.coins ?? 0} />
            <ResourceDisplay amount={user?.resources?.[0]?.amount ?? 0} label={user?.resources?.[0]?.name} />
            <StreakBadge streak={user?.login_streak ?? 0} />
          </div>
        </div>
        <div className="flex items-center gap-3">
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
          <button
            className="text-white/70 hover:text-white text-xl"
            onClick={() => navigate("/settings")}
            title="Réglages"
          >
            ⚙️
          </button>
          <button
            className="text-white/40 hover:text-white text-sm transition-colors"
            onClick={() => { logout(); navigate("/login"); }}
          >
            Déconnexion
          </button>
        </div>
      </header>

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
                className="w-full flex items-center gap-3 justify-start"
                onClick={() => navigate(item.path)}
              >
                <span className="text-2xl">{item.icon}</span>
                <span>{item.label}</span>
              </Button>
            </motion.div>
          ))}
        </div>

        {/* Stats */}
        <motion.div
          className="text-white/30 text-xs text-center mt-8 space-y-1"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          <p>Packs ouverts : {user?.packs_opened ?? 0}</p>
          <p>Cartes collectées : {user?.total_cards ?? 0}</p>
        </motion.div>
      </main>
    </div>
  );
}
