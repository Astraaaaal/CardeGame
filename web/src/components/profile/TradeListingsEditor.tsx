import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { showcaseApi } from "@/api/showcase";
import { shopApi } from "@/api/shop";
import { useAuthStore } from "@/stores/authStore";
import { useCollection } from "@/hooks/useCollection";
import type { Card } from "@/types/card";
import type { TradeListingSlotIn, TradeListingMode } from "@/types/showcase";
import Button from "@/components/ui/Button";
import CardImage from "@/components/card/CardImage";
import CardPickerModal from "@/components/card/CardPickerModal";

function errMsg(e: unknown): string {
    if (e && typeof e === "object" && "response" in e) {
        const r = (e as { response?: { data?: { detail?: unknown } } }).response;
        if (typeof r?.data?.detail === "string") return r.data.detail;
    }
    return "Erreur.";
}

const MODE_LABELS: { value: TradeListingMode; label: string }[] = [
    { value: "buy_now", label: "Achat direct" },
    { value: "offer", label: "Proposition" },
];

export default function TradeListingsEditor() {
    const { user } = useAuthStore();
    const qc = useQueryClient();

    const { data: showcase, isLoading } = useQuery({
        queryKey: ["showcase", user?.id],
        queryFn: () => showcaseApi.get(user!.id),
        enabled: !!user,
    });
    const { data: collection } = useCollection({ sort_by: "rarity" });
    const { data: resources } = useQuery({ queryKey: ["resources-catalog"], queryFn: shopApi.resources });

    const [slots, setSlots] = useState<(TradeListingSlotIn | null)[]>([null, null, null]);
    const [initialized, setInitialized] = useState(false);
    const [slotPicker, setSlotPicker] = useState<number | null>(null);
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

    useEffect(() => {
        if (showcase && !initialized) {
            setSlots([0, 1, 2].map((i) => {
                const l = showcase.trade_listings.find((t) => t.slot === i);
                return l ? { user_card_id: l.card.id, resource_id: l.resource_id, price: l.price, mode: l.mode } : null;
            }));
            setInitialized(true);
        }
    }, [showcase, initialized]);

    const cardById = useMemo(() => {
        const map = new Map<string, Card>();
        for (const g of collection?.groups ?? []) map.set(g.card.id, g.card);
        for (const t of showcase?.trade_listings ?? []) map.set(t.card.id, t.card);
        return map;
    }, [collection, showcase]);

    const patchSlot = (i: number, patch: Partial<TradeListingSlotIn>) =>
        setSlots((s) => s.map((v, j) => (j === i && v ? { ...v, ...patch } : v)));

    const save = useMutation({
        mutationFn: () => showcaseApi.updateTradeListings(slots),
        onSuccess: (updated) => {
            qc.setQueryData(["showcase", user?.id], updated);
            setMsg({ text: "Annonces enregistrées.", ok: true });
        },
        onError: (e) => setMsg({ text: errMsg(e), ok: false }),
    });

    if (isLoading) return <p className="text-white/40 text-sm">Chargement...</p>;

    return (
        <div className="bg-game-surface rounded-2xl border border-white/10 p-4">
            <h3 className="text-white font-bold text-sm mb-1">Cartes à échanger (3 max)</h3>
            <p className="text-white/30 text-xs mb-3">
                "Achat direct" : un autre joueur peut acheter la carte immédiatement au prix indiqué.
                "Proposition" : le prix est juste indicatif, un clic lance une demande d'échange (entre amis).
            </p>
            <div className="grid grid-cols-3 gap-2">
                {slots.map((slot, i) => {
                    const card = slot ? cardById.get(slot.user_card_id) : undefined;
                    return (
                        <div key={i} className="space-y-1.5">
                            {card ? (
                                <button onClick={() => setSlotPicker(i)} className="w-full">
                                    <CardImage card={card} size="sm" />
                                </button>
                            ) : (
                                <button
                                    onClick={() => setSlotPicker(i)}
                                    className="w-full aspect-[5/7] rounded-lg border-2 border-dashed border-white/15
                                               text-white/30 text-xs flex items-center justify-center hover:border-accent hover:text-accent transition-colors"
                                >
                                    + Choisir
                                </button>
                            )}
                            {slot && (
                                <>
                                    <div className="flex gap-1">
                                        <input
                                            type="number" min={0}
                                            className="w-full bg-black/30 border border-white/10 rounded px-1.5 py-1 text-xs text-white"
                                            value={slot.price}
                                            onChange={(e) => patchSlot(i, { price: Math.max(0, +e.target.value) })}
                                        />
                                        <select
                                            className="bg-black/30 border border-white/10 rounded px-1 py-1 text-xs text-white"
                                            value={slot.resource_id}
                                            onChange={(e) => patchSlot(i, { resource_id: e.target.value })}
                                        >
                                            {(resources ?? []).map((r) => (
                                                <option key={r.id} value={r.id}>{r.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <select
                                        className="w-full bg-black/30 border border-white/10 rounded px-1.5 py-1 text-xs text-white"
                                        value={slot.mode}
                                        onChange={(e) => patchSlot(i, { mode: e.target.value as TradeListingMode })}
                                    >
                                        {MODE_LABELS.map((m) => (
                                            <option key={m.value} value={m.value}>{m.label}</option>
                                        ))}
                                    </select>
                                    <button
                                        className="text-red-400/70 hover:text-red-400 text-[10px] w-full text-center"
                                        onClick={() => setSlots((s) => s.map((v, j) => (j === i ? null : v)))}
                                    >
                                        Retirer
                                    </button>
                                </>
                            )}
                        </div>
                    );
                })}
            </div>

            {msg && (
                <p className={`text-xs mt-3 ${msg.ok ? "text-green-400" : "text-red-400"}`}>{msg.text}</p>
            )}

            <Button variant="primary" className="w-full mt-3" loading={save.isPending} onClick={() => save.mutate()}>
                Enregistrer
            </Button>

            {slotPicker !== null && (
                <CardPickerModal
                    onClose={() => setSlotPicker(null)}
                    onPick={(cardId) => {
                        setSlots((s) => s.map((v, j) => (j === slotPicker
                            ? { user_card_id: cardId, resource_id: resources?.[0]?.id ?? "coins", price: v?.price ?? 0, mode: v?.mode ?? "buy_now" }
                            : v)));
                        setSlotPicker(null);
                    }}
                />
            )}
        </div>
    );
}
