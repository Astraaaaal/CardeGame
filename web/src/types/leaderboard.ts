export interface LeaderboardEntry {
    rank: number;
    user_id: number;
    username: string;
    display_name: string;
    total_power: number;
}

export interface LeaderboardResponse {
    entries: LeaderboardEntry[];
}
