import { useQuery } from "@tanstack/react-query";
import { friendsApi } from "@/api/friends";
import { useAuthStore } from "@/stores/authStore";

export const TRADE_PULSE_KEY = ["trade-pulse"];

/** État des échanges interrogé en continu — une seule requête partagée par
 * tous les composants qui l'utilisent (même clé de cache). */
export function useTradePulse() {
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
    return useQuery({
        queryKey: TRADE_PULSE_KEY,
        queryFn: friendsApi.tradePulse,
        enabled: isAuthenticated,
        refetchInterval: 4000,
    });
}

/** Une proposition envoyée attend une réponse : on peut être tiré dans
 * l'échange à tout moment, donc pas d'animation à lancer. */
export function useHasPendingTradeProposal() {
    const { data } = useTradePulse();
    return (data?.outgoing_ids.length ?? 0) > 0;
}
