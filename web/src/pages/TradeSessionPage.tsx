import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { tradeSessionsApi } from "@/api/tradeSessions";
import type { TradeSessionItem } from "@/types/trade";
import type { Card } from "@/types/card";
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import CardImage from "@/components/card/CardImage";
import CardDetail from "@/components/card/CardDetail";
import ResourceIcon from "@/components/ui/ResourceIcon";
import AddResourceModal from "@/components/trade/AddResourceModal";
import FloatingActionBar from "@/components/ui/FloatingActionBar";
import { errMsg } from "@/utils/errors";
import { showRewards, type RewardItem } from "@/stores/rewardPopupStore";

const MAX_ITEMS_PER_SIDE = 12;

const ACTIVE = new Set(["negotiating", "confirming"]);

function ItemChip({ item, onRemove, onOpenDetail }: { item: TradeSessionItem; onRemove?: () => void; onOpenDetail?: (card: Card) => void }) {
    if (item.item_type === "card" && item.card) {
        return (
            <div className="relative">
                {onRemove && (
                    <button
                        className="absolute -top-1.5 -right-1.5 z-10 w-5 h-5 rounded-full bg-red-500 text-white text-xs leading-none flex items-center justify-center"
                        onClick={onRemove}
                    >
                        ×
                    </button>
                )}
                <CardImage card={item.card} size="sm" onClick={onOpenDetail ? () => onOpenDetail(item.card!) : undefined} />
            </div>
        );
    }
    if (item.item_type === "card") {
        return (
            <div className="bg-black/30 border border-white/10 rounded-xl px-2 py-4 flex flex-col items-center justify-center gap-1 aspect-[5/7]">
                <span className="text-white/30 text-xs text-center">Carte indisponible</span>
            </div>
        );
    }
    return (
        <div className="relative bg-black/30 border border-white/10 rounded-xl px-3 py-4 flex flex-col items-center justify-center gap-1 aspect-[5/7]">
            {onRemove && (
                <button
                    className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-red-500 text-white text-xs leading-none flex items-center justify-center"
                    onClick={onRemove}
                >
                    ×
                </button>
            )}
            <ResourceIcon resourceId={item.resource_id ?? "coins"} className="w-6 h-6" />
            <span className="text-white text-sm font-bold">{item.amount?.toLocaleString("fr-FR")}</span>
            <span className="text-white/40 text-[10px] text-center">{item.resource_name}</span>
        </div>
    );
}

export default function TradeSessionPage() {
    const { sessionId } = useParams<{ sessionId: string }>();
    const id = Number(sessionId);
    const navigate = useNavigate();
    const qc = useQueryClient();
    const [addResourceOpen, setAddResourceOpen] = useState(false);
    const [err, setErr] = useState("");
    const [detailCard, setDetailCard] = useState<Card | null>(null);
    const requestSelection = useCardSelectionStore((s) => s.requestSelection);
    const consumeResult = useCardSelectionStore((s) => s.consumeResult);

    const { data: trade, isLoading } = useQuery({
        queryKey: ["trade-session", id],
        queryFn: () => tradeSessionsApi.get(id),
        refetchInterval: (query) => (query.state.data && ACTIVE.has(query.state.data.status) ? 1800 : false),
    });

    const invalidate = () => qc.invalidateQueries({ queryKey: ["trade-session", id] });

    const addCard = useMutation({
        mutationFn: (cardId: string) => tradeSessionsApi.addCard(id, cardId),
        onSuccess: (data) => { qc.setQueryData(["trade-session", id], data); setErr(""); },
        onError: (e) => setErr(errMsg(e)),
    });

    // Retour depuis la page Collection (mode sélection) : ajoute chaque carte choisie.
    useEffect(() => {
        const result = consumeResult();
        if (!result || result.context?.purpose !== "trade-add" || result.context?.tradeSessionId !== sessionId) return;
        for (const { id: cardId } of result.selectedCards) {
            addCard.mutate(cardId);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [sessionId]);
    const addResource = useMutation({
        mutationFn: ({ resourceId, amount }: { resourceId: string; amount: number }) =>
            tradeSessionsApi.addResource(id, resourceId, amount),
        onSuccess: (data) => { qc.setQueryData(["trade-session", id], data); setAddResourceOpen(false); setErr(""); },
        onError: (e) => setErr(errMsg(e)),
    });
    const removeItem = useMutation({
        mutationFn: (itemId: number) => tradeSessionsApi.removeItem(id, itemId),
        onSuccess: (data) => qc.setQueryData(["trade-session", id], data),
        onError: (e) => setErr(errMsg(e)),
    });
    const setReady = useMutation({
        mutationFn: (ready: boolean) => tradeSessionsApi.setReady(id, ready),
        onSuccess: (data) => qc.setQueryData(["trade-session", id], data),
        onError: (e) => setErr(errMsg(e)),
    });
    const confirmTrade = useMutation({
        mutationFn: () => tradeSessionsApi.confirm(id),
        onSuccess: (data) => {
            qc.setQueryData(["trade-session", id], data);
            if (data.status === "completed") {
                qc.invalidateQueries({ queryKey: ["player"] });
                qc.invalidateQueries({ queryKey: ["collection"] });
            }
        },
        onError: (e) => setErr(errMsg(e)),
    });
    const cancelTrade = useMutation({
        mutationFn: () => tradeSessionsApi.cancel(id),
        onSuccess: invalidate,
    });

    // Échange conclu sous nos yeux (pas au rechargement d'un échange déjà
    // terminé) : récapitulatif de ce qu'on a reçu, par-dessus le résumé.
    const previousStatus = useRef(trade?.status);
    useEffect(() => {
        if (!trade) return;
        const was = previousStatus.current;
        previousStatus.current = trade.status;
        if (trade.status !== "completed" || !was || !ACTIVE.has(was)) return;
        const items: RewardItem[] = trade.other_items.flatMap((item): RewardItem[] => {
            if (item.item_type === "card") return item.card ? [{ kind: "card", card: item.card }] : [];
            return item.resource_id && item.amount
                ? [{ kind: "resource", resourceId: item.resource_id, amount: item.amount, name: item.resource_name }]
                : [];
        });
        showRewards({ title: `Échange avec ${trade.other_display_name}`, items });
    }, [trade]);

    if (isLoading || !trade) {
        return <LoadingSpinner text="Chargement de l'échange..." />;
    }

    const myCardIds = new Set(trade.my_items.filter((i) => i.item_type === "card").map((i) => i.card!.id));
    const myResourceAmounts = Object.fromEntries(
        trade.my_items.filter((i) => i.item_type === "resource").map((i) => [i.resource_id!, i.amount!])
    );

    const finished = !ACTIVE.has(trade.status);

    return (
        <div className="min-h-screen bg-game-bg flex flex-col pb-8">
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button className="text-white/60 hover:text-white text-sm" onClick={() => navigate("/")}>
                    Retour
                </button>
                <h2 className="text-white font-bold">Échange avec {trade.other_display_name}</h2>
                <span className={`w-2 h-2 rounded-full ${trade.other_online ? "bg-green-400" : "bg-white/20"}`} />
            </header>

            <div className="flex-1 px-4 py-4 max-w-sm w-full mx-auto space-y-6">
                <AnimatePresence>
                    {trade.removed_items.length > 0 && trade.status === "negotiating" && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
                            className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 space-y-1"
                        >
                            {trade.removed_items.map((m, i) => (
                                <p key={i} className="text-red-400 text-xs">{m}</p>
                            ))}
                        </motion.div>
                    )}
                </AnimatePresence>

                {trade.status === "completed" && (
                    <div className="bg-green-500/10 border border-green-500/30 rounded-lg px-3 py-3 text-center">
                        <p className="text-green-400 font-bold">Échange terminé !</p>
                    </div>
                )}
                {trade.status === "cancelled" && (
                    <div className="bg-white/5 border border-white/10 rounded-lg px-3 py-3 text-center">
                        <p className="text-white/60">Échange annulé.</p>
                    </div>
                )}
                {trade.status === "expired" && (
                    <div className="bg-white/5 border border-white/10 rounded-lg px-3 py-3 text-center">
                        <p className="text-white/60">Échange expiré (inactivité).</p>
                    </div>
                )}

                {/* Mon offre */}
                <section>
                    <div className="flex items-center justify-between mb-2">
                        <h3 className="text-white/70 text-xs font-semibold uppercase tracking-wide">Ton offre</h3>
                        {trade.my_ready && (
                            <span className="text-green-400 text-xs font-semibold">Prêt</span>
                        )}
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                        {trade.my_items.map((item) => (
                            <ItemChip
                                key={item.id}
                                item={item}
                                onOpenDetail={setDetailCard}
                                onRemove={
                                    trade.status === "negotiating"
                                        ? () => removeItem.mutate(item.id)
                                        : undefined
                                }
                            />
                        ))}
                        {!finished && trade.status === "negotiating" && (
                            <>
                                <button
                                    className="aspect-[5/7] rounded-xl border-2 border-dashed border-white/15 hover:border-accent/50 flex items-center justify-center text-white/30 hover:text-accent text-3xl"
                                    onClick={() => {
                                        setAddResourceOpen(false);
                                        requestSelection({
                                            max: Math.max(1, MAX_ITEMS_PER_SIDE - trade.my_items.length),
                                            title: "Choisis une carte à échanger",
                                            excludeIds: Array.from(myCardIds),
                                            returnTo: `/trade/${id}`,
                                            context: { purpose: "trade-add", tradeSessionId: sessionId ?? "" },
                                        });
                                        navigate("/collection");
                                    }}
                                >
                                    🃏
                                </button>
                                <button
                                    className="aspect-[5/7] rounded-xl border-2 border-dashed border-white/15 hover:border-accent/50 flex items-center justify-center text-white/30 hover:text-accent text-3xl"
                                    onClick={() => setAddResourceOpen(true)}
                                >
                                    +
                                </button>
                            </>
                        )}
                    </div>
                    {trade.my_items.length === 0 && trade.status !== "negotiating" && (
                        <p className="text-white/30 text-sm">Rien proposé.</p>
                    )}
                </section>

                {/* Offre de l'autre */}
                <section>
                    <div className="flex items-center justify-between mb-2">
                        <h3 className="text-white/70 text-xs font-semibold uppercase tracking-wide">
                            Offre de {trade.other_display_name}
                        </h3>
                        {trade.other_ready && (
                            <span className="text-green-400 text-xs font-semibold">Prêt</span>
                        )}
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                        {trade.other_items.map((item) => <ItemChip key={item.id} item={item} onOpenDetail={setDetailCard} />)}
                    </div>
                    {trade.other_items.length === 0 && (
                        <p className="text-white/30 text-sm">Rien proposé pour l'instant.</p>
                    )}
                </section>

                {err && <p className="text-red-400 text-xs">{err}</p>}

                {!finished && (
                    <FloatingActionBar spacerClassName={trade.status === "confirming" ? "h-48" : "h-32"}>
                    <div className="space-y-2">
                        {trade.status === "negotiating" && (
                            <Button
                                variant={trade.my_ready ? "secondary" : "primary"}
                                className="w-full"
                                loading={setReady.isPending}
                                onClick={() => setReady.mutate(!trade.my_ready)}
                            >
                                {trade.my_ready ? "Annuler (je ne suis plus prêt)" : "Je suis prêt"}
                            </Button>
                        )}
                        {trade.status === "confirming" && (
                            <>
                                <p className="text-white/50 text-xs text-center">
                                    Vérifie bien l'échange ci-dessus — la confirmation est définitive.
                                </p>
                                <Button
                                    variant="gold"
                                    className="w-full"
                                    disabled={trade.my_confirmed}
                                    loading={confirmTrade.isPending}
                                    onClick={() => confirmTrade.mutate()}
                                >
                                    {trade.my_confirmed ? "En attente de l'autre joueur..." : "Confirmer l'échange"}
                                </Button>
                                <Button
                                    variant="secondary"
                                    className="w-full"
                                    disabled={trade.my_confirmed}
                                    onClick={() => setReady.mutate(false)}
                                >
                                    Revenir en arrière (modifier)
                                </Button>
                            </>
                        )}
                        <Button variant="danger" className="w-full" loading={cancelTrade.isPending} onClick={() => cancelTrade.mutate()}>
                            Annuler l'échange
                        </Button>
                    </div>
                    </FloatingActionBar>
                )}
                {finished && (
                    <FloatingActionBar>
                        <Button variant="primary" className="w-full" onClick={() => navigate("/")}>
                            Retour au menu
                        </Button>
                    </FloatingActionBar>
                )}
            </div>

            {addResourceOpen && (
                <AddResourceModal
                    current={myResourceAmounts}
                    onPick={(resourceId, amount) => addResource.mutate({ resourceId, amount })}
                    onClose={() => setAddResourceOpen(false)}
                />
            )}

            <CardDetail
                open={!!detailCard}
                card={detailCard}
                readOnly
                onClose={() => setDetailCard(null)}
            />
        </div>
    );
}
