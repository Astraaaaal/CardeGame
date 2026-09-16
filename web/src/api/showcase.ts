import api from "./client";
import type { Showcase, TradeListingSlotIn } from "@/types/showcase";

export const showcaseApi = {
    get: async (userId: number): Promise<Showcase> => {
        const res = await api.get(`/players/${userId}/showcase`);
        return res.data;
    },

    update: async (
        avatarCharacterId: string | null,
        cardSlots: (string | null)[],
        achievementSlots: (string | null)[],
    ): Promise<Showcase> => {
        const res = await api.put("/player/showcase", {
            avatar_character_id: avatarCharacterId,
            card_slots: cardSlots,
            achievement_slots: achievementSlots,
        });
        return res.data;
    },

    updateTradeListings: async (slots: (TradeListingSlotIn | null)[]): Promise<Showcase> => {
        const res = await api.put("/player/trade-listings", { slots });
        return res.data;
    },

    buyTradeListing: async (userId: number, slot: number): Promise<Showcase> => {
        const res = await api.post(`/players/${userId}/trade-listings/${slot}/buy`);
        return res.data;
    },

    proposeTradeListing: async (userId: number, slot: number) => {
        const res = await api.post(`/players/${userId}/trade-listings/${slot}/propose`);
        return res.data;
    },
};
