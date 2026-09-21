import { useQuery } from "@tanstack/react-query";
import { BoosterIcon, RerollIcon } from "@/components/ui/ItemIcon";
import { motion, AnimatePresence } from "framer-motion";
import { shopApi } from "@/api/shop";
import { boostersApi } from "@/api/boosters";
import { useRewardPopupStore, type RewardItem } from "@/stores/rewardPopupStore";
import Button from "@/components/ui/Button";
import CardImage from "@/components/card/CardImage";
import ResourceIcon from "@/components/ui/ResourceIcon";
import { FULL_TIER_ORDER, type TierAxis } from "@/utils/cardTiers";
import type { Card } from "@/types/card";
import { CosmeticPreview, COSMETIC_KIND_LABEL } from "@/components/cosmetics/CosmeticVisuals";

type RerollItem = Extract<RewardItem, { kind: "reroll" }>;
type StackItem = Extract<RewardItem, { kind: "resource" | "booster" | "reroll_token" }>;

const AXIS_LABEL: Record<TierAxis, string> = { rarity: "Rareté", quality: "Qualité", specialty: "Spécialité", jewelry: "Bijou" };
const axisValue = (card: Card, axis: TierAxis) => ({
    rarity: [card.rarity_id, card.rarity_name],
    quality: [card.quality_id, card.quality_name],
    specialty: [card.specialty_id, card.specialty_name],
    jewelry: [card.jewelry_id, card.jewelry_name],
}[axis]);

/** Vert si mieux, rouge si moins bien, neutre si identique. */
const trendClass = (delta: number) => (delta > 0 ? "text-green-400" : delta < 0 ? "text-red-400" : "text-white");

function RerollSummary({ item }: { item: RerollItem }) {
    const rows = item.axes.map((axis) => {
        const [beforeId, beforeName] = axisValue(item.before, axis);
        const [afterId, afterName] = axisValue(item.after, axis);
        const delta = FULL_TIER_ORDER[axis].indexOf(afterId) - FULL_TIER_ORDER[axis].indexOf(beforeId);
        return { label: AXIS_LABEL[axis], before: beforeName, after: afterName, delta };
    });
    rows.push({
        label: "Puissance",
        before: `⚡${item.before.power ?? "—"}`,
        after: `⚡${item.after.power ?? "—"}`,
        delta: (item.after.power ?? 0) - (item.before.power ?? 0),
    });

    return (
        <div className="flex gap-3 items-center">
            <div className="w-20 shrink-0">
                <CardImage card={item.after} size="sm" />
            </div>
            <div className="flex-1 space-y-1.5 text-sm">
                {rows.map((r) => (
                    <div key={r.label} className="grid grid-cols-[4.5rem_1fr] items-center gap-2">
                        <span className="text-white/40 text-xs">{r.label}</span>
                        <span className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-white/50">{r.before}</span>
                            <span className="text-white/30">→</span>
                            <span className={`font-bold ${trendClass(r.delta)}`}>{r.after}</span>
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

function RewardRow({ item, resourceName, boosterName }: {
    item: StackItem;
    resourceName: (id: string) => string;
    boosterName: (id: string) => string;
}) {
    if (item.kind === "resource") {
        return (
            <div className="flex items-center gap-3 bg-black/20 border border-white/5 rounded-xl px-4 py-3">
                <ResourceIcon resourceId={item.resourceId} className="w-6 h-6" />
                <span className="text-white font-bold text-lg tabular-nums">+{item.amount.toLocaleString("fr-FR")}</span>
                <span className="text-white/60 text-sm">{item.name ?? resourceName(item.resourceId)}</span>
            </div>
        );
    }
    if (item.kind === "reroll_token") {
        return (
            <div className="flex items-center gap-3 bg-accent/10 border border-accent/30 rounded-xl px-4 py-3">
                <RerollIcon className="w-6 h-6 text-white/80" />
                <span className="text-white font-bold text-lg">×{item.quantity}</span>
                <span className="text-white/70 text-sm">{item.name}</span>
            </div>
        );
    }
    return (
        <div className="flex items-center gap-3 bg-gold/10 border border-gold/30 rounded-xl px-4 py-3">
            <BoosterIcon className="w-6 h-6 text-white/80" />
            <span className="text-white font-bold text-lg">×{item.quantity}</span>
            <span className="text-white/70 text-sm">{item.name ?? boosterName(item.boosterId)}</span>
        </div>
    );
}

/** Récapitulatif de ce qui vient d'être obtenu (cadeau, achievement, niveau,
 * quête, recyclage, échange...) — un popup à la fois, dans l'ordre. */
export default function RewardPopup() {
    const batch = useRewardPopupStore((s) => s.queue[0]);
    const dismiss = useRewardPopupStore((s) => s.dismiss);

    const { data: resources } = useQuery({
        queryKey: ["resources-catalog"], queryFn: shopApi.resources, enabled: !!batch, staleTime: 5 * 60 * 1000,
    });
    // Chargé seulement quand un récapitulatif s'affiche : ce composant est monté
    // sur toutes les pages, y compris la connexion (appel non authentifié → 401).
    const { data: boosters } = useQuery({
        queryKey: ["boosters"], queryFn: boostersApi.list, enabled: !!batch, staleTime: 5 * 60 * 1000,
    });

    const resourceName = (id: string) =>
        resources?.find((r) => r.id === id)?.name ?? (id === "coins" ? "Pièces" : id);
    const boosterName = (id: string) => boosters?.find((b) => b.id === id)?.name ?? "Booster";

    const cards = batch?.items.filter((i): i is Extract<RewardItem, { kind: "card" }> => i.kind === "card") ?? [];
    const others = batch?.items.filter((i): i is StackItem => i.kind === "resource" || i.kind === "booster" || i.kind === "reroll_token") ?? [];
    const rerolls = batch?.items.filter((i): i is RerollItem => i.kind === "reroll") ?? [];
    const cosmetics = batch?.items.filter((i): i is Extract<RewardItem, { kind: "cosmetic" }> => i.kind === "cosmetic") ?? [];

    return (
        <AnimatePresence mode="wait">
            {batch && (
                <motion.div
                    key={batch.title + batch.items.length}
                    className="fixed inset-0 z-[70] flex items-center justify-center p-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                >
                    <div className="absolute inset-0 bg-black/70" onClick={dismiss} />
                    <motion.div
                        className="relative bg-game-surface rounded-2xl p-6 border border-gold/40 shadow-2xl max-w-sm w-full"
                        initial={{ scale: 0.6 }}
                        animate={{ scale: 1 }}
                        exit={{ scale: 0.6, opacity: 0 }}
                    >
                        <p className="text-gold text-xs font-semibold uppercase tracking-wide text-center mb-1">Obtenu !</p>
                        <h2 className="text-xl font-bold text-white text-center mb-4">{batch.title}</h2>

                        <div className="space-y-2 max-h-[55vh] overflow-y-auto">
                            {rerolls.map((item, i) => <RerollSummary key={`r${i}`} item={item} />)}
                            {cosmetics.map(({ cosmetic }) => (
                                <div key={cosmetic.id} className="flex items-center gap-3 bg-purple-500/10 border border-purple-400/30 rounded-xl px-4 py-3">
                                    <CosmeticPreview cosmetic={cosmetic} size={44} />
                                    <div>
                                        <p className="text-white font-bold text-sm">{cosmetic.name}</p>
                                        <p className="text-white/50 text-xs">{COSMETIC_KIND_LABEL[cosmetic.kind]} — à équiper depuis ta vitrine</p>
                                    </div>
                                </div>
                            ))}
                            {others.map((item, i) => (
                                <RewardRow key={i} item={item} resourceName={resourceName} boosterName={boosterName} />
                            ))}
                            {cards.length > 0 && (
                                <div className="grid grid-cols-3 gap-2 pt-1">
                                    {cards.map((c, i) => <CardImage key={i} card={c.card} size="sm" />)}
                                </div>
                            )}
                        </div>

                        <Button variant="gold" className="w-full mt-5" onClick={dismiss}>
                            Super !
                        </Button>
                        {batch.action && (
                            <Button
                                variant="secondary"
                                className="w-full mt-2"
                                onClick={() => { const action = batch.action!; dismiss(); action.onClick(); }}
                            >
                                {batch.action.label}
                            </Button>
                        )}
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
