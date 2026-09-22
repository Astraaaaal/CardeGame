import { inputCls, labelCls } from "@/components/ui/formStyles";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminActivitiesApi, type ActivitiesConfig } from "@/api/admin";
import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { errMsg } from "@/utils/errors";


type Section = Exclude<keyof ActivitiesConfig, "reward_booster_id">;

/** Réglage avancé édité en JSON (rotation, événements, paires de conversion). */
function JsonField({ label, value, onChange }: { label: string; value: unknown; onChange: (v: unknown) => void }) {
    const [text, setText] = useState(() => JSON.stringify(value, null, 1));
    const [bad, setBad] = useState(false);
    return (
        <div>
            <label className={labelCls}>{label}</label>
            <textarea className={`${inputCls} font-mono text-[11px] ${bad ? "border-red-500" : ""}`} rows={6} value={text}
                onChange={(e) => {
                    setText(e.target.value);
                    try { onChange(JSON.parse(e.target.value)); setBad(false); } catch { setBad(true); }
                }} />
        </div>
    );
}

// Champs numériques simples, par section : [clé, libellé, pas].
const FIELDS: { section: Section; title: string; fields: [string, string, number][] }[] = [
    { section: "presence", title: "Présence (bonus de chance)", fields: [
        ["max_multiplier", "Multiplicateur maximum", 0.1], ["full_after_hours", "Heures pour l'atteindre", 0.5],
        ["reset_after_minutes", "Absence qui remet à zéro (min)", 1],
    ] },
    { section: "chest", title: "Coffre d'absence", fields: [
        ["coins_per_hour", "Pièces par heure", 1], ["dust_per_hour", "Poussière par heure", 1], ["cap_hours", "Plafond (heures)", 1],
    ] },
    { section: "expeditions", title: "Expéditions", fields: [
        ["slots", "Emplacements", 1], ["max_cards", "Cartes par équipe", 1], ["coins_per_minute", "Pièces par minute", 0.1],
        ["dust_ratio", "Poussière (part des pièces)", 0.05], ["power_scale", "Puissance qui double le butin", 100],
        ["max_power_factor", "Bonus de puissance maximum", 0.1],
    ] },
    { section: "workshop", title: "Atelier", fields: [
        ["taps_per_gauge", "Taps par jauge", 1], ["max_taps_per_second", "Taps comptés par seconde", 1],
        ["coins_per_gauge", "Pièces par jauge", 1], ["dust_chance", "Chance de poussière (0-1)", 0.01],
        ["dust_amount", "Poussière gagnée", 1], ["fragments_per_booster", "Fragments pour un booster", 1],
        ["gauges_per_day", "Jauges par jour", 1],
    ] },
    { section: "higher_lower", title: "Plus ou moins", fields: [
        ["min_stake", "Mise minimum", 1], ["max_stake", "Mise maximum", 1], ["max_steps", "Manches maximum", 1],
        ["min_cashout_step", "Encaisser à partir de (manches)", 1], ["house_edge", "Marge maison (0,02 = 2 %)", 0.01],
        ["max_step_multiplier", "Gain maximum d'une manche", 1],
    ] },
    { section: "machine", title: "Machine d'amélioration", fields: [
        ["base_cost", "Prix de base (pièces)", 10], ["level_cost_factor", "Prix ×, par cran déjà obtenu", 0.1],
        ["failure_cost_factor", "Prix ×, par échec", 0.05], ["base_chance", "Chance de base (0-1)", 0.01],
        ["level_chance_factor", "Chance ×, par cran déjà obtenu", 0.05], ["failure_chance_step", "Chance +, par échec", 0.01],
        ["max_chance", "Chance maximum", 0.01], ["resource_from_level", "Ressource obligatoire dès le cran", 1],
        ["resource_base_qty", "Quantité obligatoire au 1er cran concerné", 1],
        ["resource_qty_step", "Quantité en plus par cran suivant", 1],
    ] },
    { section: "recycling", title: "Recyclage", fields: [] },
    { section: "ranking", title: "Classement", fields: [
        ["min_players", "Joueurs classés minimum pour retenir les rangs (succès « top N »)", 1],
    ] },
    { section: "prestige", title: "Prestige (niveaux après la route)", fields: [
        ["power_growth", "Puissance en plus par niveau (0,25 = +25 %)", 0.05],
        ["reward_growth", "Récompense en plus par prestige (0,1 = +10 %)", 0.05],
        ["bonus_amount", "Bonus : quantité", 1],
    ] },
    { section: "converter", title: "Convertisseur", fields: [
        ["daily_uses", "Conversions par jour", 1],
    ] },
    { section: "wheel", title: "Roue de la fortune", fields: [
        ["extra_spin_cost", "Prix d'un tour (pièces)", 1], ["extra_spins_per_day", "Tours payants par jour", 1],
    ] },
];

/** Réglages des activités (présence, coffre, expéditions, atelier, mini-jeux). */
export default function AdminActivities() {
    const qc = useQueryClient();
    const { data, isLoading } = useQuery({ queryKey: ["admin", "activities"], queryFn: adminActivitiesApi.get });
    const [cfg, setCfg] = useState<ActivitiesConfig | null>(null);
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
    useEffect(() => { if (data) setCfg(data); }, [data]);

    const save = useMutation({
        mutationFn: () => adminActivitiesApi.save(cfg!),
        onSuccess: (res) => {
            setCfg(res);
            qc.setQueryData(["admin", "activities"], res);
            setMsg({ text: "Réglages enregistrés.", ok: true });
        },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });

    if (isLoading || !cfg) return <LoadingSpinner text="Chargement..." />;

    const setField = (section: Section, key: string, value: number) =>
        setCfg({ ...cfg, [section]: { ...cfg[section], [key]: value } });
    const segments = cfg.wheel.segments;
    const setSegment = (i: number, patch: Partial<(typeof segments)[number]>) =>
        setCfg({ ...cfg, wheel: { ...cfg.wheel, segments: segments.map((s, j) => (j === i ? { ...s, ...patch } : s)) } });
    const totalWeight = segments.reduce((sum, s) => sum + (Number(s.weight) || 0), 0) || 1;

    return (
        <div className="space-y-4">
            <div>
                <label className={labelCls}>Booster des récompenses (id)</label>
                <input className={inputCls} value={cfg.reward_booster_id}
                    onChange={(e) => setCfg({ ...cfg, reward_booster_id: e.target.value })} />
            </div>

            {FIELDS.map(({ section, title, fields }) => (
                <div key={section} className="bg-game-surface/40 border border-white/10 rounded-lg p-3 space-y-2">
                    <p className="text-white text-sm font-semibold">{title}</p>
                    <div className="grid grid-cols-2 gap-2">
                        {fields.map(([key, label, step]) => (
                            <div key={key}>
                                <label className={labelCls}>{label}</label>
                                <input
                                    type="number" step={step} className={inputCls}
                                    value={(cfg[section] as Record<string, unknown>)[key] as number}
                                    onChange={(e) => setField(section, key, Number(e.target.value))}
                                />
                            </div>
                        ))}
                    </div>
                    {section === "machine" && (
                        <>
                            <JsonField
                                label="Améliorations du cycle (une par jour) : rarity_chances, rarity_guarantee, quality_chances, quality_guarantee, jewelry_chances, jewelry_guarantee, specialty_chances, power_chances, reroll_axis, reroll_boost, reroll_guarantee"
                                value={cfg.machine.cycle_upgrades}
                                onChange={(v) => setCfg({ ...cfg, machine: { ...cfg.machine, cycle_upgrades: v as string[] } })} />
                            <JsonField
                                label="Jours d'événement du cycle (cost_factor, success_bonus, lose_on_fail) — la durée du cycle = améliorations + événements"
                                value={cfg.machine.events}
                                onChange={(v) => setCfg({ ...cfg, machine: { ...cfg.machine, events: v as ActivitiesConfig["machine"]["events"] } })} />
                            <JsonField
                                label="Ressource liée à chaque amélioration, cran par cran (la dernière vaut pour les crans suivants)"
                                value={cfg.machine.resources}
                                onChange={(v) => setCfg({ ...cfg, machine: { ...cfg.machine, resources: v as Record<string, string[]> } })} />
                            <JsonField
                                label="Réussite ajoutée par unité de ressource ajoutée (0,05 = +5 %)"
                                value={cfg.machine.bonus_per_unit}
                                onChange={(v) => setCfg({ ...cfg, machine: { ...cfg.machine, bonus_per_unit: v as Record<string, number> } })} />
                            <JsonField
                                label="Réussite maximale avec ressources ajoutées, par cran (1er, 2e… le dernier vaut pour la suite)"
                                value={cfg.machine.bonus_caps}
                                onChange={(v) => setCfg({ ...cfg, machine: { ...cfg.machine, bonus_caps: v as number[] } })} />
                        </>
                    )}
                    {section === "recycling" && (
                        <>
                            <p className="text-white/40 text-[11px]">
                                Plages [min, max] : la quantité s'y place selon la puissance de la carte rapportée à son maximum.
                            </p>
                            <JsonField
                                label="Poussière selon la rareté de la carte"
                                value={cfg.recycling.dust_by_rarity}
                                onChange={(v) => setCfg({ ...cfg, recycling: { ...cfg.recycling, dust_by_rarity: v as Record<string, [number, number]> } })} />
                            <JsonField
                                label="Plage de chaque ressource"
                                value={cfg.recycling.ranges}
                                onChange={(v) => setCfg({ ...cfg, recycling: { ...cfg.recycling, ranges: v as Record<string, [number, number]> } })} />
                            {(["rarity", "jewelry", "specialty", "quality"] as const).map((axis) => (
                                <JsonField key={axis}
                                    label={`Ressource par palier — ${{ rarity: "rareté", jewelry: "bijou", specialty: "spécialité", quality: "qualité" }[axis]}`}
                                    value={cfg.recycling[axis]}
                                    onChange={(v) => setCfg({ ...cfg, recycling: { ...cfg.recycling, [axis]: v as Record<string, string> } })} />
                            ))}
                        </>
                    )}
                    {section === "converter" && (
                        <JsonField
                            label="Conversions (from → to : give donnent get, max_in au maximum par conversion)"
                            value={cfg.converter.pairs}
                            onChange={(v) => setCfg({ ...cfg, converter: { ...cfg.converter, pairs: v as ActivitiesConfig["converter"]["pairs"] } })} />
                    )}
                    {section === "wheel" && (
                        <div className="space-y-1.5">
                            <p className={labelCls}>Cases (type, id de ressource ou booster, quantité, poids)</p>
                            {segments.map((s, i) => (
                                <div key={i} className="grid grid-cols-[1fr_5.5rem_4.5rem_4rem_3.5rem] gap-1 items-center">
                                    <input className={inputCls} value={s.label} onChange={(e) => setSegment(i, { label: e.target.value })} />
                                    <select className={inputCls} value={s.kind} onChange={(e) => setSegment(i, { kind: e.target.value as typeof s.kind })}>
                                        <option value="resource">Ressource</option>
                                        <option value="booster">Booster</option>
                                        <option value="reroll">Reroll</option>
                                    </select>
                                    <input className={inputCls} value={s.id} placeholder="id" onChange={(e) => setSegment(i, { id: e.target.value })} />
                                    <input type="number" className={inputCls} value={s.amount} onChange={(e) => setSegment(i, { amount: Number(e.target.value) })} />
                                    <input type="number" className={inputCls} value={s.weight} onChange={(e) => setSegment(i, { weight: Number(e.target.value) })} />
                                    <span className="col-span-5 text-white/30 text-[10px]">
                                        {Math.round(((Number(s.weight) || 0) / totalWeight) * 1000) / 10} % de chances
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            ))}

            {msg && <p className={`text-xs ${msg.ok ? "text-green-400" : "text-red-400"}`}>{msg.text}</p>}
            <Button variant="primary" className="w-full" loading={save.isPending} onClick={() => save.mutate()}>
                Enregistrer les réglages
            </Button>
        </div>
    );
}
