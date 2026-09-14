import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { collectionApi } from "@/api/collection";
import type { Card, CardGroup } from "@/types/card";
import Modal from "@/components/ui/Modal";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import CardImage from "@/components/card/CardImage";

interface AddCardModalProps {
    excludeIds: Set<string>;
    onPick: (cardId: string, preview: Card) => void;
    onClose: () => void;
}

/** Sélection d'une carte précise (exemplaire, pas juste la combinaison) à
 * apporter dans une session d'échange — la puissance diffère par exemplaire,
 * donc un groupe avec plusieurs copies demande de choisir laquelle. */
export default function AddCardModal({ excludeIds, onPick, onClose }: AddCardModalProps) {
    const [group, setGroup] = useState<CardGroup | null>(null);

    const { data, isLoading } = useQuery({
        queryKey: ["collection", { sort_by: "rarity" }],
        queryFn: () => collectionApi.getCollection({ sort_by: "rarity" }),
    });

    const copiesQ = useQuery({
        queryKey: ["card-copies", group && {
            character_id: group.card.character_id, rarity_id: group.card.rarity_id,
            quality_id: group.card.quality_id, specialty_id: group.card.specialty_id,
            jewelry_id: group.card.jewelry_id,
        }],
        queryFn: () => collectionApi.getCardCopies({
            character_id: group!.card.character_id, rarity_id: group!.card.rarity_id,
            quality_id: group!.card.quality_id, specialty_id: group!.card.specialty_id,
            jewelry_id: group!.card.jewelry_id,
        }),
        enabled: !!group,
    });

    const availableCopies = (copiesQ.data?.copies ?? []).filter((c) => !excludeIds.has(c.id));

    if (group) {
        return (
            <Modal open onClose={() => setGroup(null)} title={`${group.card.character_name} — choisis l'exemplaire`}>
                {copiesQ.isLoading ? (
                    <LoadingSpinner text="Chargement..." />
                ) : availableCopies.length === 0 ? (
                    <p className="text-white/40 text-sm text-center py-6">
                        Tous les exemplaires de cette carte sont déjà dans l'échange.
                    </p>
                ) : (
                    <div className="grid grid-cols-3 gap-3 max-h-[55vh] overflow-y-auto">
                        {availableCopies.map((c) => {
                            const preview = { ...group.card, id: c.id, power: c.power };
                            return (
                                <button
                                    key={c.id}
                                    className="flex flex-col items-center gap-1"
                                    onClick={() => onPick(c.id, preview)}
                                >
                                    <CardImage card={preview} size="sm" />
                                    {c.power != null && (
                                        <span className="text-gold text-xs font-semibold">⚡{c.power}</span>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                )}
            </Modal>
        );
    }

    return (
        <Modal open onClose={onClose} title="Ajoute une carte">
            {isLoading ? (
                <LoadingSpinner text="Chargement..." />
            ) : (
                <div className="grid grid-cols-3 gap-2 max-h-[60vh] overflow-y-auto">
                    {(data?.groups ?? []).map((g) => (
                        <button key={g.card.id} onClick={() => setGroup(g)}>
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
