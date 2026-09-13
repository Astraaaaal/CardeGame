import api from "./client";
import type { ShopOffer, ShopBuyResponse } from "@/types/shop";

export interface ResourceCatalogItem {
    id: string;
    name: string;
}

export const shopApi = {
    list: async (): Promise<ShopOffer[]> => {
        const res = await api.get("/shop/");
        return res.data;
    },

    buy: async (offerId: string, cardId?: string): Promise<ShopBuyResponse> => {
        const res = await api.post("/shop/buy", { offer_id: offerId, card_id: cardId });
        return res.data;
    },

    resources: async (): Promise<ResourceCatalogItem[]> => {
        const res = await api.get("/shop/resources");
        return res.data;
    },
};
