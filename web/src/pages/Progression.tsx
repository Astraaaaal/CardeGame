import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { progressionApi } from "@/api/progression";
import type { Achievement, AchievementCategory, Quest } from "@/types/progression";
import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ResourceIcon from "@/components/ui/ResourceIcon";
import TrophyRoad from "@/components/progression/TrophyRoad";
import BottomNav from "@/components/layout/BottomNav";

function errMsg(e: unknown): string {
    if (e && typeof e === "object" && "response" in e) {
        const r = (e as { response?: { data?: { detail?: unknown } } }).response;
        if (typeof r?.data?.detail === "string") return r.data.detail;
    }
    return "Erreur.";
}

function ProgressBar({ value, max }: { value: number; max: number }) {
    const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 100;
    return (
        <div className="h-2 bg-black/30 rounded-full overflow-hidden">
            <div className="h-full bg-accent transition-all" style={{ width: `${pct}%` }} />
        </div>
    );
}

function RoadTab() {
    const qc = useQueryClient();
    const { data, isLoading } = useQuery({ queryKey: ["level-status"], queryFn: progressionApi.getLevel });

    const claim = useMutation({
        mutationFn: progressionApi.claimLevel,
        onSuccess: (status) => {
            qc.setQueryData(["level-status"], status);
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["booster-inventory"] });
            qc.invalidateQueries({ queryKey: ["level-tiers"] });
        },
    });

    if (isLoading || !data) return <LoadingSpinner text="Chargement..." />;

    return (
        <div className="space-y-5">
            {data.has_unclaimed && (
                <div className="bg-gold/10 border border-gold/30 rounded-2xl p-4">
                    <p className="text-white font-semibold text-sm mb-2">Récompense(s) de niveau à récupérer</p>
                    <div className="space-y-1.5 mb-3">
                        {data.pending_rewards.map((r) => (
                            <div key={r.level} className="flex items-center gap-2 text-sm text-white/80">
                                <span className="text-accent font-semibold">Niv. {r.level}</span>
                                {r.reward_amount != null && r.reward_resource_id && (
                                    <span className="flex items-center gap-1">
                                        <ResourceIcon resourceId={r.reward_resource_id} className="w-4 h-4" />
                                        {r.reward_amount.toLocaleString("fr-FR")}
                                    </span>
                                )}
                                {r.reward_booster_id && <span>{r.reward_booster_name}</span>}
                            </div>
                        ))}
                    </div>
                    <Button variant="gold" size="sm" className="w-full" loading={claim.isPending} onClick={() => claim.mutate()}>
                        Tout récupérer
                    </Button>
                </div>
            )}

            <TrophyRoad />
        </div>
    );
}

const CATEGORY_LABELS: Record<AchievementCategory, string> = {
    collection: "Collection", social: "Social", economy: "Économie",
    progression: "Progression", meta: "Meta",
};

function AchievementRow({ achievement }: { achievement: Achievement }) {
    const qc = useQueryClient();
    const [err, setErr] = useState("");
    const claim = useMutation({
        mutationFn: () => progressionApi.claimAchievement(achievement.id),
        onSuccess: (a) => {
            qc.setQueryData<Achievement[]>(["achievements"], (old) => old?.map((x) => x.id === a.id ? a : x));
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["collection"] });
        },
        onError: (e) => setErr(errMsg(e)),
    });

    const unlocked = !!achievement.unlocked_at;
    const claimed = !!achievement.claimed_at;

    return (
        <div className={`rounded-xl border p-3 ${unlocked ? "bg-game-surface border-white/10" : "bg-black/20 border-white/5"}`}>
            <div className="flex items-start justify-between gap-2 mb-1.5">
                <div className="min-w-0">
                    <p className={`text-sm font-semibold ${unlocked ? "text-white" : "text-white/40"}`}>
                        {achievement.name}
                    </p>
                    <p className="text-white/40 text-xs mt-0.5">{achievement.description}</p>
                </div>
                {(achievement.reward_amount || achievement.reward_booster_id) && (
                    <div className="flex items-center gap-1 text-xs text-white/50 shrink-0">
                        {achievement.reward_amount ? (
                            <>
                                <ResourceIcon resourceId={achievement.reward_resource_id ?? "coins"} className="w-3.5 h-3.5" />
                                {achievement.reward_amount.toLocaleString("fr-FR")}
                            </>
                        ) : "booster"}
                    </div>
                )}
            </div>
            {!unlocked && (
                <>
                    <ProgressBar value={achievement.progress} max={achievement.threshold} />
                    <p className="text-white/30 text-[11px] mt-1">
                        {achievement.progress.toLocaleString("fr-FR")} / {achievement.threshold.toLocaleString("fr-FR")}
                    </p>
                </>
            )}
            {unlocked && !claimed && (
                <Button variant="gold" size="sm" className="w-full mt-1" loading={claim.isPending} onClick={() => claim.mutate()}>
                    Récupérer
                </Button>
            )}
            {claimed && <p className="text-green-400 text-xs mt-1">Récupéré</p>}
            {err && <p className="text-red-400 text-xs mt-1">{err}</p>}
        </div>
    );
}

function AchievementsTab() {
    const { data, isLoading } = useQuery({ queryKey: ["achievements"], queryFn: progressionApi.getAchievements });

    if (isLoading || !data) return <LoadingSpinner text="Chargement..." />;

    const unlockedCount = data.filter((a) => a.unlocked_at).length;
    const byCategory = data.reduce<Record<string, Achievement[]>>((acc, a) => {
        (acc[a.category] ??= []).push(a);
        return acc;
    }, {});

    return (
        <div className="space-y-6">
            <p className="text-white/40 text-xs text-center">
                {unlockedCount} / {data.length} débloqués
            </p>
            {(Object.keys(CATEGORY_LABELS) as AchievementCategory[]).map((cat) => {
                const items = byCategory[cat];
                if (!items || items.length === 0) return null;
                return (
                    <div key={cat}>
                        <h3 className="text-white/60 text-xs font-semibold uppercase tracking-wide mb-2">
                            {CATEGORY_LABELS[cat]}
                        </h3>
                        <div className="space-y-2">
                            {items.map((a) => <AchievementRow key={a.id} achievement={a} />)}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

function QuestsTab() {
    const qc = useQueryClient();
    const [err, setErr] = useState("");
    const { data, isLoading } = useQuery({ queryKey: ["quests"], queryFn: progressionApi.getQuests });

    const claim = useMutation({
        mutationFn: (id: number) => progressionApi.claimQuest(id),
        onSuccess: (q) => {
            qc.setQueryData<Quest[]>(["quests"], (old) => old?.map((x) => x.id === q.id ? q : x));
            qc.invalidateQueries({ queryKey: ["player"] });
        },
        onError: (e) => setErr(errMsg(e)),
    });

    if (isLoading || !data) return <LoadingSpinner text="Chargement..." />;

    const daily = data.filter((q) => q.period === "daily");
    const weekly = data.filter((q) => q.period === "weekly");

    const Section = ({ title, quests, hint }: { title: string; quests: typeof data; hint: string }) => (
        <div>
            <h3 className="text-white/60 text-xs font-semibold uppercase tracking-wide mb-1">{title}</h3>
            <p className="text-white/30 text-[11px] mb-2">{hint}</p>
            <div className="space-y-2">
                {quests.map((q) => (
                    <div key={q.id} className="bg-game-surface rounded-xl border border-white/10 p-3">
                        <div className="flex items-start justify-between gap-2 mb-1.5">
                            <div className="min-w-0">
                                <p className="text-white text-sm font-semibold">{q.name}</p>
                                <p className="text-white/40 text-xs mt-0.5">{q.description}</p>
                            </div>
                            {q.reward_amount && (
                                <div className="flex items-center gap-1 text-xs text-white/50 shrink-0">
                                    <ResourceIcon resourceId={q.reward_resource_id ?? "coins"} className="w-3.5 h-3.5" />
                                    {q.reward_amount.toLocaleString("fr-FR")}
                                </div>
                            )}
                        </div>
                        <ProgressBar value={q.progress} max={q.threshold} />
                        <p className="text-white/30 text-[11px] mt-1">{q.progress} / {q.threshold}</p>
                        {q.completed && !q.claimed_at && (
                            <Button variant="gold" size="sm" className="w-full mt-1.5" loading={claim.isPending} onClick={() => claim.mutate(q.id)}>
                                Récupérer
                            </Button>
                        )}
                        {q.claimed_at && <p className="text-green-400 text-xs mt-1.5">Récupéré</p>}
                    </div>
                ))}
            </div>
        </div>
    );

    return (
        <div className="space-y-6">
            {err && <p className="text-red-400 text-xs">{err}</p>}
            <Section title="Journalières" quests={daily} hint="Se renouvellent chaque jour." />
            <Section title="Hebdomadaires" quests={weekly} hint="Se renouvellent chaque semaine." />
        </div>
    );
}

type Tab = "road" | "achievements" | "quests";

export default function Progression() {
    const navigate = useNavigate();
    const [tab, setTab] = useState<Tab>("road");

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button className="text-accent text-sm font-semibold" onClick={() => navigate("/")}>
                    Retour
                </button>
                <h1 className="text-white font-bold">Progression</h1>
                <span className="w-14" />
            </header>

            <div className="flex border-b border-white/5">
                {([
                    { key: "road", label: "Route des niveaux" },
                    { key: "achievements", label: "Achievements" },
                    { key: "quests", label: "Quêtes" },
                ] as const).map((t) => (
                    <button
                        key={t.key}
                        className={`flex-1 py-2.5 text-sm font-semibold transition-colors ${
                            tab === t.key ? "text-accent border-b-2 border-accent" : "text-white/40 hover:text-white/70"
                        }`}
                        onClick={() => setTab(t.key)}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            <main className="flex-1 px-4 py-6 max-w-sm mx-auto w-full overflow-y-auto">
                {tab === "road" && <RoadTab />}
                {tab === "achievements" && <AchievementsTab />}
                {tab === "quests" && <QuestsTab />}
            </main>

            <BottomNav />
        </div>
    );
}
