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
    set_id: string;
    cards_count: number;
    price: number;
    guaranteed_rare: boolean;
    description: string;
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
