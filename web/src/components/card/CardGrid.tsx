import { useRef, useState } from "react";
import type { Card, CardGroup } from "@/types/card";
import CardImage from "./CardImage";
import CardDetail from "./CardDetail";
import CopyPickerModal from "./CopyPickerModal";

interface CardGridProps {
    groups: CardGroup[];
    /** Mode sélection (cadeau, échange...) : tapoter une carte la coche au
     * lieu d'ouvrir son détail. `excludeIds` = exemplaires déjà engagés
     * ailleurs (non sélectionnables) ; `selectedCards` = choisis dans CETTE
     * sélection (togglables) ; `onToggle` reçoit l'id + un aperçu de la carte. */
    selectionMode?: boolean;
    excludeIds?: Set<string>;
    selectedIds?: Set<string>;
    onToggle?: (cardId: string, preview: Card) => void;
}

export default function CardGrid({
    groups, selectionMode, excludeIds, selectedIds, onToggle,
}: CardGridProps) {
    // Sélection par id de carte (pas par index) : la liste peut se ré-trier.
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const selected = groups.find((g) => g.card.id === selectedId) ?? null;
    const [pickerGroup, setPickerGroup] = useState<CardGroup | null>(null);
    // Mode sélection : appui long (ou clic droit) = voir le détail sans cocher.
    const [peek, setPeek] = useState<CardGroup | null>(null);
    const pressTimer = useRef<number | null>(null);
    const longPressed = useRef(false);
    const startPress = (g: CardGroup) => {
        if (!selectionMode) return;
        longPressed.current = false;
        pressTimer.current = window.setTimeout(() => { longPressed.current = true; setPeek(g); }, 450);
    };
    const endPress = () => {
        if (pressTimer.current) window.clearTimeout(pressTimer.current);
        pressTimer.current = null;
    };

    const handleTap = (g: CardGroup) => {
        if (longPressed.current) {  // l'appui long a déjà ouvert le détail
            longPressed.current = false;
            return;
        }
        if (!selectionMode) {
            setSelectedId(g.card.id);
            return;
        }
        if (g.quantity > 1) {
            setPickerGroup(g);
        } else {
            onToggle?.(g.card.id, g.card);
        }
    };

    return (
        <>
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-3 px-2">
                {groups.map((g) => {
                    const isSingleSelected = selectionMode && g.quantity === 1 && selectedIds?.has(g.card.id);
                    const isSingleExcluded = selectionMode && g.quantity === 1 && excludeIds?.has(g.card.id);
                    return (
                        <div key={g.card.id} className="relative select-none"
                            onPointerDown={() => startPress(g)} onPointerUp={endPress} onPointerLeave={endPress}
                            onPointerCancel={endPress}
                            onContextMenu={(e) => { if (selectionMode) { e.preventDefault(); endPress(); setPeek(g); } }}>
                            <div className={isSingleSelected ? "ring-2 ring-accent rounded-xl" : undefined}>
                                <CardImage
                                    card={g.card}
                                    size="sm"
                                    onClick={isSingleExcluded ? undefined : () => handleTap(g)}
                                    className={isSingleExcluded ? "opacity-30 pointer-events-none" : undefined}
                                />
                            </div>
                            {(!!g.favorite_colors?.length || !!g.locked_count) && (
                                <div className="absolute -top-1 -left-1 flex items-center gap-0.5 bg-game-bg/80 rounded-full px-1 py-0.5 pointer-events-none">
                                    {g.favorite_colors?.slice(0, 4).map((c) => (
                                        <span key={c} className="w-2.5 h-2.5 rounded-full border border-black/40" style={{ background: c }} />
                                    ))}
                                    {!!g.locked_count && <span className="text-[9px] leading-none">🔒</span>}
                                </div>
                            )}
                            {g.quantity > 1 && (
                                <span className="absolute -top-1 -right-1 bg-gold text-game-bg
                             text-xs font-bold rounded-full w-5 h-5
                             flex items-center justify-center">
                                    {g.quantity}
                                </span>
                            )}
                        </div>
                    );
                })}
            </div>

            {!selectionMode && (
                <CardDetail
                    open={!!selected}
                    card={selected?.card ?? null}
                    quantity={selected?.quantity}
                    canRecycle
                    onClose={() => setSelectedId(null)}
                />
            )}

            {selectionMode && (
                <CardDetail
                    open={!!peek}
                    card={peek?.card ?? null}
                    quantity={peek?.quantity}
                    readOnly
                    onClose={() => setPeek(null)}
                />
            )}

            {selectionMode && pickerGroup && (
                <CopyPickerModal
                    group={pickerGroup}
                    excludeIds={excludeIds ?? new Set()}
                    selectedIds={selectedIds}
                    onToggle={(id, preview) => onToggle?.(id, preview)}
                    onClose={() => setPickerGroup(null)}
                />
            )}
        </>
    );
}
