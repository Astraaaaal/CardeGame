export interface Player {
    id: number;
    username: string;
    display_name: string;
    coins: number;
    packs_opened: number;
    total_cards: number;
    login_streak: number;
    created_at: string;
    last_login: string | null;
}

export interface DailyReward {
    reward: number;
    streak: number;
    is_new: boolean;
    total_coins: number;
}
