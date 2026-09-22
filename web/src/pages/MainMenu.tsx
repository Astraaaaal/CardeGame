import { useEffect } from "react";
import { toast } from "@/stores/toastStore";
import { useUnlocks, type FeatureKey } from "@/hooks/useUnlocks";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { playerApi } from "@/api/player";
import { progressionApi } from "@/api/progression";
import { showcaseApi } from "@/api/showcase";
import { useAuthStore } from "@/stores/authStore";
import Button from "@/components/ui/Button";
import CoinDisplay from "@/components/player/CoinDisplay";
import WalletMenu from "@/components/player/WalletMenu";
import PresencePanel from "@/components/activities/PresencePanel";
import StreakBadge from "@/components/player/StreakBadge";
import DailyRewardPopup from "@/components/player/DailyRewardPopup";
import BottomNav from "@/components/layout/BottomNav";
import { FramedAvatar } from "@/components/cosmetics/CosmeticVisuals";

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

  const { isUnlocked, levelFor } = useUnlocks();
  const menuItems: { label: string; path: string; feature?: FeatureKey }[] = [
    { label: "Boutique", path: "/shop" },
    { label: "Ma Collection", path: "/collection" },
    { label: "Activités", path: "/activities", feature: "workshop" },
    { label: "Guilde", path: "/guild", feature: "guild_join" },
    { label: "Inventaire", path: "/inventory" },
    { label: "Classement", path: "/leaderboard", feature: "leaderboard" },
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
          <WalletMenu />
          <CoinDisplay coins={user?.coins ?? 0} />
        </div>

        <button
          className="w-full bg-game-surface/50 border border-white/5 rounded-2xl px-4 py-3 flex items-center justify-between hover:border-accent/40 transition-colors text-left"
          onClick={() => navigate("/profile")}
          title="Vitrine et statistiques"
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <FramedAvatar frame={showcase?.avatar_frame} size={36}>
              {showcase?.avatar ? (
                <img
                  src={`/characters/${showcase.avatar.image_url}`}
                  alt=""
                  className="w-full h-full object-cover"
                />
              ) : (
                <span className="text-white/20 text-sm">?</span>
              )}
            </FramedAvatar>
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

      <div className="px-4 pt-2 max-w-sm mx-auto w-full">
        <PresencePanel />
      </div>

      {user && (!user.email || !user.email_verified) && (
        <button
          className="mx-4 mt-3 flex items-center justify-between gap-2 bg-amber-400/10 border border-amber-400/40
                     rounded-xl px-4 py-2.5 text-left max-w-sm self-center w-[calc(100%-2rem)]"
          onClick={() => navigate("/settings")}
        >
          <span className="text-white text-sm">
            {user.email
              ? "Confirme ton adresse e-mail pour sécuriser ton compte."
              : "Ajoute ton adresse e-mail pour sécuriser ton compte."}
          </span>
          <span className="text-amber-300 text-xs font-semibold shrink-0">{user.email ? "Voir" : "Ajouter"}</span>
        </button>
      )}

      {/* Content */}
      <main className="flex-1 flex flex-col items-center justify-center gap-5 px-4 pb-24">
        <motion.h1
          className="text-3xl font-extrabold text-white text-center"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          Carde<span className="text-accent">Game</span>
        </motion.h1>

        {/* Deux colonnes : les 7 entrées tiennent dans l'écran, sans passer sous les
            boutons flottants ; la dernière prend toute la largeur si le nombre est impair. */}
        <div className="w-full max-w-sm grid grid-cols-2 gap-2.5">
          {menuItems.map((item, idx) => (
            <motion.div
              key={item.path}
              className={idx === menuItems.length - 1 && menuItems.length % 2 === 1 ? "col-span-2" : ""}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * (idx + 1) }}
            >
              {item.feature && !isUnlocked(item.feature) ? (
                <Button
                  variant="secondary"
                  className="w-full opacity-50"
                  onClick={() => toast.info(`${item.label} se débloque au niveau ${levelFor(item.feature!)}.`)}
                >
                  <span className="block text-center leading-tight">
                    {item.label}
                    <span className="block text-[10px] font-semibold text-white/60">Niv. {levelFor(item.feature)}</span>
                  </span>
                </Button>
              ) : (
                <Button
                  variant="secondary"
                  className="w-full"
                  onClick={() => navigate(item.path)}
                >
                  {item.label}
                </Button>
              )}
            </motion.div>
          ))}
        </div>
      </main>

      <BottomNav />
    </div>
  );
}
