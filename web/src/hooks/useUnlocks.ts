import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";

export type FeatureKey =
    | "workshop" | "absence_chest" | "leaderboard" | "expeditions" | "resource_shop" | "gifts" | "wheel"
    | "trades" | "guild_join" | "presence_luck" | "higher_lower" | "rerolls" | "listings" | "converter"
    | "machine" | "guild_create" | "showcase";

export interface UnlocksStatus {
    level: number;
    features: Record<FeatureKey, { label: string; level: number; unlocked: boolean }>;
}

export const UNLOCKS_KEY = ["unlocks"];

/** Plus haut niveau atteint et déblocage de chaque fonctionnalité (cf. backend services/unlocks.py). */
export function useUnlocks() {
    const { data } = useQuery({
        queryKey: UNLOCKS_KEY,
        queryFn: () => api.get<UnlocksStatus>("/player/unlocks").then((r) => r.data),
        staleTime: 15_000,
    });
    return {
        data,
        level: data?.level ?? 1,
        // Tant que l'état n'est pas chargé, on n'affiche pas de cadenas (le serveur tranche de toute façon).
        isUnlocked: (key: FeatureKey) => !data || data.features[key]?.unlocked !== false,
        levelFor: (key: FeatureKey) => data?.features[key]?.level ?? 1,
        labelFor: (key: FeatureKey) => data?.features[key]?.label ?? "",
    };
}
