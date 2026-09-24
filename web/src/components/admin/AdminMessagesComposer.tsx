import { inputCls, labelCls } from "@/components/ui/formStyles";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { adminMessagesApi, adminPremiumApi, type AdminMessageReward } from "@/api/admin";
import type { AdminBooster, AdminCharacter, AdminResource, Tuning } from "@/types/content";
import Button from "@/components/ui/Button";
import { errMsg } from "@/utils/errors";


type Kind = AdminMessageReward["kind"];

interface AdminMessagesComposerProps {
    resources: AdminResource[];
    boosters: AdminBooster[];
    characters: AdminCharacter[];
    tuning: Tuning | undefined;
}

const AXES = [
    ["reroll_rarity", "Rareté"], ["reroll_quality", "Qualité"], ["reroll_specialty", "Spécialité"],
    ["reroll_jewelry", "Bijou"], ["reroll_power", "Puissance"],
] as const;

/** Formulaire d'ajout d'une récompense, selon son type. */
function RewardForm({ kind, resources, boosters, characters, tuning, onAdd, onCancel }: AdminMessagesComposerProps & {
    kind: Kind;
    onAdd: (reward: AdminMessageReward) => void;
    onCancel: () => void;
}) {
    const [resourceId, setResourceId] = useState(resources[0]?.id ?? "coins");
    const [amount, setAmount] = useState(1);
    const [boosterId, setBoosterId] = useState(boosters[0]?.id ?? "");
    const [minRarity, setMinRarity] = useState("");
    const [multiplier, setMultiplier] = useState<number | "">("");
    const [label, setLabel] = useState("");
    const [rules, setRules] = useState({
        reroll_rarity: false, reroll_quality: false, reroll_specialty: false, reroll_jewelry: false, reroll_power: false,
        reroll_mode: "guaranteed_min" as "random" | "guaranteed_min",
    });
    const [card, setCard] = useState({
        character_id: characters[0]?.id ?? "", rarity_id: tuning?.rarities[0]?.id ?? "",
        quality_id: tuning?.qualities[0]?.id ?? "", specialty_id: tuning?.specialties[0]?.id ?? "",
        jewelry_id: tuning?.jewelries[0]?.id ?? "",
    });
    const [powerMode, setPowerMode] = useState<"rolled" | "fixed">("rolled");
    const [power, setPower] = useState<number | "">("");
    const [chosenIds, setChosenIds] = useState<string[]>([]);
    const { data: cosmetics = [] } = useQuery({
        queryKey: ["admin-cosmetics"], queryFn: adminPremiumApi.listCosmetics,
        enabled: kind === "cosmetic_choice", staleTime: 60_000,
    });

    const build = (): AdminMessageReward | null => {
        if (kind === "resource") return amount > 0 ? { kind, id: resourceId, amount } : null;
        if (kind === "booster") {
            return boosterId && amount > 0 ? {
                kind, id: boosterId, quantity: amount, force_min_rarity_id: minRarity || null,
                rarity_weight_multiplier: multiplier || null, label: label.trim(),
            } : null;
        }
        if (kind === "reroll") {
            const anyAxis = AXES.some(([key]) => rules[key]);
            return anyAxis && label.trim() && amount > 0 ? { kind, label: label.trim(), quantity: amount, rules } : null;
        }
        // Entre deux et huit options : un « choix » à une seule option n'en est
        // pas un, et au-delà de huit la liste devient un catalogue.
        if (kind === "cosmetic_choice") {
            return chosenIds.length >= 2 && chosenIds.length <= 8 ? { kind, ids: chosenIds } : null;
        }
        if (Object.values(card).some((v) => !v) || (powerMode === "fixed" && !power)) return null;
        return { kind, ...card, power_mode: powerMode, power: powerMode === "fixed" ? Number(power) : null };
    };
    const reward = build();

    const refSelect = (key: keyof typeof card, title: string, options: { id: string; name: string }[]) => (
        <div>
            <label className={labelCls}>{title}</label>
            <select className={inputCls} value={card[key]} onChange={(e) => setCard({ ...card, [key]: e.target.value })}>
                {options.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
            </select>
        </div>
    );
    const quantityInput = (title: string) => (
        <div>
            <label className={labelCls}>{title}</label>
            <input type="number" min={1} className={inputCls} value={amount}
                onChange={(e) => setAmount(Math.max(0, Number(e.target.value) || 0))} />
        </div>
    );

    return (
        <div className="border border-accent/30 rounded-lg p-3 space-y-2 bg-black/20">
            {kind === "resource" && (
                <div className="grid grid-cols-2 gap-2">
                    <div>
                        <label className={labelCls}>Ressource</label>
                        <select className={inputCls} value={resourceId} onChange={(e) => setResourceId(e.target.value)}>
                            {resources.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                        </select>
                    </div>
                    {quantityInput("Quantité")}
                </div>
            )}

            {kind === "booster" && (
                <>
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <label className={labelCls}>Booster</label>
                            <select className={inputCls} value={boosterId} onChange={(e) => setBoosterId(e.target.value)}>
                                {boosters.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                            </select>
                        </div>
                        {quantityInput("Quantité")}
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <label className={labelCls}>Rareté min. (optionnel)</label>
                            <select className={inputCls} value={minRarity} onChange={(e) => setMinRarity(e.target.value)}>
                                <option value="">Aucune</option>
                                {(tuning?.rarities ?? []).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className={labelCls}>Chances × (optionnel)</label>
                            <input type="number" min={0.1} max={100} step={0.1} className={inputCls} value={multiplier}
                                onChange={(e) => setMultiplier(e.target.value ? Number(e.target.value) : "")} />
                        </div>
                    </div>
                    {(minRarity || multiplier) && (
                        <div>
                            <label className={labelCls}>Libellé du bonus</label>
                            <input className={inputCls} maxLength={100} placeholder="ex. Cadeau de l'équipe"
                                value={label} onChange={(e) => setLabel(e.target.value)} />
                        </div>
                    )}
                </>
            )}

            {kind === "reroll" && (
                <>
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <label className={labelCls}>Nom</label>
                            <input className={inputCls} maxLength={100} placeholder="ex. Reroll rareté"
                                value={label} onChange={(e) => setLabel(e.target.value)} />
                        </div>
                        {quantityInput("Quantité")}
                    </div>
                    <div>
                        <label className={labelCls}>Axes relancés</label>
                        <div className="flex flex-wrap gap-3">
                            {AXES.map(([key, name]) => (
                                <label key={key} className="flex items-center gap-1.5 text-white/80 text-xs">
                                    <input type="checkbox" checked={rules[key]}
                                        onChange={(e) => setRules({ ...rules, [key]: e.target.checked })} />
                                    {name}
                                </label>
                            ))}
                        </div>
                    </div>
                    <div>
                        <label className={labelCls}>Mode</label>
                        <select className={inputCls} value={rules.reroll_mode}
                            onChange={(e) => setRules({ ...rules, reroll_mode: e.target.value as typeof rules.reroll_mode })}>
                            <option value="guaranteed_min">Garanti égal ou mieux</option>
                            <option value="random">Aléatoire (risqué)</option>
                        </select>
                    </div>
                </>
            )}

            {kind === "cosmetic_choice" && (
                <div className="space-y-1">
                    <label className={labelCls}>Bordures proposées ({chosenIds.length} cochée(s), 2 à 8)</label>
                    <div className="max-h-48 overflow-y-auto space-y-1">
                        {cosmetics.map((c) => (
                            <label key={c.id} className="flex items-center gap-2 text-white/80 text-xs cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={chosenIds.includes(c.id)}
                                    onChange={(e) => setChosenIds(e.target.checked
                                        ? [...chosenIds, c.id]
                                        : chosenIds.filter((id) => id !== c.id))}
                                />
                                <span
                                    className="w-4 h-4 rounded-full border border-white/20 shrink-0"
                                    style={{ background: `linear-gradient(135deg, ${c.color_from}, ${c.color_to})` }}
                                />
                                {c.name}
                            </label>
                        ))}
                        {cosmetics.length === 0 && <p className="text-white/40 text-xs">Aucun cosmétique.</p>}
                    </div>
                </div>
            )}

            {kind === "card" && (
                <>
                    {refSelect("character_id", "Personnage", characters)}
                    <div className="grid grid-cols-2 gap-2">
                        {refSelect("rarity_id", "Rareté", tuning?.rarities ?? [])}
                        {refSelect("quality_id", "Qualité", tuning?.qualities ?? [])}
                        {refSelect("specialty_id", "Spécialité", tuning?.specialties ?? [])}
                        {refSelect("jewelry_id", "Bijou", tuning?.jewelries ?? [])}
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <label className={labelCls}>Puissance</label>
                            <select className={inputCls} value={powerMode} onChange={(e) => setPowerMode(e.target.value as "rolled" | "fixed")}>
                                <option value="rolled">Tirée à la récupération</option>
                                <option value="fixed">Fixe</option>
                            </select>
                        </div>
                        {powerMode === "fixed" && (
                            <div>
                                <label className={labelCls}>Valeur (plafonnée au max possible)</label>
                                <input type="number" min={1} className={inputCls} value={power}
                                    onChange={(e) => setPower(e.target.value ? Number(e.target.value) : "")} />
                            </div>
                        )}
                    </div>
                    <p className="text-white/40 text-[11px]">Chaque destinataire reçoit son propre exemplaire.</p>
                </>
            )}

            <div className="flex gap-2">
                <Button variant="secondary" size="sm" className="flex-1" onClick={onCancel}>Annuler</Button>
                <Button variant="primary" size="sm" className="flex-1" disabled={!reward} onClick={() => reward && onAdd(reward)}>
                    Ajouter
                </Button>
            </div>
        </div>
    );
}

export default function AdminMessagesComposer(props: AdminMessagesComposerProps) {
    const { resources, boosters, characters, tuning } = props;
    const [audience, setAudience] = useState<"all" | "specific">("all");
    const [usernames, setUsernames] = useState("");
    const [subject, setSubject] = useState("");
    const [body, setBody] = useState("");
    const [rewards, setRewards] = useState<AdminMessageReward[]>([]);
    const [adding, setAdding] = useState<Kind | null>(null);
    const [result, setResult] = useState<{ text: string; ok: boolean } | null>(null);

    const send = useMutation({
        mutationFn: () => adminMessagesApi.send({
            usernames: audience === "all" ? null : usernames.split(",").map((u) => u.trim()).filter(Boolean),
            subject: subject.trim(),
            body: body.trim(),
            rewards,
        }),
        onSuccess: (res) => {
            setResult({ text: `Message envoyé à ${res.sent_count} joueur(s).`, ok: true });
            setSubject(""); setBody(""); setRewards([]); setUsernames("");
        },
        onError: (e) => setResult({ text: errMsg(e), ok: false }),
    });

    const canSend = !!subject.trim() && (audience === "all" || usernames.trim().length > 0) && !adding;

    const nameOf = (list: { id: string; name: string }[], id: string) => list.find((x) => x.id === id)?.name ?? id;
    const describe = (r: AdminMessageReward): string => {
        if (r.kind === "resource") return `${r.amount.toLocaleString("fr-FR")} ${nameOf(resources, r.id)}`;
        if (r.kind === "booster") {
            const bonus = [r.force_min_rarity_id && `min. ${nameOf(tuning?.rarities ?? [], r.force_min_rarity_id)}`,
                r.rarity_weight_multiplier && `chances ×${r.rarity_weight_multiplier}`].filter(Boolean).join(", ");
            return `🎴 ${nameOf(boosters, r.id)} ×${r.quantity}${bonus ? ` (${bonus})` : ""}`;
        }
        if (r.kind === "reroll") {
            const axes = AXES.filter(([key]) => r.rules[key]).map(([, name]) => name.toLowerCase()).join(" + ");
            return `🎲 ${r.label} ×${r.quantity} — ${axes}, ${r.rules.reroll_mode === "guaranteed_min" ? "garanti" : "aléatoire"}`;
        }
        if (r.kind === "cosmetic_choice") return `🎨 Bordure au choix — ${r.ids.length} options`;
        return `🃏 ${[nameOf(characters, r.character_id), nameOf(tuning?.rarities ?? [], r.rarity_id),
            nameOf(tuning?.qualities ?? [], r.quality_id), nameOf(tuning?.specialties ?? [], r.specialty_id),
            nameOf(tuning?.jewelries ?? [], r.jewelry_id)].join(" · ")} — ${r.power_mode === "fixed" ? `⚡${r.power}` : "puissance tirée"}`;
    };

    return (
        <div className="bg-game-surface/40 border border-white/10 rounded-lg p-4 space-y-3">
            <div>
                <p className={labelCls}>Destinataires</p>
                <div className="flex gap-2 mb-2">
                    <button
                        className={`flex-1 py-1.5 rounded-lg text-xs font-semibold ${audience === "all" ? "bg-accent text-white" : "bg-white/10 text-white/50"}`}
                        onClick={() => setAudience("all")}
                    >
                        Tous les joueurs
                    </button>
                    <button
                        className={`flex-1 py-1.5 rounded-lg text-xs font-semibold ${audience === "specific" ? "bg-accent text-white" : "bg-white/10 text-white/50"}`}
                        onClick={() => setAudience("specific")}
                    >
                        Pseudos précis
                    </button>
                </div>
                {audience === "specific" && (
                    <input
                        className={inputCls}
                        placeholder="pseudo1, pseudo2, ..."
                        value={usernames}
                        onChange={(e) => setUsernames(e.target.value)}
                    />
                )}
            </div>

            <div>
                <p className={labelCls}>Objet</p>
                <input className={inputCls} maxLength={100} value={subject} onChange={(e) => setSubject(e.target.value)} />
            </div>

            <div>
                <p className={labelCls}>Message</p>
                <textarea
                    className={`${inputCls} resize-none`} rows={3} maxLength={2000}
                    value={body} onChange={(e) => setBody(e.target.value)}
                />
            </div>

            <div className="space-y-2">
                <p className={labelCls}>Récompenses (optionnel)</p>
                {rewards.map((r, i) => (
                    <div key={i} className="flex items-center gap-2 bg-black/30 border border-white/10 rounded-lg px-3 py-2">
                        <span className="flex-1 text-white text-xs">{describe(r)}</span>
                        <button className="text-white/40 hover:text-red-400 text-xs" onClick={() => setRewards(rewards.filter((_, j) => j !== i))}>
                            ✕
                        </button>
                    </div>
                ))}
                {adding ? (
                    <RewardForm
                        key={adding}
                        kind={adding}
                        {...props}
                        onAdd={(reward) => { setRewards([...rewards, reward]); setAdding(null); }}
                        onCancel={() => setAdding(null)}
                    />
                ) : (
                    <div className="grid grid-cols-2 gap-2">
                        {([["resource", "+ Ressource"], ["booster", "+ Booster"], ["reroll", "+ Reroll"],
                           ["card", "+ Carte"], ["cosmetic_choice", "+ Bordure au choix"]] as const).map(([kind, text]) => (
                            <Button key={kind} variant="secondary" size="sm" disabled={rewards.length >= 20} onClick={() => setAdding(kind)}>
                                {text}
                            </Button>
                        ))}
                    </div>
                )}
            </div>

            {result && (
                <p className={`text-xs ${result.ok ? "text-green-400" : "text-red-400"}`}>{result.text}</p>
            )}

            <Button variant="primary" className="w-full" disabled={!canSend} loading={send.isPending} onClick={() => send.mutate()}>
                Envoyer
            </Button>
        </div>
    );
}
