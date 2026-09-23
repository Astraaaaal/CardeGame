import { motion, useReducedMotion } from "framer-motion";

/**
 * Flamme de la série de connexion. Elle change de matière par paliers : plus
 * la série est longue, plus la flamme est chaude — braise grise, flamme
 * orange, feu rouge, cœur bleu, puis or. Le joueur voit sa constance sans
 * lire le chiffre.
 */
const TIERS = [
    { min: 1, top: "#d1d5db", bottom: "#9ca3af", glow: "rgba(156,163,175,0)" },
    { min: 3, top: "#fcd34d", bottom: "#f97316", glow: "rgba(249,115,22,0.35)" },
    { min: 7, top: "#fdba74", bottom: "#ef4444", glow: "rgba(239,68,68,0.45)" },
    { min: 14, top: "#bfdbfe", bottom: "#6366f1", glow: "rgba(99,102,241,0.5)" },
    { min: 30, top: "#fffbeb", bottom: "#f5d67b", glow: "rgba(245,214,123,0.65)" },
];

export function tierOf(streak: number) {
    return TIERS.reduce((best, tier) => (streak >= tier.min ? tier : best), TIERS[0]);
}

interface StreakFlameProps {
    streak: number;
    size?: number;
    /** Rejoue l'apparition (montée en flamme) — à chaque connexion. */
    animateOnMount?: boolean;
}

export default function StreakFlame({ streak, size = 18, animateOnMount = true }: StreakFlameProps) {
    const reduced = useReducedMotion();
    const tier = tierOf(streak);
    const gradientId = `flame-${tier.min}`;

    return (
        <motion.svg
            width={size} height={size} viewBox="0 0 24 24" aria-hidden
            style={{ filter: `drop-shadow(0 0 ${size / 4}px ${tier.glow})` }}
            initial={animateOnMount && !reduced ? { scale: 0.4, opacity: 0, y: 4 } : false}
            animate={reduced
                ? { scale: 1, opacity: 1, y: 0 }
                // Apparition, puis vacillement continu : une flamme ne tient pas en place.
                : { scale: [0.4, 1.15, 1], opacity: 1, y: 0, scaleY: [0.4, 1.15, 1, 1.05, 1] }}
            transition={reduced ? { duration: 0 } : {
                duration: 0.6, times: [0, 0.55, 0.8, 0.9, 1], ease: "easeOut",
            }}
        >
            <defs>
                <linearGradient id={gradientId} x1="0" y1="1" x2="0" y2="0">
                    <stop offset="0%" stopColor={tier.bottom} />
                    <stop offset="100%" stopColor={tier.top} />
                </linearGradient>
            </defs>
            {/* Flamme : base large, pointe recourbée. */}
            <path
                d="M12 2c1.8 3.2 1 5-.6 6.6-1.4 1.4-3.4 2.9-3.4 5.6A6 6 0 0 0 18 14c0-2.4-1-3.8-2.2-5.2.2 1.4-.4 2.3-1.2 2.7.7-2.6-.3-5.4-2.6-9.5Z"
                fill={`url(#${gradientId})`}
            />
            {/* Cœur clair : donne le relief sans dessiner de contour. */}
            <path d="M12 12.5c1.2 1 1.6 1.9 1.6 2.7a1.7 1.7 0 0 1-3.3 0c0-.9.6-1.8 1.7-2.7Z"
                fill={tier.top} fillOpacity="0.85" />
        </motion.svg>
    );
}
