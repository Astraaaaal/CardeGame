import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { activitiesApi, type WorkshopState } from "@/api/activities";
import { showRewards } from "@/stores/rewardPopupStore";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

const WORKSHOP_KEY = ["workshop"];
const FLUSH_MS = 1000;

/** Atelier : taper pour remplir la jauge ; les taps partent au serveur par lots. */
export default function WorkshopTab() {
    const qc = useQueryClient();
    const { data } = useQuery({ queryKey: WORKSHOP_KEY, queryFn: activitiesApi.workshop });
    const pending = useRef(0);
    const [localTaps, setLocalTaps] = useState(0);
    const [gain, setGain] = useState<string | null>(null);
    const [bumps, setBumps] = useState<number[]>([]);
    const bumpId = useRef(0);

    // Envoi groupé des taps une fois par seconde ; le serveur fait foi.
    useEffect(() => {
        const flush = () => {
            const count = pending.current;
            if (!count) return;
            pending.current = 0;
            activitiesApi.workshopTaps(count).then((res) => {
                setLocalTaps(0);
                qc.setQueryData<WorkshopState>(WORKSHOP_KEY, res);
                if (res.reward.gauges) {
                    const bits = [`+${res.reward.coins} pièces`];
                    if (res.reward.dust) bits.push(`+${res.reward.dust} poussière`);
                    setGain(bits.join(" · "));
                    qc.invalidateQueries({ queryKey: ["player"] });
                }
                if (res.reward.boosters && res.booster_id) {
                    showRewards({
                        title: "Booster assemblé !",
                        items: [{ kind: "booster", boosterId: res.booster_id, quantity: res.reward.boosters, name: res.booster_name }],
                    });
                    qc.invalidateQueries({ queryKey: ["booster-inventory"] });
                }
            }).catch(() => setLocalTaps(0));
        };
        const t = window.setInterval(flush, FLUSH_MS);
        return () => { window.clearInterval(t); flush(); };
    }, [qc]);

    if (!data) return <LoadingSpinner text="Chargement de l'atelier..." />;

    const capped = data.gauges_today >= data.gauges_per_day;
    const taps = Math.min(data.taps_per_gauge, data.taps + localTaps);
    const onTap = () => {
        if (capped) return;
        pending.current += 1;
        setLocalTaps((n) => n + 1);
        // Identifiant unique par tap (plusieurs taps peuvent tomber dans la même milliseconde).
        bumpId.current += 1;
        const id = bumpId.current;
        setBumps((b) => [...b.slice(-5), id]);
    };

    return (
        <div className="space-y-5 select-none">
            <p className="text-white/40 text-xs">
                Tape pour remplir la jauge : chaque jauge pleine rapporte {data.coins_per_gauge} pièces (parfois de la
                poussière) et un fragment ; {data.fragments_per_booster} fragments assemblent un booster.
            </p>

            <div>
                <div className="flex justify-between text-xs text-white/50 mb-1">
                    <span>Jauge</span>
                    <span>{taps} / {data.taps_per_gauge}</span>
                </div>
                <div className="h-3 bg-black/30 rounded-full overflow-hidden">
                    <div className="h-full bg-gold transition-all duration-100" style={{ width: `${(taps / data.taps_per_gauge) * 100}%` }} />
                </div>
            </div>

            <div className="relative flex justify-center py-4">
                <motion.button
                    className="w-40 h-40 rounded-full bg-gradient-to-br from-accent to-purple-600 border-4 border-white/20
                               text-white text-4xl shadow-xl disabled:opacity-40 disabled:cursor-not-allowed"
                    whileTap={{ scale: 0.92 }}
                    disabled={capped}
                    onPointerDown={onTap}
                >
                    🔨
                </motion.button>
                {bumps.map((id) => (
                    <motion.span
                        key={id}
                        className="absolute top-2 text-gold font-bold pointer-events-none"
                        initial={{ opacity: 1, y: 0 }}
                        animate={{ opacity: 0, y: -40 }}
                        transition={{ duration: 0.7 }}
                    >
                        +1
                    </motion.span>
                ))}
            </div>

            {gain && <p className="text-center text-green-400 text-sm font-semibold">{gain}</p>}

            <div className="grid grid-cols-2 gap-2 text-center">
                <div className="bg-game-surface rounded-xl border border-white/10 p-3">
                    <p className="text-white/40 text-[11px]">Jauges aujourd'hui</p>
                    <p className="text-white font-bold">{data.gauges_today} / {data.gauges_per_day}</p>
                </div>
                <div className="bg-game-surface rounded-xl border border-white/10 p-3">
                    <p className="text-white/40 text-[11px]">Fragments de booster</p>
                    <p className="text-white font-bold">{data.fragments} / {data.fragments_per_booster}</p>
                </div>
            </div>
            {capped && <p className="text-center text-white/40 text-xs">Atelier fermé pour aujourd'hui, reviens demain !</p>}
        </div>
    );
}
