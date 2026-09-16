import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { shopApi } from "@/api/shop";
import { useBoosters } from "@/hooks/useBoosters";
import { useRewardPopupStore, type RewardItem } from "@/stores/rewardPopupStore";
import Button from "@/components/ui/Button";
import CardImage from "@/components/card/CardImage";
import ResourceIcon from "@/components/ui/ResourceIcon";

function RewardRow({ item, resourceName, boosterName }: {
    item: Exclude<RewardItem, { kind: "card" }>;
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
    return (
        <div className="flex items-center gap-3 bg-gold/10 border border-gold/30 rounded-xl px-4 py-3">
            <span className="text-xl">🎴</span>
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
    const { data: boosters } = useBoosters();

    const resourceName = (id: string) =>
        resources?.find((r) => r.id === id)?.name ?? (id === "coins" ? "Pièces" : id);
    const boosterName = (id: string) => boosters?.find((b) => b.id === id)?.name ?? "Booster";

    const cards = batch?.items.filter((i): i is Extract<RewardItem, { kind: "card" }> => i.kind === "card") ?? [];
    const others = batch?.items.filter((i): i is Exclude<RewardItem, { kind: "card" }> => i.kind !== "card") ?? [];

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
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
