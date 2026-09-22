import api from "./client";
import type { LeaderboardResponse } from "@/types/leaderboard";

export interface MonthlyReward {
    kind: string;
    name: string;
    quantity: number;
    resource_id: string | null;
}

export interface MonthlyChallengeData {
    month_key: string;
    month_label: string;
    ends_at: string;
    solo: { rank: number; user_id: number; display_name: string; points: number }[];
    guilds: { rank: number; guild_id: number; name: string; tag: string; icon: string; color: string; points: number }[];
    me: { rank: number | null; points: number };
    my_guild: { rank: number; points: number } | null;
    players: number;
    solo_rewards: { label: string; rewards: MonthlyReward[] }[];
    guild_rewards: { label: string; rewards: MonthlyReward[] }[];
    last_champion: { month_label: string; user_id: number | null; display_name: string | null; guild_name: string | null } | null;
}

export const leaderboardApi = {
    friends: () => api.get<LeaderboardResponse>("/leaderboard/friends").then((r) => r.data),
    global: () => api.get<LeaderboardResponse>("/leaderboard/global").then((r) => r.data),
    monthly: () => api.get<MonthlyChallengeData>("/leaderboard/monthly").then((r) => r.data),
    byType: (typeName: string) =>
        api.get<LeaderboardResponse>("/leaderboard/by-type", { params: { type_name: typeName } }).then((r) => r.data),
};
