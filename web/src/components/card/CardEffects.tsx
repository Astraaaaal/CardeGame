import { useMemo } from "react";
import { motion } from "framer-motion";
import type { Card } from "@/types/card";
import { TIER_STEPS, tierLevel, type TierAxis } from "@/utils/cardTiers";
import CardImage from "./CardImage";

/**
 * Effets visuels par palier (rareté, bijou, spécialité, qualité), partagés
 * entre la révélation d'un booster (CardReveal) et le détail d'une carte.
 */

// Palette des effets (visuel pur, indépendante des couleurs d'affichage des cartes).
const RARITY_GLOW: Record<string, string> = { rare: "#3b9dff", epic: "#a855f7", legendary: "#fbbf24" };
const JEWELRY_SPARK: Record<string, string> = { silver: "#e2e8f0", gold: "#fcd34d", diamond: "#a5f3fc" };
export const RARITY_TEXT: Record<string, string> = { rare: "#7cc0ff", epic: "#c89bff", legendary: "#fcd34d" };

export interface Tier {
    id: string;
    level: number;
}

/** Palier atteint par la carte sur un axe (undefined si aucun effet). */
export function cardTier(card: Card, axis: TierAxis): Tier | undefined {
    const level = tierLevel(card, axis);
    return level ? { id: TIER_STEPS[axis][level - 1], level } : undefined;
}

/** Halo lumineux derrière la carte — rareté. */
export function RarityHalo({ tier }: { tier: Tier }) {
    const color = RARITY_GLOW[tier.id];
    return (
        <motion.div
            key={tier.id}
            className="absolute -inset-8 rounded-[2rem] pointer-events-none"
            style={{ background: `radial-gradient(circle, ${color}cc 0%, ${color}55 45%, transparent 72%)`, filter: "blur(18px)" }}
            initial={{ opacity: 0, scale: 0.7 }}
            animate={{ opacity: [0.55, 0.9 + tier.level * 0.03, 0.55], scale: [0.96, 1.04 + tier.level * 0.02, 0.96] }}
            transition={{ duration: (1.8 - tier.level * 0.25) * 2, repeat: Infinity, ease: "easeInOut" }}
        />
    );
}

/** Particules scintillantes autour de la carte — bijou. */
export function JewelrySparkles({ tier }: { tier: Tier }) {
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

/** Rayons tournants — full art. */
export function FullArtRays({ className = "" }: { className?: string }) {
    return (
        <motion.div
            className={`absolute pointer-events-none ${className}`}
            style={{ background: "repeating-conic-gradient(from 0deg, rgba(255,255,255,.55) 0deg 8deg, transparent 8deg 30deg)" }}
            animate={{ rotate: 360 }}
            transition={{ duration: 9, repeat: Infinity, ease: "linear" }}
        />
    );
}

/** Effet sur la carte — spécialité (full art : rayons, EX : bordure électrique, shiny : holographique). */
export function SpecialtyOverlay({ id }: { id: string }) {
    if (id === "full_art") {
        return <FullArtRays key={id} className="-inset-1/2 opacity-40" />;
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
                transition={{ duration: 1.4, repeat: Infinity }}
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
export function QualityStars({ level }: { level: number }) {
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

/** Carte face visible avec tous ses effets animés en continu (détail d'une carte). */
export function CardWithEffects({ card, className = "" }: { card: Card; className?: string }) {
    const rarity = cardTier(card, "rarity");
    const jewelry = cardTier(card, "jewelry");
    const specialty = cardTier(card, "specialty");
    const quality = cardTier(card, "quality");

    return (
        <div className={`flex flex-col items-center gap-2 ${className}`}>
            <div className="relative w-full aspect-[5/7]">
                {rarity && <RarityHalo tier={rarity} />}
                {/* Full art : rayons derrière la carte, pour ne pas masquer l'illustration. */}
                {specialty?.id === "full_art" && (
                    <div className="absolute -inset-6 rounded-[2rem] overflow-hidden pointer-events-none">
                        <FullArtRays className="-inset-1/2 opacity-30" />
                    </div>
                )}
                {jewelry && <JewelrySparkles tier={jewelry} />}
                <div className="absolute inset-0 rounded-xl overflow-hidden">
                    <CardImage card={card} size="lg" />
                    {specialty && specialty.id !== "full_art" && <SpecialtyOverlay id={specialty.id} />}
                </div>
            </div>
            {quality && <QualityStars level={quality.level} />}
        </div>
    );
}
