import api from "./client";
import type { Booster, PackOpenRequest, PackOpenResponse } from "@/types/booster";

export const boostersApi = {
    list: async (): Promise<Booster[]> => {
        const res = await api.get("/boosters/");
        return res.data;
    },

    openPacks: async (data: PackOpenRequest): Promise<PackOpenResponse> => {
        const res = await api.post("/boosters/open", data);
        return res.data;
    },
};
