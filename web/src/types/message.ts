import type { Card } from "@/types/card";

export type MessageSenderType = "admin" | "player";

export interface AppMessage {
    id: number;
    sender_type: MessageSenderType;
    sender_display_name: string;
    subject: string;
    body: string;
    reward_resource_id: string | null;
    reward_resource_name: string | null;
    reward_amount: number | null;
    reward_card: Card | null;
    reward_booster_id: string | null;
    reward_booster_name: string | null;
    reward_booster_cover_url: string | null;
    reward_booster_qty: number | null;
    reward_booster_label: string | null;
    reward_reroll_label: string | null;
    reward_reroll_qty: number | null;
    has_reward: boolean;
    created_at: string;
    read_at: string | null;
    claimed_at: string | null;
    claim_error: string | null;
}
