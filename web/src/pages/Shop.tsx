import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { useAuthStore } from "@/stores/authStore";
import { useGameStore } from "@/stores/gameStore";
import { useBoosters } from "@/hooks/useBoosters";
import { usePackOpening, useOpenOwnedBoosters } from "@/hooks/usePackOpening";
import { boostersApi } from "@/api/boosters";
import { shopApi } from "@/api/shop";
import type { Booster } from "@/types/booster";
import type { ShopOffer } from "@/types/shop";
import Button from "@/components/ui/Button";
import CoinDisplay from "@/components/player/CoinDisplay";
import BoosterCard from "@/components/shop/BoosterCard";
import PriceTag from "@/components/shop/PriceTag";
import Modal from "@/components/ui/Modal";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import CardPickerModal from "@/components/card/CardPickerModal";
import BottomNav from "@/components/layout/BottomNav";
import { getResourceBalance } from "@/utils/resources";
import { errMsg } from "@/utils/errors";

type Quantity = 1 | 5 | 10;

function BoostersTab() {
    const navigate = useNavigate();
    const { user } = useAuthStore();
    const { data: boosters, isLoading } = useBoosters();
    const openMutation = usePackOpening();
    const openOwnedMutation = useOpenOwnedBoosters();

    const { data: inventory } = useQuery({ queryKey: ["booster-inventory"], queryFn: boostersApi.getInventory });

    const [selected, setSelected] = useState<Booster | null>(null);
    const [quantity, setQuantity] = useState<Quantity>(1);

    const handleOpenOwned = (boosterId: string, ownedQuantity: number) => {
        openOwnedMutation.mutate(
            { booster_id: boosterId, quantity: ownedQuantity },
            { onSuccess: () => navigate("/opening") },
        );
    };

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

    const discount = (q: Quantity) => (q >= 10 ? 0.15 : q >= 5 ? 0.1 : 0);
    const totalPrice = selected
        ? Math.floor(selected.price * quantity * (1 - discount(quantity)))
        : 0;
    const balance = getResourceBalance(user, selected?.resource_id ?? "coins");
    const cantAfford = !!selected && balance < totalPrice;

    return (
        <>
            {!!inventory?.length && (
                <div className="max-w-sm mx-auto mb-5 space-y-2">
                    <h3 className="text-white/50 text-xs font-semibold uppercase tracking-wide">
                        Boosters reçus — à ouvrir
                    </h3>
                    {inventory.map((o) => (
                        <div key={o.booster_id} className="flex items-center justify-between bg-gold/10 border border-gold/30 rounded-xl px-4 py-3">
                            <div>
                                <p className="text-white font-semibold text-sm">{o.booster_name}</p>
                                <p className="text-white/40 text-xs">×{o.quantity} possédé{o.quantity > 1 ? "s" : ""}</p>
                            </div>
                            <Button
                                variant="gold" size="sm"
                                loading={openOwnedMutation.isPending && openOwnedMutation.variables?.booster_id === o.booster_id}
                                onClick={() => handleOpenOwned(o.booster_id, o.quantity)}
                            >
                                Ouvrir
                            </Button>
                        </div>
                    ))}
                </div>
            )}

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

            <Modal open={!!selected} onClose={() => setSelected(null)} title={selected?.name}>
                <AnimatePresence>
                    {selected && (
                        <motion.div
                            className="space-y-4"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                        >
                            <p className="text-white/60 text-sm">{selected.description}</p>

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
                                <PriceTag
                                    basePrice={selected.price}
                                    quantity={quantity}
                                    resourceId={selected.resource_id}
                                />
                            </div>

                            <Button
                                variant="gold"
                                size="lg"
                                className="w-full"
                                onClick={handleOpen}
                                loading={openMutation.isPending}
                                disabled={cantAfford}
                            >
                                Acheter et Ouvrir
                            </Button>

                            {cantAfford && (
                                <p className="text-red-400 text-xs text-center">
                                    Pas assez de {selected.resource_name.toLowerCase()}
                                </p>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>
            </Modal>
        </>
    );
}

function offerPreview(o: ShopOffer): string {
    if (o.kind === "booster") {
        const bits = ["Ouvre 1 pack"];
        if (o.force_min_rarity_name) bits.push(`min. ${o.force_min_rarity_name} garanti`);
        if (o.rarity_weight_multiplier) bits.push(`x${o.rarity_weight_multiplier} chances rare+`);
        return bits.join(" · ");
    }
    if (o.kind === "specific_card") {
        return [o.character_name, o.rarity_name, o.quality_name, o.specialty_name, o.jewelry_name]
            .filter(Boolean).join(" · ");
    }
    // reroll
    const axes = [
        o.reroll_rarity && "rareté", o.reroll_quality && "qualité",
        o.reroll_specialty && "spécialité", o.reroll_jewelry && "jewelry",
    ].filter(Boolean).join(" + ");
    const mode = o.reroll_mode === "guaranteed_min" ? "garanti égal ou mieux" : "aléatoire (risqué)";
    return `Retire ${axes} — ${mode}`;
}

function ResourcesTab() {
    const navigate = useNavigate();
    const qc = useQueryClient();
    const { setPacks } = useGameStore();
    const { data: offers, isLoading } = useQuery({ queryKey: ["shop-offers"], queryFn: shopApi.list });
    const [pickerFor, setPickerFor] = useState<ShopOffer | null>(null);
    const [feedback, setFeedback] = useState<{ offerId: string; text: string; ok: boolean } | null>(null);

    const buy = useMutation({
        mutationFn: ({ offer, cardId }: { offer: ShopOffer; cardId?: string }) =>
            shopApi.buy(offer.id, cardId),
        onSuccess: (res, { offer }) => {
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["collection"] });
            setPickerFor(null);
            if (offer.kind === "booster" && res.cards.length > 0) {
                // Même écran de révélation que l'achat classique d'un booster —
                // sinon les cartes obtenues apparaissent silencieusement dans la
                // collection, sans aucun retour visible ("j'ai rien reçu ?").
                setPacks([res.cards]);
                navigate("/opening");
                return;
            }
            setFeedback({ offerId: offer.id, text: res.message, ok: true });
        },
        onError: (e, { offer }) => setFeedback({ offerId: offer.id, text: errMsg(e), ok: false }),
    });

    const handleBuy = (offer: ShopOffer) => {
        setFeedback(null);
        if (offer.kind === "reroll") {
            setPickerFor(offer);
        } else {
            buy.mutate({ offer });
        }
    };

    return (
        <>
            {isLoading ? (
                <LoadingSpinner text="Chargement du shop..." />
            ) : !offers || offers.length === 0 ? (
                <p className="text-white/40 text-sm text-center mt-10">
                    Aucune offre disponible pour l'instant.
                </p>
            ) : (
                <div className="space-y-3 max-w-sm mx-auto">
                    {offers.map((o) => {
                        const limitReached = !!o.purchase_limit_per_day
                            && o.purchases_today >= o.purchase_limit_per_day;
                        return (
                            <div key={o.id} className={`bg-game-surface rounded-2xl p-4 border ${o.featured_today ? "border-gold/60" : "border-white/10"}`}>
                                <div className="flex items-center justify-between mb-1">
                                    <h3 className="text-white font-bold">
                                        {o.name}
                                    </h3>
                                    <span className="text-purple-300 font-bold text-sm">
                                        {o.price} {o.resource_name}
                                    </span>
                                </div>
                                <p className="text-white/50 text-xs mb-2">{offerPreview(o)}</p>
                                {o.description && (
                                    <p className="text-white/40 text-xs mb-2">{o.description}</p>
                                )}
                                {o.purchase_limit_per_day && (
                                    <p className="text-white/40 text-xs mb-2">
                                        {o.purchases_today}/{o.purchase_limit_per_day} aujourd'hui
                                    </p>
                                )}
                                <Button
                                    variant="primary"
                                    size="sm"
                                    className="w-full"
                                    disabled={limitReached}
                                    loading={buy.isPending && buy.variables?.offer.id === o.id}
                                    onClick={() => handleBuy(o)}
                                >
                                    {limitReached ? "Limite atteinte" : "Acheter"}
                                </Button>
                                {feedback?.offerId === o.id && (
                                    <p className={`text-xs mt-2 ${feedback.ok ? "text-green-400" : "text-red-400"}`}>
                                        {feedback.text}
                                    </p>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {pickerFor && (
                <CardPickerModal
                    onClose={() => setPickerFor(null)}
                    onPick={(cardId) => buy.mutate({ offer: pickerFor, cardId })}
                />
            )}
        </>
    );
}

type Tab = "boosters" | "resources";

export default function Shop() {
    const navigate = useNavigate();
    const { user } = useAuthStore();
    const [tab, setTab] = useState<Tab>("boosters");

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button className="text-accent text-sm font-semibold" onClick={() => navigate("/")}>
                    Retour
                </button>
                <h1 className="text-white font-bold">Boutique</h1>
                <CoinDisplay coins={user?.coins ?? 0} />
            </header>

            <div className="flex border-b border-white/5">
                {([
                    { key: "boosters", label: "Boosters" },
                    { key: "resources", label: "Ressources" },
                ] as const).map((t) => (
                    <button
                        key={t.key}
                        className={`flex-1 py-2.5 text-sm font-semibold transition-colors ${
                            tab === t.key ? "text-accent border-b-2 border-accent" : "text-white/40 hover:text-white/70"
                        }`}
                        onClick={() => setTab(t.key)}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            <main className="flex-1 px-4 py-6">
                {tab === "boosters" ? <BoostersTab /> : <ResourcesTab />}
            </main>

            <BottomNav />
        </div>
    );
}
