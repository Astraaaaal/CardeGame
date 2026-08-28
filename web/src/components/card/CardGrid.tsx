import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import type { CardGroup } from "@/types/card";
import CardImage from "./CardImage";
import CardDetail from "./CardDetail";

interface CardGridProps {
    groups: CardGroup[];
}

export default function CardGrid({ groups }: CardGridProps) {
    const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

    return (
        <>
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-3 px-2">
                {groups.map((g, idx) => (
                    <div key={idx} className="relative">
                        <CardImage
                            card={g.card}
                            size="sm"
                            onClick={() => setSelectedIdx(idx)}
                        />
                        {g.quantity > 1 && (
                            <span className="absolute -top-1 -right-1 bg-gold text-game-bg
                             text-xs font-bold rounded-full w-5 h-5
                             flex items-center justify-center">
                                {g.quantity}
                            </span>
                        )}
                    </div>
                ))}
            </div>

            <AnimatePresence>
                {selectedIdx !== null && (
                    <CardDetail
                        card={groups[selectedIdx].card}
                        quantity={groups[selectedIdx].quantity}
                        onClose={() => setSelectedIdx(null)}
                    />
                )}
            </AnimatePresence>
        </>
    );
}
