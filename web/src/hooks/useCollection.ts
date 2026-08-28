import { useQuery } from "@tanstack/react-query";
import { collectionApi, type CollectionParams } from "@/api/collection";

export function useCollection(params?: CollectionParams) {
    return useQuery({
        queryKey: ["collection", params],
        queryFn: () => collectionApi.getCollection(params),
        staleTime: 30_000, // 30 secondes
    });
}

export function useCardDetail(cardId: string | null) {
    return useQuery({
        queryKey: ["card", cardId],
        queryFn: () => collectionApi.getCardDetail(cardId!),
        enabled: !!cardId,
    });
}
