import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { shopApi } from "@/api/shop";
import { collectionApi } from "@/api/collection";
import type { ShopOffer } from "@/types/shop";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import CardImage from "@/components/card/CardImage";

function errMsg(e: unknown): string {
    if (e && typeof e === "object" && "response" in e) {
        const r = (e as { response?: { data?: { detail?: unknown } } }).response;
        if (typeof r?.data?.detail === "string") return r.data.detail;
    }
    return "Erreur.";
}

function offerPreview(o: ShopOffer): string {
    if (o.kind === "booster") {
        const bits = ["Ouvre 1 pack"];
        if (o.force_min_rarity_name) bits.push(`min. ${o.force_min_rarity_name} garanti`);
        if (o.rarity_weight_multiplier) bits.push(`x${o.rarity_weight_multiplier} chances rare+`);
        return bits.join(" · ");
    }
    if (o.kind === "specific_card") {
        return [o.character_name, o.rarity_name, o.quality_name, o.specialty_name, o.jewelry_name]
            .filter(Boolean).join(" · ");
    }
    if (o.kind === "upgrade") {
        const parts = [];
        if (o.target_quality_name) parts.push(`Qualité → ${o.target_quality_name}`);
        if (o.target_specialty_name) parts.push(`Spécialité → ${o.target_specialty_name}`);
        return parts.join(" · ") || "Amélioration";
    }
    // reroll
    const axes = [
        o.reroll_rarity && "rareté", o.reroll_quality && "qualité",
        o.reroll_specialty && "spécialité", o.reroll_jewelry && "jewelry",
    ].filter(Boolean).join(" + ");
    const mode = o.reroll_mode === "guaranteed_min" ? "garanti égal ou mieux" : "aléatoire (risqué)";
    return `Retire ${axes} — ${mode}`;
}

/** Petit sélecteur de carte possédée, pour les offres "upgrade" et "reroll". */
function CardPicker({ onPick, onClose }: { onPick: (cardId: string) => void; onClose: () => void }) {
    const { data, isLoading } = useQuery({
        queryKey: ["collection", { sort_by: "rarity" }],
        queryFn: () => collectionApi.getCollection({ sort_by: "rarity" }),
    });

    return (
        <Modal open onClose={onClose} title="Choisis une carte">
            {isLoading ? (
                <LoadingSpinner text="Chargement..." />
            ) : (
                <div className="grid grid-cols-3 gap-2 max-h-[60vh] overflow-y-auto">
                    {(data?.groups ?? []).map((g) => (
                        <button key={g.card.id} onClick={() => onPick(g.card.id)}>
                            <CardImage card={g.card} size="sm" />
                        </button>
                    ))}
                    {data && data.groups.length === 0 && (
                        <p className="col-span-3 text-white/40 text-sm text-center py-6">
                            Aucune carte dans ta collection.
                        </p>
                    )}
                </div>
            )}
        </Modal>
    );
}

export default function ResourceShop() {
    const navigate = useNavigate();
    const qc = useQueryClient();
    const { data: offers, isLoading } = useQuery({ queryKey: ["shop-offers"], queryFn: shopApi.list });
    const [pickerFor, setPickerFor] = useState<ShopOffer | null>(null);
    const [feedback, setFeedback] = useState<{ offerId: string; text: string; ok: boolean } | null>(null);

    const buy = useMutation({
        mutationFn: ({ offer, cardId }: { offer: ShopOffer; cardId?: string }) =>
            shopApi.buy(offer.id, cardId),
        onSuccess: (res, { offer }) => {
            setFeedback({ offerId: offer.id, text: res.message, ok: true });
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["collection"] });
            setPickerFor(null);
        },
        onError: (e, { offer }) => setFeedback({ offerId: offer.id, text: errMsg(e), ok: false }),
    });

    const handleBuy = (offer: ShopOffer) => {
        setFeedback(null);
        if (offer.kind === "upgrade" || offer.kind === "reroll") {
            setPickerFor(offer);
        } else {
            buy.mutate({ offer });
        }
    };

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button className="text-accent text-sm font-semibold" onClick={() => navigate("/")}>
                    ← Retour
                </button>
                <h1 className="text-white font-bold">✨ Shop Ressources</h1>
                <span className="w-14" />
            </header>

            <main className="flex-1 px-4 py-6">
                {isLoading ? (
                    <LoadingSpinner text="Chargement du shop..." />
                ) : !offers || offers.length === 0 ? (
                    <p className="text-white/40 text-sm text-center mt-10">
                        Aucune offre disponible pour l'instant.
                    </p>
                ) : (
                    <div className="space-y-3 max-w-sm mx-auto">
                        {offers.map((o) => {
                            const limitReached = !!o.purchase_limit_per_day
                                && o.purchases_today >= o.purchase_limit_per_day;
                            return (
                                <div key={o.id} className={`bg-game-surface rounded-2xl p-4 border ${o.featured_today ? "border-gold/60" : "border-white/10"}`}>
                                    <div className="flex items-center justify-between mb-1">
                                        <h3 className="text-white font-bold">
                                            {o.featured_today && <span className="text-gold">⭐ </span>}
                                            {o.name}
                                        </h3>
                                        <span className="text-purple-300 font-bold text-sm">
                                            {o.price} {o.resource_name}
                                        </span>
                                    </div>
                                    <p className="text-white/50 text-xs mb-2">{offerPreview(o)}</p>
                                    {o.description && (
                                        <p className="text-white/40 text-xs mb-2">{o.description}</p>
                                    )}
                                    {o.purchase_limit_per_day && (
                                        <p className="text-white/40 text-xs mb-2">
                                            {o.purchases_today}/{o.purchase_limit_per_day} aujourd'hui
                                        </p>
                                    )}
                                    <Button
                                        variant="primary"
                                        size="sm"
                                        className="w-full"
                                        disabled={limitReached}
                                        loading={buy.isPending && buy.variables?.offer.id === o.id}
                                        onClick={() => handleBuy(o)}
                                    >
                                        {limitReached ? "Limite atteinte" : "Acheter"}
                                    </Button>
                                    {feedback?.offerId === o.id && (
                                        <p className={`text-xs mt-2 ${feedback.ok ? "text-green-400" : "text-red-400"}`}>
                                            {feedback.text}
                                        </p>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </main>

            {pickerFor && (
                <CardPicker
                    onClose={() => setPickerFor(null)}
                    onPick={(cardId) => buy.mutate({ offer: pickerFor, cardId })}
                />
            )}
        </div>
    );
}
