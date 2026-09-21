import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Card } from "@/types/card";
import { collectionApi } from "@/api/collection";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import ConfirmModal from "@/components/ui/ConfirmModal";
import { CardWithEffects } from "./CardEffects";
import { errMsg } from "@/utils/errors";
import { showRewards } from "@/stores/rewardPopupStore";
import { favoritesApi } from "@/api/favorites";

interface CardDetailProps {
    open: boolean;
    card: Card | null;
    quantity?: number;
    onClose: () => void;
    /** Vue d'une carte qui n'appartient pas au joueur courant (vitrine d'un
     * autre profil) : cache les actions de gestion (recyclage), qui ne
     * s'appliqueraient de toute façon qu'à ses propres cartes. */
    readOnly?: boolean;
}

function rarityColorToCSS(color: number[]): string {
    return `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
}

/**
 * Reste toujours monté (comme Modal.tsx) et gère sa propre AnimatePresence
 * en interne, pilotée par `open` — plutôt que d'être conditionnellement
 * inséré/retiré par le parent (CardGrid), ce qui laissait parfois l'ancienne
 * instance bloquée en DOM (invisible mais toujours cliquable par-dessus la
 * grille) au lieu d'être proprement démontée après l'animation de sortie.
 * `card` peut rester non-null un instant après `open=false` : on garde la
 * dernière carte affichée (`lastCard`) pour que l'animation de fermeture
 * ait encore un contenu à afficher pendant qu'elle s'estompe.
 */
export default function CardDetail({ open, card, quantity, onClose, readOnly }: CardDetailProps) {
    const qc = useQueryClient();
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [result, setResult] = useState<string | null>(null);
    const [confirmingRecycle, setConfirmingRecycle] = useState(false);

    const [lastCard, setLastCard] = useState<Card | null>(card);
    const [lastQuantity, setLastQuantity] = useState<number | undefined>(quantity);
    useEffect(() => {
        if (card) {
            setLastCard(card);
            setLastQuantity(quantity);
            setSelectedIds(new Set());
            setResult(null);
            setFocusId(null);
        }
    }, [card, quantity]);

    // Exemplaire précis consulté depuis la liste des doublons (sa puissance,
    // sa date d'obtention...) ; sinon la carte telle qu'ouverte.
    const [focusId, setFocusId] = useState<string | null>(null);
    const baseCard = card ?? lastCard;
    const focusQ = useQuery({
        queryKey: ["card-detail", focusId],
        queryFn: () => collectionApi.getCardDetail(focusId!),
        enabled: !!focusId,
    });
    const displayCard = (focusId && focusQ.data) || baseCard;
    const owned = lastQuantity ?? 1;

    const copiesQ = useQuery({
        queryKey: ["card-copies", displayCard?.character_id, displayCard?.rarity_id, displayCard?.quality_id, displayCard?.specialty_id, displayCard?.jewelry_id],
        queryFn: () => collectionApi.getCardCopies({
            character_id: baseCard!.character_id,
            rarity_id: baseCard!.rarity_id,
            quality_id: baseCard!.quality_id,
            specialty_id: baseCard!.specialty_id,
            jewelry_id: baseCard!.jewelry_id,
        }),
        enabled: !!baseCard && !readOnly,
    });

    const recycleIds = (owned > 1 ? Array.from(selectedIds) : (displayCard ? [displayCard.id] : []))
        .filter((id) => !(copiesQ.data?.copies ?? []).some((c) => c.id === id && c.locked));

    const recycle = useMutation({
        mutationFn: () => collectionApi.recycle({ card_ids: recycleIds }),
        onSuccess: (res) => {
            showRewards({
                title: `Recyclage ×${res.recycled_count}`,
                items: [{ kind: "resource", resourceId: res.resource_id, amount: res.gained, name: res.resource_name }],
            });
            setResult(`+${res.gained.toLocaleString("fr-FR")} ${res.resource_name} (solde : ${res.new_balance.toLocaleString("fr-FR")})`);
            setConfirmingRecycle(false);
            setSelectedIds(new Set());
            qc.invalidateQueries({ queryKey: ["collection"] });
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["card-copies"] });
        },
        onError: (e) => { setResult(errMsg(e)); setConfirmingRecycle(false); },
    });

    // Exemplaires identiques regroupés (même puissance, mêmes favoris, même verrou :
    // ⚡13 ×5 plutôt que 5 lignes) ; cocher une ligne sélectionne tous ses exemplaires.
    const copyGroups = Object.values(
        (copiesQ.data?.copies ?? []).reduce<Record<string, { key: string; power: number | null; locked: boolean; favs: number[]; ids: string[] }>>((acc, c) => {
            const favs = [...c.favorite_ids].sort((a, b) => a - b);
            const key = `${c.power}|${c.locked}|${favs.join(",")}`;
            (acc[key] ??= { key, power: c.power, locked: c.locked, favs, ids: [] }).ids.push(c.id);
            return acc;
        }, {})
    ).sort((a, b) => (b.power ?? -1) - (a.power ?? -1));

    // Favoris / verrou : s'appliquent à la ligne affichée (ou à l'unique exemplaire).
    const { data: favCats } = useQuery({ queryKey: ["favorites"], queryFn: favoritesApi.list, enabled: !readOnly });
    const activeRow = copyGroups.find((g) => (focusId ? g.ids.includes(focusId) : owned === 1));
    const refreshFavs = () => {
        qc.invalidateQueries({ queryKey: ["card-copies"] });
        qc.invalidateQueries({ queryKey: ["collection"] });
        qc.invalidateQueries({ queryKey: ["favorites"] });
    };
    const toggleFav = useMutation({
        mutationFn: ({ id, on }: { id: number; on: boolean }) =>
            on ? favoritesApi.addCards(id, activeRow!.ids) : favoritesApi.removeCards(id, activeRow!.ids),
        onSuccess: refreshFavs,
        onError: (e) => setResult(errMsg(e)),
    });
    const toggleLock = useMutation({
        mutationFn: (locked: boolean) => favoritesApi.lock(activeRow!.ids, locked),
        onSuccess: refreshFavs,
        onError: (e) => setResult(errMsg(e)),
    });

    const toggleCopies = (ids: string[]) => {
        setSelectedIds((prev) => {
            const next = new Set(prev);
            const allSelected = ids.every((id) => next.has(id));
            for (const id of ids) {
                if (allSelected) next.delete(id); else next.add(id);
            }
            return next;
        });
    };

    if (!displayCard) return null;

    const rarityColor = rarityColorToCSS(displayCard.rarity_color);
    const recycleCount = recycleIds.length;
    const losesAllCopies = recycleCount >= owned;
    const cardLabel = [displayCard.character_name, displayCard.rarity_name, displayCard.quality_name,
        displayCard.specialty_id !== "normal" ? displayCard.specialty_name : null,
        displayCard.jewelry_id !== "none" ? displayCard.jewelry_name : null]
        .filter(Boolean).join(" · ");

    return (
        <AnimatePresence>
            {open && (
                <motion.div
                    className="fixed inset-0 z-50 flex items-center justify-center p-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.18 }}
                >
                    <div className="absolute inset-0 bg-black/80" onClick={onClose} />

                    <motion.div
                        className="relative flex flex-col items-center gap-3 max-w-sm w-full max-h-[88vh]"
                        initial={{ y: 30, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        exit={{ y: 30, opacity: 0 }}
                        transition={{ duration: 0.18 }}
                    >
                        {/* Carte */}
                        <CardWithEffects card={displayCard} className="w-56 shrink-0" />

                        {/* Info panel */}
                        <div className="bg-game-surface rounded-2xl p-4 w-full border border-white/10 flex-1 min-h-0 overflow-y-auto overscroll-contain">
                            <h3 className="text-xl font-bold text-white mb-2">{displayCard.character_name}</h3>

                            <div className="flex flex-wrap gap-1.5 mb-3">
                                <Badge label={displayCard.rarity_name} color={rarityColor} />
                                {displayCard.quality_id !== "authentic" && (
                                    <Badge label={displayCard.quality_name} className="bg-white/20 text-white" />
                                )}
                                {displayCard.specialty_id !== "normal" && (
                                    <Badge label={displayCard.specialty_name} className="bg-purple-600/80 text-white" />
                                )}
                                {displayCard.jewelry_id !== "none" && (
                                    <Badge
                                        label={displayCard.jewelry_name}
                                        color={`rgb(${displayCard.jewelry_color.join(",")})`}
                                    />
                                )}
                            </div>

                            <div className="space-y-1 text-sm text-white/70">
                                <p>Set: <span className="text-white">{displayCard.set_name}</span></p>
                                <p>Type: <span className="text-white">{displayCard.character_type}</span></p>
                                <p>Génération: <span className="text-white">Gen {displayCard.gen}</span></p>
                                {displayCard.booster_name && (
                                    <p>Booster: <span className="text-white">{displayCard.booster_name}</span></p>
                                )}
                                {displayCard.obtained_at && (
                                    <p>
                                        Obtenue le:{" "}
                                        <span className="text-white">
                                            {new Date(displayCard.obtained_at).toLocaleDateString("fr-FR", {
                                                day: "2-digit", month: "2-digit", year: "numeric",
                                            })}
                                        </span>
                                    </p>
                                )}
                                {displayCard.character_description && displayCard.quality_id !== "unplayable" && (
                                    <p className="italic text-white/50 mt-2">{displayCard.character_description}</p>
                                )}
                                <p>
                                    Rareté du tirage:{" "}
                                    <span className="text-accent">
                                        {displayCard.drop_probability > 0
                                            ? `1 sur ${Math.round(1 / displayCard.drop_probability).toLocaleString("fr-FR")}`
                                            : "—"}
                                    </span>
                                </p>
                                {displayCard.power != null && (
                                    <p>
                                        Puissance:{" "}
                                        <span className="text-gold font-bold">{displayCard.power}</span>
                                        {displayCard.combined_rarity != null && (
                                            <span className="text-white/40">
                                                {" "}(rareté globale : 1 sur {displayCard.combined_rarity.toLocaleString("fr-FR")})
                                            </span>
                                        )}
                                    </p>
                                )}
                                {owned > 1 && (
                                    <p>
                                        Exemplaires: <span className="text-gold font-bold">×{owned}</span>
                                    </p>
                                )}
                            </div>

                            {/* Favoris + verrou de l'exemplaire affiché */}
                            {!readOnly && (
                                <div className="mt-3 pt-3 border-t border-white/10 space-y-2">
                                    {!activeRow ? (
                                        <p className="text-white/40 text-xs">
                                            ★ Touche un exemplaire dans la liste ci-dessous pour le ranger dans tes favoris ou le verrouiller.
                                        </p>
                                    ) : (
                                        <>
                                            <div className="flex items-center justify-between">
                                                <p className="text-white/60 text-xs">
                                                    Favoris{activeRow.ids.length > 1 ? ` (×${activeRow.ids.length} exemplaires)` : ""}
                                                </p>
                                                <button
                                                    className={`text-xs px-2 py-1 rounded-full border ${activeRow.locked ? "bg-gold/20 border-gold/50 text-gold" : "border-white/15 text-white/60"}`}
                                                    disabled={toggleLock.isPending}
                                                    onClick={() => toggleLock.mutate(!activeRow.locked)}
                                                    title="Un exemplaire verrouillé ne peut pas être recyclé"
                                                >
                                                    {activeRow.locked ? "🔒 Verrouillé" : "🔓 Verrouiller"}
                                                </button>
                                            </div>
                                            {favCats?.length ? (
                                                <div className="flex flex-wrap gap-1.5">
                                                    {favCats.map((c) => {
                                                        const on = activeRow.favs.includes(c.id);
                                                        return (
                                                            <button key={c.id} disabled={toggleFav.isPending}
                                                                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs border transition-colors ${on ? "text-white" : "text-white/50 border-white/10"}`}
                                                                style={on ? { borderColor: c.color, background: `${c.color}33` } : undefined}
                                                                onClick={() => toggleFav.mutate({ id: c.id, on: !on })}>
                                                                <span className="w-2.5 h-2.5 rounded-full" style={{ background: c.color }} />
                                                                {c.name}{on ? " ✓" : ""}
                                                            </button>
                                                        );
                                                    })}
                                                </div>
                                            ) : (
                                                <p className="text-white/40 text-xs">Crée des catégories de favoris depuis la collection (bouton « + Créer des favoris »).</p>
                                            )}
                                        </>
                                    )}
                                </div>
                            )}

                            {/* Recyclage */}
                            {!readOnly && (
                                <div className="mt-3 pt-3 border-t border-white/10">
                                    <p className="text-white/60 text-xs mb-2">
                                        Recycler contre de la poussière (irréversible)
                                    </p>

                                    {owned > 1 && (
                                        <div className="mb-2">
                                            <p className="text-white/40 text-[11px] mb-1.5">
                                                Coche le ou les exemplaires à recycler — touche une ligne pour voir cet exemplaire :
                                            </p>
                                            {copiesQ.isLoading ? (
                                                <p className="text-white/40 text-xs">Chargement...</p>
                                            ) : (
                                                <div className="bg-black/30 rounded-lg px-3 py-2 space-y-1.5 max-h-32 overflow-y-auto">
                                                    {copyGroups.map((g) => {
                                                        const focused = !!focusId && g.ids.includes(focusId);
                                                        return (
                                                            <div
                                                                key={g.key}
                                                                className={`flex items-center gap-2 text-sm cursor-pointer rounded px-1 -mx-1 ${
                                                                    focused ? "bg-accent/20 text-white" : "text-white/80 hover:bg-white/5"
                                                                }`}
                                                                onClick={() => setFocusId(focused ? null : g.ids[0])}
                                                            >
                                                                <input
                                                                    type="checkbox"
                                                                    disabled={g.locked}
                                                                    title={g.locked ? "Verrouillé : impossible de recycler" : undefined}
                                                                    checked={!g.locked && g.ids.every((id) => selectedIds.has(id))}
                                                                    onClick={(e) => e.stopPropagation()}
                                                                    onChange={() => toggleCopies(g.ids)}
                                                                />
                                                                {g.power != null ? `⚡${g.power}` : "—"}
                                                                {g.ids.length > 1 && (
                                                                    <span className="text-white/40 text-xs">×{g.ids.length}</span>
                                                                )}
                                                                {g.locked && <span className="text-[11px]">🔒</span>}
                                                                {g.favs.map((id) => {
                                                                    const cat = favCats?.find((c) => c.id === id);
                                                                    return cat ? <span key={id} className="w-2 h-2 rounded-full" style={{ background: cat.color }} /> : null;
                                                                })}
                                                                {focused && <span className="ml-auto text-accent text-[11px]">affiché</span>}
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    <div className="flex items-center gap-2">
                                        <Button
                                            variant="secondary"
                                            size="sm"
                                            className="flex-1"
                                            disabled={recycleCount === 0}
                                            onClick={() => { setResult(null); setConfirmingRecycle(true); }}
                                        >
                                            Recycler {recycleCount > 1 ? `×${recycleCount}` : ""}
                                        </Button>
                                    </div>
                                    {result && (
                                        <p className="text-xs mt-2 text-purple-300">{result}</p>
                                    )}
                                </div>
                            )}
                        </div>

                        <button
                            className="shrink-0 text-white/50 hover:text-white transition-colors text-sm"
                            onClick={onClose}
                        >
                            Fermer
                        </button>
                    </motion.div>

                    <ConfirmModal
                        open={confirmingRecycle}
                        title="Confirmer le recyclage"
                        message={`Recycler ${recycleCount} exemplaire${recycleCount > 1 ? "s" : ""} de « ${cardLabel} » contre de la poussière ? Cette action est irréversible.`}
                        warning={losesAllCopies
                            ? `Tu recycles ${owned > 1 ? "tous tes exemplaires" : "ton dernier exemplaire"} de cette carte : tu n'en posséderas plus aucun après cette opération.`
                            : undefined}
                        confirmLabel="Recycler"
                        confirmVariant="primary"
                        busy={recycle.isPending}
                        onConfirm={() => recycle.mutate()}
                        onCancel={() => setConfirmingRecycle(false)}
                    />
                </motion.div>
            )}
        </AnimatePresence>
    );
}
