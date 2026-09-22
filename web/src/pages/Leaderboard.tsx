import { useState } from "react";
import LockedFeature from "@/components/ui/LockedFeature";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { leaderboardApi } from "@/api/leaderboard";
import { useTypes } from "@/hooks/useTypes";
import { useAuthStore } from "@/stores/authStore";
import type { LeaderboardEntry } from "@/types/leaderboard";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import BottomNav from "@/components/layout/BottomNav";
import GuildRankings from "@/components/guild/GuildRankings";
import MonthlyChallenge from "@/components/leaderboard/MonthlyChallenge";

function EntryRow({ entry, isSelf }: { entry: LeaderboardEntry; isSelf: boolean }) {
    const navigate = useNavigate();
    return (
        <button
            className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border text-left transition-colors ${
                isSelf ? "bg-accent/10 border-accent/40" : "bg-game-surface border-white/10 hover:border-white/30"
            }`}
            onClick={() => navigate(`/players/${entry.user_id}`)}
        >
            <div className="flex items-center gap-3 min-w-0">
                <span className="text-white/50 font-bold text-sm w-6 text-center shrink-0">
                    {entry.rank}
                </span>
                <span className={`text-sm font-semibold truncate ${isSelf ? "text-accent" : "text-white"}`}>
                    {entry.display_name}
                </span>
            </div>
            <span className="text-gold font-bold text-sm shrink-0">
                ⚡ {entry.total_power.toLocaleString("fr-FR")}
            </span>
        </button>
    );
}

function EntryList({ entries, isLoading }: { entries: LeaderboardEntry[]; isLoading: boolean }) {
    const { user } = useAuthStore();

    if (isLoading) return <LoadingSpinner text="Chargement..." />;
    if (entries.length === 0) {
        return (
            <p className="text-white/30 text-sm text-center py-10">
                Aucune carte avec de la puissance pour l'instant.
            </p>
        );
    }
    return (
        <div className="space-y-2">
            {entries.map((e) => (
                <EntryRow key={e.user_id} entry={e} isSelf={e.user_id === user?.id} />
            ))}
        </div>
    );
}

type Tab = "friends" | "global" | "type" | "guilds" | "monthly";

export default function Leaderboard() {
    const navigate = useNavigate();
    const [tab, setTab] = useState<Tab>("friends");
    const { data: types } = useTypes();
    const [selectedType, setSelectedType] = useState<string>("");

    const friendsQ = useQuery({
        queryKey: ["leaderboard", "friends"],
        queryFn: leaderboardApi.friends,
        enabled: tab === "friends",
    });
    const globalQ = useQuery({
        queryKey: ["leaderboard", "global"],
        queryFn: leaderboardApi.global,
        enabled: tab === "global",
    });
    const typeName = selectedType || types?.[0]?.name || "";
    const byTypeQ = useQuery({
        queryKey: ["leaderboard", "by-type", typeName],
        queryFn: () => leaderboardApi.byType(typeName),
        enabled: tab === "type" && !!typeName,
    });

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button className="text-accent text-sm font-semibold" onClick={() => navigate("/")}>
                    Retour
                </button>
                <h1 className="text-white font-bold">Classement</h1>
                <span className="w-14" />
            </header>

            <div className="flex border-b border-white/5">
                {([
                    { key: "friends", label: "Amis" },
                    { key: "global", label: "Global" },
                    { key: "type", label: "Par type" },
                    { key: "guilds", label: "Guildes" },
                    { key: "monthly", label: "Défi" },
                ] as const).map((t) => (
                    <button
                        key={t.key}
                        className={`flex-1 min-w-0 px-1 py-2.5 text-xs font-semibold truncate transition-colors ${
                            tab === t.key ? "text-accent border-b-2 border-accent" : "text-white/40 hover:text-white/70"
                        }`}
                        onClick={() => setTab(t.key)}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            <main className="flex-1 px-4 py-6 max-w-sm mx-auto w-full">
              <LockedFeature feature="leaderboard">
                {tab === "friends" && (
                    <>
                        <p className="text-white/30 text-xs mb-4">
                            Puissance totale = somme de la puissance de toutes tes cartes (et celles de tes amis).
                        </p>
                        <EntryList entries={friendsQ.data?.entries ?? []} isLoading={friendsQ.isLoading} />
                    </>
                )}

                {tab === "global" && (
                    <>
                        <p className="text-white/30 text-xs mb-4">Top 10 des joueurs, toutes puissances confondues.</p>
                        <EntryList entries={globalQ.data?.entries ?? []} isLoading={globalQ.isLoading} />
                    </>
                )}

                {tab === "type" && (
                    <>
                        <select
                            className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white mb-4"
                            value={typeName}
                            onChange={(e) => setSelectedType(e.target.value)}
                        >
                            {(types ?? []).map((t) => (
                                <option key={t.id} value={t.name}>{t.name}</option>
                            ))}
                        </select>
                        <EntryList entries={byTypeQ.data?.entries ?? []} isLoading={byTypeQ.isLoading} />
                    </>
                )}

                {tab === "guilds" && <GuildRankings />}
                {tab === "monthly" && <MonthlyChallenge />}
              </LockedFeature>
            </main>

            <BottomNav />
        </div>
    );
}
