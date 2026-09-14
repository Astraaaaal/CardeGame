import { create } from "zustand";
import type { Card } from "@/types/card";

/**
 * Sélection de carte(s) réutilisable — plutôt que de scroller dans une
 * mini-liste ad hoc à chaque endroit qui a besoin d'une carte (cadeau,
 * échange...), on envoie l'utilisateur sur la vraie page Collection (avec
 * tous ses outils de recherche/tri/filtre) en "mode sélection", puis on le
 * ramène là où il était avec les cartes choisies.
 *
 * `context` est un sac libre de chaînes que l'appelant utilise pour se
 * retrouver au retour (ex: { purpose: "gift", presetUsername: "bob" }) —
 * il transite tel quel jusqu'au résultat.
 */
export interface CardSelectionRequest {
    max: number;
    title: string;
    excludeIds: string[];
    returnTo: string;
    context?: Record<string, string>;
}

export interface SelectedCard {
    id: string;
    preview: Card;
}

export interface CardSelectionResult {
    selectedCards: SelectedCard[];
    context?: Record<string, string>;
}

interface CardSelectionState {
    request: CardSelectionRequest | null;
    result: CardSelectionResult | null;

    requestSelection: (req: CardSelectionRequest) => void;
    resolveSelection: (cards: SelectedCard[]) => void;
    cancelSelection: () => void;
    consumeResult: () => CardSelectionResult | null;
}

export const useCardSelectionStore = create<CardSelectionState>()((set, get) => ({
    request: null,
    result: null,

    requestSelection: (req) => set({ request: req, result: null }),

    resolveSelection: (cards) => {
        const context = get().request?.context;
        set({ request: null, result: { selectedCards: cards, context } });
    },

    cancelSelection: () => set({ request: null }),

    consumeResult: () => {
        const result = get().result;
        if (result) set({ result: null });
        return result;
    },
}));
