import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { boostersApi } from "@/api/boosters";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

interface AddBoosterModalProps {
    onPick: (boosterId: string, name: string, quantity: number) => void;
    onClose: () => void;
}

export default function AddBoosterModal({ onPick, onClose }: AddBoosterModalProps) {
    const { data, isLoading } = useQuery({ queryKey: ["boosters-inventory"], queryFn: boostersApi.getInventory });
    const [selected, setSelected] = useState<{ id: string; name: string; owned: number } | null>(null);
    const [quantity, setQuantity] = useState(1);

    const owned = (data ?? []).filter((b) => b.quantity > 0);

    if (selected) {
        const max = selected.owned;
        return (
            <Modal open onClose={() => setSelected(null)} title={selected.name}>
                <div className="space-y-4">
                    <div className="flex items-center justify-center gap-2 text-2xl font-bold text-white">
                        <span>×{quantity}</span>
                    </div>
                    <input
                        type="range"
                        min={1}
                        max={max}
                        value={quantity}
                        onChange={(e) => setQuantity(Number(e.target.value))}
                        className="w-full"
                    />
                    <div className="flex items-center gap-2">
                        <input
                            type="number"
                            min={1}
                            max={max}
                            value={quantity}
                            onChange={(e) => setQuantity(Math.max(1, Math.min(max, Number(e.target.value) || 1)))}
                            className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                        />
                        <Button variant="secondary" size="sm" onClick={() => setQuantity(max)}>
                            Max ({max})
                        </Button>
                    </div>
                    <Button variant="primary" className="w-full" onClick={() => onPick(selected.id, selected.name, quantity)}>
                        Choisir
                    </Button>
                </div>
            </Modal>
        );
    }

    return (
        <Modal open onClose={onClose} title="Choisis un booster">
            {isLoading ? (
                <LoadingSpinner text="Chargement..." />
            ) : owned.length === 0 ? (
                <p className="text-white/40 text-sm text-center py-6">
                    Tu n'as aucun booster non ouvert à offrir.
                </p>
            ) : (
                <div className="space-y-2">
                    {owned.map((b) => (
                        <button
                            key={b.booster_id}
                            className="w-full flex items-center gap-3 bg-black/20 border border-white/5 hover:border-white/20 rounded-lg px-3 py-2.5 text-left"
                            onClick={() => {
                                setSelected({ id: b.booster_id, name: b.booster_name, owned: b.quantity });
                                setQuantity(1);
                            }}
                        >
                            {b.booster_cover_url && (
                                <img
                                    src={`/boosters/${b.booster_cover_url}`}
                                    alt=""
                                    className="w-10 h-10 rounded object-cover shrink-0"
                                />
                            )}
                            <span className="flex-1 text-white text-sm font-semibold">{b.booster_name}</span>
                            <span className="text-white/40 text-xs">×{b.quantity}</span>
                        </button>
                    ))}
                </div>
            )}
        </Modal>
    );
}
