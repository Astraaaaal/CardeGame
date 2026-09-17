import { useEffect, useRef, useState } from "react";
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
import { useCardSelectionStore } from "@/stores/cardSelectionStore";
import { useHasPendingTradeProposal } from "@/hooks/useTradePulse";
import { showRewards } from "@/stores/rewardPopupStore";
import BottomNav from "@/components/layout/BottomNav";
import PremiumTab, { PREMIUM_RESOURCE_ID } from "@/components/shop/PremiumTab";
import { premiumApi } from "@/api/premium";
import { getResourceBalance } from "@/utils/resources";
import { errMsg } from "@/utils/errors";

type Quantity = 1 | 5 | 10;

function BoostersTab() {
    const navigate = useNavigate();
    const { user } = useAuthStore();
    const { data: boosters, isLoading } = useBoosters();
    const openMutation = usePackOpening();
    const openOwnedMutation = useOpenOwnedBoosters();
    const tradePending = useHasPendingTradeProposal();
    const qc = useQueryClient();
    const [buyError, setBuyError] = useState("");

    const { data: inventory } = useQuery({ queryKey: ["booster-inventory"], queryFn: boostersApi.getInventory });

    const [selected, setSelected] = useState<Booster | null>(null);
    const [quantity, setQuantity] = useState<Quantity>(1);

    const buyToInventory = useMutation({
        mutationFn: ({ booster, qty }: { booster: Booster; qty: Quantity }) =>
            boostersApi.buyToInventory({ booster_id: booster.id, quantity: qty }),
        onSuccess: (res) => {
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["booster-inventory"] });
            setSelected(null);
            showRewards({
                title: "Ajouté à l'inventaire",
                items: [{ kind: "booster", boosterId: res.booster_id, quantity: res.quantity, name: res.booster_name }],
            });
        },
        onError: (e) => setBuyError(errMsg(e)),
    });

    const handleOpenOwned = (boosterId: string, ownedQuantity: number, bonusId: number | null) => {
        openOwnedMutation.mutate(
            { booster_id: boosterId, quantity: ownedQuantity, bonus_id: bonusId },
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
                    {tradePending && <TradePendingNotice />}
                    {inventory.map((o) => (
                        <div key={`${o.booster_id}-${o.bonus_id ?? "base"}`} className="flex items-center justify-between bg-gold/10 border border-gold/30 rounded-xl px-4 py-3">
                            <div>
                                <p className="text-white font-semibold text-sm">{o.booster_name}</p>
                                {o.bonus_label && <p className="text-gold text-xs">{o.bonus_label}</p>}
                                <p className="text-white/40 text-xs">×{o.quantity} possédé{o.quantity > 1 ? "s" : ""}</p>
                            </div>
                            <Button
                                variant="gold" size="sm"
                                disabled={tradePending}
                                loading={openOwnedMutation.isPending
                                    && openOwnedMutation.variables?.booster_id === o.booster_id
                                    && (openOwnedMutation.variables?.bonus_id ?? null) === o.bonus_id}
                                onClick={() => handleOpenOwned(o.booster_id, o.quantity, o.bonus_id)}
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

            <Modal open={!!selected} onClose={() => { setSelected(null); setBuyError(""); }} title={selected?.name}>
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
                                disabled={cantAfford || tradePending}
                            >
                                Acheter et ouvrir
                            </Button>
                            <Button
                                variant="secondary"
                                className="w-full"
                                loading={buyToInventory.isPending}
                                disabled={cantAfford}
                                onClick={() => { setBuyError(""); buyToInventory.mutate({ booster: selected, qty: quantity }); }}
                            >
                                Acheter → inventaire
                            </Button>
                            {buyError && <p className="text-red-400 text-xs text-center">{buyError}</p>}

                            {tradePending && <TradePendingNotice />}
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

function TradePendingNotice() {
    return (
        <p className="text-amber-300/80 text-xs text-center">
            Ouverture de boosters indisponible tant qu'une proposition d'échange attend une réponse.
        </p>
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
    const { data: allOffers, isLoading } = useQuery({ queryKey: ["shop-offers"], queryFn: shopApi.list });
    // Les offres payées en éclats vivent dans l'onglet Premium.
    const offers = allOffers?.filter((o) => o.resource_id !== PREMIUM_RESOURCE_ID);
    const requestSelection = useCardSelectionStore((s) => s.requestSelection);
    const consumeResultIfPurpose = useCardSelectionStore((s) => s.consumeResultIfPurpose);
    const [feedback, setFeedback] = useState<{ offerId: string; text: string; ok: boolean } | null>(null);
    const rerollHandled = useRef(false);
    const tradePending = useHasPendingTradeProposal();

    const buy = useMutation({
        mutationFn: ({ offer, cardId, toInventory }: { offer: ShopOffer; cardId?: string; toInventory?: boolean }) =>
            shopApi.buy(offer.id, cardId, toInventory),
        onSuccess: (res, { offer, toInventory }) => {
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["collection"] });
            if (toInventory) {
                qc.invalidateQueries({ queryKey: ["booster-inventory"] });
                showRewards({
                    title: "Ajouté à l'inventaire",
                    items: [{ kind: "booster", boosterId: offer.booster_id ?? "", quantity: 1, name: offer.name }],
                });
                setFeedback({ offerId: offer.id, text: res.message, ok: true });
                return;
            }
            if (offer.kind === "reroll" && res.previous_card && res.cards[0]) {
                const axes = ([
                    ["rarity", offer.reroll_rarity], ["quality", offer.reroll_quality],
                    ["specialty", offer.reroll_specialty], ["jewelry", offer.reroll_jewelry],
                ] as const).filter(([, on]) => on).map(([axis]) => axis);
                showRewards({ title: offer.name, items: [{ kind: "reroll", before: res.previous_card, after: res.cards[0], axes }] });
                setFeedback({ offerId: offer.id, text: res.message, ok: true });
                return;
            }
            if (offer.kind === "booster" && res.cards.length > 0) {
                // Même écran de révélation que l'achat classique d'un booster —
                // sinon les cartes obtenues apparaissent silencieusement dans la
                // collection, sans aucun retour visible ("j'ai rien reçu ?").
                setPacks([res.cards]);
                navigate("/opening");
                return;
            }
            showRewards({ title: offer.name, items: res.cards.map((card) => ({ kind: "card" as const, card })) });
            setFeedback({ offerId: offer.id, text: res.message, ok: true });
        },
        onError: (e, { offer }) => setFeedback({ offerId: offer.id, text: errMsg(e), ok: false }),
    });

    // Retour de la Collection (mode sélection) avec la carte à relancer.
    useEffect(() => {
        if (rerollHandled.current || !offers) return;
        const result = consumeResultIfPurpose(["reroll"]);
        if (!result) return;
        rerollHandled.current = true;
        const offer = offers.find((o) => o.id === result.context?.offerId);
        const cardId = result.selectedCards[0]?.id;
        if (offer && cardId) buy.mutate({ offer, cardId });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [offers]);

    const handleBuy = (offer: ShopOffer) => {
        setFeedback(null);
        if (offer.kind === "reroll") {
            requestSelection({
                max: 1,
                title: "Choisis la carte à relancer",
                excludeIds: [],
                returnTo: "/shop",
                context: { purpose: "reroll", offerId: offer.id },
            });
            navigate("/collection");
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
                        const blockedByTrade = tradePending && o.kind === "booster";
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
                                    disabled={limitReached || blockedByTrade}
                                    loading={buy.isPending && buy.variables?.offer.id === o.id && !buy.variables?.toInventory}
                                    onClick={() => handleBuy(o)}
                                >
                                    {limitReached ? "Limite atteinte" : o.kind === "booster" ? "Acheter et ouvrir" : "Acheter"}
                                </Button>
                                {o.kind === "booster" && !limitReached && (
                                    <Button
                                        variant="secondary"
                                        size="sm"
                                        className="w-full mt-2"
                                        loading={buy.isPending && buy.variables?.offer.id === o.id && !!buy.variables?.toInventory}
                                        onClick={() => { setFeedback(null); buy.mutate({ offer: o, toInventory: true }); }}
                                    >
                                        Acheter → inventaire
                                    </Button>
                                )}
                                {blockedByTrade && <div className="mt-2"><TradePendingNotice /></div>}
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
        </>
    );
}

type Tab = "boosters" | "resources" | "premium";

export default function Shop() {
    const navigate = useNavigate();
    const { user } = useAuthStore();
    const [tab, setTab] = useState<Tab>(() => {
        if (new URLSearchParams(window.location.search).has("premium")) return "premium";
        return useCardSelectionStore.getState().result?.context?.purpose === "reroll" ? "resources" : "boosters";
    });
    const { data: premium } = useQuery({ queryKey: ["premium-status"], queryFn: premiumApi.status });
    const tabs: { key: Tab; label: string }[] = [
        { key: "boosters", label: "Boosters" },
        { key: "resources", label: "Ressources" },
        ...(premium?.access ? [{ key: "premium" as const, label: "✦ Premium" }] : []),
    ];

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
                {tabs.map((t) => (
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
                {tab === "boosters" && <BoostersTab />}
                {tab === "resources" && <ResourcesTab />}
                {tab === "premium" && premium?.access && <PremiumTab />}
            </main>

            <BottomNav />
        </div>
    );
}
