import api from "./client";
import type { LeaderboardResponse } from "@/types/leaderboard";

export const leaderboardApi = {
    friends: () => api.get<LeaderboardResponse>("/leaderboard/friends").then((r) => r.data),
    global: () => api.get<LeaderboardResponse>("/leaderboard/global").then((r) => r.data),
    byType: (typeName: string) =>
        api.get<LeaderboardResponse>("/leaderboard/by-type", { params: { type_name: typeName } }).then((r) => r.data),
};
