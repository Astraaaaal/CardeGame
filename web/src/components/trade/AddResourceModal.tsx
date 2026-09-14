import { useState } from "react";
import { useAuthStore } from "@/stores/authStore";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import ResourceIcon from "@/components/ui/ResourceIcon";

interface AddResourceModalProps {
    /** Montant déjà proposé de chaque ressource dans cet échange (pour préremplir/ajuster). */
    current: Record<string, number>;
    onPick: (resourceId: string, amount: number) => void;
    onClose: () => void;
}

export default function AddResourceModal({ current, onPick, onClose }: AddResourceModalProps) {
    const { user } = useAuthStore();
    const [selected, setSelected] = useState<{ id: string; name: string; balance: number } | null>(null);
    const [amount, setAmount] = useState(1);

    const options = [
        { id: "coins", name: "Pièces", balance: user?.coins ?? 0 },
        ...(user?.resources ?? []).filter((r) => r.amount > 0).map((r) => ({ id: r.id, name: r.name, balance: r.amount })),
    ];

    if (selected) {
        const max = selected.balance;
        return (
            <Modal open onClose={() => setSelected(null)} title={selected.name}>
                <div className="space-y-4">
                    <div className="flex items-center justify-center gap-2 text-2xl font-bold text-white">
                        <ResourceIcon resourceId={selected.id} />
                        <span>{amount.toLocaleString("fr-FR")}</span>
                    </div>
                    <input
                        type="range"
                        min={1}
                        max={max}
                        value={amount}
                        onChange={(e) => setAmount(Number(e.target.value))}
                        className="w-full"
                    />
                    <div className="flex items-center gap-2">
                        <input
                            type="number"
                            min={1}
                            max={max}
                            value={amount}
                            onChange={(e) => setAmount(Math.max(1, Math.min(max, Number(e.target.value) || 1)))}
                            className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                        />
                        <Button variant="secondary" size="sm" onClick={() => setAmount(max)}>
                            Max ({max.toLocaleString("fr-FR")})
                        </Button>
                    </div>
                    <Button variant="primary" className="w-full" onClick={() => onPick(selected.id, amount)}>
                        Ajouter à l'échange
                    </Button>
                </div>
            </Modal>
        );
    }

    return (
        <Modal open onClose={onClose} title="Ajoute une ressource">
            {options.length === 0 ? (
                <p className="text-white/40 text-sm text-center py-6">Aucune ressource disponible.</p>
            ) : (
                <div className="space-y-2">
                    {options.map((o) => (
                        <button
                            key={o.id}
                            className="w-full flex items-center justify-between bg-black/20 border border-white/5 hover:border-white/20 rounded-lg px-3 py-2.5 text-left"
                            onClick={() => {
                                setSelected(o);
                                setAmount(Math.min(o.balance, Math.max(1, current[o.id] || 1)));
                            }}
                        >
                            <span className="text-white text-sm font-semibold flex items-center gap-1.5">
                                <ResourceIcon resourceId={o.id} /> {o.name}
                            </span>
                            <span className="text-white/40 text-xs">{o.balance.toLocaleString("fr-FR")} dispo</span>
                        </button>
                    ))}
                </div>
            )}
        </Modal>
    );
}
