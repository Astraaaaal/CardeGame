import { useState } from "react";
import { toast } from "@/stores/toastStore";
import { motion } from "framer-motion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { activitiesApi, type WheelSpin } from "@/api/activities";
import { showRewards, type RewardItem } from "@/stores/rewardPopupStore";
import Button from "@/components/ui/Button";
import { errMsg } from "@/utils/errors";

const WHEEL_KEY = ["wheel"];
const COLORS = ["#4f46e5", "#0891b2", "#7c3aed", "#ca8a04", "#2563eb", "#9333ea", "#0d9488", "#dc2626"];

/** Roue de la fortune : un tour gratuit par jour, puis des tours payants. */
export default function FortuneWheel() {
    const qc = useQueryClient();
    const { data } = useQuery({ queryKey: WHEEL_KEY, queryFn: activitiesApi.wheel });
    const [rotation, setRotation] = useState(0);
    const [spinning, setSpinning] = useState(false);
    const setErr = (m: string | null) => { if (m) toast.error(m); };

    const spin = useMutation({
        mutationFn: activitiesApi.spinWheel,
        onSuccess: (res: WheelSpin) => {
            setErr("");
            const n = res.state.segments.length;
            const seg = 360 / n;
            // Case gagnante sous l'aiguille (en haut), après quelques tours complets.
            const target = 360 * 5 + (360 - (res.index * seg + seg / 2));
            setSpinning(true);
            setRotation((r) => r - (r % 360) + target);
            window.setTimeout(() => {
                setSpinning(false);
                qc.setQueryData(WHEEL_KEY, res.state);
                qc.invalidateQueries({ queryKey: ["player"] });
                qc.invalidateQueries({ queryKey: ["booster-inventory"] });
                qc.invalidateQueries({ queryKey: ["reroll-tokens"] });
                const r = res.reward;
                const items: RewardItem[] = r.kind === "resource" && r.resource_id
                    ? [{ kind: "resource", resourceId: r.resource_id, amount: r.amount }]
                    : r.kind === "booster" && r.booster_id
                        ? [{ kind: "booster", boosterId: r.booster_id, quantity: r.amount, name: r.booster_name }]
                        : [{ kind: "reroll_token", name: r.label, quantity: r.amount }];
                showRewards({ title: `Roue : ${r.label}`, items });
            }, 3200);
        },
        onError: (e) => setErr(errMsg(e)),
    });

    if (!data) return null;
    const n = data.segments.length;
    const seg = 360 / n;
    const gradient = data.segments.map((_, i) => `${COLORS[i % COLORS.length]} ${i * seg}deg ${(i + 1) * seg}deg`).join(", ");
    const extraLeft = data.extra_spins_per_day - data.extra_spins_used;
    const canSpin = data.free_available || extraLeft > 0;

    return (
        <div className="space-y-4">
            <div className="relative mx-auto w-64 h-64">
                <div className="absolute left-1/2 -top-2 -translate-x-1/2 z-10 w-0 h-0 border-l-[10px] border-r-[10px] border-t-[18px]
                                border-l-transparent border-r-transparent border-t-white drop-shadow" />
                <motion.div
                    className="w-full h-full rounded-full border-4 border-white/20 relative overflow-hidden"
                    style={{ background: `conic-gradient(${gradient})` }}
                    animate={{ rotate: rotation }}
                    transition={{ duration: 3, ease: [0.15, 0.8, 0.25, 1] }}
                >
                    {data.segments.map((s, i) => (
                        <div
                            key={i}
                            className="absolute inset-0 flex justify-center"
                            style={{ transform: `rotate(${i * seg + seg / 2}deg)` }}
                        >
                            <span className="mt-4 text-white text-[10px] font-bold text-center w-16 leading-tight drop-shadow">
                                {s.label}
                            </span>
                        </div>
                    ))}
                </motion.div>
            </div>

            <Button
                variant="gold" className="w-full" disabled={!canSpin || spinning} loading={spin.isPending} success={spin.isSuccess}
                onClick={() => spin.mutate()}
            >
                {data.free_available
                    ? "Tour gratuit du jour"
                    : extraLeft > 0 ? `Tourner (${data.extra_spin_cost} pièces)` : "Plus de tours aujourd'hui"}
            </Button>
            <p className="text-center text-white/40 text-[11px]">
                Tours payants restants aujourd'hui : {extraLeft} / {data.extra_spins_per_day}
            </p>
        </div>
    );
}
