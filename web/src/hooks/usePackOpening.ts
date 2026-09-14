import { useMutation, useQueryClient } from "@tanstack/react-query";
import { boostersApi } from "@/api/boosters";
import { useAuthStore } from "@/stores/authStore";
import { useGameStore } from "@/stores/gameStore";
import type { PackOpenRequest, OpenOwnedRequest } from "@/types/booster";

export function usePackOpening() {
    const queryClient = useQueryClient();
    const { updateCoins } = useAuthStore();
    const { setPacks } = useGameStore();

    return useMutation({
        mutationFn: (data: PackOpenRequest) => boostersApi.openPacks(data),
        onSuccess: (result) => {
            updateCoins(result.remaining_coins);
            setPacks(result.packs);
            // Invalider la collection après ouverture
            queryClient.invalidateQueries({ queryKey: ["collection"] });
            queryClient.invalidateQueries({ queryKey: ["player"] });
        },
    });
}

/** Ouvre des boosters déjà possédés (récompenses non réclamées en cartes
 * directement) — gratuit, réutilise le même écran/animation de révélation. */
export function useOpenOwnedBoosters() {
    const queryClient = useQueryClient();
    const { setPacks } = useGameStore();

    return useMutation({
        mutationFn: (data: OpenOwnedRequest) => boostersApi.openOwned(data),
        onSuccess: (result) => {
            setPacks(result.packs);
            queryClient.invalidateQueries({ queryKey: ["collection"] });
            queryClient.invalidateQueries({ queryKey: ["player"] });
            queryClient.invalidateQueries({ queryKey: ["booster-inventory"] });
        },
    });
}
