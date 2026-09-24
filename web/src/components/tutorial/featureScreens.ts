import type { FeatureKey } from "@/hooks/useUnlocks";

/**
 * Où chaque fonctionnalité s'explique.
 *
 * Une bulle qui annonce « Roue de la fortune » pendant qu'on ouvre un booster
 * ne veut rien dire. L'explication attend qu'on arrive sur l'écran concerné,
 * et se lit alors en regardant la chose.
 *
 * Les fonctionnalités sans écran à elles (cadeaux, échanges — un panneau, pas
 * une page) s'annoncent à l'accueil, qui est le point de passage de tous.
 */
export const FEATURE_SCREENS: Record<string, FeatureKey[]> = {
    "/": ["presence_luck", "absence_chest", "gifts", "trades"],
    "/activities": ["workshop", "expeditions", "wheel", "higher_lower", "machine", "converter", "rerolls"],
    "/shop": ["resource_shop"],
    "/leaderboard": ["leaderboard"],
    "/guild": ["guild_join", "guild_create"],
    "/profile": ["showcase", "listings"],
};

/** Fonctionnalités à expliquer sur cet écran (chemin exact). */
export const featuresForScreen = (pathname: string): FeatureKey[] =>
    FEATURE_SCREENS[pathname] ?? [];
