import api from "./client";
import type { Booster, PackOpenRequest, PackOpenResponse, OwnedBooster, OpenOwnedRequest } from "@/types/booster";

export const boostersApi = {
    list: async (): Promise<Booster[]> => {
        const res = await api.get("/boosters/");
        return res.data;
    },

    openPacks: async (data: PackOpenRequest): Promise<PackOpenResponse> => {
        const res = await api.post("/boosters/open", data);
        return res.data;
    },

    getInventory: async (): Promise<OwnedBooster[]> => {
        const res = await api.get("/boosters/inventory");
        return res.data;
    },

    openOwned: async (data: OpenOwnedRequest): Promise<PackOpenResponse> => {
        const res = await api.post("/boosters/inventory/open", data);
        return res.data;
    },
};
