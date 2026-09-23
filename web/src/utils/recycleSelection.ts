/**
 * Outils de sélection du mode recyclage — fonctions pures, sans React, pour
 * que les règles de protection restent lisibles et vérifiables à un seul
 * endroit.
 *
 * Deux niveaux de protection :
 *  - verrou (🔒) : jamais sélectionnable, ni à la main ni par un outil ;
 *  - favori : ignoré par les outils de sélection rapide (sauf « inclure mes
 *    favoris »), mais sélectionnable par un appui volontaire sur la carte.
 */

import type { CardCopy, CardGroup } from "@/types/card";

export interface SelectionOptions {
    /** Les outils rapides prennent aussi les exemplaires rangés en favori. */
    includeFavorites: boolean;
}

export function isLocked(copy: CardCopy): boolean {
    return copy.locked;
}

export function isFavorite(copy: CardCopy): boolean {
    return (copy.favorite_ids?.length ?? 0) > 0;
}

/** Exemplaire que les outils rapides ont le droit de prendre. */
function eligible(copy: CardCopy, { includeFavorites }: SelectionOptions): boolean {
    return !isLocked(copy) && (includeFavorites || !isFavorite(copy));
}

/** Exemplaires qu'un appui sur la carte sélectionne (le verrou seul bloque). */
export function copiesOfGroup(group: CardGroup): CardCopy[] {
    return (group.copies ?? []).filter((c) => !isLocked(c));
}

/** Tout ce qui est affiché (donc ce que les filtres laissent passer). */
export function selectAll(groups: CardGroup[], options: SelectionOptions): string[] {
    return groups.flatMap((g) => (g.copies ?? []).filter((c) => eligible(c, options)).map((c) => c.id));
}

/**
 * Les doublons de chaque carte, en gardant le meilleur exemplaire. Les copies
 * arrivent triées par puissance décroissante : le premier exemplaire gardable
 * est celui qu'on conserve — un verrou ou un favori protégé tient déjà ce rôle,
 * inutile d'en épargner un second.
 */
export function selectDuplicates(groups: CardGroup[], options: SelectionOptions): string[] {
    return groups.flatMap((g) => {
        const copies = g.copies ?? [];
        if (copies.length < 2) return [];
        const kept = copies.find((c) => !eligible(c, options)) ?? copies[0];
        return copies.filter((c) => c.id !== kept.id && eligible(c, options)).map((c) => c.id);
    });
}

/** Ce que contient la sélection, pour la fenêtre de confirmation. */
export interface SelectionSummary {
    count: number;
    favorites: number;
    /** Cartes d'un palier de rareté notable (épique ou mieux). */
    precious: number;
}

export function summarize(
    groups: CardGroup[], selected: Set<string>, preciousRarityIds: string[],
): SelectionSummary {
    let favorites = 0;
    let precious = 0;
    for (const g of groups) {
        const isPrecious = preciousRarityIds.includes(g.card.rarity_id);
        for (const copy of g.copies ?? []) {
            if (!selected.has(copy.id)) continue;
            if (isFavorite(copy)) favorites += 1;
            if (isPrecious) precious += 1;
        }
    }
    return { count: selected.size, favorites, precious };
}
