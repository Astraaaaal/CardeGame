import { useQuery } from "@tanstack/react-query";
import { shopApi } from "@/api/shop";

/** Nom de chaque ressource (catalogue public, mis en cache) : id → nom. */
export function useResourceNames(): Record<string, string> {
    const { data } = useQuery({ queryKey: ["resources-catalog"], queryFn: shopApi.resources, staleTime: 5 * 60 * 1000 });
    return Object.fromEntries((data ?? []).map((r) => [r.id, r.name]));
}
