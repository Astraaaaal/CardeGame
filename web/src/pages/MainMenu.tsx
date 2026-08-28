import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { playerApi } from "@/api/player";
import { useAuthStore } from "@/stores/authStore";
import Button from "@/components/ui/Button";
import CoinDisplay from "@/components/player/CoinDisplay";
import StreakBadge from "@/components/player/StreakBadge";
import DailyRewardPopup from "@/components/player/DailyRewardPopup";
import { useLogout } from "@/hooks/useAuth";

export default function MainMenu() {
  const navigate = useNavigate();
  const { user, setUser } = useAuthStore();
  const logout = useLogout();

  const { data: player } = useQuery({
    queryKey: ["player"],
    queryFn: playerApi.getMe,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (player) setUser(player);
  }, [player, setUser]);

  const menuItems = [
    { label: "Boutique de Boosters", icon: "🛍️", path: "/shop", color: "bg-accent" },
    { label: "Ma Collection", icon: "📚", path: "/collection", color: "bg-purple-600" },
  ];

  return (
    <div className="min-h-screen bg-game-bg flex flex-col">
      <DailyRewardPopup />

      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
        <div>
          <h2 className="text-white font-bold text-lg">
            {user?.display_name || "Joueur"}
          </h2>
          <div className="flex items-center gap-2 mt-0.5">
            <CoinDisplay coins={user?.coins ?? 0} />
            <StreakBadge streak={user?.login_streak ?? 0} />
          </div>
        </div>
        <button
          className="text-white/40 hover:text-white text-sm transition-colors"
          onClick={() => { logout(); navigate("/login"); }}
        >
          Déconnexion
        </button>
      </header>

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
