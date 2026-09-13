export interface GameSet {
    id: string;
    name: string;
    description: string;
    booster_count?: number;
    character_count?: number;
}

export interface AdminBooster {
    id: string;
    name: string;
    set_ids: string[];
    cards_count: number;
    resource_id: string;
    resource_name: string;
    price: number;
    guaranteed_rare: boolean;
    description: string;
    active: boolean;
    visible_in_shop: boolean;
    cover_image_url: string;
}

export interface AdminType {
    id: string;
    name: string;
    color: number[];
    in_use: number;
}

export interface AdminResource {
    id: string;
    name: string;
    description: string;
    protected: boolean;
}

export interface AdminShopOffer {
    id: string;
    kind: "booster" | "specific_card" | "reroll";
    name: string;
    description: string;
    active: boolean;
    resource_id: string;
    resource_name: string;
    price: number;
    purchase_limit_per_day: number | null;
    purchases_today: number;
    is_daily_pool: boolean;
    featured_today: boolean;
    booster_id: string | null;
    force_min_rarity_id: string | null;
    force_min_rarity_name: string | null;
    rarity_weight_multiplier: number | null;
    character_id: string | null;
    character_name: string | null;
    rarity_id: string | null;
    rarity_name: string | null;
    quality_id: string | null;
    quality_name: string | null;
    specialty_id: string | null;
    specialty_name: string | null;
    jewelry_id: string | null;
    jewelry_name: string | null;
    reroll_rarity: boolean;
    reroll_quality: boolean;
    reroll_specialty: boolean;
    reroll_jewelry: boolean;
    reroll_mode: "random" | "guaranteed_min" | null;
}

export interface DailyFeature {
    feature_date: string;
    offer_id: string;
    offer_name: string;
}

export interface CharacterSetLink {
    set_id: string;
    weight: number;
}

export interface AdminCharacter {
    id: string;
    name: string;
    description: string;
    type: string;
    gen: number;
    image_url: string;
    sets: CharacterSetLink[];
}

export interface TuningEntry {
    id: string;
    name: string;
    weight: number | null;
}

export interface Tuning {
    rarities: TuningEntry[];
    qualities: TuningEntry[];
    specialties: TuningEntry[];
    jewelries: TuningEntry[];
}
