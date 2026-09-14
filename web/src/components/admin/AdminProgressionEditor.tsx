import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi, type AdminLevelTier, type AdminAchievementDef, type AdminQuestDef } from "@/api/admin";
import type { AdminResource } from "@/types/content";
import Button from "@/components/ui/Button";

const inputCls =
    "bg-black/30 border border-white/10 rounded-lg px-2 py-1.5 text-sm text-white " +
    "focus:border-accent focus:outline-none transition-colors";

function errMsg(e: unknown): string {
    if (e && typeof e === "object" && "response" in e) {
        const r = (e as { response?: { data?: { detail?: unknown } } }).response;
        if (typeof r?.data?.detail === "string") return r.data.detail;
    }
    return "Erreur.";
}

function ResourceSelect({ value, resources, onChange }: { value: string | null; resources: AdminResource[]; onChange: (v: string) => void }) {
    return (
        <select className={inputCls} value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
            <option value="">Aucune</option>
            {resources.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
        </select>
    );
}

function LevelTiersSection({ resources }: { resources: AdminResource[] }) {
    const qc = useQueryClient();
    const { data, isLoading } = useQuery({ queryKey: ["admin", "level-tiers"], queryFn: adminApi.listLevelTiers });
    const [drafts, setDrafts] = useState<Record<number, Partial<AdminLevelTier>>>({});
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const save = useMutation({
        mutationFn: (t: AdminLevelTier) => adminApi.updateLevelTier(t.level, {
            power_required: t.power_required, reward_resource_id: t.reward_resource_id || null, reward_amount: t.reward_amount,
        }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin", "level-tiers"] }); setMsg({ text: "Enregistré.", ok: true }); },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });

    if (isLoading) return <p className="text-white/40 text-sm">…</p>;

    return (
        <div className="space-y-2">
            {msg && <p className={`text-xs ${msg.ok ? "text-green-400" : "text-red-400"}`}>{msg.text}</p>}
            {(data ?? []).map((t) => {
                const draft = { ...t, ...drafts[t.level] };
                return (
                    <div key={t.level} className="bg-game-surface/60 border border-white/5 rounded-lg px-3 py-2 flex items-center gap-2 flex-wrap">
                        <span className="text-white text-sm font-semibold w-16 shrink-0">Niv. {t.level}</span>
                        <input
                            type="number" className={`${inputCls} w-28`} value={draft.power_required}
                            onChange={(e) => setDrafts((d) => ({ ...d, [t.level]: { ...draft, power_required: Number(e.target.value) } }))}
                        />
                        <ResourceSelect
                            value={draft.reward_resource_id}
                            resources={resources}
                            onChange={(v) => setDrafts((d) => ({ ...d, [t.level]: { ...draft, reward_resource_id: v } }))}
                        />
                        <input
                            type="number" className={`${inputCls} w-24`} placeholder="Qté" value={draft.reward_amount ?? ""}
                            onChange={(e) => setDrafts((d) => ({ ...d, [t.level]: { ...draft, reward_amount: e.target.value ? Number(e.target.value) : null } }))}
                        />
                        <Button variant="secondary" size="sm" loading={save.isPending && save.variables?.level === t.level} onClick={() => save.mutate(draft as AdminLevelTier)}>
                            OK
                        </Button>
                    </div>
                );
            })}
        </div>
    );
}

function AchievementsSection({ resources }: { resources: AdminResource[] }) {
    const qc = useQueryClient();
    const { data, isLoading } = useQuery({ queryKey: ["admin", "achievement-defs"], queryFn: adminApi.listAchievementDefs });
    const [drafts, setDrafts] = useState<Record<string, Partial<AdminAchievementDef>>>({});
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const save = useMutation({
        mutationFn: (a: AdminAchievementDef) => adminApi.updateAchievementDef(a.id, {
            threshold: a.threshold, reward_resource_id: a.reward_resource_id || null, reward_amount: a.reward_amount, active: a.active,
        }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin", "achievement-defs"] }); setMsg({ text: "Enregistré.", ok: true }); },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });

    if (isLoading) return <p className="text-white/40 text-sm">…</p>;

    const byCategory = (data ?? []).reduce<Record<string, AdminAchievementDef[]>>((acc, a) => {
        (acc[a.category] ??= []).push(a);
        return acc;
    }, {});

    return (
        <div className="space-y-4">
            {msg && <p className={`text-xs ${msg.ok ? "text-green-400" : "text-red-400"}`}>{msg.text}</p>}
            {Object.entries(byCategory).map(([cat, items]) => (
                <div key={cat}>
                    <h4 className="text-white/50 text-xs font-semibold uppercase mb-1.5">{cat}</h4>
                    <div className="space-y-2">
                        {items.map((a) => {
                            const draft = { ...a, ...drafts[a.id] };
                            return (
                                <div key={a.id} className="bg-game-surface/60 border border-white/5 rounded-lg px-3 py-2">
                                    <p className="text-white text-sm font-semibold">{a.name}</p>
                                    <p className="text-white/30 text-[11px] mb-1.5">{a.metric}{a.metric_param ? ` (${a.metric_param})` : ""}</p>
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <input
                                            type="number" className={`${inputCls} w-24`} title="Seuil" value={draft.threshold}
                                            onChange={(e) => setDrafts((d) => ({ ...d, [a.id]: { ...draft, threshold: Number(e.target.value) } }))}
                                        />
                                        <ResourceSelect
                                            value={draft.reward_resource_id}
                                            resources={resources}
                                            onChange={(v) => setDrafts((d) => ({ ...d, [a.id]: { ...draft, reward_resource_id: v } }))}
                                        />
                                        <input
                                            type="number" className={`${inputCls} w-24`} placeholder="Qté" value={draft.reward_amount ?? ""}
                                            onChange={(e) => setDrafts((d) => ({ ...d, [a.id]: { ...draft, reward_amount: e.target.value ? Number(e.target.value) : null } }))}
                                        />
                                        <Button variant="secondary" size="sm" loading={save.isPending && save.variables?.id === a.id} onClick={() => save.mutate(draft as AdminAchievementDef)}>
                                            OK
                                        </Button>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            ))}
        </div>
    );
}

function QuestsSection({ resources }: { resources: AdminResource[] }) {
    const qc = useQueryClient();
    const { data, isLoading } = useQuery({ queryKey: ["admin", "quest-defs"], queryFn: adminApi.listQuestDefs });
    const [drafts, setDrafts] = useState<Record<string, Partial<AdminQuestDef>>>({});
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const save = useMutation({
        mutationFn: (q: AdminQuestDef) => adminApi.updateQuestDef(q.id, {
            threshold: q.threshold, reward_resource_id: q.reward_resource_id || null, reward_amount: q.reward_amount, active: q.active,
        }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin", "quest-defs"] }); setMsg({ text: "Enregistré.", ok: true }); },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });

    if (isLoading) return <p className="text-white/40 text-sm">…</p>;

    return (
        <div className="space-y-2">
            {msg && <p className={`text-xs ${msg.ok ? "text-green-400" : "text-red-400"}`}>{msg.text}</p>}
            {(data ?? []).map((q) => {
                const draft = { ...q, ...drafts[q.id] };
                return (
                    <div key={q.id} className="bg-game-surface/60 border border-white/5 rounded-lg px-3 py-2">
                        <p className="text-white text-sm font-semibold">{q.name} <span className="text-white/30 text-xs">({q.period})</span></p>
                        <p className="text-white/30 text-[11px] mb-1.5">{q.metric}</p>
                        <div className="flex items-center gap-2 flex-wrap">
                            <input
                                type="number" className={`${inputCls} w-24`} title="Seuil" value={draft.threshold}
                                onChange={(e) => setDrafts((d) => ({ ...d, [q.id]: { ...draft, threshold: Number(e.target.value) } }))}
                            />
                            <ResourceSelect
                                value={draft.reward_resource_id}
                                resources={resources}
                                onChange={(v) => setDrafts((d) => ({ ...d, [q.id]: { ...draft, reward_resource_id: v } }))}
                            />
                            <input
                                type="number" className={`${inputCls} w-24`} placeholder="Qté" value={draft.reward_amount ?? ""}
                                onChange={(e) => setDrafts((d) => ({ ...d, [q.id]: { ...draft, reward_amount: e.target.value ? Number(e.target.value) : null } }))}
                            />
                            <Button variant="secondary" size="sm" loading={save.isPending && save.variables?.id === q.id} onClick={() => save.mutate(draft as AdminQuestDef)}>
                                OK
                            </Button>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

type Section = "levels" | "achievements" | "quests";

export default function AdminProgressionEditor({ resources }: { resources: AdminResource[] }) {
    const [section, setSection] = useState<Section>("levels");

    return (
        <div className="space-y-3">
            <div className="flex gap-2">
                {([
                    { key: "levels", label: "Niveaux" },
                    { key: "achievements", label: "Achievements" },
                    { key: "quests", label: "Quêtes" },
                ] as const).map((s) => (
                    <button
                        key={s.key}
                        className={`px-3 py-1.5 rounded-full text-xs font-semibold ${section === s.key ? "bg-accent text-white" : "bg-white/10 text-white/50"}`}
                        onClick={() => setSection(s.key)}
                    >
                        {s.label}
                    </button>
                ))}
            </div>
            {section === "levels" && <LevelTiersSection resources={resources} />}
            {section === "achievements" && <AchievementsSection resources={resources} />}
            {section === "quests" && <QuestsSection resources={resources} />}
        </div>
    );
}
