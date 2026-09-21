import type { Card } from "@/types/card";

export type TradeSessionStatus = "negotiating" | "confirming" | "completed" | "cancelled" | "expired";

export interface TradeSessionItem {
    id: number;
    owner_id: number;
    item_type: "card" | "resource" | "booster" | "reroll";
    card: Card | null;
    resource_id: string | null;
    resource_name: string | null;
    amount: number | null;
    booster_id: string | null;
    /** Booster ou reroll : son nom. */
    name: string | null;
    /** Bonus du booster ou règles du reroll. */
    label: string | null;
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
    /** Taxe en pièces payée par chacun sur ce qu'il reçoit. */
    tax_rate: number;
    my_tax: number;
    other_tax: number;
}
