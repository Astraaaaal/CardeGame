import { useMemo } from "react";
import { motion } from "framer-motion";
import type { Card } from "@/types/card";
import { TIER_STEPS, isPolishedCard, tierLevel, type TierAxis } from "@/utils/cardTiers";
import { useTypes, typeColor } from "@/hooks/useTypes";
import TiltCard, { MAX_DEG, useTilt } from "./TiltCard";
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

/** Reflet lumineux fin, en diagonale, qui balaye la carte — cartes pas tout à
 * fait ordinaires (cf. isPolishedCard). */
export function DiagonalSheen() {
    return (
        <motion.div
            className="absolute -inset-1/2 pointer-events-none mix-blend-screen"
            style={{
                background: "linear-gradient(138deg, transparent 46%, rgba(255,255,255,.55) 50%, transparent 54%)",
                backgroundSize: "300% 300%",
            }}
            animate={{ backgroundPosition: ["100% 100%", "0% 0%"] }}
            transition={{ duration: 3.4, repeat: Infinity, ease: "easeInOut", repeatDelay: 1.4 }}
        />
    );
}

/** Contour lumineux qui fait le tour de la carte, dans la couleur du type — full art. */
export function TypeOutline({ color }: { color: string }) {
    return (
        <motion.div
            className="absolute -inset-[3px] rounded-[14px] pointer-events-none"
            style={{
                background: `conic-gradient(from var(--outline-angle), transparent 0deg 300deg, ${color} 342deg, transparent 360deg)`,
                WebkitMask: "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
                WebkitMaskComposite: "xor",
                maskComposite: "exclude",
                padding: 3,
            }}
            animate={{ "--outline-angle": ["0deg", "360deg"] } as never}
            transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
        />
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
        // Pendant la révélation, la carte est encore face cachée : les rayons
        // habillent le dos (le contour coloré, lui, arrive avec la face visible).
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
    const { data: types } = useTypes();

    return (
        <div className={`flex flex-col items-center gap-2 ${className}`}>
            <TiltCard className="relative w-full aspect-[5/7]">
                {rarity && <RarityHalo tier={rarity} />}
                {jewelry && <JewelrySparkles tier={jewelry} />}
                <div className="absolute inset-0 rounded-xl overflow-hidden">
                    <CardImage card={card} size="lg" />
                    {specialty && specialty.id !== "full_art" && <SpecialtyOverlay id={specialty.id} />}
                    {isPolishedCard(card) && <DiagonalSheen />}
                </div>
                {specialty?.id === "full_art" && <TypeOutline color={typeColor(types, card.character_type)} />}
            </TiltCard>
            {quality && <QualityStars level={quality.level} />}
        </div>
    );
}

/**
 * Indice au dos d'une carte pendant la révélation : invisible à plat, une
 * lueur apparaît sur le bord côté doigt quand on incline la carte. Sa couleur
 * et son intensité trahissent la meilleure caractéristique encore cachée.
 */
const HINT_COLORS: Record<string, string> = {
    rare: "#3b9dff", epic: "#a855f7", legendary: "#fbbf24",
    silver: "#e2e8f0", gold: "#facc15", diamond: "#a5f3fc", prismatic: "rainbow",
    full_art: "#f472b6", ex: "#fb923c", shiny: "rainbow",
    excellent: "#86efac", graded: "#4ade80", mint: "#34d399", authentic: "#10b981",
};
const RAINBOW = "#f87171, #facc15, #4ade80, #60a5fa, #c084fc";

export function BackEdgeHint({ hint }: { hint: { id: string; strength: number } | null }) {
    const { x, y } = useTilt();
    if (!hint) return null;
    const amount = Math.min(1, Math.hypot(x, y) / MAX_DEG);
    // Côté vers lequel pointe le doigt (0deg = haut, 90deg = droite).
    const angle = (Math.atan2(y, x) * 180) / Math.PI;
    const color = HINT_COLORS[hint.id] ?? "#ffffff";
    const stops = color === "rainbow" ? RAINBOW : `${color}, ${color}`;
    return (
        <div
            className="absolute -inset-[3px] rounded-[18px] pointer-events-none"
            style={{
                background: `linear-gradient(${angle}deg, transparent 35%, ${stops})`,
                WebkitMask: "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
                WebkitMaskComposite: "xor",
                maskComposite: "exclude",
                padding: 3,
                opacity: amount * Math.min(1, 0.35 + 0.15 * hint.strength),
                filter: `drop-shadow(0 0 ${4 + hint.strength * 2}px ${color === "rainbow" ? "#ffffff" : color})`,
                transition: "opacity 0.2s",
            }}
        />
    );
}

const HINT_STRENGTH: Record<string, number> = {
    rare: 1, epic: 2, legendary: 4,
    silver: 1, gold: 2, diamond: 3, prismatic: 4,
    full_art: 2, ex: 3, shiny: 4,
    excellent: 1, graded: 2, mint: 3, authentic: 4,
};

/** Meilleure caractéristique parmi celles pas encore dévoilées (null si aucune). */
export function bestHiddenTier(hidden: { id: string }[]): { id: string; strength: number } | null {
    let best: { id: string; strength: number } | null = null;
    for (const step of hidden) {
        const strength = HINT_STRENGTH[step.id] ?? 1;
        if (!best || strength > best.strength) best = { id: step.id, strength };
    }
    return best;
}
