import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { premiumApi } from "@/api/premium";
import { shopApi } from "@/api/shop";
import type { ShopOffer } from "@/types/shop";
import { formatEuros } from "@/types/premium";
import { showRewards } from "@/stores/rewardPopupStore";
import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { CosmeticPreview, COSMETIC_KIND_LABEL } from "@/components/cosmetics/CosmeticVisuals";
import { errMsg } from "@/utils/errors";

export const PREMIUM_RESOURCE_ID = "shards";

/**
 * Onglet premium : lots en euros (paiement Stripe) et catalogue payé en
 * Éclats (cosmétiques, boosters, cartes). Visible seulement quand la
 * boutique premium est ouverte ou pour les comptes testeurs.
 */
export default function PremiumTab() {
    const qc = useQueryClient();
    const [params, setParams] = useSearchParams();
    const [feedback, setFeedback] = useState<{ key: string; text: string; ok: boolean } | null>(null);
    const paymentReturn = params.get("premium");

    const { data: status } = useQuery({ queryKey: ["premium-status"], queryFn: premiumApi.status });
    const { data: products, isLoading } = useQuery({
        queryKey: ["premium-products"], queryFn: premiumApi.products, enabled: !!status?.access,
    });
    const { data: cosmetics } = useQuery({
        queryKey: ["premium-cosmetics"], queryFn: premiumApi.cosmetics, enabled: !!status?.access,
    });
    const { data: offers } = useQuery({ queryKey: ["shop-offers"], queryFn: shopApi.list });
    // Le reroll passe par la sélection de carte de l'onglet Ressources : pas proposé ici.
    const catalog = (offers ?? []).filter((o) => o.resource_id === PREMIUM_RESOURCE_ID && o.kind !== "reroll");

    // Retour de la page de paiement : le crédit arrive par webhook, quelques secondes après.
    useEffect(() => {
        if (paymentReturn !== "success") return;
        const refresh = () => {
            qc.invalidateQueries({ queryKey: ["premium-status"] });
            qc.invalidateQueries({ queryKey: ["premium-products"] });
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["booster-inventory"] });
            qc.invalidateQueries({ queryKey: ["my-cosmetics"] });
        };
        refresh();
        const timers = [3000, 8000, 15000].map((ms) => setTimeout(refresh, ms));
        return () => timers.forEach(clearTimeout);
    }, [paymentReturn, qc]);

    const checkout = useMutation({
        mutationFn: premiumApi.checkout,
        onSuccess: (url) => { window.location.href = url; },
        onError: (e, productId) => setFeedback({ key: productId, text: errMsg(e), ok: false }),
    });

    const buy = useMutation({
        mutationFn: (offer: ShopOffer) => shopApi.buy(offer.id, undefined, offer.kind === "booster"),
        onSuccess: (res, offer) => {
            qc.invalidateQueries({ queryKey: ["shop-offers"] });
            qc.invalidateQueries({ queryKey: ["premium-cosmetics"] });
            qc.invalidateQueries({ queryKey: ["premium-status"] });
            qc.invalidateQueries({ queryKey: ["player"] });
            qc.invalidateQueries({ queryKey: ["collection"] });
            qc.invalidateQueries({ queryKey: ["booster-inventory"] });
            qc.invalidateQueries({ queryKey: ["my-cosmetics"] });
            const cosmetic = cosmetics?.find((c) => c.id === offer.cosmetic_id);
            if (offer.kind === "cosmetic" && cosmetic) {
                showRewards({ title: offer.name, items: [{ kind: "cosmetic", cosmetic }] });
            } else if (offer.kind === "booster") {
                showRewards({ title: "Ajouté à l'inventaire", items: [{ kind: "booster", boosterId: offer.booster_id ?? "", quantity: 1, name: offer.name }] });
            } else {
                showRewards({ title: offer.name, items: res.cards.map((card) => ({ kind: "card" as const, card })) });
            }
            setFeedback({ key: offer.id, text: res.message, ok: true });
        },
        onError: (e, offer) => setFeedback({ key: offer.id, text: errMsg(e), ok: false }),
    });

    if (!status) return <LoadingSpinner text="Chargement..." />;

    return (
        <div className="max-w-sm mx-auto space-y-6">
            <div className="flex items-center justify-between bg-gradient-to-r from-purple-600/20 to-cyan-500/20 border border-purple-400/30 rounded-2xl px-4 py-3">
                <span className="text-white/70 text-sm">Tes éclats</span>
                <span className="text-white font-extrabold text-xl tabular-nums">✦ {status.shards.toLocaleString("fr-FR")}</span>
            </div>

            {paymentReturn && (
                <div className={`rounded-xl px-4 py-3 text-sm ${paymentReturn === "success" ? "bg-green-500/10 text-green-300" : "bg-white/5 text-white/60"}`}>
                    {paymentReturn === "success"
                        ? "Paiement reçu, merci ! Tes achats sont crédités dans quelques secondes."
                        : "Paiement annulé, rien n'a été débité."}
                    <button className="ml-2 text-xs underline" onClick={() => setParams({}, { replace: true })}>OK</button>
                </div>
            )}

            <section>
                <h3 className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-2">Éclats et lots</h3>
                {isLoading ? (
                    <LoadingSpinner text="Chargement..." />
                ) : !products?.length ? (
                    <p className="text-white/30 text-sm">Aucune offre pour l'instant.</p>
                ) : (
                    <div className="space-y-3">
                        {products.map((p) => (
                            <div key={p.id} className="bg-game-surface rounded-2xl p-4 border border-purple-400/30">
                                <div className="flex items-center justify-between mb-1">
                                    <h4 className="text-white font-bold">{p.name}</h4>
                                    <span className="text-white font-bold">{formatEuros(p.price_cents)}</span>
                                </div>
                                {p.description && <p className="text-white/40 text-xs mb-2">{p.description}</p>}
                                <ul className="text-white/70 text-sm space-y-0.5 mb-3">
                                    {p.grants.map((g, i) => (
                                        <li key={i}>• {g.kind === "cosmetic" ? g.name : `${g.amount.toLocaleString("fr-FR")} × ${g.name}`}</li>
                                    ))}
                                </ul>
                                {p.once_per_account && (
                                    <p className="text-amber-300/80 text-xs mb-2">
                                        {p.already_purchased ? "Déjà acheté (une fois par compte)." : "Achetable une seule fois par compte."}
                                    </p>
                                )}
                                <Button
                                    variant="gold" size="sm" className="w-full"
                                    disabled={!status.payments_available || p.already_purchased}
                                    loading={checkout.isPending && checkout.variables === p.id}
                                    onClick={() => { setFeedback(null); checkout.mutate(p.id); }}
                                >
                                    {status.payments_available ? `Acheter — ${formatEuros(p.price_cents)}` : "Paiement bientôt disponible"}
                                </Button>
                                {feedback?.key === p.id && (
                                    <p className={`text-xs mt-2 ${feedback.ok ? "text-green-400" : "text-red-400"}`}>{feedback.text}</p>
                                )}
                            </div>
                        ))}
                        <p className="text-white/30 text-[11px] leading-snug">
                            Contenu numérique livré immédiatement après le paiement : en validant ton achat, tu
                            demandes son exécution immédiate et renonces à ton droit de rétractation.
                            Voir les <Link to="/legal" className="underline">conditions de vente</Link>.
                        </p>
                    </div>
                )}
            </section>

            <section>
                <h3 className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-2">Catalogue en éclats</h3>
                {catalog.length === 0 ? (
                    <p className="text-white/30 text-sm">Aucun article pour l'instant.</p>
                ) : (
                    <div className="grid grid-cols-2 gap-3">
                        {catalog.map((o) => {
                            const cosmetic = cosmetics?.find((c) => c.id === o.cosmetic_id);
                            const cantAfford = status.shards < o.price;
                            const limitReached = !!o.purchase_limit_per_day && o.purchases_today >= o.purchase_limit_per_day;
                            return (
                                <div key={o.id} className="bg-game-surface rounded-2xl p-3 border border-white/10 flex flex-col gap-2">
                                    <div className="h-16 flex items-center justify-center">
                                        {cosmetic ? <CosmeticPreview cosmetic={cosmetic} size={52} /> : <span className="text-3xl">🎴</span>}
                                    </div>
                                    <div className="min-h-[2.5rem]">
                                        <p className="text-white text-sm font-semibold leading-tight">{o.name}</p>
                                        {cosmetic && <p className="text-white/40 text-[11px]">{COSMETIC_KIND_LABEL[cosmetic.kind]}</p>}
                                    </div>
                                    {o.purchase_limit_per_day && (
                                        <p className="text-white/40 text-[11px]">{o.purchases_today}/{o.purchase_limit_per_day} aujourd'hui</p>
                                    )}
                                    <Button
                                        variant="primary" size="sm" className="w-full mt-auto"
                                        disabled={cantAfford || limitReached}
                                        loading={buy.isPending && buy.variables?.id === o.id}
                                        onClick={() => { setFeedback(null); buy.mutate(o); }}
                                    >
                                        {limitReached ? "Limite atteinte" : `✦ ${o.price.toLocaleString("fr-FR")}`}
                                    </Button>
                                    {feedback?.key === o.id && (
                                        <p className={`text-[11px] ${feedback.ok ? "text-green-400" : "text-red-400"}`}>{feedback.text}</p>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </section>
        </div>
    );
}
