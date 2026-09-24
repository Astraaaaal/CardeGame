export interface LeaderboardEntry {
    rank: number;
    user_id: number;
    username: string;
    display_name: string;
    total_power: number;
}

export interface LeaderboardResponse {
    /** Type réellement affiché quand le serveur l'a choisi. */
    type_name?: string | null;
    entries: LeaderboardEntry[];
}
