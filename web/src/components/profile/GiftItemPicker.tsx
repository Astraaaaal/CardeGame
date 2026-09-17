import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { boostersApi } from "@/api/boosters";
import { useAuthStore } from "@/stores/authStore";
import { useRerollTokens } from "@/hooks/useRerollTokens";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ResourceIcon from "@/components/ui/ResourceIcon";
import { PREMIUM_RESOURCE_ID } from "@/components/shop/PremiumTab";

/** Objet (hors carte) choisi pour un cadeau. */
export type GiftItem =
    | { kind: "resource"; resourceId: string; name: string; amount: number }
    | { kind: "booster"; boosterId: string; bonusId: number | null; name: string; amount: number }
    | { kind: "reroll"; tokenId: number; name: string; amount: number };

type Option = { key: string; label: string; sublabel?: string | null; available: number; icon: React.ReactNode; toItem: (amount: number) => GiftItem };

function Section({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div>
            <p className="text-white/40 text-[11px] font-semibold uppercase tracking-wide mb-1.5">{title}</p>
            <div className="space-y-2">{children}</div>
        </div>
    );
}

/** Choix de ce qu'on offre en dehors d'une carte : ressources, boosters (bonus conservé) et rerolls. */
export default function GiftItemPicker({ onPick, onClose }: { onPick: (item: GiftItem) => void; onClose: () => void }) {
    const { user } = useAuthStore();
    const { data: boosters, isLoading: boostersLoading } = useQuery({ queryKey: ["booster-inventory"], queryFn: boostersApi.getInventory });
    const { data: tokens, isLoading: tokensLoading } = useRerollTokens();
    const [selected, setSelected] = useState<Option | null>(null);
    const [amount, setAmount] = useState(1);

    const resources: Option[] = [
        { id: "coins", name: "Pièces", amount: user?.coins ?? 0 },
        // Monnaie premium liée au compte : jamais offrable.
        ...(user?.resources ?? []).filter((r) => r.id !== "coins" && r.id !== PREMIUM_RESOURCE_ID),
    ].filter((r) => r.amount > 0).map((r) => ({
        key: `r-${r.id}`, label: r.name, available: r.amount,
        icon: <ResourceIcon resourceId={r.id} />,
        toItem: (n) => ({ kind: "resource", resourceId: r.id, name: r.name, amount: n }),
    }));
    const boosterOptions: Option[] = (boosters ?? []).filter((b) => b.quantity > 0).map((b) => ({
        key: `b-${b.booster_id}-${b.bonus_id ?? "base"}`, label: b.booster_name, sublabel: b.bonus_label, available: b.quantity,
        icon: <span>🎴</span>,
        toItem: (n) => ({ kind: "booster", boosterId: b.booster_id, bonusId: b.bonus_id, name: b.bonus_label ?? b.booster_name, amount: n }),
    }));
    const rerollOptions: Option[] = (tokens ?? []).filter((t) => t.quantity > 0).map((t) => ({
        key: `t-${t.id}`, label: t.label, available: t.quantity,
        icon: <span>🎲</span>,
        toItem: (n) => ({ kind: "reroll", tokenId: t.id, name: t.label, amount: n }),
    }));

    if (selected) {
        const max = selected.available;
        return (
            <Modal open onClose={() => setSelected(null)} title={selected.label}>
                <div className="space-y-4">
                    <div className="flex items-center justify-center gap-2 text-2xl font-bold text-white">
                        {selected.icon}
                        <span>{amount.toLocaleString("fr-FR")}</span>
                    </div>
                    {max > 1 && (
                        <input type="range" min={1} max={max} value={amount} onChange={(e) => setAmount(Number(e.target.value))} className="w-full" />
                    )}
                    <div className="flex items-center gap-2">
                        <input
                            type="number" min={1} max={max} value={amount}
                            onChange={(e) => setAmount(Math.max(1, Math.min(max, Number(e.target.value) || 1)))}
                            className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                        />
                        <Button variant="secondary" size="sm" onClick={() => setAmount(max)}>
                            Max ({max.toLocaleString("fr-FR")})
                        </Button>
                    </div>
                    <Button variant="primary" className="w-full" onClick={() => onPick(selected.toItem(amount))}>
                        Choisir
                    </Button>
                </div>
            </Modal>
        );
    }

    const row = (o: Option) => (
        <button
            key={o.key}
            className="w-full flex items-center justify-between gap-2 bg-black/20 border border-white/5 hover:border-white/20 rounded-lg px-3 py-2.5 text-left"
            onClick={() => { setSelected(o); setAmount(1); }}
        >
            <span className="min-w-0">
                <span className="text-white text-sm font-semibold flex items-center gap-1.5">{o.icon} <span className="truncate">{o.label}</span></span>
                {o.sublabel && <span className="block text-gold text-xs truncate">{o.sublabel}</span>}
            </span>
            <span className="text-white/40 text-xs shrink-0">{o.available.toLocaleString("fr-FR")} dispo</span>
        </button>
    );

    const empty = !resources.length && !boosterOptions.length && !rerollOptions.length;
    return (
        <Modal open onClose={onClose} title="Choisis quoi offrir">
            {boostersLoading || tokensLoading ? (
                <LoadingSpinner text="Chargement..." />
            ) : empty ? (
                <p className="text-white/40 text-sm text-center py-6">Rien à offrir pour l'instant.</p>
            ) : (
                <div className="space-y-4 max-h-[60vh] overflow-y-auto">
                    {!!resources.length && <Section title="Ressources">{resources.map(row)}</Section>}
                    {!!boosterOptions.length && <Section title="Boosters">{boosterOptions.map(row)}</Section>}
                    {!!rerollOptions.length && <Section title="Rerolls">{rerollOptions.map(row)}</Section>}
                </div>
            )}
        </Modal>
    );
}
