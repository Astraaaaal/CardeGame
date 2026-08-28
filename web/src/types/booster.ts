export interface Booster {
    id: string;
    name: string;
    set_id: string;
    cards_count: number;
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
}
