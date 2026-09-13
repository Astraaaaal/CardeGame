import { useQuery } from "@tanstack/react-query";
import { collectionApi } from "@/api/collection";
import Modal from "@/components/ui/Modal";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import CardImage from "@/components/card/CardImage";

/** Sélecteur d'une carte possédée — utilisé par le shop (reroll) et la vitrine du profil. */
export default function CardPickerModal({
    title = "Choisis une carte",
    onPick, onClose,
}: { title?: string; onPick: (cardId: string) => void; onClose: () => void }) {
    const { data, isLoading } = useQuery({
        queryKey: ["collection", { sort_by: "rarity" }],
        queryFn: () => collectionApi.getCollection({ sort_by: "rarity" }),
    });

    return (
        <Modal open onClose={onClose} title={title}>
            {isLoading ? (
                <LoadingSpinner text="Chargement..." />
            ) : (
                <div className="grid grid-cols-3 gap-2 max-h-[60vh] overflow-y-auto">
                    {(data?.groups ?? []).map((g) => (
                        <button key={g.card.id} onClick={() => onPick(g.card.id)}>
                            <CardImage card={g.card} size="sm" />
                        </button>
                    ))}
                    {data && data.groups.length === 0 && (
                        <p className="col-span-3 text-white/40 text-sm text-center py-6">
                            Aucune carte dans ta collection.
                        </p>
                    )}
                </div>
            )}
        </Modal>
    );
}
