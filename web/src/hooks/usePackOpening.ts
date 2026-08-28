import { useMutation, useQueryClient } from "@tanstack/react-query";
import { boostersApi } from "@/api/boosters";
import { useAuthStore } from "@/stores/authStore";
import { useGameStore } from "@/stores/gameStore";
import type { PackOpenRequest } from "@/types/booster";

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
