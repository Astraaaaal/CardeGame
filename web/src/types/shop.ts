import type { Card } from "./card";

export type LimitPeriod = "none" | "day" | "week" | "month" | "account";

export interface OfferGrant {
    kind: "resource" | "booster" | "cosmetic";
    id: string;
    amount: number;
    name: string;
}

export interface ShopOffer {
    id: string;
    kind: "booster" | "specific_card" | "reroll" | "cosmetic" | "bundle";
    name: string;
    description: string;
    resource_id: string;
    resource_name: string;
    price: number;
    purchase_limit_per_day: number | null;
    purchases_today: number;
    /** Limite réglable : période, nombre autorisé, achats déjà faits. */
    limit_period: LimitPeriod;
    limit_count: number;
    purchases_in_period: number;
    /** Contenu d'un lot (kind = bundle). */
    grants: OfferGrant[];
    is_daily_pool: boolean;
    featured_today: boolean;
    booster_id: string | null;
    force_min_rarity_id: string | null;
    force_min_rarity_name: string | null;
    rarity_weight_multiplier: number | null;
    character_id: string | null;
    character_name: string | null;
    rarity_id: string | null;
    rarity_name: string | null;
    quality_id: string | null;
    quality_name: string | null;
    specialty_id: string | null;
    specialty_name: string | null;
    jewelry_id: string | null;
    jewelry_name: string | null;
    reroll_rarity: boolean;
    reroll_quality: boolean;
    reroll_specialty: boolean;
    reroll_jewelry: boolean;
    reroll_power: boolean;
    reroll_mode: "random" | "guaranteed_min" | null;
    cosmetic_id: string | null;
    cosmetic_name: string | null;
}

export interface ShopBuyResponse {
    message: string;
    resource_id: string;
    new_balance: number;
    cards: Card[];
    /** Booster ouvert : un pack par exemplaire acheté. */
    packs: Card[][];
    /** Reroll : la carte telle qu'elle était avant. */
    previous_card: Card | null;
}

/** Reroll acheté et gardé en inventaire (règles figées à l'achat). */
export interface RerollToken {
    id: number;
    offer_id: string | null;
    label: string;
    quantity: number;
    axes: ("rarity" | "quality" | "specialty" | "jewelry")[];
    reroll_power: boolean;
    reroll_mode: "random" | "guaranteed_min" | null;
}

export interface RerollUseResponse {
    message: string;
    previous_card: Card;
    card: Card;
    token: RerollToken;
}
