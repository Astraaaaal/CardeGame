import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import type { CardGroup } from "@/types/card";
import CardImage from "./CardImage";
import CardDetail from "./CardDetail";

interface CardGridProps {
    groups: CardGroup[];
}

export default function CardGrid({ groups }: CardGridProps) {
    // Sélection par id de carte (pas par index) : la liste peut se ré-trier.
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const selected = groups.find((g) => g.card.id === selectedId) ?? null;

    return (
        <>
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-3 px-2">
                {groups.map((g) => (
                    <div key={g.card.id} className="relative">
                        <CardImage
                            card={g.card}
                            size="sm"
                            onClick={() => setSelectedId(g.card.id)}
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
                {selected && (
                    <CardDetail
                        card={selected.card}
                        quantity={selected.quantity}
                        onClose={() => setSelectedId(null)}
                    />
                )}
            </AnimatePresence>
        </>
    );
}
