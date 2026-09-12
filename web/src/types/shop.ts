import type { Card } from "./card";

export interface ShopOffer {
    id: string;
    kind: "booster" | "specific_card" | "upgrade" | "reroll";
    name: string;
    description: string;
    resource_id: string;
    resource_name: string;
    price: number;
    purchase_limit_per_day: number | null;
    purchases_today: number;
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
    target_quality_id: string | null;
    target_quality_name: string | null;
    target_specialty_id: string | null;
    target_specialty_name: string | null;
    reroll_rarity: boolean;
    reroll_quality: boolean;
    reroll_specialty: boolean;
    reroll_jewelry: boolean;
    reroll_mode: "random" | "guaranteed_min" | null;
}

export interface ShopBuyResponse {
    message: string;
    resource_id: string;
    new_balance: number;
    cards: Card[];
}
