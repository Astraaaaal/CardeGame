import api from "./client";
import type { CardGroup, Card } from "@/types/card";

export type TierOp = "eq" | "gte" | "lte";

// axios sérialise un tableau en "key[]=val" par défaut, alors que FastAPI
// (Query(list[str])) attend des clés répétées "key=val1&key=val2" — sans ça
// le filtre par type est silencieusement ignoré côté serveur.
function serializeParams(params: object): string {
    const usp = new URLSearchParams();
    for (const [key, value] of Object.entries(params as Record<string, unknown>)) {
        if (value === undefined || value === null || value === "") continue;
        if (Array.isArray(value)) {
            value.forEach((v) => usp.append(key, String(v)));
        } else {
            usp.append(key, String(value));
        }
    }
    return usp.toString();
}

export interface CollectionParams {
    sort_by?: string;
    set_id?: string;
    rarity_id?: string;
    rarity_op?: TierOp;
    quality_id?: string;
    quality_op?: TierOp;
    specialty_id?: string;
    specialty_op?: TierOp;
    jewelry_id?: string;
    jewelry_op?: TierOp;
    type_names?: string[];
    min_power?: number;
    max_power?: number;
    favorite_id?: number;
}

export interface CollectionResponse {
    total_cards: number;
    unique_cards: number;
    groups: CardGroup[];
}

export interface ProbabilityItem {
    id: string;
    name: string;
    weight: number;
    percentage: number;
}

export interface ProbabilityTable {
    rarities: ProbabilityItem[];
    qualities: ProbabilityItem[];
    specialties: ProbabilityItem[];
    jewelries: ProbabilityItem[];
}

export interface RecycleByIdsRequest {
    card_ids: string[];
}

export interface RecycleByIdsResponse {
    resource_id: string;
    resource_name: string;
    gained: number;
    new_balance: number;
    recycled_count: number;
}

export interface CardComboParams {
    character_id: string;
    rarity_id: string;
    quality_id: string;
    specialty_id: string;
    jewelry_id: string;
}

export interface CardCopy {
    id: string;
    power: number | null;
    locked: boolean;
    favorite_ids: number[];
}

export interface CardCopiesResponse {
    copies: CardCopy[];
}

export const collectionApi = {
    getCollection: async (params?: CollectionParams): Promise<CollectionResponse> => {
        const res = await api.get("/collection/", { params, paramsSerializer: serializeParams });
        return res.data;
    },

    getCardDetail: async (cardId: string): Promise<Card> => {
        const res = await api.get(`/collection/${cardId}`);
        return res.data;
    },

    getProbabilities: async (): Promise<ProbabilityTable> => {
        const res = await api.get("/collection/probabilities");
        return res.data;
    },

    recycle: async (body: RecycleByIdsRequest): Promise<RecycleByIdsResponse> => {
        const res = await api.post("/collection/recycle", body);
        return res.data;
    },

    getCardCopies: async (params: CardComboParams): Promise<CardCopiesResponse> => {
        const res = await api.get("/collection/copies", { params });
        return res.data;
    },
};
