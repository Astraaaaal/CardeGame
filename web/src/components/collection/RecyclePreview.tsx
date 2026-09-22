import { useQuery } from "@tanstack/react-query";
import { collectionApi } from "@/api/collection";
import ResourceIcon from "@/components/ui/ResourceIcon";
import { formatNumber } from "@/utils/format";

/** Ce que rapportera le recyclage de ces exemplaires (calculé par le serveur). */
export default function RecyclePreview({ cardIds }: { cardIds: string[] }) {
    const { data, isLoading, isError } = useQuery({
        queryKey: ["recycle-preview", [...cardIds].sort()],
        queryFn: () => collectionApi.recyclePreview({ card_ids: cardIds }),
        enabled: cardIds.length > 0,
        staleTime: 30_000,
    });
    if (!cardIds.length) return null;
    return (
        <div className="bg-black/20 rounded-lg px-3 py-2 mb-2">
            <p className="text-white/40 text-[11px] mb-1.5">Tu vas recevoir :</p>
            {isLoading && <p className="text-white/40 text-xs">Calcul…</p>}
            {isError && <p className="text-red-400 text-xs">Aperçu indisponible.</p>}
            <div className="flex flex-wrap gap-x-3 gap-y-1">
                {data?.gains.map((g) => (
                    <span key={g.resource_id} className="inline-flex items-center gap-1 text-sm text-white">
                        <ResourceIcon resourceId={g.resource_id} className="w-4 h-4" />
                        <span className="font-semibold tabular-nums">{formatNumber(g.amount)}</span>
                        <span className="text-white/50 text-xs">{g.name}</span>
                    </span>
                ))}
            </div>
        </div>
    );
}
