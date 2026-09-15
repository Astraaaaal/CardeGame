export interface ResourceBalance {
    id: string;
    name: string;
    amount: number;
}

export type TradeRequestPolicy = "everyone" | "friends" | "close_friends" | "none";
export type GiftPolicy = "everyone" | "friends" | "close_friends" | "none";

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
    resources: ResourceBalance[];
    allow_friend_requests: boolean;
    trade_request_policy: TradeRequestPolicy;
    trade_request_popup_enabled: boolean;
}

export interface PlayerSettings {
    allow_friend_requests: boolean;
    trade_request_policy: TradeRequestPolicy;
    trade_request_popup_enabled: boolean;
    gift_policy: GiftPolicy;
}

export interface DailyReward {
    reward: number;
    streak: number;
    is_new: boolean;
    total_coins: number;
}

export interface PlayerStats {
    total_cards: number;
    unique_cards: number;
    packs_opened: number;
    cards_recycled: number;
    coins: number;
    dust: number;
    total_power: number;
    average_power: number;
    highest_power_card: import("./card").Card | null;
    luckiest_card: import("./card").Card | null;
    most_duplicated_card: import("./card").Card | null;
    most_duplicated_count: number;
    friends_count: number;
    trades_completed: number;
    gifts_sent: number;
    gifts_received: number;
    current_level: number;
    achievements_unlocked: number;
    achievements_total: number;
    login_streak: number;
    favorite_type_name: string | null;
    favorite_type_count: number;
    oldest_card: import("./card").Card | null;
}
