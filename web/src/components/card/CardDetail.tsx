import { motion } from "framer-motion";
import type { Card } from "@/types/card";
import Badge from "@/components/ui/Badge";

interface CardDetailProps {
    card: Card;
    quantity?: number;
    onClose: () => void;
}

function rarityColorToCSS(color: number[]): string {
    return `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
}

export default function CardDetail({ card, quantity, onClose }: CardDetailProps) {
    const rarityColor = rarityColorToCSS(card.rarity_color);

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
                {/* Card Image */}
                <div
                    className="w-64 aspect-[9/16] rounded-2xl overflow-hidden shadow-2xl"
                    style={{ border: `3px solid ${rarityColor}`, boxShadow: `0 0 30px ${rarityColor}60` }}
                >
                    {card.rendered_url ? (
                        <img
                            src={card.rendered_url}
                            alt={card.character_name}
                            className="w-full h-full object-cover"
                        />
                    ) : (
                        <div className="w-full h-full bg-game-surface flex items-center justify-center">
                            <span className="text-white/40">{card.character_name}</span>
                        </div>
                    )}
                </div>

                {/* Info panel */}
                <div className="bg-game-surface rounded-2xl p-4 w-full border border-white/10">
                    <h3 className="text-xl font-bold text-white mb-2">{card.character_name}</h3>

                    <div className="flex flex-wrap gap-1.5 mb-3">
                        <Badge label={card.rarity_name} color={rarityColor} />
                        {card.quality_name !== "Authentique" && (
                            <Badge label={card.quality_name} className="bg-white/20 text-white" />
                        )}
                        {card.specialty_name !== "Normal" && (
                            <Badge label={card.specialty_name} className="bg-purple-600/80 text-white" />
                        )}
                        {card.jewelry_name !== "Aucun" && (
                            <Badge
                                label={card.jewelry_name}
                                color={`rgb(${card.jewelry_color.join(",")})`}
                            />
                        )}
                    </div>

                    <div className="space-y-1 text-sm text-white/70">
                        <p>Set: <span className="text-white">{card.set_name}</span></p>
                        <p>Type: <span className="text-white">{card.character_type}</span></p>
                        {card.character_description && card.quality_name !== "Injouable" && (
                            <p className="italic text-white/50 mt-2">{card.character_description}</p>
                        )}
                        <p>
                            Probabilité:{" "}
                            <span className="text-accent">{(card.drop_probability * 100).toFixed(4)}%</span>
                        </p>
                        {quantity !== undefined && quantity > 1 && (
                            <p>
                                Exemplaires: <span className="text-gold font-bold">×{quantity}</span>
                            </p>
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
