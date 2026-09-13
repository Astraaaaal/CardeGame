import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { friendsApi } from "@/api/friends";
import Button from "@/components/ui/Button";
import ConfirmModal from "@/components/ui/ConfirmModal";

function errMsg(e: unknown): string {
    if (e && typeof e === "object" && "response" in e) {
        const r = (e as { response?: { data?: { detail?: unknown } } }).response;
        if (typeof r?.data?.detail === "string") return r.data.detail;
    }
    return "Erreur.";
}

type Tab = "friends" | "requests" | "trades";

interface FriendsPanelProps {
    open: boolean;
    onClose: () => void;
}

export default function FriendsPanel({ open, onClose }: FriendsPanelProps) {
    const qc = useQueryClient();
    const [tab, setTab] = useState<Tab>("friends");
    const [username, setUsername] = useState("");
    const [err, setErr] = useState("");
    const [toRemove, setToRemove] = useState<{ id: number; name: string } | null>(null);

    const friendsQ = useQuery({
        queryKey: ["friends"], queryFn: friendsApi.list,
        enabled: open, refetchInterval: open ? 20_000 : false,
    });
    const requestsQ = useQuery({
        queryKey: ["friend-requests"], queryFn: friendsApi.listRequests,
        enabled: open, refetchInterval: open ? 20_000 : false,
    });
    const tradesQ = useQuery({
        queryKey: ["trade-requests"], queryFn: friendsApi.listTradeRequests,
        enabled: open, refetchInterval: open ? 20_000 : false,
    });

    const refreshAll = () => {
        qc.invalidateQueries({ queryKey: ["friends"] });
        qc.invalidateQueries({ queryKey: ["friend-requests"] });
    };

    const sendReq = useMutation({
        mutationFn: () => friendsApi.send(username.trim()),
        onSuccess: () => { setUsername(""); setErr(""); refreshAll(); },
        onError: (e) => setErr(errMsg(e)),
    });
    const acceptReq = useMutation({
        mutationFn: (id: number) => friendsApi.accept(id),
        onSuccess: refreshAll,
    });
    const declineReq = useMutation({
        mutationFn: (id: number) => friendsApi.decline(id),
        onSuccess: refreshAll,
    });
    const removeFriend = useMutation({
        mutationFn: (userId: number) => friendsApi.remove(userId),
        onSuccess: () => { setToRemove(null); refreshAll(); },
    });
    const proposeTrade = useMutation({
        mutationFn: (userId: number) => friendsApi.proposeTrade(userId),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["trade-requests"] }),
    });
    const cancelTrade = useMutation({
        mutationFn: (id: number) => friendsApi.cancelTradeRequest(id),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["trade-requests"] }),
    });

    const friends = friendsQ.data ?? [];
    const incomingReq = requestsQ.data?.incoming ?? [];
    const outgoingReq = requestsQ.data?.outgoing ?? [];
    const incomingTrades = tradesQ.data?.incoming ?? [];
    const outgoingTrades = tradesQ.data?.outgoing ?? [];

    const outgoingTradeTo = (userId: number) => outgoingTrades.find((t) => t.user_id === userId);

    const tabs: { key: Tab; label: string; badge: number }[] = [
        { key: "friends", label: "Amis", badge: 0 },
        { key: "requests", label: "Demandes", badge: incomingReq.length },
        { key: "trades", label: "Échanges", badge: incomingTrades.length },
    ];

    return (
        <>
            <AnimatePresence>
                {open && (
                    <>
                        <motion.div
                            className="fixed inset-0 bg-black/60 z-40"
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            onClick={onClose}
                        />
                        <motion.aside
                            className="fixed top-0 right-0 h-full w-full max-w-sm bg-game-surface
                                       border-l border-white/10 z-50 flex flex-col shadow-2xl"
                            initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
                            transition={{ type: "tween", duration: 0.25 }}
                        >
                            <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
                                <h2 className="text-white font-bold">👥 Amis</h2>
                                <button className="text-white/40 hover:text-white text-xl leading-none" onClick={onClose}>
                                    ×
                                </button>
                            </div>

                            <div className="flex border-b border-white/5">
                                {tabs.map((t) => (
                                    <button
                                        key={t.key}
                                        className={`flex-1 py-2.5 text-sm font-semibold relative transition-colors ${
                                            tab === t.key ? "text-accent border-b-2 border-accent" : "text-white/40 hover:text-white/70"
                                        }`}
                                        onClick={() => setTab(t.key)}
                                    >
                                        {t.label}
                                        {t.badge > 0 && (
                                            <span className="ml-1.5 inline-flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4">
                                                {t.badge}
                                            </span>
                                        )}
                                    </button>
                                ))}
                            </div>

                            <div className="flex-1 overflow-y-auto p-4 space-y-3">
                                {tab === "friends" && (
                                    <>
                                        <div className="flex gap-2">
                                            <input
                                                className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30"
                                                placeholder="Pseudo à ajouter..."
                                                value={username}
                                                onChange={(e) => { setUsername(e.target.value); setErr(""); }}
                                                onKeyDown={(e) => e.key === "Enter" && username.trim() && sendReq.mutate()}
                                            />
                                            <Button
                                                variant="primary" size="sm"
                                                disabled={!username.trim()}
                                                loading={sendReq.isPending}
                                                onClick={() => sendReq.mutate()}
                                            >
                                                Ajouter
                                            </Button>
                                        </div>
                                        {err && <p className="text-red-400 text-xs">{err}</p>}

                                        {friendsQ.isLoading ? (
                                            <p className="text-white/40 text-sm">Chargement...</p>
                                        ) : friends.length === 0 ? (
                                            <p className="text-white/30 text-sm text-center py-6">
                                                Aucun ami pour l'instant.
                                            </p>
                                        ) : (
                                            <div className="space-y-2">
                                                {friends.map((f) => {
                                                    const pendingTrade = outgoingTradeTo(f.user_id);
                                                    return (
                                                        <div key={f.user_id}
                                                            className="bg-black/20 border border-white/5 rounded-lg px-3 py-2.5">
                                                            <div className="flex items-center justify-between mb-1.5">
                                                                <div className="flex items-center gap-2 min-w-0">
                                                                    <span
                                                                        className={`w-2 h-2 rounded-full shrink-0 ${f.online ? "bg-green-400" : "bg-white/20"}`}
                                                                        title={f.online ? "En ligne" : "Hors ligne"}
                                                                    />
                                                                    <span className="text-white text-sm font-semibold truncate">{f.display_name}</span>
                                                                </div>
                                                                <button
                                                                    className="text-red-400/70 hover:text-red-400 text-xs shrink-0"
                                                                    onClick={() => setToRemove({ id: f.user_id, name: f.display_name })}
                                                                >
                                                                    Retirer
                                                                </button>
                                                            </div>
                                                            <Button
                                                                variant="secondary" size="sm" className="w-full"
                                                                disabled={!!pendingTrade}
                                                                loading={proposeTrade.isPending && proposeTrade.variables === f.user_id}
                                                                onClick={() => proposeTrade.mutate(f.user_id)}
                                                            >
                                                                {pendingTrade ? "Échange en attente..." : "Proposer un échange"}
                                                            </Button>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        )}
                                    </>
                                )}

                                {tab === "requests" && (
                                    <>
                                        <div>
                                            <p className="text-white/40 text-xs font-semibold mb-2 uppercase tracking-wide">
                                                Reçues
                                            </p>
                                            {incomingReq.length === 0 ? (
                                                <p className="text-white/30 text-sm">Aucune demande reçue.</p>
                                            ) : (
                                                <div className="space-y-2">
                                                    {incomingReq.map((r) => (
                                                        <div key={r.id} className="bg-black/20 border border-white/5 rounded-lg px-3 py-2.5">
                                                            <p className="text-white text-sm font-semibold mb-2">{r.display_name}</p>
                                                            <div className="flex gap-2">
                                                                <Button variant="primary" size="sm" className="flex-1"
                                                                    loading={acceptReq.isPending && acceptReq.variables === r.id}
                                                                    onClick={() => acceptReq.mutate(r.id)}>
                                                                    Accepter
                                                                </Button>
                                                                <Button variant="secondary" size="sm" className="flex-1"
                                                                    loading={declineReq.isPending && declineReq.variables === r.id}
                                                                    onClick={() => declineReq.mutate(r.id)}>
                                                                    Refuser
                                                                </Button>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                        <div>
                                            <p className="text-white/40 text-xs font-semibold mb-2 mt-4 uppercase tracking-wide">
                                                Envoyées
                                            </p>
                                            {outgoingReq.length === 0 ? (
                                                <p className="text-white/30 text-sm">Aucune demande envoyée.</p>
                                            ) : (
                                                <div className="space-y-2">
                                                    {outgoingReq.map((r) => (
                                                        <div key={r.id} className="flex items-center justify-between bg-black/20 border border-white/5 rounded-lg px-3 py-2.5">
                                                            <span className="text-white text-sm">{r.display_name}</span>
                                                            <button
                                                                className="text-white/40 hover:text-red-400 text-xs"
                                                                onClick={() => declineReq.mutate(r.id)}
                                                            >
                                                                Annuler
                                                            </button>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    </>
                                )}

                                {tab === "trades" && (
                                    <>
                                        <p className="text-white/30 text-xs bg-white/5 rounded-lg px-3 py-2">
                                            Le système d'échange complet arrive bientôt — pour l'instant, propose
                                            juste l'intention d'échanger à un ami.
                                        </p>
                                        <div>
                                            <p className="text-white/40 text-xs font-semibold mb-2 mt-2 uppercase tracking-wide">
                                                Reçues
                                            </p>
                                            {incomingTrades.length === 0 ? (
                                                <p className="text-white/30 text-sm">Aucune proposition reçue.</p>
                                            ) : (
                                                <div className="space-y-2">
                                                    {incomingTrades.map((t) => (
                                                        <div key={t.id} className="flex items-center justify-between bg-black/20 border border-white/5 rounded-lg px-3 py-2.5">
                                                            <span className="text-white text-sm">{t.display_name} propose un échange</span>
                                                            <button
                                                                className="text-white/40 hover:text-red-400 text-xs shrink-0"
                                                                onClick={() => cancelTrade.mutate(t.id)}
                                                            >
                                                                Fermer
                                                            </button>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                        <div>
                                            <p className="text-white/40 text-xs font-semibold mb-2 mt-4 uppercase tracking-wide">
                                                Envoyées
                                            </p>
                                            {outgoingTrades.length === 0 ? (
                                                <p className="text-white/30 text-sm">Aucune proposition envoyée.</p>
                                            ) : (
                                                <div className="space-y-2">
                                                    {outgoingTrades.map((t) => (
                                                        <div key={t.id} className="flex items-center justify-between bg-black/20 border border-white/5 rounded-lg px-3 py-2.5">
                                                            <span className="text-white text-sm">En attente de {t.display_name}</span>
                                                            <button
                                                                className="text-white/40 hover:text-red-400 text-xs shrink-0"
                                                                onClick={() => cancelTrade.mutate(t.id)}
                                                            >
                                                                Annuler
                                                            </button>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    </>
                                )}
                            </div>
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>

            <ConfirmModal
                open={!!toRemove}
                title="Retirer cet ami"
                message={toRemove ? `Retirer ${toRemove.name} de tes amis ?` : ""}
                confirmLabel="Retirer"
                busy={removeFriend.isPending}
                onConfirm={() => toRemove && removeFriend.mutate(toRemove.id)}
                onCancel={() => setToRemove(null)}
            />
        </>
    );
}
