import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { guildsApi, type GuildRankingRow, type RankingKind } from "@/api/guilds";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import GuildEmblem from "./GuildEmblem";
import { MY_GUILD_KEY } from "./NoGuild";

const KINDS: { key: RankingKind; label: string; hint: string }[] = [
    { key: "overall", label: "Général", hint: "Classement combiné du niveau, de la puissance et du coffre." },
    { key: "level", label: "Niveau", hint: "Niveau de la guilde (XP du coffre et des défis)." },
    { key: "power", label: "Puissance", hint: "Puissance totale des cartes de tous les membres." },
    { key: "chest", label: "Coffre", hint: "Points donnés au coffre depuis la création." },
    { key: "challenge", label: "Défi", hint: "Palier de défi hebdomadaire le plus haut atteint." },
];

const fmt = (n: number) => n.toLocaleString("fr-FR");

function score(kind: RankingKind, r: GuildRankingRow) {
    switch (kind) {
        case "overall": return null;  // trié par rang moyen, seule la position compte
        case "level": return `Niv. ${r.level}`;
        case "power": return `⚡ ${fmt(r.power)}`;
        case "chest": return `${fmt(r.chest_total)} pts`;
        case "challenge": return `Palier ${r.challenge_best_tier}`;
    }
}

/** Onglet « Guildes » du classement : 5 sous-classements. */
export default function GuildRankings() {
    const [kind, setKind] = useState<RankingKind>("overall");
    const { data, isLoading } = useQuery({ queryKey: ["guild", "rankings", kind], queryFn: () => guildsApi.rankings(kind) });
    const { data: mine } = useQuery({ queryKey: MY_GUILD_KEY, queryFn: guildsApi.me });
    const myId = mine?.guild?.id;

    return (
        <div className="space-y-3">
            <div className="flex gap-1 overflow-x-auto">
                {KINDS.map((k) => (
                    <button key={k.key}
                        className={`px-2.5 py-1 rounded-full text-xs font-bold shrink-0 ${kind === k.key ? "bg-accent text-white" : "bg-white/10 text-white/60"}`}
                        onClick={() => setKind(k.key)}>{k.label}</button>
                ))}
            </div>
            <p className="text-white/30 text-xs">{KINDS.find((k) => k.key === kind)!.hint}</p>
            {isLoading ? (
                <LoadingSpinner text="Chargement..." />
            ) : data?.length ? (
                <div className="space-y-2">
                    {data.map((r) => (
                        <div key={r.id}
                            className={`flex items-center gap-3 px-3 py-2.5 rounded-xl border ${
                                r.id === myId ? "bg-accent/10 border-accent/40" : "bg-game-surface border-white/10"
                            }`}>
                            <span className="text-white/50 font-bold text-sm w-8 text-center shrink-0">{r.rank === 1 ? "1er" : `${r.rank}e`}</span>
                            <GuildEmblem icon={r.icon} color={r.color} size={30} />
                            <div className="flex-1 min-w-0">
                                <p className={`text-sm font-semibold truncate ${r.id === myId ? "text-accent" : "text-white"}`}>
                                    [{r.tag}] {r.name}
                                </p>
                                <p className="text-white/40 text-[11px]">Niv. {r.level} · {r.members} membres</p>
                            </div>
                            {score(kind, r) && <span className="text-gold font-bold text-xs shrink-0">{score(kind, r)}</span>}
                        </div>
                    ))}
                </div>
            ) : (
                <p className="text-white/30 text-sm text-center py-10">Aucune guilde pour l'instant.</p>
            )}
        </div>
    );
}
