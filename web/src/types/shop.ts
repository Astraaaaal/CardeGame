import type { Card } from "./card";

export interface ShopOffer {
    id: string;
    kind: "booster" | "specific_card" | "upgrade";
    name: string;
    description: string;
    resource_id: string;
    resource_name: string;
    price: number;
    booster_id: string | null;
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
}

export interface ShopBuyResponse {
    message: string;
    resource_id: string;
    new_balance: number;
    cards: Card[];
}
