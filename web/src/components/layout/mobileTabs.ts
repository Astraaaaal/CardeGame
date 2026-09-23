/**
 * Les cinq écrans de la navigation téléphone, dans l'ordre où on les traverse
 * en glissant : la barre d'onglets et le geste mènent aux mêmes endroits, dans
 * le même ordre, pour que la barre enseigne le geste au lieu de le doubler.
 *
 * Glisser vers la gauche avance dans cette liste (accueil → activités), vers
 * la droite recule (accueil → collection).
 */

import type { FeatureKey } from "@/hooks/useUnlocks";

export interface MobileTab {
    path: string;
    label: string;
    icon: string;
    feature?: FeatureKey;
}

export const MOBILE_TABS: MobileTab[] = [
    { path: "/shop", label: "Boutique", icon: "🛒" },
    { path: "/collection", label: "Collection", icon: "🃏" },
    { path: "/", label: "Accueil", icon: "🏠" },
    { path: "/activities", label: "Activités", icon: "🎲", feature: "workshop" },
    { path: "/guild", label: "Guilde", icon: "🛡️", feature: "guild_join" },
];

export function tabIndexOf(pathname: string): number {
    return MOBILE_TABS.findIndex((t) => t.path === pathname);
}
