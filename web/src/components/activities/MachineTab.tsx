import { formatNumber as fmt, formatPercent as pct } from "@/utils/format";
import { useState } from "react";
import { BoosterIcon, RerollIcon } from "@/components/ui/ItemIcon";
import LockedFeature from "@/components/ui/LockedFeature";
import { toast } from "@/stores/toastStore";
import { useToastMessage } from "@/hooks/useToastMessage";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { activitiesApi, type MachineItem, type MachineResult } from "@/api/activities";
import { useAuthStore } from "@/stores/authStore";
import { getResourceBalance } from "@/utils/resources";
import Button from "@/components/ui/Button";
import ResourceIcon from "@/components/ui/ResourceIcon";
import { errMsg } from "@/utils/errors";

const RESOURCE_NAME: Record<string, string> = { coins: "pièces", dust: "poussière" };

/** Machine d'amélioration (booster / reroll, amélioration du jour) + convertisseur de ressources. */
export default function MachineTab() {
    return (
        <div className="space-y-6">
            <LockedFeature feature="machine" compact><Machine /></LockedFeature>
            <Converter />
        </div>
    );
}

function Machine() {
    const qc = useQueryClient();
    const { user } = useAuthStore();
    const { data } = useQuery({ queryKey: ["machine"], queryFn: activitiesApi.machine });
    const [last, setLast] = useState<{ key: string; res: MachineResult } | null>(null);
    const setErr = (m: string | null) => { if (m) toast.error(m); };
    const [showRotation, setShowRotation] = useState(false);

    const upgrade = useMutation({
        mutationFn: ({ item, kind }: { item: MachineItem; kind: string; key: string }) => activitiesApi.upgrade(item, kind),
        onSuccess: (res, { key }) => {
            setErr("");
            setLast({ key, res });
            qc.setQueryData(["machine"], res.state);
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["booster-inventory"] });
            qc.invalidateQueries({ queryKey: ["reroll-tokens"] });
        },
        onError: (e) => setErr(errMsg(e)),
    });

    if (!data) return null;
    const coins = getResourceBalance(user, "coins");
    const itemKey = (i: MachineItem) => (i.item === "booster" ? `b-${i.booster_id}-${i.bonus_id ?? "base"}` : `r-${i.token_id}`);
    const upgradable = data.items.filter((i) => i.upgrades.length > 0);

    return (
        <section className="space-y-3">
            <div className="bg-game-surface border border-white/10 rounded-2xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                    <h2 className="text-white font-bold">Machine d'amélioration</h2>
                    <button className="text-accent text-xs" onClick={() => setShowRotation((v) => !v)}>
                        {showRotation ? "Masquer" : "Le cycle"}
                    </button>
                </div>
                <p className="text-white/70 text-sm">
                    Jour {data.day}/{data.length} : <span className="text-gold font-semibold">
                        {data.today.map((t) => t.label).join(" + ") || "rien"}
                    </span>
                </p>
                {data.event && (
                    <p className="text-xs bg-purple-500/15 border border-purple-400/40 text-purple-200 rounded-lg px-2 py-1.5">
                        Événement : {data.event.label}
                    </p>
                )}
                {showRotation && (
                    <div className="text-white/50 text-xs space-y-1">
                        <p>{data.length} jours dans le désordre : {data.cycle_upgrades.join(", ")}, et {data.cycle_events.length} jours surprise :</p>
                        <ul className="list-disc pl-4">
                            {data.cycle_events.map((e) => <li key={e}>{e}</li>)}
                        </ul>
                    </div>
                )}
                <p className="text-white/40 text-[11px]">
                    Un échec garde l'objet (sauf jour risqué) et augmente la chance du prochain essai.
                </p>
            </div>

            {!upgradable.length && (
                <p className="text-white/30 text-sm text-center">
                    {data.items.length ? "Aucun de tes objets ne peut recevoir l'amélioration du jour." : "Aucun booster ni reroll en stock."}
                </p>
            )}
            {upgradable.map((item) => {
                const key = itemKey(item);
                return (
                    <div key={key} className="bg-game-surface border border-white/10 rounded-xl p-3 space-y-2">
                        <div className="flex items-center justify-between gap-2">
                            <div className="min-w-0">
                                <p className="text-white text-sm font-semibold truncate">{item.item === "booster" ? <BoosterIcon /> : <RerollIcon />} {item.name}</p>
                                <p className="text-white/40 text-[11px] truncate">{item.detail}</p>
                            </div>
                            <span className="text-white/50 text-xs shrink-0">×{item.quantity}</span>
                        </div>
                        {item.upgrades.map((u) => (
                            <div key={u.kind} className="flex items-center gap-2 bg-black/20 rounded-lg px-2.5 py-2">
                                <div className="flex-1 min-w-0">
                                    <p className="text-white text-xs">→ {u.next}</p>
                                    <p className="text-white/40 text-[11px]">Réussite {pct(u.chance)} · cran {u.level + 1}</p>
                                </div>
                                <Button variant="gold" size="sm" disabled={coins < u.cost || upgrade.isPending}
                                    loading={upgrade.isPending && upgrade.variables?.key === key && upgrade.variables?.kind === u.kind}
                                    onClick={() => upgrade.mutate({ item, kind: u.kind, key })}>
                                    <span className="inline-flex items-center gap-1">{fmt(u.cost)} <ResourceIcon resourceId="coins" /></span>
                                </Button>
                            </div>
                        ))}
                        {last?.key === key && (
                            <p className={`text-xs font-semibold ${last.res.success ? "text-green-400" : "text-red-400"}`}>
                                {last.res.success
                                    ? `Réussi ! → ${last.res.result}`
                                    : last.res.destroyed ? "Raté… et l'objet a été détruit (jour risqué)." : "Raté… l'objet est intact, la prochaine tentative a plus de chances."}
                            </p>
                        )}
                    </div>
                );
            })}
            {last && !upgradable.some((i) => itemKey(i) === last.key) && (
                <p className={`text-xs font-semibold text-center ${last.res.success ? "text-green-400" : "text-red-400"}`}>
                    {last.res.success ? `Réussi ! → ${last.res.result}` : last.res.destroyed ? "Raté… l'objet a été détruit." : "Raté…"}
                </p>
            )}
        </section>
    );
}

function Converter() {
    const qc = useQueryClient();
    const { user } = useAuthStore();
    const { data } = useQuery({ queryKey: ["converter"], queryFn: activitiesApi.converter });
    const [pairIndex, setPairIndex] = useState(0);
    const [amount, setAmount] = useState("");
    const [, setMsg] = useToastMessage();

    const convert = useMutation({
        mutationFn: () => {
            const p = data!.pairs[pairIndex];
            return activitiesApi.convert(p.from, p.to, Number(amount));
        },
        onSuccess: (r) => {
            const p = data!.pairs[pairIndex];
            qc.setQueryData(["converter"], r.state);
            qc.invalidateQueries({ queryKey: ["player"] });
            setMsg({ text: `${fmt(r.spent)} ${RESOURCE_NAME[p.from] ?? p.from} → ${fmt(r.gained)} ${RESOURCE_NAME[p.to] ?? p.to}`, ok: true });
            setAmount("");
        },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });

    if (!data?.pairs.length) return null;
    const pair = data.pairs[Math.min(pairIndex, data.pairs.length - 1)];
    const value = Math.floor(Number(amount) || 0);
    const valid = value >= pair.give && value % pair.give === 0 && value <= pair.max_in && value <= getResourceBalance(user, pair.from);

    return (
        <section className="bg-game-surface border border-white/10 rounded-2xl p-4 space-y-3">
            <div className="flex items-center justify-between">
                <h2 className="text-white font-bold">Convertisseur</h2>
                <span className="text-white/50 text-xs">{data.uses_left} / {data.daily_uses} aujourd'hui</span>
            </div>
            <p className="text-white/40 text-[11px]">Pour compléter une ressource qui manque (avec perte).</p>
            <div className="flex gap-1.5">
                {data.pairs.map((p, i) => (
                    <button key={`${p.from}-${p.to}`}
                        className={`flex-1 py-1.5 rounded-lg text-xs font-bold inline-flex items-center justify-center gap-1 ${i === pairIndex ? "bg-accent text-white" : "bg-white/10 text-white/60"}`}
                        onClick={() => { setPairIndex(i); setAmount(""); }}>
                        <ResourceIcon resourceId={p.from} /> → <ResourceIcon resourceId={p.to} />
                    </button>
                ))}
            </div>
            <p className="text-white/60 text-xs">
                {pair.give} {RESOURCE_NAME[pair.from] ?? pair.from} → {pair.get} {RESOURCE_NAME[pair.to] ?? pair.to} ·
                {" "}{fmt(pair.max_in)} au plus par conversion
            </p>
            <div className="flex gap-2">
                <input type="number" min={pair.give} step={pair.give} max={pair.max_in} placeholder={`Multiple de ${pair.give}`}
                    className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                    value={amount} onChange={(e) => setAmount(e.target.value)} />
                <Button variant="gold" size="sm" disabled={!valid || data.uses_left <= 0} loading={convert.isPending} success={convert.isSuccess}
                    onClick={() => { setMsg(null); convert.mutate(); }}>
                    Convertir
                </Button>
            </div>
            {valid && <p className="text-white/40 text-[11px]">→ {fmt(Math.floor(value / pair.give) * pair.get)} {RESOURCE_NAME[pair.to] ?? pair.to}</p>}
        </section>
    );
}
