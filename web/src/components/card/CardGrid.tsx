import { memo, useCallback, useEffect, useRef, useState } from "react";
import type { Card, CardGroup } from "@/types/card";
import CardImage from "./CardImage";
import CardDetail from "./CardDetail";
import CopyPickerModal from "./CopyPickerModal";

// Combien de cartes on peint d'un coup, et de combien on avance ensuite. Une
// collection fournie dépasse vite le millier de vignettes : les peindre toutes
// à l'ouverture fige l'écran une seconde, alors que l'écran n'en montre qu'une
// douzaine. Le reste arrive quand on descend.
const PREMIER_LOT = 100;
const LOT_SUIVANT = 60;

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
    /** Mode recyclage : tapoter prend TOUS les exemplaires affichés de la carte
     * (sauf verrouillés), appui long ouvre le réglage exemplaire par exemplaire.
     * `recycleSelected` = exemplaires cochés, pour l'état visuel de la grille. */
    recycleMode?: boolean;
    recycleSelected?: Set<string>;
    onRecycleToggleGroup?: (group: CardGroup) => void;
    onRecycleOpenCopies?: (group: CardGroup) => void;
}

interface TuileProps {
    group: CardGroup;
    selected: boolean;
    excluded: boolean;
    pickedCount: number;
    fullyPicked: boolean;
    interactive: boolean;
    onTap: (g: CardGroup) => void;
    onPressStart: (g: CardGroup) => void;
    onPressEnd: () => void;
    onPeek: (g: CardGroup) => void;
}

/** Une vignette. Mémoïsée : sans ça, ouvrir le détail d'une carte re-rendait
 * les mille autres, avec leurs dégradés et leurs ombres — l'ouverture
 * paraissait lente alors que c'est la grille entière qui se repeignait. */
const Tuile = memo(function Tuile({
    group: g, selected, excluded, pickedCount, fullyPicked, interactive,
    onTap, onPressStart, onPressEnd, onPeek,
}: TuileProps) {
    return (
        <div className="relative select-none"
            onPointerDown={() => onPressStart(g)} onPointerUp={onPressEnd} onPointerLeave={onPressEnd}
            onPointerCancel={onPressEnd}
            onContextMenu={(e) => { if (interactive) { e.preventDefault(); onPressEnd(); onPeek(g); } }}>
            <div className={
                selected || fullyPicked ? "ring-2 ring-accent rounded-xl"
                    : pickedCount > 0 ? "ring-2 ring-accent/50 rounded-xl" : undefined}>
                <CardImage
                    card={g.card}
                    size="sm"
                    onClick={excluded ? undefined : () => onTap(g)}
                    className={excluded ? "opacity-30 pointer-events-none" : undefined}
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
            {/* Mode recyclage : combien d'exemplaires partent au recyclage. */}
            {pickedCount > 0 && (
                <span className="absolute bottom-1 right-1 bg-accent text-white text-[10px] font-bold
                                    rounded-full px-1.5 py-0.5 pointer-events-none">
                    {pickedCount === g.quantity ? "♻" : `♻ ${pickedCount}/${g.quantity}`}
                </span>
            )}
        </div>
    );
});

export default function CardGrid({
    groups, selectionMode, excludeIds, selectedIds, onToggle,
    recycleMode, recycleSelected, onRecycleToggleGroup, onRecycleOpenCopies,
}: CardGridProps) {
    // Sélection par id de carte (pas par index) : la liste peut se ré-trier.
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const selected = groups.find((g) => g.card.id === selectedId) ?? null;
    const [pickerGroup, setPickerGroup] = useState<CardGroup | null>(null);
    // Mode sélection : appui long (ou clic droit) = voir le détail sans cocher.
    const [peek, setPeek] = useState<CardGroup | null>(null);
    const pressTimer = useRef<number | null>(null);
    const longPressed = useRef(false);

    // Les gestionnaires passent à des vignettes mémoïsées : ils doivent garder
    // la même identité d'un rendu à l'autre, sinon la mémoïsation ne sert à rien.
    const startPress = useCallback((g: CardGroup) => {
        if (!selectionMode && !recycleMode) return;
        longPressed.current = false;
        pressTimer.current = window.setTimeout(() => {
            longPressed.current = true;
            if (recycleMode) onRecycleOpenCopies?.(g);
            else setPeek(g);
        }, 450);
    }, [selectionMode, recycleMode, onRecycleOpenCopies]);

    const endPress = useCallback(() => {
        if (pressTimer.current) window.clearTimeout(pressTimer.current);
        pressTimer.current = null;
    }, []);

    const handleTap = useCallback((g: CardGroup) => {
        if (longPressed.current) {  // l'appui long a déjà ouvert le détail
            longPressed.current = false;
            return;
        }
        if (recycleMode) {
            onRecycleToggleGroup?.(g);
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
    }, [recycleMode, selectionMode, onRecycleToggleGroup, onToggle]);

    // Rendu progressif : un premier lot, puis la suite quand la sentinelle du
    // bas entre dans le champ. Le compteur repart à chaque changement de liste
    // (tri, filtre), sinon un filtre restrictif garderait un lot déjà grand.
    const [visibles, setVisibles] = useState(PREMIER_LOT);
    const sentinelle = useRef<HTMLDivElement | null>(null);
    // On suit le CONTENU, pas l'identité du tableau : un appelant qui recrée sa
    // liste à chaque rendu remettrait sinon le compteur à zéro sans arrêt. La
    // taille et la première carte changent dès qu'on trie ou qu'on filtre.
    const signature = `${groups.length}|${groups[0]?.card.id ?? ""}`;
    useEffect(() => setVisibles(PREMIER_LOT), [signature]);
    useEffect(() => {
        const cible = sentinelle.current;
        if (!cible || visibles >= groups.length) return;
        const observateur = new IntersectionObserver((entrees) => {
            if (entrees.some((e) => e.isIntersecting)) {
                setVisibles((n) => Math.min(n + LOT_SUIVANT, groups.length));
            }
        }, { rootMargin: "600px" });  // on précharge avant d'arriver au bord
        observateur.observe(cible);
        return () => observateur.disconnect();
    }, [visibles, groups.length]);

    return (
        <>
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-3 px-2">
                {groups.slice(0, visibles).map((g) => {
                    const pickedCount = recycleMode
                        ? (g.copies ?? []).filter((c) => recycleSelected?.has(c.id)).length : 0;
                    return (
                        <Tuile
                            key={g.card.id}
                            group={g}
                            selected={!!(selectionMode && g.quantity === 1 && selectedIds?.has(g.card.id))}
                            excluded={!!(selectionMode && g.quantity === 1 && excludeIds?.has(g.card.id))}
                            pickedCount={pickedCount}
                            fullyPicked={!!recycleMode && pickedCount > 0 && pickedCount === g.quantity}
                            interactive={!!selectionMode}
                            onTap={handleTap}
                            onPressStart={startPress}
                            onPressEnd={endPress}
                            onPeek={setPeek}
                        />
                    );
                })}
            </div>
            {visibles < groups.length && (
                <div ref={sentinelle} className="py-6 text-center text-white/30 text-xs">
                    {groups.length - visibles} carte(s) de plus…
                </div>
            )}

            {!selectionMode && !recycleMode && (
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
