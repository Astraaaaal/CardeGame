import { useQuery } from "@tanstack/react-query";
import { collectionApi } from "@/api/collection";
import type { Card, CardGroup } from "@/types/card";
import Modal from "@/components/ui/Modal";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import CardImage from "@/components/card/CardImage";

interface CopyPickerModalProps {
    group: CardGroup;
    excludeIds: Set<string>;
    /** Exemplaires déjà choisis ailleurs dans la sélection en cours — affichés
     * marqués, et un clic dessus les retire au lieu d'en ajouter un nouveau. */
    selectedIds?: Set<string>;
    onToggle: (cardId: string, preview: Card) => void;
    onClose: () => void;
}

/** Choisit un exemplaire précis (pas juste la combinaison) d'un groupe de
 * la collection — la puissance diffère par exemplaire, donc un groupe avec
 * plusieurs copies demande de préciser laquelle. */
export default function CopyPickerModal({ group, excludeIds, selectedIds, onToggle, onClose }: CopyPickerModalProps) {
    const copiesQ = useQuery({
        queryKey: ["card-copies", {
            character_id: group.card.character_id, rarity_id: group.card.rarity_id,
            quality_id: group.card.quality_id, specialty_id: group.card.specialty_id,
            jewelry_id: group.card.jewelry_id,
        }],
        queryFn: () => collectionApi.getCardCopies({
            character_id: group.card.character_id, rarity_id: group.card.rarity_id,
            quality_id: group.card.quality_id, specialty_id: group.card.specialty_id,
            jewelry_id: group.card.jewelry_id,
        }),
    });

    const availableCopies = (copiesQ.data?.copies ?? []).filter((c) => !excludeIds.has(c.id));

    return (
        <Modal open onClose={onClose} title={`${group.card.character_name} — choisis l'exemplaire`}>
            {copiesQ.isLoading ? (
                <LoadingSpinner text="Chargement..." />
            ) : availableCopies.length === 0 ? (
                <p className="text-white/40 text-sm text-center py-6">
                    Tous les exemplaires de cette carte sont déjà pris.
                </p>
            ) : (
                <div className="grid grid-cols-3 gap-3 max-h-[55vh] overflow-y-auto">
                    {availableCopies.map((c) => {
                        const preview = { ...group.card, id: c.id, power: c.power };
                        const isSelected = selectedIds?.has(c.id);
                        return (
                            <button
                                key={c.id}
                                className={`flex flex-col items-center gap-1 rounded-lg ${isSelected ? "ring-2 ring-accent" : ""}`}
                                onClick={() => onToggle(c.id, preview)}
                            >
                                <div className="relative w-full">
                                    <CardImage card={preview} size="sm" />
                                </div>
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
