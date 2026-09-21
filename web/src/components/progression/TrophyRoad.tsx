import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { progressionApi } from "@/api/progression";
import { useUnlocks } from "@/hooks/useUnlocks";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ResourceIcon from "@/components/ui/ResourceIcon";

/**
 * Tous les paliers de niveau avec leur état (atteint / récupéré / verrouillé),
 * ce que chacun débloque, une ligne de progression qui se remplit jusqu'au
 * niveau atteint, et une récompense qui s'envole quand on la récupère.
 */
export default function TrophyRoad() {
    const { data, isLoading } = useQuery({ queryKey: ["level-tiers"], queryFn: progressionApi.getLevelTiers });
    const { data: unlocks } = useUnlocks();

    // Paliers qui viennent de passer à « récupéré » : petite animation d'envol.
    const previous = useRef<Set<number> | null>(null);
    const [justClaimed, setJustClaimed] = useState<number[]>([]);
    useEffect(() => {
        if (!data) return;
        const claimed = new Set(data.filter((t) => t.claimed).map((t) => t.level));
        if (previous.current) {
            const fresh = [...claimed].filter((l) => !previous.current!.has(l));
            if (fresh.length) {
                setJustClaimed(fresh);
                const timer = setTimeout(() => setJustClaimed([]), 1600);
                previous.current = claimed;
                return () => clearTimeout(timer);
            }
        }
        previous.current = claimed;
    }, [data]);

    if (isLoading || !data) return <LoadingSpinner text="Chargement..." />;

    const featuresAt = (level: number) =>
        unlocks ? Object.values(unlocks.features).filter((f) => f.level === level && level > 1) : [];
    const lastReached = data.reduce((acc, t, i) => (t.reached || t.claimed ? i : acc), 0);
    const fill = data.length > 1 ? (lastReached / (data.length - 1)) * 100 : 0;

    return (
        <div className="relative pl-8">
            <div className="absolute left-[15px] top-2 bottom-2 w-0.5 bg-white/10" />
            {/* Progression jusqu'au dernier palier atteint, remplie en s'animant. */}
            <motion.div
                className="absolute left-[15px] top-2 w-0.5 bg-gradient-to-b from-accent to-gold origin-top"
                initial={{ height: 0 }}
                animate={{ height: `calc(${fill}% - ${fill ? 8 : 0}px)` }}
                transition={{ duration: 1.2, ease: "easeOut", delay: 0.2 }}
            />
            {data.map((t, i) => {
                const state = t.claimed ? "claimed" : t.reached ? "reached" : "locked";
                const features = featuresAt(t.level);
                const flying = justClaimed.includes(t.level);
                return (
                    <motion.div key={t.level} className="relative mb-4 last:mb-0"
                        initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: Math.min(i, 12) * 0.04 }}>
                        <motion.div
                            className={`absolute -left-8 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 z-10
                                ${state === "claimed" ? "bg-accent border-accent text-white"
                                    : state === "reached" ? "bg-gold border-gold text-game-bg animate-pulse"
                                        : "bg-black/40 border-white/15 text-white/30"}`}
                            animate={flying ? { scale: [1, 1.5, 1], boxShadow: ["0 0 0px #fbbf24", "0 0 24px #fbbf24", "0 0 0px #fbbf24"] } : undefined}
                            transition={{ duration: 0.8 }}
                        >
                            {t.level}
                        </motion.div>
                        <div
                            className={`relative ml-3 rounded-xl border px-3 py-2 space-y-1
                                ${state === "locked" ? "bg-black/20 border-white/5" : "bg-game-surface border-white/10"}`}
                        >
                            <div className="flex items-center justify-between gap-2">
                                <div>
                                    <p className={`text-sm font-semibold ${state === "locked" ? "text-white/40" : "text-white"}`}>
                                        Niveau {t.level}
                                    </p>
                                    <p className="text-white/30 text-[11px]">
                                        {t.power_required.toLocaleString("fr-FR")} puissance
                                    </p>
                                </div>
                                <div className="flex items-center gap-2 text-xs shrink-0">
                                    {t.reward_amount != null && t.reward_resource_id && (
                                        <span className={`flex items-center gap-1 ${state === "locked" ? "text-white/30" : "text-white/70"}`}>
                                            <ResourceIcon resourceId={t.reward_resource_id} className="w-3.5 h-3.5" />
                                            {t.reward_amount.toLocaleString("fr-FR")}
                                        </span>
                                    )}
                                    {t.reward_booster_id && (
                                        <span className={state === "locked" ? "text-white/30" : "text-white/70"}>booster</span>
                                    )}
                                </div>
                            </div>
                            {features.length > 0 && (
                                <div className="flex flex-wrap gap-1">
                                    {features.map((f) => (
                                        <span key={f.label}
                                            className={`text-[10px] px-1.5 py-0.5 rounded-full border ${
                                                state === "locked" ? "border-white/10 text-white/35" : "border-accent/40 text-accent bg-accent/10"}`}>
                                            {state === "locked" ? "🔒" : "🔓"} {f.label}
                                        </span>
                                    ))}
                                </div>
                            )}
                            {/* Récompense qui s'envole à la récupération. */}
                            <AnimatePresence>
                                {flying && t.reward_amount != null && t.reward_resource_id && (
                                    <motion.span
                                        className="absolute right-3 top-1 flex items-center gap-1 text-gold font-extrabold text-sm pointer-events-none"
                                        initial={{ opacity: 0, y: 0, scale: 0.8 }}
                                        animate={{ opacity: [0, 1, 1, 0], y: -48, scale: 1.2 }}
                                        exit={{ opacity: 0 }}
                                        transition={{ duration: 1.4, ease: "easeOut" }}
                                    >
                                        +{t.reward_amount.toLocaleString("fr-FR")}
                                        <ResourceIcon resourceId={t.reward_resource_id} className="w-4 h-4" />
                                    </motion.span>
                                )}
                            </AnimatePresence>
                        </div>
                    </motion.div>
                );
            })}
        </div>
    );
}
