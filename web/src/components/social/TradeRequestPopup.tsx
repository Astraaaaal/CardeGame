import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { friendsApi } from "@/api/friends";
import { useAuthStore } from "@/stores/authStore";
import Button from "@/components/ui/Button";

export default function TradeRequestPopup() {
    const { user } = useAuthStore();
    const qc = useQueryClient();
    const enabled = !!user?.trade_request_popup_enabled;

    const { data } = useQuery({
        queryKey: ["trade-requests-unseen"],
        queryFn: friendsApi.listUnseenTradeRequests,
        enabled,
        staleTime: 15_000,
    });

    const dismiss = useMutation({
        mutationFn: friendsApi.markTradeRequestsSeen,
        onSuccess: () => {
            qc.setQueryData(["trade-requests-unseen"], []);
            qc.invalidateQueries({ queryKey: ["trade-requests"] });
        },
    });

    const requests = data ?? [];
    const show = enabled && requests.length > 0;

    return (
        <AnimatePresence>
            {show && (
                <motion.div
                    className="fixed inset-0 z-50 flex items-center justify-center p-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                >
                    <div className="absolute inset-0 bg-black/70" />

                    <motion.div
                        className="relative bg-game-surface rounded-2xl p-8 text-center
                       border border-accent/30 shadow-2xl max-w-sm w-full"
                        initial={{ scale: 0.5, rotate: -5 }}
                        animate={{ scale: 1, rotate: 0 }}
                        exit={{ scale: 0.5, opacity: 0 }}
                    >
                        <div className="text-5xl mb-4">🔄</div>

                        <h2 className="text-xl font-bold text-white mb-3">
                            {requests.length === 1 ? "Nouvelle demande d'échange !" : "Nouvelles demandes d'échange !"}
                        </h2>

                        <div className="space-y-1 mb-4">
                            {requests.map((r) => (
                                <p key={r.id} className="text-white/70 text-sm">
                                    <span className="text-accent font-semibold">{r.display_name}</span> te propose un échange
                                </p>
                            ))}
                        </div>

                        <p className="text-white/30 text-xs mb-4">
                            Retrouve-les dans le panneau Amis, onglet Échanges.
                        </p>

                        <Button variant="primary" loading={dismiss.isPending} onClick={() => dismiss.mutate()}>
                            Compris !
                        </Button>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
