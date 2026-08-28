import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { playerApi } from "@/api/player";
import { useAuthStore } from "@/stores/authStore";
import Button from "@/components/ui/Button";

export default function DailyRewardPopup() {
    const [show, setShow] = useState(false);
    const [reward, setReward] = useState<{
        reward: number;
        streak: number;
    } | null>(null);
    const { updateCoins } = useAuthStore();
    const queryClient = useQueryClient();

    const claimMutation = useMutation({
        mutationFn: playerApi.claimDailyReward,
        onSuccess: (data) => {
            if (data.is_new) {
                setReward({ reward: data.reward, streak: data.streak });
                updateCoins(data.total_coins);
                setShow(true);
                queryClient.invalidateQueries({ queryKey: ["player"] });
            }
        },
    });

    useEffect(() => {
        claimMutation.mutate();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <AnimatePresence>
            {show && reward && (
                <motion.div
                    className="fixed inset-0 z-50 flex items-center justify-center p-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                >
                    <div className="absolute inset-0 bg-black/70" />

                    <motion.div
                        className="relative bg-game-surface rounded-2xl p-8 text-center
                       border border-gold/30 shadow-2xl max-w-sm w-full"
                        initial={{ scale: 0.5, rotate: -5 }}
                        animate={{ scale: 1, rotate: 0 }}
                        exit={{ scale: 0.5, opacity: 0 }}
                    >
                        <motion.div
                            className="text-6xl mb-4"
                            animate={{ rotate: [0, -10, 10, -10, 0] }}
                            transition={{ duration: 0.5, delay: 0.3 }}
                        >
                            🎁
                        </motion.div>

                        <h2 className="text-2xl font-bold text-gold mb-2">
                            Récompense quotidienne !
                        </h2>

                        <p className="text-white/80 mb-1">
                            Jour <span className="text-accent font-bold">{reward.streak}</span>
                        </p>

                        <motion.p
                            className="text-4xl font-bold text-gold my-4"
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ type: "spring", delay: 0.4 }}
                        >
                            +{reward.reward.toLocaleString("fr-FR")} 🪙
                        </motion.p>

                        <Button variant="gold" onClick={() => setShow(false)}>
                            Merci !
                        </Button>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
