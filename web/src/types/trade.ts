import type { Card } from "@/types/card";

export type TradeSessionStatus = "negotiating" | "confirming" | "completed" | "cancelled" | "expired";

export interface TradeSessionItem {
    id: number;
    owner_id: number;
    item_type: "card" | "resource";
    card: Card | null;
    resource_id: string | null;
    resource_name: string | null;
    amount: number | null;
}

export interface TradeSession {
    id: number;
    status: TradeSessionStatus;
    other_user_id: number;
    other_username: string;
    other_display_name: string;
    other_online: boolean;
    my_ready: boolean;
    other_ready: boolean;
    my_confirmed: boolean;
    other_confirmed: boolean;
    my_items: TradeSessionItem[];
    other_items: TradeSessionItem[];
    updated_at: string;
    removed_items: string[];
}
