import { toast } from "@/stores/toastStore";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { friendsApi } from "@/api/friends";
import { useAuthStore } from "@/stores/authStore";
import { TRADE_PULSE_KEY } from "@/hooks/useTradePulse";
import type { TradePulse, TradeRequestItem } from "@/types/social";
import Button from "@/components/ui/Button";
import { errMsg } from "@/utils/errors";

interface TradeRequestPopupProps {
    requests: TradeRequestItem[];
    /** Animation en cours, déjà dans un échange... : on attend avant d'afficher. */
    blocked: boolean;
}

export default function TradeRequestPopup({ requests, blocked }: TradeRequestPopupProps) {
    const { user } = useAuthStore();
    const navigate = useNavigate();
    const qc = useQueryClient();
    const setErr = (m: string | null) => { if (m) toast.error(m); };

    const dropRequest = (requestId: number) => {
        qc.setQueryData<TradePulse>(TRADE_PULSE_KEY, (p) =>
            p && { ...p, incoming_unseen: p.incoming_unseen.filter((r) => r.id !== requestId) }
        );
        qc.invalidateQueries({ queryKey: TRADE_PULSE_KEY });
        qc.invalidateQueries({ queryKey: ["trade-requests"] });
    };

    const accept = useMutation({
        mutationFn: friendsApi.acceptTradeRequest,
        onSuccess: (trade, requestId) => {
            setErr("");
            dropRequest(requestId);
            navigate(`/trade/${trade.id}`);
        },
        onError: (e, requestId) => { setErr(errMsg(e)); dropRequest(requestId); },
    });
    const refuse = useMutation({
        mutationFn: friendsApi.cancelTradeRequest,
        onSuccess: (_, requestId) => dropRequest(requestId),
        onError: (e) => setErr(errMsg(e)),
    });
    const later = useMutation({
        mutationFn: friendsApi.markTradeRequestSeen,
        onSuccess: (_, requestId) => dropRequest(requestId),
        onError: (e) => setErr(errMsg(e)),
    });

    const show = !!user?.trade_request_popup_enabled && !blocked && requests.length > 0;
    const busy = accept.isPending || refuse.isPending || later.isPending;

    return (
        <AnimatePresence>
            {show && (
                <motion.div
                    className="fixed inset-0 z-[60] flex items-center justify-center p-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                >
                    <div className="absolute inset-0 bg-black/70" />

                    <motion.div
                        className="relative bg-game-surface rounded-2xl p-6 border border-accent/30 shadow-2xl max-w-sm w-full"
                        initial={{ scale: 0.5, rotate: -5 }}
                        animate={{ scale: 1, rotate: 0 }}
                        exit={{ scale: 0.5, opacity: 0 }}
                    >
                        <h2 className="text-xl font-bold text-white mb-4 text-center">
                            {requests.length === 1 ? "Nouvelle demande d'échange !" : "Nouvelles demandes d'échange !"}
                        </h2>

                        <div className="space-y-3 max-h-[55vh] overflow-y-auto">
                            {requests.map((r) => (
                                <div key={r.id} className="bg-black/20 border border-white/5 rounded-xl p-3">
                                    <p className="text-white/80 text-sm mb-2.5">
                                        <span className="text-accent font-semibold">{r.display_name}</span> te propose un échange
                                    </p>
                                    <div className="flex gap-2">
                                        <Button
                                            variant="primary" size="sm" className="flex-1"
                                            disabled={busy}
                                            loading={accept.isPending && accept.variables === r.id}
                                            onClick={() => accept.mutate(r.id)}
                                        >
                                            Accepter
                                        </Button>
                                        <Button
                                            variant="secondary" size="sm" className="flex-1"
                                            disabled={busy}
                                            loading={refuse.isPending && refuse.variables === r.id}
                                            onClick={() => refuse.mutate(r.id)}
                                        >
                                            Refuser
                                        </Button>
                                        <Button
                                            variant="secondary" size="sm"
                                            disabled={busy}
                                            loading={later.isPending && later.variables === r.id}
                                            onClick={() => later.mutate(r.id)}
                                        >
                                            Plus tard
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>


                        <p className="text-white/30 text-xs mt-4 text-center">
                            « Plus tard » la garde dans le panneau Social, onglet Échanges.
                        </p>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
