export interface Booster {
    id: string;
    name: string;
    set_id: string;
    set_ids: string[];
    cards_count: number;
    resource_id: string;
    resource_name: string;
    price: number;
    guaranteed_rare: boolean;
    description: string;
    cover_image_url: string;
}

export interface PackOpenRequest {
    booster_id: string;
    quantity: 1 | 5 | 10;
}

export interface PackOpenResponse {
    packs: import("./card").Card[][];
    total_cost: number;
    remaining_coins: number;
    resource_id: string;
    resource_name: string;
    new_balance: number;
}

export interface OwnedBooster {
    booster_id: string;
    booster_name: string;
    booster_cover_url: string | null;
    quantity: number;
    /** Booster acheté via une offre à bonus (rareté garantie, chances boostées). */
    bonus_id: number | null;
    bonus_label: string | null;
    force_min_rarity_id: string | null;
    rarity_weight_multiplier: number | null;
}

export interface BuyToInventoryResponse {
    booster_id: string;
    booster_name: string;
    quantity: number;
    total_cost: number;
    resource_id: string;
    resource_name: string;
    new_balance: number;
}

export interface OpenOwnedRequest {
    booster_id: string;
    quantity: number;
    bonus_id?: number | null;
}
