import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { playerApi } from "@/api/player";
import { progressionApi } from "@/api/progression";
import { showcaseApi } from "@/api/showcase";
import { useAuthStore } from "@/stores/authStore";
import Button from "@/components/ui/Button";
import CoinDisplay from "@/components/player/CoinDisplay";
import ResourceDisplay from "@/components/player/ResourceDisplay";
import StreakBadge from "@/components/player/StreakBadge";
import DailyRewardPopup from "@/components/player/DailyRewardPopup";
import ActiveTradeBanner from "@/components/trade/ActiveTradeBanner";
import BottomNav from "@/components/layout/BottomNav";

export default function MainMenu() {
  const navigate = useNavigate();
  const { user, setUser } = useAuthStore();

  const { data: player } = useQuery({
    queryKey: ["player"],
    queryFn: playerApi.getMe,
    staleTime: 30_000,
  });

  const { data: levelStatus } = useQuery({
    queryKey: ["level-status"],
    queryFn: progressionApi.getLevel,
    staleTime: 30_000,
  });

  const { data: showcase } = useQuery({
    queryKey: ["showcase", user?.id],
    queryFn: () => showcaseApi.get(user!.id),
    enabled: !!user?.id,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (player) setUser(player);
  }, [player, setUser]);

  const menuItems = [
    { label: "Boutique", path: "/shop" },
    { label: "Ma Collection", path: "/collection" },
    { label: "Inventaire", path: "/inventory" },
    { label: "Classement", path: "/leaderboard" },
    { label: "Progression", path: "/progression" },
  ];

  const powerPct = levelStatus?.next_level_power_required
    ? Math.min(100, Math.round((levelStatus.total_power / levelStatus.next_level_power_required) * 100))
    : 100;

  return (
    <div className="min-h-screen bg-game-bg flex flex-col">
      <DailyRewardPopup />

      <div className="px-4 pt-4 max-w-sm mx-auto w-full space-y-2">
        <div className="flex items-center justify-between">
          <ResourceDisplay amount={user?.resources?.[0]?.amount ?? 0} label={user?.resources?.[0]?.name} />
          <CoinDisplay coins={user?.coins ?? 0} />
        </div>

        <button
          className="w-full bg-game-surface/50 border border-white/5 rounded-2xl px-4 py-3 flex items-center justify-between hover:border-accent/40 transition-colors text-left"
          onClick={() => navigate("/profile")}
          title="Vitrine et statistiques"
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-9 h-9 rounded-full overflow-hidden bg-black/30 border border-white/10 shrink-0 flex items-center justify-center">
              {showcase?.avatar ? (
                <img
                  src={`/characters/${showcase.avatar.image_url}`}
                  alt=""
                  className="w-full h-full object-cover"
                />
              ) : (
                <span className="text-white/20 text-sm">?</span>
              )}
            </div>
            <span className="text-white font-bold text-lg truncate">{user?.display_name || "Joueur"}</span>
          </div>
          <StreakBadge streak={user?.login_streak ?? 0} />
        </button>

        <button
          className="w-full bg-game-surface/50 border border-white/5 rounded-2xl px-4 py-3 hover:border-accent/40 transition-colors text-left"
          onClick={() => navigate("/progression")}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-white/40 text-xs uppercase tracking-wide">Niveau</span>
            <span className="text-accent font-extrabold text-lg">{levelStatus?.current_level ?? "—"}</span>
          </div>
          {levelStatus && (
            <>
              <div className="h-1.5 bg-black/30 rounded-full overflow-hidden">
                <div className="h-full bg-accent transition-all" style={{ width: `${powerPct}%` }} />
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-white/30 text-[11px]">
                  {levelStatus.total_power.toLocaleString("fr-FR")} puissance
                </span>
                {levelStatus.next_level_power_required != null && (
                  <span className="text-white/30 text-[11px]">
                    {levelStatus.total_power.toLocaleString("fr-FR")} / {levelStatus.next_level_power_required.toLocaleString("fr-FR")}
                  </span>
                )}
              </div>
            </>
          )}
        </button>
      </div>

      <ActiveTradeBanner />

      {/* Content */}
      <main className="flex-1 flex flex-col items-center justify-center gap-6 px-4">
        <motion.h1
          className="text-3xl font-extrabold text-white text-center inline-flex items-baseline gap-2"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          Carde<span className="text-accent">Game</span>
          <span className="text-xs font-bold tracking-wide text-white/40">BÊTA</span>
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

      <BottomNav />
    </div>
  );
}
