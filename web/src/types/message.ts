import type { Card } from "@/types/card";

export type MessageSenderType = "admin" | "player";

export interface AppMessage {
    id: number;
    sender_type: MessageSenderType;
    sender_display_name: string;
    subject: string;
    body: string;
    /** Taxe (pièces) à payer pour récupérer un cadeau de joueur. */
    tax: number;
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
    /** Messages admin : récompenses multiples. */
    reward_items: MessageRewardItem[];
    has_reward: boolean;
    created_at: string;
    read_at: string | null;
    claimed_at: string | null;
    claim_error: string | null;
}

/** Décoration proposée par une récompense « au choix ». */
export interface CosmeticOption {
    id: string;
    name: string;
    description: string;
    color_from: string;
    color_to: string;
    animation: string;
    image_url: string;
}

export interface MessageRewardItem {
    kind: "resource" | "booster" | "reroll" | "card" | "cosmetic_choice";
    name: string;
    quantity: number;
    resource_id: string | null;
    booster_id: string | null;
    label: string | null;
    card: Card | null;
    /** Récompense « au choix » : les options, puis celle retenue. */
    options: CosmeticOption[] | null;
    chosen_id: string | null;
}
