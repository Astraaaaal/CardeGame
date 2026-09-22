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

export function useProbabilities(enabled: boolean) {
    return useQuery({
        queryKey: ["probabilities"],
        queryFn: collectionApi.getProbabilities,
        enabled,
        staleTime: 5 * 60_000, // change rarement (réglages admin)
    });
}
