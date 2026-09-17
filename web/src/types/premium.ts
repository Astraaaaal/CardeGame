export type CosmeticKind = "avatar_frame" | "showcase_background";
export type CosmeticAnimation = "none" | "shine" | "pulse" | "rainbow";

export interface Cosmetic {
    id: string;
    kind: CosmeticKind;
    name: string;
    description: string;
    color_from: string;
    color_to: string;
    animation: CosmeticAnimation;
    image_url: string;
    active: boolean;
}

export type GrantKind = "resource" | "booster" | "cosmetic";

export interface Grant {
    kind: GrantKind;
    id: string;
    amount: number;
}

export interface GrantOut extends Grant {
    name: string;
}

export interface PremiumProduct {
    id: string;
    name: string;
    description: string;
    price_cents: number;
    currency: string;
    grants: GrantOut[];
    once_per_account: boolean;
    already_purchased: boolean;
    active: boolean;
    sort_order: number;
}

export interface PremiumStatus {
    access: boolean;
    shards: number;
    payments_available: boolean;
}

export interface MyCosmetics {
    owned: Cosmetic[];
    equipped_avatar_frame_id: string | null;
    equipped_showcase_background_id: string | null;
}

export interface PremiumOrder {
    id: number;
    username: string | null;
    product_name: string;
    amount_cents: number;
    currency: string;
    status: "pending" | "paid" | "failed" | "refunded";
    created_at: string;
    paid_at: string | null;
}

export interface PremiumConfig {
    premium_shop_enabled: boolean;
    premium_testers: string;
    stripe_configured: boolean;
    email_configured: boolean;
}

export const formatEuros = (cents: number) =>
    (cents / 100).toLocaleString("fr-FR", { style: "currency", currency: "EUR" });
