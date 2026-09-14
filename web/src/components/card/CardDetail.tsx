import { useState } from "react";
import { motion } from "framer-motion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Card } from "@/types/card";
import { collectionApi } from "@/api/collection";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import ConfirmModal from "@/components/ui/ConfirmModal";
import CardImage from "./CardImage";

interface CardDetailProps {
    card: Card;
    quantity?: number;
    onClose: () => void;
}

function rarityColorToCSS(color: number[]): string {
    return `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
}

function errMsg(e: unknown): string {
    if (e && typeof e === "object" && "response" in e) {
        const r = (e as { response?: { data?: { detail?: unknown } } }).response;
        if (typeof r?.data?.detail === "string") return r.data.detail;
    }
    return "Erreur.";
}

export default function CardDetail({ card, quantity, onClose }: CardDetailProps) {
    const rarityColor = rarityColorToCSS(card.rarity_color);
    const owned = quantity ?? 1;
    const qc = useQueryClient();
    const [recycleCount, setRecycleCount] = useState(1);
    const [result, setResult] = useState<string | null>(null);
    const [confirmingRecycle, setConfirmingRecycle] = useState(false);
    const [showPowers, setShowPowers] = useState(false);

    const powersQ = useQuery({
        queryKey: ["card-powers", card.character_id, card.rarity_id, card.quality_id, card.specialty_id, card.jewelry_id],
        queryFn: () => collectionApi.getCardPowers({
            character_id: card.character_id,
            rarity_id: card.rarity_id,
            quality_id: card.quality_id,
            specialty_id: card.specialty_id,
            jewelry_id: card.jewelry_id,
        }),
        enabled: showPowers && owned > 1,
    });

    const recycle = useMutation({
        mutationFn: () => collectionApi.recycle({
            character_id: card.character_id,
            rarity_id: card.rarity_id,
            quality_id: card.quality_id,
            specialty_id: card.specialty_id,
            jewelry_id: card.jewelry_id,
            count: recycleCount,
        }),
        onSuccess: (res) => {
            setResult(`+${res.gained.toLocaleString("fr-FR")} ${res.resource_name} (solde : ${res.new_balance.toLocaleString("fr-FR")})`);
            setConfirmingRecycle(false);
            qc.invalidateQueries({ queryKey: ["collection"] });
            qc.invalidateQueries({ queryKey: ["player"] });
        },
        onError: (e) => { setResult(errMsg(e)); setConfirmingRecycle(false); },
    });

    const losesAllCopies = recycleCount >= owned;
    const cardLabel = [card.character_name, card.rarity_name, card.quality_name,
        card.specialty_id !== "normal" ? card.specialty_name : null,
        card.jewelry_id !== "none" ? card.jewelry_name : null]
        .filter(Boolean).join(" · ");

    return (
        <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
        >
            <div className="absolute inset-0 bg-black/80" onClick={onClose} />

            <motion.div
                className="relative flex flex-col items-center gap-4 max-w-sm w-full"
                initial={{ y: 50, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
            >
                {/* Carte */}
                <div className="w-64">
                    <CardImage card={card} size="lg" />
                </div>

                {/* Info panel */}
                <div className="bg-game-surface rounded-2xl p-4 w-full border border-white/10">
                    <h3 className="text-xl font-bold text-white mb-2">{card.character_name}</h3>

                    <div className="flex flex-wrap gap-1.5 mb-3">
                        <Badge label={card.rarity_name} color={rarityColor} />
                        {card.quality_id !== "authentic" && (
                            <Badge label={card.quality_name} className="bg-white/20 text-white" />
                        )}
                        {card.specialty_id !== "normal" && (
                            <Badge label={card.specialty_name} className="bg-purple-600/80 text-white" />
                        )}
                        {card.jewelry_id !== "none" && (
                            <Badge
                                label={card.jewelry_name}
                                color={`rgb(${card.jewelry_color.join(",")})`}
                            />
                        )}
                    </div>

                    <div className="space-y-1 text-sm text-white/70">
                        <p>Set: <span className="text-white">{card.set_name}</span></p>
                        <p>Type: <span className="text-white">{card.character_type}</span></p>
                        <p>Génération: <span className="text-white">Gen {card.gen}</span></p>
                        {card.booster_name && (
                            <p>Booster: <span className="text-white">{card.booster_name}</span></p>
                        )}
                        {card.obtained_at && (
                            <p>
                                Obtenue le:{" "}
                                <span className="text-white">
                                    {new Date(card.obtained_at).toLocaleDateString("fr-FR", {
                                        day: "2-digit", month: "2-digit", year: "numeric",
                                    })}
                                </span>
                            </p>
                        )}
                        {card.character_description && card.quality_id !== "unplayable" && (
                            <p className="italic text-white/50 mt-2">{card.character_description}</p>
                        )}
                        <p>
                            Rareté du tirage:{" "}
                            <span className="text-accent">
                                {card.drop_probability > 0
                                    ? `1 sur ${Math.round(1 / card.drop_probability).toLocaleString("fr-FR")}`
                                    : "—"}
                            </span>
                        </p>
                        {card.power != null && (
                            <p>
                                Puissance:{" "}
                                <span className="text-gold font-bold">⚡{card.power}</span>
                                {card.combined_rarity != null && (
                                    <span className="text-white/40">
                                        {" "}(rareté globale : 1 sur {card.combined_rarity.toLocaleString("fr-FR")})
                                    </span>
                                )}
                            </p>
                        )}
                        {quantity !== undefined && quantity > 1 && (
                            <p>
                                Exemplaires: <span className="text-gold font-bold">×{quantity}</span>
                                {" — "}
                                <button
                                    className="text-accent hover:underline"
                                    onClick={() => setShowPowers((v) => !v)}
                                >
                                    {showPowers ? "masquer les puissances" : "voir les puissances"}
                                </button>
                            </p>
                        )}
                        {showPowers && quantity !== undefined && quantity > 1 && (
                            <div className="bg-black/30 rounded-lg px-3 py-2 flex flex-wrap gap-x-3 gap-y-1">
                                {powersQ.isLoading ? (
                                    <span className="text-white/40 text-xs">Chargement...</span>
                                ) : (
                                    (powersQ.data?.powers ?? []).map((p, i) => (
                                        <span key={i} className="text-xs text-white/80">
                                            {p != null ? `⚡${p}` : "—"}
                                        </span>
                                    ))
                                )}
                            </div>
                        )}
                    </div>

                    {/* Recyclage */}
                    <div className="mt-3 pt-3 border-t border-white/10">
                        <p className="text-white/60 text-xs mb-2">
                            Recycler contre de la poussière (irréversible)
                        </p>
                        <div className="flex items-center gap-2">
                            <input
                                type="number"
                                min={1}
                                max={owned}
                                value={recycleCount}
                                onChange={(e) => setRecycleCount(
                                    Math.max(1, Math.min(owned, +e.target.value || 1))
                                )}
                                className="w-16 bg-black/30 border border-white/10 rounded-lg px-2 py-1.5 text-sm text-white text-center"
                            />
                            <Button
                                variant="secondary"
                                size="sm"
                                className="flex-1"
                                onClick={() => { setResult(null); setConfirmingRecycle(true); }}
                            >
                                Recycler {recycleCount > 1 ? `×${recycleCount}` : ""}
                            </Button>
                        </div>
                        {result && (
                            <p className="text-xs mt-2 text-purple-300">{result}</p>
                        )}
                    </div>
                </div>

                <button
                    className="text-white/50 hover:text-white transition-colors text-sm"
                    onClick={onClose}
                >
                    Fermer
                </button>
            </motion.div>

            <ConfirmModal
                open={confirmingRecycle}
                title="Confirmer le recyclage"
                message={`Recycler ${recycleCount} exemplaire${recycleCount > 1 ? "s" : ""} de « ${cardLabel} » contre de la poussière ? Cette action est irréversible.`}
                warning={losesAllCopies
                    ? `Tu recycles ${owned > 1 ? "tous tes exemplaires" : "ton dernier exemplaire"} de cette carte : tu n'en posséderas plus aucun après cette opération.`
                    : undefined}
                confirmLabel="Recycler"
                confirmVariant="primary"
                busy={recycle.isPending}
                onConfirm={() => recycle.mutate()}
                onCancel={() => setConfirmingRecycle(false)}
            />
        </motion.div>
    );
}
