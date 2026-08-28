import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useAuthStore } from "@/stores/authStore";
import { useBoosters } from "@/hooks/useBoosters";
import { usePackOpening } from "@/hooks/usePackOpening";
import type { Booster } from "@/types/booster";
import Button from "@/components/ui/Button";
import CoinDisplay from "@/components/player/CoinDisplay";
import BoosterCard from "@/components/shop/BoosterCard";
import PriceTag from "@/components/shop/PriceTag";
import Modal from "@/components/ui/Modal";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

type Quantity = 1 | 5 | 10;

export default function BoosterShop() {
    const navigate = useNavigate();
    const { user } = useAuthStore();
    const { data: boosters, isLoading } = useBoosters();
    const openMutation = usePackOpening();

    const [selected, setSelected] = useState<Booster | null>(null);
    const [quantity, setQuantity] = useState<Quantity>(1);

    const handleOpen = () => {
        if (!selected) return;
        openMutation.mutate(
            { booster_id: selected.id, quantity },
            {
                onSuccess: () => {
                    setSelected(null);
                    navigate("/opening");
                },
            }
        );
    };

    const quantities: Quantity[] = [1, 5, 10];

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            {/* Header */}
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button
                    className="text-accent text-sm font-semibold"
                    onClick={() => navigate("/")}
                >
                    ← Retour
                </button>
                <CoinDisplay coins={user?.coins ?? 0} />
            </header>

            <main className="flex-1 px-4 py-6">
                <h1 className="text-2xl font-bold text-white mb-6 text-center">
                    🛍️ Boutique
                </h1>

                {isLoading ? (
                    <LoadingSpinner text="Chargement des boosters..." />
                ) : (
                    <div className="space-y-4 max-w-sm mx-auto">
                        {boosters?.map((b) => (
                            <motion.div
                                key={b.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                            >
                                <BoosterCard booster={b} onSelect={setSelected} />
                            </motion.div>
                        ))}
                    </div>
                )}
            </main>

            {/* Modal d'achat */}
            <Modal
                open={!!selected}
                onClose={() => setSelected(null)}
                title={selected?.name}
            >
                <AnimatePresence>
                    {selected && (
                        <motion.div
                            className="space-y-4"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                        >
                            <p className="text-white/60 text-sm">{selected.description}</p>

                            {/* Quantity selector */}
                            <div className="flex gap-2 justify-center">
                                {quantities.map((q) => (
                                    <button
                                        key={q}
                                        className={`px-4 py-2 rounded-xl font-bold transition-all
                      ${quantity === q
                                                ? "bg-accent text-white"
                                                : "bg-white/10 text-white/60 hover:bg-white/20"
                                            }`}
                                        onClick={() => setQuantity(q)}
                                    >
                                        ×{q}
                                    </button>
                                ))}
                            </div>

                            <div className="flex items-center justify-center">
                                <PriceTag basePrice={selected.price} quantity={quantity} />
                            </div>

                            <Button
                                variant="gold"
                                size="lg"
                                className="w-full"
                                onClick={handleOpen}
                                loading={openMutation.isPending}
                                disabled={
                                    (user?.coins ?? 0) <
                                    Math.floor(
                                        selected.price *
                                        quantity *
                                        (1 - (quantity >= 10 ? 0.15 : quantity >= 5 ? 0.1 : 0))
                                    )
                                }
                            >
                                Acheter et Ouvrir
                            </Button>

                            {(user?.coins ?? 0) <
                                Math.floor(
                                    selected.price *
                                    quantity *
                                    (1 - (quantity >= 10 ? 0.15 : quantity >= 5 ? 0.1 : 0))
                                ) && (
                                    <p className="text-red-400 text-xs text-center">
                                        Pas assez de pièces
                                    </p>
                                )}
                        </motion.div>
                    )}
                </AnimatePresence>
            </Modal>
        </div>
    );
}
