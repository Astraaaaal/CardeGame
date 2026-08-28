export interface Card {
    id: string;
    character_id: string;
    character_name: string;
    character_type: string;
    character_description: string;
    gen: number;
    image_url: string;
    set_id: string;
    set_name: string;
    rarity_id: string;
    rarity_name: string;
    rarity_color: number[];
    quality_id: string;
    quality_name: string;
    specialty_id: string;
    specialty_name: string;
    jewelry_id: string;
    jewelry_name: string;
    jewelry_color: number[];
    drop_probability: number;
    rendered_url: string | null;
    obtained_at: string | null;
}

export interface CardGroup {
    card: Card;
    quantity: number;
}
