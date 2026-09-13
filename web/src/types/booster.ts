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
