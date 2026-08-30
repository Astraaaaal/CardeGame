import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { Card } from "@/types/card";
import CardImage from "./CardImage";

interface CardRevealProps {
    card: Card;
    onNext: () => void;
}

function rarityColorToCSS(color: number[]): string {
    return `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
}

export default function CardReveal({ card, onNext }: CardRevealProps) {
    const [flipped, setFlipped] = useState(false);
    const rarityColor = rarityColorToCSS(card.rarity_color);

    const handleClick = () => {
        if (!flipped) {
            setFlipped(true);
        } else {
            setFlipped(false);
            setTimeout(onNext, 100);
        }
    };

    return (
        <div
            className="flex flex-col items-center justify-center gap-6 cursor-pointer"
            onClick={handleClick}
        >
            <div className="relative w-56 aspect-[5/7]" style={{ perspective: "1000px" }}>
                <AnimatePresence mode="wait">
                    {!flipped ? (
                        <motion.div
                            key="back"
                            className="absolute inset-0 rounded-2xl overflow-hidden bg-gradient-to-br
                         from-accent/40 to-purple-600/40 border-2 border-white/20
                         flex items-center justify-center"
                            initial={{ rotateY: 0 }}
                            exit={{ rotateY: 90 }}
                            transition={{ duration: 0.25 }}
                        >
                            <span className="text-6xl">🃏</span>
                        </motion.div>
                    ) : (
                        <motion.div
                            key="front"
                            className="absolute inset-0"
                            initial={{ rotateY: -90 }}
                            animate={{ rotateY: 0 }}
                            transition={{ duration: 0.25 }}
                        >
                            <CardImage card={card} size="lg" />
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {flipped && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center"
                >
                    <p className="text-white font-bold text-lg">{card.character_name}</p>
                    <p className="text-sm" style={{ color: rarityColor }}>
                        {card.rarity_name}
                        {card.specialty_id !== "normal" && ` • ${card.specialty_name}`}
                        {card.jewelry_id !== "none" && ` • ${card.jewelry_name}`}
                    </p>
                    <p className="text-white/40 text-xs mt-2">Touchez pour continuer</p>
                </motion.div>
            )}
        </div>
    );
}
