import { rgbCss as rarityColorToCSS } from "@/utils/format";
import { useMemo, useState } from "react";
import { motion, AnimatePresence, useAnimationControls } from "framer-motion";
import type { Card } from "@/types/card";
import { useProbabilities } from "@/hooks/useCollection";
import { suspenseSteps, type SuspenseStep, type TierAxis } from "@/utils/cardTiers";
import CardImage from "./CardImage";
import {
    RarityHalo, JewelrySparkles, SpecialtyOverlay, QualityStars, TypeOutline, DiagonalSheen,
    RARITY_TEXT, BackEdgeHint, bestHiddenTier, type Tier,
} from "./CardEffects";
import TiltCard from "./TiltCard";
import { useTypes, typeColor } from "@/hooks/useTypes";
import { isPolishedCard } from "@/utils/cardTiers";

interface CardRevealProps {
    card: Card;
    onNext: () => void;
}


/** Dernier palier dévoilé sur un axe (undefined si aucun). */
function currentTier(revealed: SuspenseStep[], axis: TierAxis): Tier | undefined {
    const onAxis = revealed.filter((s) => s.axis === axis);
    return onAxis.length ? { id: onAxis[onAxis.length - 1].id, level: onAxis.length } : undefined;
}

/**
 * Révélation d'une carte avec suspense : chaque palier remarquable de la
 * carte (rareté, bijou, spécialité, qualité — cf. utils/cardTiers.ts) demande
 * un clic et ajoute son effet avant que la carte ne se retourne.
 */
export default function CardReveal({ card, onNext }: CardRevealProps) {
    const steps = useMemo(() => suspenseSteps(card), [card]);
    const [revealedCount, setRevealedCount] = useState(0);
    const [flipped, setFlipped] = useState(false);
    const { data: tiers } = useProbabilities(true);
    const { data: types } = useTypes();
    const shake = useAnimationControls();

    const revealed = steps.slice(0, revealedCount);
    const rarity = currentTier(revealed, "rarity");
    const jewelry = currentTier(revealed, "jewelry");
    const specialty = currentTier(revealed, "specialty");
    const quality = currentTier(revealed, "quality");
    const lastStep = revealed[revealed.length - 1];
    const hint = bestHiddenTier(steps.slice(revealedCount));

    const tierName = (step: SuspenseStep) => {
        const list = tiers && {
            rarity: tiers.rarities, jewelry: tiers.jewelries, specialty: tiers.specialties, quality: tiers.qualities,
        }[step.axis];
        return list?.find((t) => t.id === step.id)?.name ?? step.id;
    };

    const handleClick = () => {
        if (flipped) {
            onNext();
        } else if (revealedCount < steps.length) {
            setRevealedCount((n) => n + 1);
            shake.start({ scale: [1, 1.07, 1], rotate: [0, -2, 2, 0], transition: { duration: 0.35 } });
        } else {
            setFlipped(true);
        }
    };

    const rarityColor = rarityColorToCSS(card.rarity_color);

    return (
        <div className="flex flex-col items-center justify-center gap-6 cursor-pointer select-none" onClick={handleClick}>
            <TiltCard className="relative w-56 aspect-[5/7]">
                {rarity && <RarityHalo tier={rarity} />}
                {jewelry && <JewelrySparkles tier={jewelry} />}

                <motion.div className="absolute inset-0" animate={shake}>
                    <AnimatePresence mode="wait">
                        {!flipped ? (
                            <motion.div
                                key="back"
                                className="absolute inset-0 rounded-2xl overflow-hidden bg-gradient-to-br
                                     from-accent/40 to-purple-600/40 border-2 border-white/20
                                     flex items-center justify-center"
                                initial={{ rotateY: 0 }}
                                exit={{ rotateY: 90 }}
                                transition={{ duration: 0.25 }}
                            >
                                {card.booster_cover_url && (
                                    <img
                                        src={`/boosters/${card.booster_cover_url}`}
                                        alt=""
                                        className="w-full h-full object-cover"
                                    />
                                )}
                                {specialty && <SpecialtyOverlay id={specialty.id} />}
                            </motion.div>
                        ) : (
                            <motion.div
                                key="front"
                                className="absolute inset-0"
                                initial={{ rotateY: -90 }}
                                animate={{ rotateY: 0 }}
                                transition={{ duration: 0.25 }}
                            >
                                <div className="absolute inset-0 rounded-xl overflow-hidden">
                                    <CardImage card={card} size="lg" />
                                    {isPolishedCard(card) && <DiagonalSheen />}
                                </div>
                                {card.specialty_id === "full_art" && (
                                    <TypeOutline color={typeColor(types, card.character_type)} />
                                )}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.div>
                {!flipped && <BackEdgeHint hint={hint} />}
            </TiltCard>

            <QualityStars level={quality?.level ?? 0} />

            {!flipped ? (
                <div className="text-center min-h-[3.5rem]">
                    {/* Pas d'animation de sortie : un tap rapide doit afficher le palier suivant immédiatement. */}
                    {lastStep && (
                        <motion.p
                            key={revealedCount}
                            className="font-extrabold text-2xl"
                            style={{ color: lastStep.axis === "rarity" ? RARITY_TEXT[lastStep.id] : "#fde68a" }}
                            initial={{ opacity: 0, scale: 0.5, y: 6 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            transition={{ duration: 0.25 }}
                        >
                            {tierName(lastStep)} !
                        </motion.p>
                    )}
                    <p className="text-white/40 text-xs mt-2">Touchez pour révéler</p>
                </div>
            ) : (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center"
                >
                    <p className="text-white font-bold text-lg">{card.character_name}</p>
                    <p className="text-sm" style={{ color: rarityColor }}>
                        {card.rarity_name}
                        {card.specialty_id !== "normal" && ` • ${card.specialty_name}`}
                        {card.jewelry_id !== "none" && ` • ${card.jewelry_name}`}
                    </p>
                    <p className="text-white/40 text-xs mt-2">Touchez pour continuer</p>
                </motion.div>
            )}
        </div>
    );
}
