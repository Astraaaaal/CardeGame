import { create } from "zustand";
import type { Card } from "@/types/card";
import type { Booster } from "@/types/booster";

interface GameState {
    // Pack opening state
    currentPacks: Card[][] | null;
    currentPackIndex: number;
    currentCardIndex: number;
    isRevealing: boolean;

    // Selected booster
    selectedBooster: Booster | null;

    // Actions
    setPacks: (packs: Card[][]) => void;
    nextCard: () => boolean;
    nextPack: () => boolean;
    skipToEnd: () => void;
    setRevealing: (v: boolean) => void;
    setSelectedBooster: (b: Booster | null) => void;
    resetPackState: () => void;
}

export const useGameStore = create<GameState>()((set, get) => ({
    currentPacks: null,
    currentPackIndex: 0,
    currentCardIndex: 0,
    isRevealing: false,
    selectedBooster: null,

    setPacks: (packs) =>
        set({
            currentPacks: packs,
            currentPackIndex: 0,
            currentCardIndex: 0,
            isRevealing: true,
        }),

    nextCard: () => {
        const { currentPacks, currentPackIndex, currentCardIndex } = get();
        if (!currentPacks) return false;
        const pack = currentPacks[currentPackIndex];
        if (currentCardIndex < pack.length - 1) {
            set({ currentCardIndex: currentCardIndex + 1 });
            return true;
        }
        return false;
    },

    nextPack: () => {
        const { currentPacks, currentPackIndex } = get();
        if (!currentPacks) return false;
        if (currentPackIndex < currentPacks.length - 1) {
            set({ currentPackIndex: currentPackIndex + 1, currentCardIndex: 0 });
            return true;
        }
        set({ isRevealing: false });
        return false;
    },

    skipToEnd: () => {
        set({ isRevealing: false });
    },

    setRevealing: (v) => set({ isRevealing: v }),
    setSelectedBooster: (b) => set({ selectedBooster: b }),

    resetPackState: () =>
        set({
            currentPacks: null,
            currentPackIndex: 0,
            currentCardIndex: 0,
            isRevealing: false,
        }),
}));
