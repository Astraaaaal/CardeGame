import type { CardGroup } from "@/types/card";
import { selectAll, selectDuplicates } from "@/utils/recycleSelection";

interface RecycleToolsProps {
    groups: CardGroup[];
    includeFavorites: boolean;
    onIncludeFavorites: (value: boolean) => void;
    /** Ajoute ces exemplaires à la sélection. */
    onSelect: (ids: string[]) => void;
    onClear: () => void;
}

const CHIP = "px-2.5 py-1.5 rounded-lg text-[11px] font-semibold bg-white/10 text-white/70 hover:bg-white/20";

/**
 * Outils de sélection rapide du mode recyclage. Ils ne touchent qu'aux cartes
 * AFFICHÉES : trier par rareté, qualité ou puissance se fait avec les filtres
 * de la collection, puis « tout l'affichage » ramasse le résultat — inutile de
 * dupliquer ces critères ici. Les favoris sont épargnés tant que la case n'est
 * pas cochée.
 */
export default function RecycleTools({
    groups, includeFavorites, onIncludeFavorites, onSelect, onClear,
}: RecycleToolsProps) {
    const options = { includeFavorites };

    return (
        <div className="px-4 py-2 space-y-2 border-b border-white/10 bg-game-surface/60">
            <div className="flex flex-wrap gap-1.5">
                <button className={CHIP} onClick={() => onSelect(selectAll(groups, options))}>
                    Tout sélectionner
                </button>
                <button className={CHIP} onClick={() => onSelect(selectDuplicates(groups, options))}>
                    Doublons (garder le meilleur)
                </button>
                <button className={`${CHIP} !text-white/40`} onClick={onClear}>Tout décocher</button>
            </div>

            <label className="flex items-center gap-2 text-[11px] text-white/50">
                <input type="checkbox" checked={includeFavorites}
                    onChange={(e) => onIncludeFavorites(e.target.checked)} />
                Inclure mes favoris dans ces outils (les cartes verrouillées restent protégées)
            </label>
        </div>
    );
}
