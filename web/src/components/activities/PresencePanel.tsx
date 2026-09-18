import { useMutation, useQueryClient } from "@tanstack/react-query";
import { activitiesApi } from "@/api/activities";
import { PRESENCE_KEY, usePresenceStatus } from "@/hooks/usePresence";
import { showRewards } from "@/stores/rewardPopupStore";

function fmtDuration(seconds: number): string {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return h ? `${h} h ${String(m).padStart(2, "0")}` : `${m} min`;
}

/** Accueil : bonus de chance lié à la présence, et coffre d'absence à récupérer. */
export default function PresencePanel() {
    const qc = useQueryClient();
    const { data } = usePresenceStatus();

    const claim = useMutation({
        mutationFn: activitiesApi.claimChest,
        onSuccess: (res) => {
            showRewards({
                title: "Coffre d'absence",
                items: [
                    { kind: "resource", resourceId: "coins", amount: res.coins, name: "Pièces" },
                    { kind: "resource", resourceId: "dust", amount: res.dust, name: "Poussière" },
                ],
            });
            qc.invalidateQueries({ queryKey: PRESENCE_KEY });
            qc.invalidateQueries({ queryKey: ["player"] });
        },
    });

    if (!data) return null;
    const progress = Math.min(1, (data.multiplier - 1) / (data.max_multiplier - 1 || 1));
    const chestReady = data.chest.coins > 0 || data.chest.dust > 0;

    return (
        <div className="bg-game-surface/50 border border-white/5 rounded-2xl px-4 py-3 space-y-2.5">
            <div>
                <div className="flex items-center justify-between mb-1.5">
                    <span className="text-white/40 text-xs uppercase tracking-wide">Chance de présence</span>
                    <span className="text-gold font-extrabold">×{data.multiplier.toLocaleString("fr-FR", { maximumFractionDigits: 2 })}</span>
                </div>
                <div className="h-1.5 bg-black/30 rounded-full overflow-hidden">
                    <div className="h-full bg-gold transition-all" style={{ width: `${progress * 100}%` }} />
                </div>
                <p className="text-white/30 text-[11px] mt-1">
                    {data.multiplier >= data.max_multiplier
                        ? "Bonus maximum : les raretés de tes boosters sont boostées."
                        : `Reste sur l'appli : jusqu'à ×${data.max_multiplier.toLocaleString("fr-FR")} après ${data.full_after_hours} h`
                          + (data.present_seconds ? ` (présent depuis ${fmtDuration(data.present_seconds)})` : "")}
                </p>
            </div>

            {chestReady && (
                <button
                    className="w-full flex items-center justify-between gap-2 bg-gold/10 border border-gold/30 rounded-xl px-3 py-2 text-left disabled:opacity-60"
                    disabled={claim.isPending}
                    onClick={() => claim.mutate()}
                >
                    <span className="text-white text-sm">
                        🧰 Coffre d'absence : {data.chest.coins.toLocaleString("fr-FR")} pièces
                        {data.chest.dust ? ` + ${data.chest.dust.toLocaleString("fr-FR")} poussière` : ""}
                    </span>
                    <span className="text-gold text-xs font-semibold shrink-0">Récupérer</span>
                </button>
            )}
        </div>
    );
}
