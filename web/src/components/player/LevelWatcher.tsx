import { play } from "@/utils/sound";
import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, animate, motion, useMotionValue, useTransform } from "framer-motion";
import { progressionApi } from "@/api/progression";
import { useAuthStore } from "@/stores/authStore";
import { UNLOCKS_KEY, useUnlocks } from "@/hooks/useUnlocks";
import Button from "@/components/ui/Button";

// Gros gain de puissance : au moins +15 % (et +100) d'un coup.
const BIG_GAIN_RATIO = 0.15;
const BIG_GAIN_MIN = 100;

function read(key: string): number | null {
    try {
        const v = localStorage.getItem(key);
        return v == null ? null : Number(v);
    } catch {
        return null;
    }
}
function write(key: string, value: number) {
    try { localStorage.setItem(key, String(value)); } catch { /* indisponible */ }
}

interface Celebration {
    fromPower: number;
    toPower: number;
    nextRequired: number | null;
    fromLevel: number;
    toLevel: number;
}

/**
 * Surveille le niveau et la puissance du joueur (à chaque changement de page) :
 * annonce animée à la montée de niveau (avec ce qui se débloque) et barre qui
 * se remplit lors d'un gros gain de puissance.
 */
export default function LevelWatcher() {
    const { user } = useAuthStore();
    const { pathname } = useLocation();
    const qc = useQueryClient();
    const { data: unlocks } = useUnlocks();
    const { data: status, refetch } = useQuery({
        queryKey: ["level-status"],
        queryFn: progressionApi.getLevel,
        enabled: !!user,
        staleTime: 5_000,
    });
    const [celebration, setCelebration] = useState<Celebration | null>(null);

    // Rafraîchit à chaque changement de page (ouverture de booster, échange…).
    useEffect(() => {
        if (!user) return;
        refetch();
        qc.invalidateQueries({ queryKey: UNLOCKS_KEY });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [pathname, user?.id]);

    useEffect(() => {
        if (!user || !status || pathname === "/opening") return;  // on attend la fin de l'ouverture
        const powerKey = `seen-power-${user.id}`;
        const levelKey = `seen-level-${user.id}`;
        const prevPower = read(powerKey);
        const prevLevel = read(levelKey);
        write(powerKey, status.total_power);
        write(levelKey, Math.max(prevLevel ?? 0, status.current_level));
        if (prevPower == null || prevLevel == null) return;  // première visite : rien à fêter
        const gain = status.total_power - prevPower;
        const levelUp = status.current_level > prevLevel;
        const bigGain = gain >= BIG_GAIN_MIN && gain >= prevPower * BIG_GAIN_RATIO;
        if (levelUp || bigGain) {
            play("levelUp");
            setCelebration({
                fromPower: prevPower, toPower: status.total_power, nextRequired: status.next_level_power_required,
                fromLevel: prevLevel, toLevel: Math.max(prevLevel, status.current_level),
            });
        }
    }, [status, user, pathname]);

    const unlocked = celebration && unlocks
        ? Object.values(unlocks.features).filter((f) => f.level > celebration.fromLevel && f.level <= celebration.toLevel)
        : [];

    return (
        <AnimatePresence>
            {celebration && (
                <motion.div className="fixed inset-0 z-[90] flex items-center justify-center p-6"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                    <div className="absolute inset-0 bg-black/75" onClick={() => setCelebration(null)} />
                    <motion.div
                        className="relative w-full max-w-sm bg-game-surface border border-accent/40 rounded-3xl p-6 text-center space-y-4 shadow-2xl"
                        initial={{ scale: 0.7, y: 40 }} animate={{ scale: 1, y: 0 }}
                        transition={{ type: "spring", stiffness: 260, damping: 20 }}
                    >
                        {celebration.toLevel > celebration.fromLevel ? (
                            <motion.p className="text-4xl font-extrabold text-accent"
                                initial={{ scale: 0.4 }} animate={{ scale: [0.4, 1.25, 1] }} transition={{ duration: 0.6, delay: 0.2 }}>
                                Niveau {celebration.toLevel} !
                            </motion.p>
                        ) : (
                            <p className="text-2xl font-extrabold text-gold">Gros gain de puissance !</p>
                        )}
                        <PowerCounter from={celebration.fromPower} to={celebration.toPower} next={celebration.nextRequired} />
                        {unlocked.length > 0 && (
                            <div className="space-y-1.5">
                                <p className="text-white/50 text-xs uppercase tracking-wide">Nouveau</p>
                                {unlocked.map((f, i) => (
                                    <motion.p key={f.label} className="text-white font-semibold"
                                        initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 1.2 + i * 0.15 }}>
                                        🔓 {f.label}
                                    </motion.p>
                                ))}
                            </div>
                        )}
                        {celebration.toLevel > celebration.fromLevel && (
                            <p className="text-white/40 text-xs">Récupère ta récompense dans Progression.</p>
                        )}
                        <Button variant="primary" className="w-full" onClick={() => setCelebration(null)}>Continuer</Button>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

/** Compteur de puissance qui défile, avec la barre vers le niveau suivant qui se remplit. */
function PowerCounter({ from, to, next }: { from: number; to: number; next: number | null }) {
    const value = useMotionValue(from);
    const text = useTransform(value, (v) => `⚡ ${Math.round(v).toLocaleString("fr-FR")}`);
    const width = useTransform(value, (v) => `${next ? Math.min(100, (v / next) * 100) : 100}%`);
    useEffect(() => {
        const controls = animate(value, to, { duration: 1.4, ease: "easeOut", delay: 0.3 });
        return () => controls.stop();
    }, [from, to, value]);
    return (
        <div className="space-y-1.5">
            <motion.p className="text-gold text-2xl font-extrabold tabular-nums">{text}</motion.p>
            <div className="h-2.5 bg-black/40 rounded-full overflow-hidden">
                <motion.div className="h-full bg-gradient-to-r from-accent to-gold" style={{ width }} />
            </div>
            <p className="text-white/40 text-[11px]">
                +{(to - from).toLocaleString("fr-FR")} puissance
                {next ? ` · prochain niveau à ${next.toLocaleString("fr-FR")}` : ""}
            </p>
        </div>
    );
}
