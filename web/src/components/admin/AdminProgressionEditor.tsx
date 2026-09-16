import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi, type AdminLevelTier, type AdminAchievementDef, type AdminQuestDef } from "@/api/admin";
import type { AdminResource, AdminBooster } from "@/types/content";
import Button from "@/components/ui/Button";
import { errMsg } from "@/utils/errors";

const inputCls =
    "bg-black/30 border border-white/10 rounded-lg px-2 py-1.5 text-sm text-white " +
    "focus:border-accent focus:outline-none transition-colors";

function ResourceSelect({ value, resources, onChange }: { value: string | null; resources: AdminResource[]; onChange: (v: string) => void }) {
    return (
        <select className={inputCls} value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
            <option value="">Aucune</option>
            {resources.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
        </select>
    );
}

function BoosterSelect({ value, boosters, onChange }: { value: string | null; boosters: AdminBooster[]; onChange: (v: string) => void }) {
    return (
        <select className={inputCls} value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
            <option value="">Aucun booster</option>
            {boosters.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
    );
}

function LevelTiersSection({
    data, drafts, setDrafts, resources, boosters,
}: {
    data: AdminLevelTier[];
    drafts: Record<number, Partial<AdminLevelTier>>;
    setDrafts: (fn: (d: Record<number, Partial<AdminLevelTier>>) => Record<number, Partial<AdminLevelTier>>) => void;
    resources: AdminResource[];
    boosters: AdminBooster[];
}) {
    return (
        <div className="space-y-2">
            {data.map((t) => {
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
                        <BoosterSelect
                            value={draft.reward_booster_id}
                            boosters={boosters}
                            onChange={(v) => setDrafts((d) => ({ ...d, [t.level]: { ...draft, reward_booster_id: v } }))}
                        />
                    </div>
                );
            })}
        </div>
    );
}

function AchievementsSection({
    data, drafts, setDrafts, resources, boosters,
}: {
    data: AdminAchievementDef[];
    drafts: Record<string, Partial<AdminAchievementDef>>;
    setDrafts: (fn: (d: Record<string, Partial<AdminAchievementDef>>) => Record<string, Partial<AdminAchievementDef>>) => void;
    resources: AdminResource[];
    boosters: AdminBooster[];
}) {
    const byCategory = data.reduce<Record<string, AdminAchievementDef[]>>((acc, a) => {
        (acc[a.category] ??= []).push(a);
        return acc;
    }, {});

    return (
        <div className="space-y-4">
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
                                        <BoosterSelect
                                            value={draft.reward_booster_id}
                                            boosters={boosters}
                                            onChange={(v) => setDrafts((d) => ({ ...d, [a.id]: { ...draft, reward_booster_id: v } }))}
                                        />
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

function QuestsSection({
    data, drafts, setDrafts, resources, boosters,
}: {
    data: AdminQuestDef[];
    drafts: Record<string, Partial<AdminQuestDef>>;
    setDrafts: (fn: (d: Record<string, Partial<AdminQuestDef>>) => Record<string, Partial<AdminQuestDef>>) => void;
    resources: AdminResource[];
    boosters: AdminBooster[];
}) {
    return (
        <div className="space-y-2">
            {data.map((q) => {
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
                            <BoosterSelect
                                value={draft.reward_booster_id}
                                boosters={boosters}
                                onChange={(v) => setDrafts((d) => ({ ...d, [q.id]: { ...draft, reward_booster_id: v } }))}
                            />
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

type Section = "levels" | "achievements" | "quests";

export default function AdminProgressionEditor({ resources, boosters }: { resources: AdminResource[]; boosters: AdminBooster[] }) {
    const qc = useQueryClient();
    const [section, setSection] = useState<Section>("levels");
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const levelTiersQ = useQuery({ queryKey: ["admin", "level-tiers"], queryFn: adminApi.listLevelTiers });
    const achievementsQ = useQuery({ queryKey: ["admin", "achievement-defs"], queryFn: adminApi.listAchievementDefs });
    const questsQ = useQuery({ queryKey: ["admin", "quest-defs"], queryFn: adminApi.listQuestDefs });

    const [levelDrafts, setLevelDrafts] = useState<Record<number, Partial<AdminLevelTier>>>({});
    const [achievementDrafts, setAchievementDrafts] = useState<Record<string, Partial<AdminAchievementDef>>>({});
    const [questDrafts, setQuestDrafts] = useState<Record<string, Partial<AdminQuestDef>>>({});

    const dirtyCount = Object.keys(levelDrafts).length + Object.keys(achievementDrafts).length + Object.keys(questDrafts).length;

    const saveAll = useMutation({
        mutationFn: async () => {
            const calls: Promise<unknown>[] = [];

            for (const [level, patch] of Object.entries(levelDrafts)) {
                const t = { ...levelTiersQ.data!.find((x) => x.level === Number(level))!, ...patch };
                calls.push(adminApi.updateLevelTier(t.level, {
                    power_required: t.power_required, reward_resource_id: t.reward_resource_id || null,
                    reward_amount: t.reward_amount, reward_booster_id: t.reward_booster_id || null,
                }));
            }
            for (const [id, patch] of Object.entries(achievementDrafts)) {
                const a = { ...achievementsQ.data!.find((x) => x.id === id)!, ...patch };
                calls.push(adminApi.updateAchievementDef(a.id, {
                    threshold: a.threshold, reward_resource_id: a.reward_resource_id || null,
                    reward_amount: a.reward_amount, reward_booster_id: a.reward_booster_id || null, active: a.active,
                }));
            }
            for (const [id, patch] of Object.entries(questDrafts)) {
                const q = { ...questsQ.data!.find((x) => x.id === id)!, ...patch };
                calls.push(adminApi.updateQuestDef(q.id, {
                    threshold: q.threshold, reward_resource_id: q.reward_resource_id || null,
                    reward_amount: q.reward_amount, reward_booster_id: q.reward_booster_id || null, active: q.active,
                }));
            }

            await Promise.all(calls);
        },
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["admin", "level-tiers"] });
            qc.invalidateQueries({ queryKey: ["admin", "achievement-defs"] });
            qc.invalidateQueries({ queryKey: ["admin", "quest-defs"] });
            setLevelDrafts({});
            setAchievementDrafts({});
            setQuestDrafts({});
            setMsg({ text: "Tout est enregistré.", ok: true });
        },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });

    const loading = levelTiersQ.isLoading || achievementsQ.isLoading || questsQ.isLoading;

    return (
        <div className="space-y-3 pb-2">
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

            {loading ? (
                <p className="text-white/40 text-sm">…</p>
            ) : (
                <>
                    {section === "levels" && (
                        <LevelTiersSection data={levelTiersQ.data ?? []} drafts={levelDrafts} setDrafts={setLevelDrafts} resources={resources} boosters={boosters} />
                    )}
                    {section === "achievements" && (
                        <AchievementsSection data={achievementsQ.data ?? []} drafts={achievementDrafts} setDrafts={setAchievementDrafts} resources={resources} boosters={boosters} />
                    )}
                    {section === "quests" && (
                        <QuestsSection data={questsQ.data ?? []} drafts={questDrafts} setDrafts={setQuestDrafts} resources={resources} boosters={boosters} />
                    )}
                </>
            )}

            <div className="sticky bottom-0 bg-game-bg/95 backdrop-blur border-t border-white/10 pt-3 -mx-4 px-4 pb-2">
                {msg && <p className={`text-xs mb-2 ${msg.ok ? "text-green-400" : "text-red-400"}`}>{msg.text}</p>}
                <Button
                    variant="primary" className="w-full"
                    disabled={dirtyCount === 0}
                    loading={saveAll.isPending}
                    onClick={() => saveAll.mutate()}
                >
                    {dirtyCount > 0 ? `Enregistrer tout (${dirtyCount})` : "Enregistrer tout"}
                </Button>
            </div>
        </div>
    );
}
