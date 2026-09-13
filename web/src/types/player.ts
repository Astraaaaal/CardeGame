export interface ResourceBalance {
    id: string;
    name: string;
    amount: number;
}

export type TradeRequestPolicy = "everyone" | "friends" | "close_friends" | "none";

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
}

export interface DailyReward {
    reward: number;
    streak: number;
    is_new: boolean;
    total_coins: number;
}
