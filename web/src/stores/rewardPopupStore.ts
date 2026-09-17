import { create } from "zustand";
import type { Card } from "@/types/card";
import type { TierAxis } from "@/utils/cardTiers";
import type { Cosmetic } from "@/types/premium";

export type RewardItem =
    | { kind: "resource"; resourceId: string; amount: number; name?: string | null }
    | { kind: "booster"; boosterId: string; quantity: number; name?: string | null }
    | { kind: "card"; card: Card }
    | { kind: "cosmetic"; cosmetic: Cosmetic }
    /** Reroll : caractéristiques retirées, avant → après (+ puissance). */
    | { kind: "reroll"; before: Card; after: Card; axes: TierAxis[] }
    /** Reroll gardé en inventaire. */
    | { kind: "reroll_token"; name: string; quantity: number };

export interface RewardBatch {
    title: string;
    items: RewardItem[];
    /** Bouton secondaire (ex. « Relancer encore ») : ferme le récapitulatif puis exécute l'action. */
    action?: { label: string; onClick: () => void };
}

/** File de récapitulatifs "ce que tu viens d'obtenir" (cf. RewardPopup). */
interface RewardPopupState {
    queue: RewardBatch[];
    show: (batch: RewardBatch) => void;
    dismiss: () => void;
}

export const useRewardPopupStore = create<RewardPopupState>()((set) => ({
    queue: [],
    show: (batch) => {
        const items = batch.items.filter((i) =>
            i.kind === "resource" ? i.amount > 0 : i.kind === "booster" ? i.quantity > 0 : true
        );
        if (items.length) set((s) => ({ queue: [...s.queue, { ...batch, items }] }));
    },
    dismiss: () => set((s) => ({ queue: s.queue.slice(1) })),
}));

export const showRewards = (batch: RewardBatch) => useRewardPopupStore.getState().show(batch);

/** Récompense "ressource et/ou booster" telle que décrite par la plupart des objets du jeu. */
export function rewardItems(r: {
    reward_resource_id?: string | null;
    reward_resource_name?: string | null;
    reward_amount?: number | null;
    reward_booster_id?: string | null;
    reward_booster_name?: string | null;
    reward_booster_qty?: number | null;
}): RewardItem[] {
    const items: RewardItem[] = [];
    if (r.reward_resource_id && r.reward_amount) {
        items.push({ kind: "resource", resourceId: r.reward_resource_id, amount: r.reward_amount, name: r.reward_resource_name });
    }
    if (r.reward_booster_id) {
        items.push({ kind: "booster", boosterId: r.reward_booster_id, quantity: r.reward_booster_qty ?? 1, name: r.reward_booster_name });
    }
    return items;
}
