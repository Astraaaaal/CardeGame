import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import { useProbabilities } from "@/hooks/useCollection";
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

interface FilterModalProps {
    open: boolean;
    onClose: () => void;
    filters: CollectionParams;
    onChange: (patch: Partial<CollectionParams>) => void;
    onReset: () => void;
}

export default function FilterModal({ open, onClose, filters, onChange, onReset }: FilterModalProps) {
    const { data } = useProbabilities(open);

    const axes: AxisConfig[] = data
        ? [
            { key: "rarity", label: "Rareté", items: data.rarities },
            { key: "quality", label: "Qualité", items: data.qualities },
            { key: "specialty", label: "Spécialité", items: data.specialties },
            { key: "jewelry", label: "Jewelry", items: data.jewelries },
        ]
        : [];

    return (
        <Modal open={open} onClose={onClose} title="🔎 Filtres avancés">
            <div className="space-y-4 max-h-[65vh] overflow-y-auto pr-1">
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
