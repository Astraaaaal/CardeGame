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

export interface Showcase {
    user_id: number;
    username: string;
    display_name: string;
    avatar: AvatarInfo | null;
    cards: Card[];
    trade_listings: TradeListing[];
}

export interface TradeListingSlotIn {
    user_card_id: string;
    resource_id: string;
    price: number;
    mode: TradeListingMode;
}
