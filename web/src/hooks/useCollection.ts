import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { collectionApi, type CollectionParams } from "@/api/collection";

export function useCollection(params?: CollectionParams) {
    return useQuery({
        queryKey: ["collection", params],
        queryFn: () => collectionApi.getCollection(params),
        staleTime: 30_000, // 30 secondes
        // Garde la grille affichée pendant qu'un nouveau tri charge (surtout utile
        // quand l'API est lente : cold start Render). Sinon la grille disparaît.
        placeholderData: keepPreviousData,
    });
}

export function useCardDetail(cardId: string | null) {
    return useQuery({
        queryKey: ["card", cardId],
        queryFn: () => collectionApi.getCardDetail(cardId!),
        enabled: !!cardId,
    });
}
