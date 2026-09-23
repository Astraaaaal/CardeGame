import { useEffect, useState } from "react";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import { useProbabilities } from "@/hooks/useCollection";
import { useTypes } from "@/hooks/useTypes";
import type { CollectionParams, TierOp, ProbabilityItem } from "@/api/collection";

interface AxisConfig {
    key: "rarity" | "quality" | "specialty" | "jewelry";
    label: string;
    items: ProbabilityItem[];
}

const OP_LABELS: { value: TierOp; label: string }[] = [
    { value: "eq", label: "Exactement" },
    { value: "gte", label: "À partir de" },
    { value: "lte", label: "Et en dessous" },
];

// Plafond le plus haut atteignable par une carte (cf. services/power.py,
// TIER_CAPS) : le curseur doit pouvoir monter jusque-là.
const POWER_MAX = 50000;
const POWER_STEP = 100;

const RANGE_INPUT = `absolute inset-0 w-full appearance-none bg-transparent pointer-events-none
    [&::-webkit-slider-runnable-track]:bg-transparent [&::-moz-range-track]:bg-transparent
    [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:appearance-none
    [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:rounded-full
    [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-accent
    [&::-webkit-slider-thumb]:cursor-pointer
    [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:w-5 [&::-moz-range-thumb]:h-5
    [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-white [&::-moz-range-thumb]:border-2
    [&::-moz-range-thumb]:border-accent [&::-moz-range-thumb]:cursor-pointer`;

/** Intervalle de puissance à deux curseurs. La valeur est appliquée au
 * filtre 300 ms après le dernier mouvement, pas à chaque pixel glissé. */
function PowerRangeFilter({ min, max, onChange }: {
    min?: number;
    max?: number;
    onChange: (patch: Partial<CollectionParams>) => void;
}) {
    const [lo, setLo] = useState(min ?? 0);
    const [hi, setHi] = useState(max ?? POWER_MAX);

    useEffect(() => {
        setLo(min ?? 0);
        setHi(max ?? POWER_MAX);
    }, [min, max]);

    useEffect(() => {
        const nextMin = lo > 0 ? lo : undefined;
        const nextMax = hi < POWER_MAX ? hi : undefined;
        if (nextMin === min && nextMax === max) return;
        const t = setTimeout(() => onChange({ min_power: nextMin, max_power: nextMax }), 300);
        return () => clearTimeout(t);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [lo, hi]);

    return (
        <div>
            <div className="flex items-center justify-between mb-1.5">
                <label className="text-white/50 text-xs font-semibold uppercase tracking-wide">Puissance</label>
                <span className="text-white text-xs font-semibold tabular-nums">
                    {lo.toLocaleString("fr-FR")} – {hi.toLocaleString("fr-FR")}{hi === POWER_MAX ? "+" : ""}
                </span>
            </div>
            <div className="relative h-6">
                <div className="absolute top-1/2 -translate-y-1/2 inset-x-0 h-1.5 rounded-full bg-white/10" />
                <div
                    className="absolute top-1/2 -translate-y-1/2 h-1.5 rounded-full bg-accent"
                    style={{ left: `${(lo / POWER_MAX) * 100}%`, right: `${100 - (hi / POWER_MAX) * 100}%` }}
                />
                <input
                    type="range" min={0} max={POWER_MAX} step={POWER_STEP} value={lo}
                    aria-label="Puissance minimale"
                    className={RANGE_INPUT}
                    // Curseurs superposés en fin de piste : celui du bas doit rester attrapable.
                    style={{ zIndex: lo > POWER_MAX - POWER_STEP * 5 ? 2 : 1 }}
                    onChange={(e) => setLo(Math.min(Number(e.target.value), hi))}
                />
                <input
                    type="range" min={0} max={POWER_MAX} step={POWER_STEP} value={hi}
                    aria-label="Puissance maximale"
                    className={RANGE_INPUT}
                    onChange={(e) => setHi(Math.max(Number(e.target.value), lo))}
                />
            </div>
            {/* Saisie exacte (le curseur avance par pas de 100). */}
            <div className="flex items-center gap-2 mt-2">
                <input
                    type="number" min={0} max={POWER_MAX} inputMode="numeric" aria-label="Puissance minimale exacte"
                    className="w-full bg-black/30 border border-white/10 rounded-lg px-2 py-1 text-xs text-white"
                    value={lo || ""} placeholder="min"
                    onChange={(e) => setLo(Math.max(0, Math.min(Number(e.target.value) || 0, hi)))}
                />
                <span className="text-white/30 text-xs">à</span>
                <input
                    type="number" min={0} max={POWER_MAX} inputMode="numeric" aria-label="Puissance maximale exacte"
                    className="w-full bg-black/30 border border-white/10 rounded-lg px-2 py-1 text-xs text-white"
                    value={hi === POWER_MAX ? "" : hi} placeholder="max"
                    onChange={(e) => {
                        const v = e.target.value === "" ? POWER_MAX : Number(e.target.value) || 0;
                        setHi(Math.min(POWER_MAX, Math.max(v, lo)));
                    }}
                />
            </div>
        </div>
    );
}

interface FilterModalProps {
    open: boolean;
    onClose: () => void;
    filters: CollectionParams;
    onChange: (patch: Partial<CollectionParams>) => void;
    onReset: () => void;
}

export default function FilterModal({ open, onClose, filters, onChange, onReset }: FilterModalProps) {
    const { data } = useProbabilities(open);
    const { data: types } = useTypes();

    const axes: AxisConfig[] = data
        ? [
            { key: "rarity", label: "Rareté", items: data.rarities },
            { key: "quality", label: "Qualité", items: data.qualities },
            { key: "specialty", label: "Spécialité", items: data.specialties },
            { key: "jewelry", label: "Jewelry", items: data.jewelries },
        ]
        : [];

    const selectedTypes = filters.type_names ?? [];
    const toggleType = (name: string) => {
        const next = selectedTypes.includes(name)
            ? selectedTypes.filter((t) => t !== name)
            : [...selectedTypes, name];
        onChange({ type_names: next.length ? next : undefined });
    };

    return (
        <Modal open={open} onClose={onClose} title="Filtres avancés">
            <div className="space-y-4 max-h-[65vh] overflow-y-auto pr-1">
                <PowerRangeFilter min={filters.min_power} max={filters.max_power} onChange={onChange} />

                <div>
                    <label className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-1.5 block">
                        Type{selectedTypes.length > 0 ? ` (${selectedTypes.length})` : ""}
                    </label>
                    <div className="flex flex-wrap gap-1.5">
                        {(types ?? []).map((t) => (
                            <button
                                key={t.id}
                                className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-all ${
                                    selectedTypes.includes(t.name)
                                        ? "bg-accent text-white"
                                        : "bg-white/10 text-white/50 hover:bg-white/20"
                                }`}
                                onClick={() => toggleType(t.name)}
                            >
                                {t.name}
                            </button>
                        ))}
                    </div>
                </div>

                {axes.map((axis) => {
                    const idKey = `${axis.key}_id` as const;
                    const opKey = `${axis.key}_op` as const;
                    const currentId = filters[idKey] ?? "";
                    const currentOp = filters[opKey] ?? "eq";

                    return (
                        <div key={axis.key}>
                            <label className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-1.5 block">
                                {axis.label}
                            </label>
                            <select
                                className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white mb-2"
                                value={currentId}
                                onChange={(e) => onChange({ [idKey]: e.target.value || undefined } as Partial<CollectionParams>)}
                            >
                                <option value="">— Tous —</option>
                                {axis.items.map((it) => (
                                    <option key={it.id} value={it.id}>{it.name}</option>
                                ))}
                            </select>
                            {currentId && (
                                <div className="flex gap-1.5">
                                    {OP_LABELS.map((op) => (
                                        <button
                                            key={op.value}
                                            className={`flex-1 px-2 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                                                currentOp === op.value
                                                    ? "bg-accent text-white"
                                                    : "bg-white/10 text-white/50 hover:bg-white/20"
                                            }`}
                                            onClick={() => onChange({ [opKey]: op.value } as Partial<CollectionParams>)}
                                        >
                                            {op.label}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
            <div className="flex gap-2 pt-4">
                <Button variant="secondary" className="flex-1" onClick={onReset}>
                    Réinitialiser
                </Button>
                <Button variant="primary" className="flex-1" onClick={onClose}>
                    Fermer
                </Button>
            </div>
        </Modal>
    );
}
