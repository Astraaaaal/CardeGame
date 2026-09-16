import type { Card } from "./card";

export interface AvatarInfo {
    character_id: string;
    character_name: string;
    image_url: string;
}

export type TradeListingMode = "buy_now" | "offer";

export interface TradeListing {
    slot: number;
    card: Card;
    resource_id: string;
    resource_name: string;
    price: number;
    mode: TradeListingMode;
}

export type FriendshipStatus = "self" | "friends" | "pending" | "none";

export interface ShowcaseAchievement {
    id: string;
    name: string;
    description: string;
    category: string;
}

export interface Showcase {
    user_id: number;
    username: string;
    display_name: string;
    avatar: AvatarInfo | null;
    cards: Card[];
    trade_listings: TradeListing[];
    friendship_status: FriendshipStatus;
    level: number;
    best_login_streak: number;
    current_global_rank: number | null;
    best_global_rank: number | null;
    achievements: ShowcaseAchievement[];
    achievement_slots: (string | null)[];
}

export interface TradeListingSlotIn {
    user_card_id: string;
    resource_id: string;
    price: number;
    mode: TradeListingMode;
}
