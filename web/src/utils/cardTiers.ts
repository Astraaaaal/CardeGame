import type { Card } from "@/types/card";

/**
 * Paliers "remarquables" d'une carte pour la révélation d'un booster :
 * chaque palier atteint = un effet visuel + un clic de suspense en plus.
 * Ordres croissants alignés sur backend/app/services/tier_order.py.
 */
export type TierAxis = "rarity" | "jewelry" | "specialty" | "quality";

export const TIER_STEPS: Record<TierAxis, string[]> = {
    rarity: ["rare", "epic", "legendary"],
    jewelry: ["silver", "gold", "diamond", "prismatic"],
    specialty: ["full_art", "ex", "shiny"],
    quality: ["excellent", "graded", "mint", "authentic"],
};

/** Ordre complet du pire au meilleur, par axe (miroir de tier_order.py). */
export const FULL_TIER_ORDER: Record<TierAxis, string[]> = {
    rarity: ["common", "rare", "epic", "legendary"],
    jewelry: ["none", "silver", "gold", "diamond", "prismatic"],
    specialty: ["normal", "full_art", "ex", "shiny"],
    quality: [
        "destroyed", "unreadable", "unplayable", "damaged", "torn", "scratched", "faded",
        "worn", "fair", "preserved", "excellent", "graded", "mint", "authentic",
    ],
};

// Ordre d'enchaînement pendant le suspense (choix de design).
const AXIS_ORDER: TierAxis[] = ["rarity", "jewelry", "specialty", "quality"];

export interface SuspenseStep {
    axis: TierAxis;
    id: string;
}

const cardTierId = (card: Card, axis: TierAxis): string => ({
    rarity: card.rarity_id,
    jewelry: card.jewelry_id,
    specialty: card.specialty_id,
    quality: card.quality_id,
}[axis]);

/** Niveau atteint sur un axe : 0 = aucun effet, 1 = premier palier, etc. */
export function tierLevel(card: Card, axis: TierAxis): number {
    return TIER_STEPS[axis].indexOf(cardTierId(card, axis)) + 1;
}

/** Tous les paliers à dévoiler un par un avant de retourner la carte. */
export function suspenseSteps(card: Card): SuspenseStep[] {
    return AXIS_ORDER.flatMap((axis) =>
        TIER_STEPS[axis].slice(0, tierLevel(card, axis)).map((id) => ({ axis, id }))
    );
}

/** Carte qui doit être gardée pour la fin du booster. */
export function isHighlightCard(card: Card): boolean {
    return (
        card.rarity_id === "legendary"
        || card.jewelry_id === "diamond" || card.jewelry_id === "prismatic"
        || tierLevel(card, "quality") > 0
    );
}

/** Garde l'ordre tiré pour les cartes ordinaires, puis les cartes marquantes
 * de la moins à la plus chanceuse : la meilleure est révélée en dernier. */
export function orderPackForReveal(pack: Card[]): Card[] {
    const regular = pack.filter((c) => !isHighlightCard(c));
    const highlights = pack
        .filter(isHighlightCard)
        .sort((a, b) => (a.combined_rarity ?? 0) - (b.combined_rarity ?? 0));
    return [...regular, ...highlights];
}

/** Carte au-dessus du tout-venant : rareté rare ou mieux, bijou argent ou mieux,
 * qualité correcte ou mieux, ou spécialité autre que normale. Sert au reflet
 * vertical (cf. CardEffects). */
export function isPolishedCard(card: Card): boolean {
    const atLeast = (axis: TierAxis, id: string) =>
        FULL_TIER_ORDER[axis].indexOf(cardTierId(card, axis)) >= FULL_TIER_ORDER[axis].indexOf(id);
    return atLeast("rarity", "rare") || atLeast("jewelry", "silver")
        || atLeast("quality", "fair") || card.specialty_id !== "normal";
}
