import { useQuery } from "@tanstack/react-query";
import { progressionApi } from "@/api/progression";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ResourceIcon from "@/components/ui/ResourceIcon";

/** Liste de tous les paliers de niveau avec leur état (atteint / récupéré / verrouillé). */
export default function TrophyRoad() {
    const { data, isLoading } = useQuery({ queryKey: ["level-tiers"], queryFn: progressionApi.getLevelTiers });

    if (isLoading || !data) return <LoadingSpinner text="Chargement..." />;

    return (
        <div className="relative pl-8">
            <div className="absolute left-[15px] top-2 bottom-2 w-0.5 bg-white/10" />
            {data.map((t) => {
                const state = t.claimed ? "claimed" : t.reached ? "reached" : "locked";
                return (
                    <div key={t.level} className="relative mb-4 last:mb-0">
                        <div
                            className={`absolute -left-8 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 z-10
                                ${state === "claimed" ? "bg-accent border-accent text-white"
                                    : state === "reached" ? "bg-gold border-gold text-game-bg animate-pulse"
                                        : "bg-black/40 border-white/15 text-white/30"}`}
                        >
                            {t.level}
                        </div>
                        <div
                            className={`ml-3 rounded-xl border px-3 py-2 flex items-center justify-between gap-2
                                ${state === "locked" ? "bg-black/20 border-white/5" : "bg-game-surface border-white/10"}`}
                        >
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
                                    <span className={state === "locked" ? "text-white/30" : "text-white/70"}>
                                        booster
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
