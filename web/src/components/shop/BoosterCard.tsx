import type { Booster, OwnedBooster } from "@/types/booster";
import OwnedBoosterRow from "./OwnedBoosterRow";
import Button from "@/components/ui/Button";
import ResourceIcon from "@/components/ui/ResourceIcon";

interface BoosterCardProps {
    booster: Booster;
    onSelect: (booster: Booster) => void;
    /** Exemplaires déjà possédés de ce booster (avec ou sans bonus). */
    owned?: OwnedBooster[];
}

export default function BoosterCard({ booster, onSelect, owned = [] }: BoosterCardProps) {
    return (
        <div className="bg-game-surface rounded-2xl overflow-hidden border border-white/10
                    hover:border-accent/50 transition-all duration-200">
            {booster.cover_image_url && (
                <img
                    src={`/boosters/${booster.cover_image_url}`}
                    alt=""
                    className="w-full aspect-[16/9] object-cover"
                />
            )}
            <div className="p-4">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-white font-bold text-lg">{booster.name}</h3>
                    <span className="text-gold font-bold inline-flex items-center gap-1.5">
                        {booster.price} <ResourceIcon resourceId={booster.resource_id} />
                    </span>
                </div>

                <p className="text-white/60 text-sm mb-2">{booster.description}</p>

                <div className="flex gap-2 text-xs text-white/40 mb-4">
                    <span>{booster.cards_count} cartes</span>
                    {booster.guaranteed_rare && (
                        <span className="text-accent">• Rare garantie</span>
                    )}
                    {booster.set_ids.length > 1 && (
                        <span>• Sets {booster.set_ids.join(", ")}</span>
                    )}
                </div>

                {owned.length > 0 && (
                    <div className="space-y-2 mb-3">
                        {owned.map((o) => <OwnedBoosterRow key={o.bonus_id ?? "base"} owned={o} />)}
                    </div>
                )}

                <Button
                    variant="primary"
                    size="sm"
                    className="w-full"
                    onClick={() => onSelect(booster)}
                >
                    Acheter
                </Button>
            </div>
        </div>
    );
}
