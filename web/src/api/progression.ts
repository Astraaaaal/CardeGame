import api from "./client";
import type { LevelStatus, LevelTierOverview, Achievement, Quest } from "@/types/progression";

export const progressionApi = {
    getLevel: () => api.get<LevelStatus>("/progression/levels").then((r) => r.data),
    getLevelTiers: () => api.get<LevelTierOverview[]>("/progression/levels/tiers").then((r) => r.data),
    claimLevel: () => api.post<LevelStatus>("/progression/levels/claim").then((r) => r.data),

    getAchievements: () => api.get<Achievement[]>("/progression/achievements").then((r) => r.data),
    claimAchievement: (id: string) =>
        api.post<Achievement>(`/progression/achievements/${id}/claim`).then((r) => r.data),

    getQuests: () => api.get<Quest[]>("/progression/quests").then((r) => r.data),
    claimQuest: (id: number) => api.post<Quest>(`/progression/quests/${id}/claim`).then((r) => r.data),
};
