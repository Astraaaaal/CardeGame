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
    price: number;
    guaranteed_rare: boolean;
    description: string;
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
}

export interface AdminShopOffer {
    id: string;
    kind: "booster" | "specific_card" | "upgrade";
    name: string;
    description: string;
    active: boolean;
    resource_id: string;
    resource_name: string;
    price: number;
    booster_id: string | null;
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
    target_quality_id: string | null;
    target_quality_name: string | null;
    target_specialty_id: string | null;
    target_specialty_name: string | null;
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
