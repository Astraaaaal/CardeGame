import { play } from "@/utils/sound";
import { formatNumber as fmt, formatPercent as pct } from "@/utils/format";
import { inputCls } from "@/components/ui/formStyles";
import { useState } from "react";
import { BoosterIcon, RerollIcon } from "@/components/ui/ItemIcon";
import LockedFeature from "@/components/ui/LockedFeature";
import { toast } from "@/stores/toastStore";
import { useToastMessage } from "@/hooks/useToastMessage";
import { useResourceNames } from "@/hooks/useResourceNames";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { activitiesApi, type MachineItem, type MachineResult, type MachineUpgrade } from "@/api/activities";
import { useAuthStore } from "@/stores/authStore";
import { getResourceBalance } from "@/utils/resources";
import Button from "@/components/ui/Button";
import ResourceIcon from "@/components/ui/ResourceIcon";
import { errMsg } from "@/utils/errors";

/** Machine d'amélioration (booster / reroll, amélioration du jour) + convertisseur de ressources. */
export default function MachineTab() {
    return (
        <div className="space-y-6">
            <LockedFeature feature="machine" compact><Machine /></LockedFeature>
            <Converter />
        </div>
    );
}

/** Réussite avec les ressources ajoutées (même règle que le serveur : plafond du cran). */
function chanceWith(u: MachineUpgrade, extra: Record<string, number>): number {
    const bonus = u.bonus_options.reduce((sum, o) => sum + o.per_unit * (extra[o.resource_id] ?? 0), 0);
    return bonus > 0 ? Math.max(u.chance, Math.min(u.cap, u.chance + bonus)) : u.chance;
}

function Machine() {
    const qc = useQueryClient();
    const { user } = useAuthStore();
    const { data } = useQuery({ queryKey: ["machine"], queryFn: activitiesApi.machine });
    const [last, setLast] = useState<{ key: string; res: MachineResult } | null>(null);
    const [showRotation, setShowRotation] = useState(false);
    // Ressources ajoutées, par amélioration (clé objet + type).
    const [extras, setExtras] = useState<Record<string, Record<string, number>>>({});
    const [openExtra, setOpenExtra] = useState<string | null>(null);

    const upgrade = useMutation({
        mutationFn: ({ item, kind, extra }: { item: MachineItem; kind: string; key: string; extra: Record<string, number> }) =>
            activitiesApi.upgrade(item, kind, extra),
        onSuccess: (res, { key, kind }) => {
            play(res.success ? "success" : "fail");
            setLast({ key, res });
            setExtras((e) => ({ ...e, [`${key}:${kind}`]: {} }));
            qc.setQueryData(["machine"], res.state);
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["booster-inventory"] });
            qc.invalidateQueries({ queryKey: ["reroll-tokens"] });
        },
        onError: (e) => toast.error(errMsg(e)),
    });

    if (!data) return null;
    const balance = (id: string) => getResourceBalance(user, id);
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
                    Ajoute des ressources liées pour augmenter la réussite.
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
                        {item.upgrades.map((u) => {
                            const uKey = `${key}:${u.kind}`;
                            const extra = extras[uKey] ?? {};
                            const need = u.required;
                            // Quantité ajoutable : le solde, moins la part obligatoire si c'est la même ressource.
                            const spare = (id: string) => balance(id) - (need?.resource_id === id ? need.amount : 0);
                            const setQty = (id: string, qty: number) =>
                                setExtras((e) => ({ ...e, [uKey]: { ...extra, [id]: Math.max(0, Math.min(qty, spare(id))) } }));
                            const needOk = !need || balance(need.resource_id) - (extra[need.resource_id] ?? 0) >= need.amount;
                            const chance = chanceWith(u, extra);
                            const added = Object.values(extra).some((q) => q > 0);
                            return (
                                <div key={u.kind} className="bg-black/20 rounded-lg px-2.5 py-2 space-y-2">
                                    <div className="flex items-center gap-2">
                                        <div className="flex-1 min-w-0">
                                            <p className="text-white text-xs">→ {u.next}</p>
                                            <p className="text-white/40 text-[11px]">
                                                Réussite <span className={added ? "text-green-400 font-semibold" : ""}>{pct(chance)}</span>
                                                {" "}· cran {u.level + 1}
                                            </p>
                                        </div>
                                        <Button variant="gold" size="sm"
                                            disabled={balance("coins") < u.cost || !needOk || upgrade.isPending}
                                            loading={upgrade.isPending && upgrade.variables?.key === key && upgrade.variables?.kind === u.kind}
                                            onClick={() => upgrade.mutate({ item, kind: u.kind, key, extra })}>
                                            <span className="inline-flex items-center gap-1">
                                                {fmt(u.cost)} <ResourceIcon resourceId="coins" />
                                                {need && <>+ {need.amount} <ResourceIcon resourceId={need.resource_id} /></>}
                                            </span>
                                        </Button>
                                    </div>
                                    {need && (
                                        <p className={`text-[11px] ${needOk ? "text-white/50" : "text-red-400"}`}>
                                            Requis à ce cran : {need.amount} {need.name} (tu en as {fmt(balance(need.resource_id))})
                                        </p>
                                    )}
                                    {u.bonus_options.length > 0 && (
                                        <button className="text-accent text-[11px]" onClick={() => setOpenExtra(openExtra === uKey ? null : uKey)}>
                                            {openExtra === uKey ? "Masquer les ressources" : `Ajouter des ressources (jusqu'à ${pct(u.cap)})`}
                                        </button>
                                    )}
                                    {openExtra === uKey && (
                                        <div className="space-y-1.5">
                                            {u.bonus_options.map((o) => {
                                                const qty = extra[o.resource_id] ?? 0;
                                                const owned = spare(o.resource_id);
                                                return (
                                                    <div key={o.resource_id} className="flex items-center gap-2 text-[11px]">
                                                        <ResourceIcon resourceId={o.resource_id} className="w-4 h-4 shrink-0" />
                                                        <span className="flex-1 min-w-0 truncate text-white/70">
                                                            {o.name} <span className="text-white/40">+{Math.round(o.per_unit * 100)} % · {fmt(owned)}</span>
                                                        </span>
                                                        <button className="w-6 h-6 rounded bg-white/10 text-white disabled:opacity-30"
                                                            disabled={qty <= 0} onClick={() => setQty(o.resource_id, qty - 1)}>−</button>
                                                        <span className="w-6 text-center text-white tabular-nums">{qty}</span>
                                                        <button className="w-6 h-6 rounded bg-white/10 text-white disabled:opacity-30"
                                                            disabled={qty >= owned || chance >= u.cap} onClick={() => setQty(o.resource_id, qty + 1)}>+</button>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
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
    const names = useResourceNames();
    const { data } = useQuery({ queryKey: ["converter"], queryFn: activitiesApi.converter });
    const [fromId, setFromId] = useState("coins");
    const [toId, setToId] = useState("dust");
    const [amount, setAmount] = useState("");
    const [, setMsg] = useToastMessage();
    const label = (id: string) => (id === "coins" ? "Pièces" : names[id] ?? id);

    const pairs = data?.pairs ?? [];
    // Ne proposer que ce qu'on peut réellement convertir : une ressource qu'on
    // n'a pas, ou pas en assez grande quantité pour un seul lot, n'est qu'une
    // ligne morte dans la liste.
    const sources = [...new Set(pairs.map((p) => p.from))].filter((id) => {
        const lotMin = Math.min(...pairs.filter((p) => p.from === id).map((p) => p.give));
        return getResourceBalance(user, id) >= lotMin;
    });
    const from = sources.includes(fromId) ? fromId : sources[0];
    const targets = pairs.filter((p) => p.from === from);
    const pair = targets.find((p) => p.to === toId) ?? targets[0];

    const convert = useMutation({
        mutationFn: () => activitiesApi.convert(pair.from, pair.to, Number(amount)),
        onSuccess: (r) => {
            qc.setQueryData(["converter"], r.state);
            qc.invalidateQueries({ queryKey: ["player"] });
            setMsg({ text: `${fmt(r.spent)} ${label(pair.from)} → ${fmt(r.gained)} ${label(pair.to)}`, ok: true });
            setAmount("");
        },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });

    if (!data) return null;
    if (!pair) {
        return (
            <section className="bg-game-surface border border-white/10 rounded-2xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                    <h2 className="text-white font-bold">Convertisseur</h2>
                    <span className="text-white/50 text-xs">{data.uses_left} / {data.daily_uses} aujourd'hui</span>
                </div>
                <p className="text-white/40 text-[11px]">
                    Rien à convertir pour l'instant : il faut assez d'une ressource pour former un lot complet.
                </p>
            </section>
        );
    }
    const value = Math.floor(Number(amount) || 0);
    const owned = getResourceBalance(user, pair.from);
    const valid = value >= pair.give && value % pair.give === 0 && value <= pair.max_in && value <= owned;
    const best = Math.min(pair.max_in, owned - (owned % pair.give));

    return (
        <section className="bg-game-surface border border-white/10 rounded-2xl p-4 space-y-3">
            <div className="flex items-center justify-between">
                <h2 className="text-white font-bold">Convertisseur</h2>
                <span className="text-white/50 text-xs">{data.uses_left} / {data.daily_uses} aujourd'hui</span>
            </div>
            <p className="text-white/40 text-[11px]">Pour compléter une ressource qui manque (avec perte).</p>
            <div className="grid grid-cols-2 gap-2">
                <label className="text-white/50 text-[11px] space-y-1">
                    <span>De</span>
                    <select className={inputCls} value={from} onChange={(e) => { setFromId(e.target.value); setAmount(""); }}>
                        {sources.map((id) => <option key={id} value={id}>{label(id)} ({fmt(getResourceBalance(user, id))})</option>)}
                    </select>
                </label>
                <label className="text-white/50 text-[11px] space-y-1">
                    <span>Vers</span>
                    <select className={inputCls} value={pair.to} onChange={(e) => { setToId(e.target.value); setAmount(""); }}>
                        {targets.map((p) => <option key={p.to} value={p.to}>{label(p.to)}</option>)}
                    </select>
                </label>
            </div>
            <p className="text-white/60 text-xs inline-flex items-center gap-1 flex-wrap">
                {pair.give} <ResourceIcon resourceId={pair.from} /> → {pair.get} <ResourceIcon resourceId={pair.to} />
                · {fmt(pair.max_in)} au plus par conversion
            </p>
            <div className="flex gap-2">
                <input type="number" min={pair.give} step={pair.give} max={pair.max_in} placeholder={`Multiple de ${pair.give}`}
                    className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                    value={amount} onChange={(e) => setAmount(e.target.value)} />
                {best >= pair.give && (
                    <button className="text-accent text-xs px-1" onClick={() => setAmount(String(best))}>Max</button>
                )}
                <Button variant="gold" size="sm" disabled={!valid || data.uses_left <= 0} loading={convert.isPending} success={convert.isSuccess}
                    onClick={() => { setMsg(null); convert.mutate(); }}>
                    Convertir
                </Button>
            </div>
            {valid && (
                <p className="text-white/40 text-[11px] inline-flex items-center gap-1">
                    → {fmt(Math.floor(value / pair.give) * pair.get)} <ResourceIcon resourceId={pair.to} /> {label(pair.to)}
                </p>
            )}
        </section>
    );
}
