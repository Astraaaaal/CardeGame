import { useQuery } from "@tanstack/react-query";
import { boostersApi } from "@/api/boosters";

export function useBoosters() {
    return useQuery({
        queryKey: ["boosters"],
        queryFn: boostersApi.list,
        staleTime: 5 * 60 * 1000, // 5 min
    });
}
