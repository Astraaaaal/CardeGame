import { useState } from "react";
import { motion } from "framer-motion";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { Card } from "@/types/card";
import { collectionApi } from "@/api/collection";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
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
            qc.invalidateQueries({ queryKey: ["collection"] });
            qc.invalidateQueries({ queryKey: ["player"] });
        },
        onError: (e) => setResult(errMsg(e)),
    });

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
                        {quantity !== undefined && quantity > 1 && (
                            <p>
                                Exemplaires: <span className="text-gold font-bold">×{quantity}</span>
                            </p>
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
                                loading={recycle.isPending}
                                onClick={() => { setResult(null); recycle.mutate(); }}
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
        </motion.div>
    );
}
