import { useMemo, useState } from "react";
import { motion, AnimatePresence, useAnimationControls } from "framer-motion";
import type { Card } from "@/types/card";
import { useProbabilities } from "@/hooks/useCollection";
import { suspenseSteps, type SuspenseStep, type TierAxis } from "@/utils/cardTiers";
import CardImage from "./CardImage";

interface CardRevealProps {
    card: Card;
    onNext: () => void;
}

// Palette des effets (visuel pur, indépendante des couleurs d'affichage des cartes).
const RARITY_GLOW: Record<string, string> = { rare: "#3b9dff", epic: "#a855f7", legendary: "#fbbf24" };
const JEWELRY_SPARK: Record<string, string> = { silver: "#e2e8f0", gold: "#fcd34d", diamond: "#a5f3fc" };
const RARITY_TEXT: Record<string, string> = { rare: "#7cc0ff", epic: "#c89bff", legendary: "#fcd34d" };

function rarityColorToCSS(color: number[]): string {
    return `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
}

/** Dernier palier dévoilé sur un axe (undefined si aucun). */
function currentTier(revealed: SuspenseStep[], axis: TierAxis): { id: string; level: number } | undefined {
    const onAxis = revealed.filter((s) => s.axis === axis);
    return onAxis.length ? { id: onAxis[onAxis.length - 1].id, level: onAxis.length } : undefined;
}

/** Halo lumineux derrière la carte — rareté. */
function RarityHalo({ tier }: { tier: { id: string; level: number } }) {
    const color = RARITY_GLOW[tier.id];
    return (
        <motion.div
            key={tier.id}
            className="absolute -inset-8 rounded-[2rem] pointer-events-none"
            style={{ background: `radial-gradient(circle, ${color}cc 0%, ${color}55 45%, transparent 72%)`, filter: "blur(18px)" }}
            initial={{ opacity: 0, scale: 0.7 }}
            animate={{ opacity: [0.55, 0.9 + tier.level * 0.03, 0.55], scale: [0.96, 1.04 + tier.level * 0.02, 0.96] }}
            transition={{ duration: 1.8 - tier.level * 0.25, repeat: Infinity, ease: "easeInOut" }}
        />
    );
}

/** Particules scintillantes autour de la carte — bijou. */
function JewelrySparkles({ tier }: { tier: { id: string; level: number } }) {
    const count = 6 + tier.level * 3;
    const sparks = useMemo(() => Array.from({ length: count }, (_, i) => {
        const angle = (i / count) * Math.PI * 2;
        const radius = 54 + ((i * 37) % 14);
        return {
            left: `${50 + Math.cos(angle) * radius}%`,
            top: `${50 + Math.sin(angle) * (radius + 6)}%`,
            size: 10 + ((i * 7) % 8),
            delay: (i * 0.23) % 1.6,
            color: tier.id === "prismatic" ? `hsl(${(i * 360) / count}, 95%, 72%)` : JEWELRY_SPARK[tier.id],
        };
    }), [count, tier.id]);

    return (
        <div className="absolute inset-0 pointer-events-none">
            {sparks.map((s, i) => (
                <motion.span
                    key={`${tier.id}-${i}`}
                    className="absolute -translate-x-1/2 -translate-y-1/2 leading-none"
                    style={{ left: s.left, top: s.top, fontSize: s.size, color: s.color, textShadow: `0 0 8px ${s.color}` }}
                    animate={{ opacity: [0, 1, 0], scale: [0.4, 1.2, 0.4], rotate: [0, 90] }}
                    transition={{ duration: 1.6, delay: s.delay, repeat: Infinity, ease: "easeInOut" }}
                >
                    ✦
                </motion.span>
            ))}
        </div>
    );
}

/** Effet sur le dos de la carte — spécialité (full art : rayons, EX : bordure électrique, shiny : holographique). */
function SpecialtyOverlay({ id }: { id: string }) {
    if (id === "full_art") {
        return (
            <motion.div
                key={id}
                className="absolute -inset-1/2 pointer-events-none opacity-40"
                style={{ background: "repeating-conic-gradient(from 0deg, rgba(255,255,255,.55) 0deg 8deg, transparent 8deg 30deg)" }}
                animate={{ rotate: 360 }}
                transition={{ duration: 9, repeat: Infinity, ease: "linear" }}
            />
        );
    }
    if (id === "ex") {
        return (
            <motion.div
                key={id}
                className="absolute inset-0 rounded-2xl pointer-events-none border-2"
                style={{ borderColor: "#facc15" }}
                animate={{
                    boxShadow: [
                        "inset 0 0 8px #facc15, 0 0 6px #facc15",
                        "inset 0 0 22px #fde047, 0 0 20px #38bdf8",
                        "inset 0 0 8px #facc15, 0 0 6px #facc15",
                    ],
                }}
                transition={{ duration: 0.7, repeat: Infinity }}
            />
        );
    }
    return (
        <motion.div
            key={id}
            className="absolute inset-y-0 -inset-x-full pointer-events-none mix-blend-screen"
            style={{
                background: "linear-gradient(115deg, transparent 30%, rgba(255,0,128,.45), rgba(255,200,0,.45), rgba(0,255,170,.45), rgba(0,140,255,.45), rgba(180,0,255,.45), transparent 70%)",
            }}
            animate={{ x: ["-30%", "30%"] }}
            transition={{ duration: 1.8, repeat: Infinity, repeatType: "reverse", ease: "easeInOut" }}
        />
    );
}

/** Étoiles sous la carte — qualité (1 à 4). */
function QualityStars({ level }: { level: number }) {
    return (
        <div className="flex gap-1.5 justify-center h-6">
            {Array.from({ length: level }, (_, i) => (
                <motion.span
                    key={i}
                    className="text-xl leading-none"
                    style={{ color: "#fde68a", textShadow: "0 0 10px #fbbf24" }}
                    initial={{ scale: 0, rotate: -90 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={{ type: "spring", stiffness: 400, damping: 14 }}
                >
                    ★
                </motion.span>
            ))}
        </div>
    );
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
    const shake = useAnimationControls();

    const revealed = steps.slice(0, revealedCount);
    const rarity = currentTier(revealed, "rarity");
    const jewelry = currentTier(revealed, "jewelry");
    const specialty = currentTier(revealed, "specialty");
    const quality = currentTier(revealed, "quality");
    const lastStep = revealed[revealed.length - 1];

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
            <div className="relative w-56 aspect-[5/7]" style={{ perspective: "1000px" }}>
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
                                <CardImage card={card} size="lg" />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.div>
            </div>

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
