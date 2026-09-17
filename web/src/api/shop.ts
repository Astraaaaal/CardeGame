import api from "./client";
import type { ShopOffer, ShopBuyResponse, RerollToken, RerollUseResponse } from "@/types/shop";

export interface ResourceCatalogItem {
    id: string;
    name: string;
}

export const shopApi = {
    list: async (): Promise<ShopOffer[]> => {
        const res = await api.get("/shop/");
        return res.data;
    },

    buy: async (offerId: string, cardId?: string, toInventory = false, quantity = 1): Promise<ShopBuyResponse> => {
        const res = await api.post("/shop/buy", { offer_id: offerId, card_id: cardId, to_inventory: toInventory, quantity });
        return res.data;
    },

    rerollTokens: async (): Promise<RerollToken[]> => {
        const res = await api.get("/shop/rerolls");
        return res.data;
    },

    applyRerollToken: async (tokenId: number, cardId: string): Promise<RerollUseResponse> => {
        const res = await api.post(`/shop/rerolls/${tokenId}/use`, { card_id: cardId });
        return res.data;
    },

    resources: async (): Promise<ResourceCatalogItem[]> => {
        const res = await api.get("/shop/resources");
        return res.data;
    },
};
