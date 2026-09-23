import { useState } from "react";
import type { CardGroup } from "@/types/card";
import type { ProbabilityItem } from "@/api/collection";
import { selectAll, selectDuplicates, selectUpToTier } from "@/utils/recycleSelection";

interface RecycleToolsProps {
    groups: CardGroup[];
    rarities: ProbabilityItem[];   // du plus faible au plus fort
    qualities: ProbabilityItem[];
    includeFavorites: boolean;
    onIncludeFavorites: (value: boolean) => void;
    /** Ajoute ces exemplaires à la sélection. */
    onSelect: (ids: string[]) => void;
    onClear: () => void;
}

const CHIP = "px-2.5 py-1.5 rounded-lg text-[11px] font-semibold bg-white/10 text-white/70 hover:bg-white/20";

/**
 * Outils de sélection rapide du mode recyclage. Ils ne touchent qu'aux cartes
 * AFFICHÉES : les filtres de la collection font donc partie des outils (un
 * filtre de puissance, puis « tout ce qui est affiché », suffit à viser les
 * petits tirages). Les favoris sont épargnés tant que la case n'est pas cochée.
 */
export default function RecycleTools({
    groups, rarities, qualities, includeFavorites, onIncludeFavorites, onSelect, onClear,
}: RecycleToolsProps) {
    const [tierAxis, setTierAxis] = useState<"rarity_id" | "quality_id" | null>(null);
    const options = { includeFavorites };
    // L'API donne les paliers du meilleur au pire ; on les remet du pire au
    // meilleur, ordre attendu par selectUpToTier et plus naturel à lire ici
    // (« commune et en dessous » d'abord).
    const items = [...(tierAxis === "quality_id" ? qualities : rarities)].reverse();

    return (
        <div className="px-4 py-2 space-y-2 border-b border-white/10 bg-game-surface/60">
            <div className="flex flex-wrap gap-1.5">
                <button className={CHIP} onClick={() => onSelect(selectAll(groups, options))}>
                    Tout l'affichage
                </button>
                <button className={CHIP} onClick={() => onSelect(selectDuplicates(groups, options))}>
                    Doublons (garder le meilleur)
                </button>
                <button className={CHIP}
                    onClick={() => setTierAxis(tierAxis === "rarity_id" ? null : "rarity_id")}>
                    Jusqu'à la rareté…
                </button>
                <button className={CHIP}
                    onClick={() => setTierAxis(tierAxis === "quality_id" ? null : "quality_id")}>
                    Jusqu'à la qualité…
                </button>
                <button className={`${CHIP} !text-white/40`} onClick={onClear}>Tout décocher</button>
            </div>

            {tierAxis && (
                <div className="flex flex-wrap gap-1.5 pt-0.5">
                    {items.map((item) => (
                        <button key={item.id}
                            className="px-2 py-1 rounded-md text-[11px] bg-accent/20 text-accent hover:bg-accent/30"
                            onClick={() => {
                                onSelect(selectUpToTier(groups, tierAxis, item.id, items.map((i) => i.id), options));
                                setTierAxis(null);
                            }}>
                            {item.name} et en dessous
                        </button>
                    ))}
                </div>
            )}

            <label className="flex items-center gap-2 text-[11px] text-white/50">
                <input type="checkbox" checked={includeFavorites}
                    onChange={(e) => onIncludeFavorites(e.target.checked)} />
                Inclure mes favoris dans ces outils (les cartes verrouillées restent protégées)
            </label>
        </div>
    );
}
