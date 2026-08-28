import type { Booster } from "@/types/booster";
import Button from "@/components/ui/Button";

interface BoosterCardProps {
    booster: Booster;
    onSelect: (booster: Booster) => void;
}

export default function BoosterCard({ booster, onSelect }: BoosterCardProps) {
    return (
        <div className="bg-game-surface rounded-2xl p-4 border border-white/10
                    hover:border-accent/50 transition-all duration-200">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-white font-bold text-lg">{booster.name}</h3>
                <span className="text-gold font-bold">{booster.price} 🪙</span>
            </div>

            <p className="text-white/60 text-sm mb-2">{booster.description}</p>

            <div className="flex gap-2 text-xs text-white/40 mb-4">
                <span>{booster.cards_count} cartes</span>
                {booster.guaranteed_rare && (
                    <span className="text-accent">• Rare garantie</span>
                )}
            </div>

            <Button
                variant="primary"
                size="sm"
                className="w-full"
                onClick={() => onSelect(booster)}
            >
                Ouvrir
            </Button>
        </div>
    );
}
