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
    /**
     * Variante sûre pour plusieurs consommateurs potentiels montés en même
     * temps (ex: ShowcaseEditor + TradeListingsEditor, tous deux sur l'onglet
     * Vitrine) : ne consomme (et ne vide donc le store) QUE si le résultat en
     * attente correspond à l'un des `purposes` donnés — sinon le laisse
     * intact pour l'autre composant susceptible de le consommer, lui.
     * `consumeResult()` seul est destructif même en cas de non-correspondance
     * (il vide le store dès l'appel), d'où la course si deux composants
     * l'appellent chacun sans vérifier avant de consommer.
     */
    consumeResultIfPurpose: (purposes: string[]) => CardSelectionResult | null;
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

    consumeResultIfPurpose: (purposes) => {
        const result = get().result;
        if (!result || !result.context?.purpose || !purposes.includes(result.context.purpose)) return null;
        set({ result: null });
        return result;
    },
}));
