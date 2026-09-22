import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { leaderboardApi } from "@/api/leaderboard";
import { useAuthStore } from "@/stores/authStore";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ResourceIcon from "@/components/ui/ResourceIcon";
import GuildEmblem from "@/components/guild/GuildEmblem";
import { formatNumber, parseUtc } from "@/utils/format";

/** Temps restant avant la fin du mois, en jours et heures. */
function remaining(endsAt: string): string {
    const ms = parseUtc(endsAt).getTime() - Date.now();
    if (ms <= 0) return "terminé";
    const hours = Math.floor(ms / 3_600_000);
    return hours >= 24 ? `${Math.floor(hours / 24)} j ${hours % 24} h` : `${hours} h`;
}

/** Défi du mois : classement de la puissance des cartes obtenues ce mois-ci, solo et par guilde. */
export default function MonthlyChallenge() {
    const navigate = useNavigate();
    const { user } = useAuthStore();
    const [view, setView] = useState<"solo" | "guilds">("solo");
    const { data, isLoading } = useQuery({ queryKey: ["monthly-challenge"], queryFn: leaderboardApi.monthly });

    if (isLoading || !data) return <LoadingSpinner text="Chargement..." />;
    const rewards = view === "solo" ? data.solo_rewards : data.guild_rewards;

    return (
        <div className="space-y-4">
            <div className="bg-game-surface border border-white/10 rounded-2xl p-4 space-y-1">
                <div className="flex items-center justify-between">
                    <h2 className="text-white font-bold">Défi de {data.month_label}</h2>
                    <span className="text-white/50 text-xs">fin dans {remaining(data.ends_at)}</span>
                </div>
                <p className="text-white/40 text-[11px]">
                    Chaque carte obtenue ce mois-ci (booster, récompense, boutique, expédition) rapporte sa puissance
                    en points. Les cartes reçues en échange ou en cadeau ne comptent pas, recycler ne retire rien.
                </p>
                <p className="text-white/70 text-sm pt-1">
                    Toi : <span className="text-gold font-bold">{formatNumber(data.me.points)} pts</span>
                    {data.me.rank ? ` · ${data.me.rank}e sur ${data.players}` : " · pas encore classé"}
                    {data.my_guild && ` · ta guilde ${data.my_guild.rank}e`}
                </p>
                {data.last_champion?.display_name && (
                    <p className="text-gold text-[11px]">
                        Champion de {data.last_champion.month_label} : {data.last_champion.display_name}
                        {data.last_champion.guild_name && ` · guilde ${data.last_champion.guild_name}`}
                    </p>
                )}
            </div>

            <div className="flex gap-1.5">
                {([["solo", "Joueurs"], ["guilds", "Guildes"]] as const).map(([key, label]) => (
                    <button key={key}
                        className={`flex-1 py-1.5 rounded-lg text-xs font-bold ${view === key ? "bg-accent text-white" : "bg-white/10 text-white/60"}`}
                        onClick={() => setView(key)}>
                        {label}
                    </button>
                ))}
            </div>

            {view === "solo" ? (
                <div className="space-y-2">
                    {data.solo.length === 0 && <p className="text-white/30 text-sm text-center py-6">Personne n'a encore marqué de points.</p>}
                    {data.solo.map((e) => (
                        <button key={e.user_id} onClick={() => navigate(`/players/${e.user_id}`)}
                            className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border text-left ${
                                e.user_id === user?.id ? "bg-accent/10 border-accent/40" : "bg-game-surface border-white/10"}`}>
                            <span className="flex items-center gap-3 min-w-0">
                                <span className="text-white/50 font-bold text-sm w-6 text-center shrink-0">{e.rank}</span>
                                <span className={`text-sm font-semibold truncate ${e.user_id === user?.id ? "text-accent" : "text-white"}`}>
                                    {e.display_name}
                                </span>
                            </span>
                            <span className="text-gold font-bold text-sm shrink-0">{formatNumber(e.points)} pts</span>
                        </button>
                    ))}
                </div>
            ) : (
                <div className="space-y-2">
                    {data.guilds.length === 0 && <p className="text-white/30 text-sm text-center py-6">Aucune guilde classée.</p>}
                    {data.guilds.map((g) => (
                        <div key={g.guild_id} className="flex items-center gap-3 px-3 py-2.5 rounded-xl border bg-game-surface border-white/10">
                            <span className="text-white/50 font-bold text-sm w-6 text-center shrink-0">{g.rank}</span>
                            <GuildEmblem icon={g.icon} color={g.color} size={28} />
                            <span className="flex-1 min-w-0 truncate text-white text-sm font-semibold">[{g.tag}] {g.name}</span>
                            <span className="text-gold font-bold text-sm shrink-0">{formatNumber(g.points)} pts</span>
                        </div>
                    ))}
                </div>
            )}

            <div className="bg-game-surface/60 border border-white/10 rounded-xl p-3 space-y-1.5">
                <p className="text-white/50 text-xs font-semibold uppercase tracking-wide">
                    Récompenses de fin de mois {view === "guilds" && "(pour chaque membre)"}
                </p>
                {rewards.map((tier) => (
                    <div key={tier.label} className="flex items-center gap-2 text-xs">
                        <span className="text-white/70 w-24 shrink-0">{tier.label}</span>
                        <span className="flex flex-wrap gap-2">
                            {tier.rewards.map((r, i) => (
                                <span key={i} className="inline-flex items-center gap-1 text-white/70">
                                    {r.resource_id && <ResourceIcon resourceId={r.resource_id} className="w-3.5 h-3.5" />}
                                    {r.quantity ? formatNumber(r.quantity) : ""} {!r.resource_id && r.name}
                                </span>
                            ))}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}
