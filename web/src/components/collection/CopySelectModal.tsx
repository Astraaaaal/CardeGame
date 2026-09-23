import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import type { CardGroup } from "@/types/card";
import { useQuery } from "@tanstack/react-query";
import { favoritesApi } from "@/api/favorites";
import { FAVORITES_KEY } from "./FavoritesManager";
import { isFavorite } from "@/utils/recycleSelection";

interface CopySelectModalProps {
    group: CardGroup;
    selectedIds: Set<string>;
    /** Coche ou décoche cet exemplaire précis. */
    onToggle: (id: string) => void;
    onClose: () => void;
}

/**
 * Réglage fin du mode recyclage : choisir exemplaire par exemplaire dans une
 * carte possédée en plusieurs exemplaires (ouvert par appui long sur la carte).
 * Les exemplaires verrouillés sont affichés mais impossibles à cocher.
 */
export default function CopySelectModal({ group, selectedIds, onToggle, onClose }: CopySelectModalProps) {
    const { data: categories } = useQuery({ queryKey: FAVORITES_KEY, queryFn: favoritesApi.list });
    const copies = group.copies ?? [];
    const selectable = copies.filter((c) => !c.locked);
    const allSelected = selectable.length > 0 && selectable.every((c) => selectedIds.has(c.id));

    return (
        <Modal open onClose={onClose} title={group.card.character_name}>
            <div className="space-y-3">
                <p className="text-white/40 text-[11px]">
                    {copies.length} exemplaire{copies.length > 1 ? "s" : ""}, du plus puissant au moins puissant.
                </p>

                <div className="max-h-64 overflow-y-auto space-y-1">
                    {copies.map((copy, index) => (
                        <label key={copy.id}
                            className={`flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm ${
                                copy.locked ? "bg-white/5 text-white/30" : "bg-white/5 text-white/80 cursor-pointer"}`}>
                            <input type="checkbox" disabled={copy.locked}
                                checked={selectedIds.has(copy.id)}
                                onChange={() => onToggle(copy.id)} />
                            <span className="tabular-nums">{copy.power != null ? `⚡ ${copy.power}` : "—"}</span>
                            {index === 0 && <span className="text-gold text-[10px]">meilleur</span>}
                            {copy.locked && <span className="text-[11px]">🔒</span>}
                            <span className="ml-auto flex items-center gap-1">
                                {copy.favorite_ids.map((id) => {
                                    const category = categories?.find((c) => c.id === id);
                                    return category ? (
                                        <span key={id} className="w-2.5 h-2.5 rounded-full border border-black/40"
                                            title={category.name} style={{ background: category.color }} />
                                    ) : null;
                                })}
                            </span>
                        </label>
                    ))}
                </div>

                {copies.some(isFavorite) && (
                    <p className="text-amber-300/70 text-[11px]">
                        Des exemplaires sont rangés dans tes favoris : les outils de sélection rapide les épargnent.
                    </p>
                )}

                <div className="flex gap-2">
                    <Button variant="secondary" className="flex-1"
                        onClick={() => selectable.forEach((c) => {
                            const picked = selectedIds.has(c.id);
                            if (allSelected ? picked : !picked) onToggle(c.id);
                        })}>
                        {allSelected ? "Tout décocher" : "Tout cocher"}
                    </Button>
                    <Button className="flex-1" onClick={onClose}>Terminé</Button>
                </div>
            </div>
        </Modal>
    );
}
