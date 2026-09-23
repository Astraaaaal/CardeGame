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
    power: number | null;
    combined_rarity: number | null;
    rendered_url: string | null;
    obtained_at: string | null;
    booster_id: string | null;
    booster_name: string | null;
    booster_cover_url: string | null;
}

/** Un exemplaire précis d'une combinaison possédée. */
export interface CardCopy {
    id: string;
    power: number | null;
    locked: boolean;
    favorite_ids: number[];
}

export interface CardGroup {
    card: Card;
    quantity: number;
    /** Couleurs des catégories de favoris où figure au moins un exemplaire. */
    favorite_colors?: string[];
    /** Exemplaires verrouillés (protégés du recyclage). */
    locked_count?: number;
    /** Détail des exemplaires affichés (mode recyclage : `with_copies`),
     *  du plus puissant au moins puissant. */
    copies?: CardCopy[];
}
