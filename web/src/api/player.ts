import api from "./client";
import type { Player, DailyReward } from "@/types/player";
import type { MessageResponse } from "@/types/auth";

export const playerApi = {
    getMe: async (): Promise<Player> => {
        const res = await api.get("/player/me");
        return res.data;
    },

    updateProfile: async (display_name: string): Promise<Player> => {
        const res = await api.patch("/player/me", { display_name });
        return res.data;
    },

    changePassword: async (current_password: string, new_password: string): Promise<MessageResponse> => {
        const res = await api.post("/player/change-password", { current_password, new_password });
        return res.data;
    },

    claimDailyReward: async (): Promise<DailyReward> => {
        const res = await api.post("/player/daily-reward");
        return res.data;
    },
};
