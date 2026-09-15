import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Card } from "@/types/card";
import { collectionApi } from "@/api/collection";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import ConfirmModal from "@/components/ui/ConfirmModal";
import CardImage from "./CardImage";
import { errMsg } from "@/utils/errors";

interface CardDetailProps {
    open: boolean;
    card: Card | null;
    quantity?: number;
    onClose: () => void;
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
export default function CardDetail({ open, card, quantity, onClose }: CardDetailProps) {
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
        }
    }, [card, quantity]);

    const displayCard = card ?? lastCard;
    const owned = lastQuantity ?? 1;

    const copiesQ = useQuery({
        queryKey: ["card-copies", displayCard?.character_id, displayCard?.rarity_id, displayCard?.quality_id, displayCard?.specialty_id, displayCard?.jewelry_id],
        queryFn: () => collectionApi.getCardCopies({
            character_id: displayCard!.character_id,
            rarity_id: displayCard!.rarity_id,
            quality_id: displayCard!.quality_id,
            specialty_id: displayCard!.specialty_id,
            jewelry_id: displayCard!.jewelry_id,
        }),
        enabled: owned > 1 && !!displayCard,
    });

    const recycleIds = owned > 1 ? Array.from(selectedIds) : (displayCard ? [displayCard.id] : []);

    const recycle = useMutation({
        mutationFn: () => collectionApi.recycle({ card_ids: recycleIds }),
        onSuccess: (res) => {
            setResult(`+${res.gained.toLocaleString("fr-FR")} ${res.resource_name} (solde : ${res.new_balance.toLocaleString("fr-FR")})`);
            setConfirmingRecycle(false);
            setSelectedIds(new Set());
            qc.invalidateQueries({ queryKey: ["collection"] });
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["card-copies"] });
        },
        onError: (e) => { setResult(errMsg(e)); setConfirmingRecycle(false); },
    });

    const toggleCopy = (id: string) => {
        setSelectedIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id); else next.add(id);
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
                        <div className="w-56 shrink-0">
                            <CardImage card={displayCard} size="lg" />
                        </div>

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

                            {/* Recyclage */}
                            <div className="mt-3 pt-3 border-t border-white/10">
                                <p className="text-white/60 text-xs mb-2">
                                    Recycler contre de la poussière (irréversible)
                                </p>

                                {owned > 1 && (
                                    <div className="mb-2">
                                        <p className="text-white/40 text-[11px] mb-1.5">
                                            Coche le ou les exemplaires à recycler :
                                        </p>
                                        {copiesQ.isLoading ? (
                                            <p className="text-white/40 text-xs">Chargement...</p>
                                        ) : (
                                            <div className="bg-black/30 rounded-lg px-3 py-2 space-y-1.5 max-h-32 overflow-y-auto">
                                                {(copiesQ.data?.copies ?? []).map((c) => (
                                                    <label key={c.id} className="flex items-center gap-2 text-sm text-white/80 cursor-pointer">
                                                        <input
                                                            type="checkbox"
                                                            checked={selectedIds.has(c.id)}
                                                            onChange={() => toggleCopy(c.id)}
                                                        />
                                                        {c.power != null ? `⚡${c.power}` : "—"}
                                                    </label>
                                                ))}
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
