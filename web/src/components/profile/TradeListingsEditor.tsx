import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { showcaseApi } from "@/api/showcase";
import { shopApi } from "@/api/shop";
import { useAuthStore } from "@/stores/authStore";
import { useCollection } from "@/hooks/useCollection";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import type { Card } from "@/types/card";
import type { TradeListingSlotIn, TradeListingMode } from "@/types/showcase";
import Button from "@/components/ui/Button";
import CardImage from "@/components/card/CardImage";
import { errMsg } from "@/utils/errors";

const MODE_LABELS: { value: TradeListingMode; label: string }[] = [
    { value: "buy_now", label: "Achat direct" },
    { value: "offer", label: "Proposition" },
];

function parseSlot(raw: string | undefined): TradeListingSlotIn | null {
    if (!raw) return null;
    try {
        return JSON.parse(raw) as TradeListingSlotIn;
    } catch {
        return null;
    }
}

export default function TradeListingsEditor() {
    const navigate = useNavigate();
    const { user } = useAuthStore();
    const qc = useQueryClient();
    const requestSelection = useCardSelectionStore((s) => s.requestSelection);
    const consumeResultIfPurpose = useCardSelectionStore((s) => s.consumeResultIfPurpose);

    const { data: showcase, isLoading } = useQuery({
        queryKey: ["showcase", user?.id],
        queryFn: () => showcaseApi.get(user!.id),
        enabled: !!user,
    });
    const { data: collection } = useCollection({ sort_by: "rarity" });
    const { data: resources } = useQuery({ queryKey: ["resources-catalog"], queryFn: shopApi.resources });

    const [slots, setSlots] = useState<(TradeListingSlotIn | null)[]>([null, null, null]);
    const [pickedPreviews, setPickedPreviews] = useState<Record<string, Card>>({});
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

    // Garde en ref (pas en state) : sous StrictMode, React rejoue les effets
    // d'un même montage avec la closure d'origine, donc un state comme
    // `initialized` peut encore y paraître faux alors que l'autre effet vient
    // tout juste de le passer à vrai — la ref est lue en direct et évite l'écrasement.
    const didInit = useRef(false);

    // Retour depuis la Collection (mode sélection) après avoir choisi une
    // carte pour un slot "à échanger" — restaure le reste de l'état non
    // enregistré (prix/ressource/mode des autres slots), transporté dans le
    // contexte, sinon il serait perdu puisque ce composant est démonté pendant
    // la navigation. Déclaré AVANT l'effet piloté par `showcase` pour avoir la priorité.
    useEffect(() => {
        if (didInit.current) return;
        const result = consumeResultIfPurpose(["trade-listing-slot"]);
        if (!result) return;
        didInit.current = true;
        const slotIndex = Number(result.context?.slotIndex ?? "0");
        const picked = result.selectedCards[0];
        const previous = parseSlot(result.context?.[`slot${slotIndex}`]);
        const newSlot: TradeListingSlotIn | null = picked
            ? {
                user_card_id: picked.id,
                resource_id: previous?.resource_id ?? resources?.[0]?.id ?? "coins",
                price: previous?.price ?? 0,
                mode: previous?.mode ?? "buy_now",
            }
            : null;
        setSlots([0, 1, 2].map((i) => (i === slotIndex ? newSlot : parseSlot(result.context?.[`slot${i}`]))));
        if (picked) setPickedPreviews((p) => ({ ...p, [picked.id]: picked.preview }));
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        if (didInit.current || !showcase) return;
        didInit.current = true;
        setSlots([0, 1, 2].map((i) => {
            const l = showcase.trade_listings.find((t) => t.slot === i);
            return l ? { user_card_id: l.card.id, resource_id: l.resource_id, price: l.price, mode: l.mode } : null;
        }));
    }, [showcase]);

    const cardById = useMemo(() => {
        const map = new Map<string, Card>();
        for (const g of collection?.groups ?? []) map.set(g.card.id, g.card);
        for (const t of showcase?.trade_listings ?? []) map.set(t.card.id, t.card);
        for (const c of Object.values(pickedPreviews)) map.set(c.id, c);
        return map;
    }, [collection, showcase, pickedPreviews]);

    const patchSlot = (i: number, patch: Partial<TradeListingSlotIn>) =>
        setSlots((s) => s.map((v, j) => (j === i && v ? { ...v, ...patch } : v)));

    const chooseSlot = (slotIndex: number) => {
        requestSelection({
            max: 1,
            title: "Choisis une carte à échanger",
            excludeIds: slots.filter((s, j) => j !== slotIndex && s).map((s) => s!.user_card_id),
            returnTo: "/profile",
            context: {
                purpose: "trade-listing-slot",
                slotIndex: String(slotIndex),
                slot0: slots[0] ? JSON.stringify(slots[0]) : "",
                slot1: slots[1] ? JSON.stringify(slots[1]) : "",
                slot2: slots[2] ? JSON.stringify(slots[2]) : "",
            },
        });
        navigate("/collection");
    };

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
                                <button onClick={() => chooseSlot(i)} className="w-full">
                                    <CardImage card={card} size="sm" />
                                </button>
                            ) : (
                                <button
                                    onClick={() => chooseSlot(i)}
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
        </div>
    );
}
