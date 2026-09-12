import api from "./client";
import type { CardGroup, Card } from "@/types/card";

export interface CollectionParams {
    sort_by?: string;
    set_id?: string;
    rarity_id?: string;
    specialty_id?: string;
    jewelry_id?: string;
}

export interface CollectionResponse {
    total_cards: number;
    unique_cards: number;
    groups: CardGroup[];
}

export interface RecycleRequest {
    character_id: string;
    rarity_id: string;
    quality_id: string;
    specialty_id: string;
    jewelry_id: string;
    count: number;
}

export interface RecycleResponse {
    resource_id: string;
    resource_name: string;
    gained: number;
    new_balance: number;
    remaining_quantity: number;
}

export const collectionApi = {
    getCollection: async (params?: CollectionParams): Promise<CollectionResponse> => {
        const res = await api.get("/collection/", { params });
        return res.data;
    },

    getCardDetail: async (cardId: string): Promise<Card> => {
        const res = await api.get(`/collection/${cardId}`);
        return res.data;
    },

    recycle: async (body: RecycleRequest): Promise<RecycleResponse> => {
        const res = await api.post("/collection/recycle", body);
        return res.data;
    },
};
