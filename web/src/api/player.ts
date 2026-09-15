import api from "./client";
import type { Player, DailyReward, PlayerSettings, PlayerStats } from "@/types/player";
import type { MessageResponse } from "@/types/auth";

export const playerApi = {
    getMe: async (): Promise<Player> => {
        const res = await api.get("/player/me");
        return res.data;
    },

    getStats: async (): Promise<PlayerStats> => {
        const res = await api.get("/player/stats");
        return res.data;
    },

    getSettings: async (): Promise<PlayerSettings> => {
        const res = await api.get("/player/settings");
        return res.data;
    },

    updateSettings: async (patch: Partial<PlayerSettings>): Promise<PlayerSettings> => {
        const res = await api.patch("/player/settings", patch);
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

    deleteAccount: async (password: string): Promise<MessageResponse> => {
        const res = await api.delete("/player/me", { data: { password } });
        return res.data;
    },
};
