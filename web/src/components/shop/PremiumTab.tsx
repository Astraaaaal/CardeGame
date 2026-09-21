import { useEffect, useState } from "react";
import { BoosterIcon } from "@/components/ui/ItemIcon";
import { toast } from "@/stores/toastStore";
import { useSearchParams, Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { premiumApi } from "@/api/premium";
import { shopApi } from "@/api/shop";
import type { ShopOffer } from "@/types/shop";
import { formatEuros, type PremiumProduct } from "@/types/premium";
import { showRewards } from "@/stores/rewardPopupStore";
import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { CosmeticPreview, COSMETIC_KIND_LABEL } from "@/components/cosmetics/CosmeticVisuals";
import { errMsg } from "@/utils/errors";
import { LIMIT_WHEN_LABEL, LIMIT_PERIOD_LABEL } from "@/utils/purchaseLimits";

export const PREMIUM_RESOURCE_ID = "shards";

type Category = "cosmetic" | "booster" | "bundle" | "card";
const CATEGORIES: { key: Category; label: string }[] = [
    { key: "cosmetic", label: "Cosmétiques" },
    { key: "booster", label: "Boosters" },
    { key: "bundle", label: "Lots" },
    { key: "card", label: "Cartes" },
];
const categoryOf = (o: ShopOffer): Category =>
    o.kind === "cosmetic" ? "cosmetic" : o.kind === "booster" ? "booster" : o.kind === "bundle" ? "bundle" : "card";

const isShardPack = (p: PremiumProduct) =>
    p.grants.length === 1 && p.grants[0].kind === "resource" && p.grants[0].id === PREMIUM_RESOURCE_ID;
const shardsOf = (p: PremiumProduct) => p.grants.find((g) => g.id === PREMIUM_RESOURCE_ID)?.amount ?? 0;

/** Visuel d'un pack d'éclats : plus de cristaux pour les gros packs. */
function ShardStack({ level }: { level: number }) {
    const count = Math.min(6, level + 1);
    return (
        <div className="h-12 flex items-end justify-center -space-x-1">
            {Array.from({ length: count }, (_, i) => (
                <span key={i} className="text-cyan-300 drop-shadow-[0_0_6px_rgba(103,232,249,0.6)] leading-none"
                    style={{ fontSize: 18 + ((i * 7) % 4) * 3 + level * 2, transform: `translateY(${(i % 2) * -4}px)` }}>
                    ✦
                </span>
            ))}
        </div>
    );
}

/**
 * Onglet premium : lots en euros (paiement Stripe) et catalogue payé en
 * Éclats (cosmétiques, boosters, cartes). Visible seulement quand la
 * boutique premium est ouverte ou pour les comptes testeurs.
 */
export default function PremiumTab() {
    const qc = useQueryClient();
    const [params, setParams] = useSearchParams();
    const setFeedback = (f: { key: string; text: string; ok: boolean } | null) => {
        if (f) (f.ok ? toast.success : toast.error)(f.text);
    };
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
    const [category, setCategory] = useState<Category>("cosmetic");
    const available = CATEGORIES.filter((c) => catalog.some((o) => categoryOf(o) === c.key));
    const activeCategory = available.some((c) => c.key === category) ? category : available[0]?.key;
    const shownCatalog = catalog.filter((o) => categoryOf(o) === activeCategory);

    // Packs d'éclats seuls (grille) vs lots mêlant plusieurs contenus (cartes larges).
    const shardPacks = (products ?? []).filter(isShardPack).sort((x, y) => x.price_cents - y.price_cents);
    const bundles = (products ?? []).filter((p) => !isShardPack(p));
    const baseRate = shardPacks.length ? shardsOf(shardPacks[0]) / shardPacks[0].price_cents : 0;
    const bestPackId = shardPacks.length > 1
        ? shardPacks.reduce((best, p) => (shardsOf(p) / p.price_cents > shardsOf(best) / best.price_cents ? p : best)).id
        : null;

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

            <section className="space-y-4">
                {isLoading ? (
                    <LoadingSpinner text="Chargement..." />
                ) : !products?.length ? (
                    <p className="text-white/30 text-sm">Aucune offre pour l'instant.</p>
                ) : (
                    <>
                        {shardPacks.length > 0 && (
                            <div>
                                <h3 className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-2">Éclats</h3>
                                {!status.payments_available && (
                                    <p className="text-white/40 text-[11px] mb-2">Paiement bientôt disponible.</p>
                                )}
                                <div className="grid grid-cols-2 gap-3">
                                    {shardPacks.map((p, i) => {
                                        const shards = shardsOf(p);
                                        const bonus = baseRate ? Math.round(((shards / p.price_cents) / baseRate - 1) * 100) : 0;
                                        const best = p.id === bestPackId;
                                        return (
                                            <div key={p.id}
                                                className={`relative rounded-2xl p-3 pt-4 border flex flex-col items-center text-center gap-1.5 bg-gradient-to-b from-purple-600/15 to-game-surface ${
                                                    best ? "border-gold/70 shadow-lg shadow-gold/10" : "border-purple-400/30"}`}>
                                                {best && (
                                                    <span className="absolute -top-2 left-1/2 -translate-x-1/2 whitespace-nowrap bg-gold text-game-bg text-[10px] font-extrabold px-2 py-0.5 rounded-full">
                                                        Meilleure offre
                                                    </span>
                                                )}
                                                {bonus > 0 && (
                                                    <span className="absolute top-1.5 right-1.5 bg-green-500/90 text-white text-[10px] font-extrabold px-1.5 py-0.5 rounded-full">
                                                        +{bonus} %
                                                    </span>
                                                )}
                                                <ShardStack level={i} />
                                                <p className="text-white font-extrabold text-lg tabular-nums leading-none">
                                                    {shards.toLocaleString("fr-FR")}
                                                </p>
                                                <p className="text-white/40 text-[10px] -mt-1">éclats</p>
                                                <Button
                                                    variant="gold" size="sm" className="w-full mt-auto"
                                                    disabled={!status.payments_available || p.already_purchased}
                                                    loading={checkout.isPending && checkout.variables === p.id}
                                                    onClick={() => checkout.mutate(p.id)}
                                                >
                                                    {formatEuros(p.price_cents)}
                                                </Button>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}

                        {bundles.length > 0 && (
                            <div>
                                <h3 className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-2">Lots</h3>
                                <div className="space-y-3">
                                    {bundles.map((p) => (
                                        <div key={p.id} className="bg-gradient-to-r from-purple-600/20 to-cyan-500/10 rounded-2xl p-4 border border-purple-400/40">
                                            <div className="flex items-center justify-between mb-1">
                                                <h4 className="text-white font-bold">{p.name}</h4>
                                                {p.once_per_account && (
                                                    <span className="text-[10px] font-bold text-amber-300 border border-amber-300/40 rounded-full px-2 py-0.5">
                                                        1 par compte
                                                    </span>
                                                )}
                                            </div>
                                            {p.description && <p className="text-white/50 text-xs mb-2">{p.description}</p>}
                                            <div className="flex flex-wrap gap-1.5 mb-3">
                                                {p.grants.map((g, i) => (
                                                    <span key={i} className="text-xs text-white bg-black/30 rounded-lg px-2 py-1">
                                                        {g.kind === "cosmetic" ? g.name : `${g.amount.toLocaleString("fr-FR")} ${g.name}`}
                                                    </span>
                                                ))}
                                            </div>
                                            {p.limit_period !== "none" && (
                                                <p className="text-white/40 text-[11px] mb-2">{p.limit_count} {LIMIT_PERIOD_LABEL[p.limit_period]}</p>
                                            )}
                                            <Button
                                                variant="gold" size="sm" className="w-full"
                                                disabled={!status.payments_available || p.already_purchased}
                                                loading={checkout.isPending && checkout.variables === p.id}
                                                onClick={() => checkout.mutate(p.id)}
                                            >
                                                {p.already_purchased ? "Déjà acheté"
                                                    : status.payments_available ? `Acheter — ${formatEuros(p.price_cents)}` : "Paiement bientôt disponible"}
                                            </Button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        <p className="text-white/30 text-[11px] leading-snug">
                            Contenu numérique livré immédiatement : en validant ton achat, tu renonces à ton droit de rétractation.
                            Voir les <Link to="/legal" className="underline">conditions de vente</Link>.
                        </p>
                    </>
                )}
            </section>

            <section>
                <h3 className="text-white/50 text-xs font-semibold uppercase tracking-wide mb-2">Dépenser mes éclats</h3>
                {catalog.length > 0 && (
                    <div className="flex gap-1.5 mb-3">
                        {CATEGORIES.filter((c) => catalog.some((o) => categoryOf(o) === c.key)).map((c) => (
                            <button key={c.key}
                                className={`flex-1 py-1.5 rounded-lg text-xs font-bold ${category === c.key ? "bg-accent text-white" : "bg-white/10 text-white/60"}`}
                                onClick={() => setCategory(c.key)}>
                                {c.label}
                            </button>
                        ))}
                    </div>
                )}
                {shownCatalog.length === 0 ? (
                    <p className="text-white/30 text-sm">Aucun article pour l'instant.</p>
                ) : (
                    <div className="grid grid-cols-2 gap-3">
                        {shownCatalog.map((o) => {
                            const cosmetic = cosmetics?.find((c) => c.id === o.cosmetic_id);
                            const cantAfford = status.shards < o.price;
                            const limited = o.limit_period !== "none";
                            const limitReached = limited && o.purchases_in_period >= o.limit_count;
                            return (
                                <div key={o.id} className="bg-game-surface rounded-2xl p-3 border border-white/10 flex flex-col gap-2">
                                    <div className="h-24 rounded-xl bg-black/20 flex items-center justify-center">
                                        {cosmetic ? <CosmeticPreview cosmetic={cosmetic} size={72} /> : <BoosterIcon className="w-12 h-12 text-white/70" />}
                                    </div>
                                    <div className="min-h-[2.5rem]">
                                        <p className="text-white text-sm font-semibold leading-tight">{o.name}</p>
                                        {cosmetic && <p className="text-white/40 text-[11px]">{COSMETIC_KIND_LABEL[cosmetic.kind]}</p>}
                                        {o.kind === "bundle" && (
                                            <p className="text-white/40 text-[11px] leading-tight">
                                                {o.grants.map((g) => (g.kind === "cosmetic" ? g.name : `${g.amount.toLocaleString("fr-FR")} ${g.name}`)).join(" + ")}
                                            </p>
                                        )}
                                    </div>
                                    {limited && (
                                        <p className="text-white/40 text-[11px]">
                                            {o.purchases_in_period}/{o.limit_count} {LIMIT_WHEN_LABEL[o.limit_period]}
                                        </p>
                                    )}
                                    <Button
                                        variant="primary" size="sm" className="w-full mt-auto"
                                        disabled={cantAfford || limitReached}
                                        loading={buy.isPending && buy.variables?.id === o.id}
                                        onClick={() => { setFeedback(null); buy.mutate(o); }}
                                    >
                                        {limitReached ? "Limite atteinte" : `✦ ${o.price.toLocaleString("fr-FR")}`}
                                    </Button>
                                </div>
                            );
                        })}
                    </div>
                )}
            </section>
        </div>
    );
}
