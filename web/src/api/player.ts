import api from "./client";
import type { Player, DailyReward } from "@/types/player";

export const playerApi = {
    getMe: async (): Promise<Player> => {
        const res = await api.get("/player/me");
        return res.data;
    },

    claimDailyReward: async (): Promise<DailyReward> => {
        const res = await api.post("/player/daily-reward");
        return res.data;
    },
};
